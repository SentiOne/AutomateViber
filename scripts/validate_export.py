#!/usr/bin/env python3
"""Validate an unpacked SentiOne Automate export against the repository checklist.

Usage: python3 scripts/validate_export.py <unpacked export dir> [--no-regex]

Checks (see AGENTS.md "Validation Checklist Before Re-Zipping"):
  - flows/*.json against flows.schema.json, integrations.json against integrations.schema.json
  - mainFlowId / defaultNluId / errorHandlingContextRef / conversationEndingContextRef resolve
  - unique ids, transitions go output.id -> state.id inside one context
  - every output (except redirect/terminate/end states) has exactly one transition
  - context / integration / request references resolve
  - `empty` states carry requestUserInput (platform requires it, see playbook B9)
  - phrases.csv rows: 5 columns, intent exists, tokens match the utterance (playbook E0)
  - test files start with `> *` or `> ` user turn and are listed in data.json
  - routing `empty` blocks (several outputs / conditions) do not carry isEmptyPoint / isQuickPoint (canvas loses the connectors)
  - context `model` carries name / uuid (= context uuid) / notes (warning for the x/y-only starter shape)
  - regular expressions in flow blocks (warning; an error with --no-regex)
  - an unconnected output of a `context` block fed only by a `start` block is the Global Listener parent tree: allowed
"""
import csv
import json
import os
import sys

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def main(root, no_regex=False):
    errors = []
    warnings = []

    def err(msg):
        errors.append(msg)

    project = json.load(open(os.path.join(root, "project.json"), encoding="utf-8"))
    flows = {}
    for fn in sorted(os.listdir(os.path.join(root, "flows"))):
        flows[fn] = json.load(open(os.path.join(root, "flows", fn), encoding="utf-8"))
    if jsonschema:
        schema = json.load(open(os.path.join(REPO, "flows.schema.json"), encoding="utf-8"))
        for fn, f in flows.items():
            for e in jsonschema.Draft202012Validator(schema).iter_errors(f):
                err("flows/%s schema: %s at %s" % (fn, e.message[:160], "/".join(map(str, e.path))))
        integ_path = os.path.join(root, "integrations.json")
        isch = json.load(open(os.path.join(REPO, "integrations.schema.json"), encoding="utf-8"))
        for e in jsonschema.Draft202012Validator(isch).iter_errors(json.load(open(integ_path, encoding="utf-8"))):
            err("integrations schema: %s at %s" % (e.message[:160], "/".join(map(str, e.path))))
    else:
        print("WARN: jsonschema not installed, schema validation skipped")

    integ = json.load(open(os.path.join(root, "integrations.json"), encoding="utf-8"))
    integ_reqs = {(i["referenceName"], r["referenceName"]) for i in integ for r in i["requests"]}
    nlu_refs = set()
    nlu_root = os.path.join(root, "nlu")
    for d in os.listdir(nlu_root):
        nlu_refs.add(json.load(open(os.path.join(nlu_root, d, "data.json"), encoding="utf-8"))["referenceName"])

    flow_refs = {f["referenceName"] for f in flows.values()}
    if project["mainFlowId"] not in flow_refs:
        err("project.mainFlowId does not point to a flow referenceName")
    for fn, f in flows.items():
        if f["defaultNluId"] not in nlu_refs:
            err("%s: defaultNluId does not resolve" % fn)
        ctx_refs = {c["referenceName"] for c in f["contexts"]}
        for key in ("errorHandlingContextRef", "conversationEndingContextRef"):
            if f.get(key) and f[key] not in ctx_refs:
                err("%s: %s does not resolve" % (fn, key))
        all_ids = set()
        for c in f["contexts"]:
            m = c["model"]
            states = {s["id"]: s for s in m["states"]}
            outs = {}
            for s in m["states"]:
                for idv in [s["id"]] + [o["id"] for o in s["outputs"]]:
                    if idv in all_ids:
                        err("%s/%s: duplicate id %s" % (fn, c["name"], idv))
                    all_ids.add(idv)
                for o in s["outputs"]:
                    outs[o["id"]] = s
                if s["type"] == "empty" and (s.get("isEmptyPoint") or s.get("isQuickPoint")) and (len(s["outputs"]) > 1 or any(o["conditions"] for o in s["outputs"])):
                    err("%s/%s/%s: routing empty block flagged isEmptyPoint/isQuickPoint (canvas shows no connectors)" % (fn, c["name"], s["name"]))
                if s["type"] == "empty" and "requestUserInput" not in s:
                    err("%s/%s/%s: empty state without requestUserInput" % (fn, c["name"], s["name"]))
                if s["type"] == "context" and s["contextReferenceName"] not in ctx_refs:
                    err("%s/%s/%s: contextReferenceName unresolved" % (fn, c["name"], s["name"]))
                if s["type"] == "Integration" and (s["integrationReferenceName"], s["requestReferenceName"]) not in integ_reqs:
                    err("%s/%s/%s: integration/request unresolved" % (fn, c["name"], s["name"]))
            if "uuid" not in m or m.get("uuid") != c["uuid"] or "notes" not in m or "name" not in m:
                warnings.append("%s/%s: context model is not {name, uuid, notes, states, transitions}" % (fn, c["name"]))
            blocks = []
            for s in m["states"]:
                memory = s.get("memory", {})
                if isinstance(memory, dict):  # older exports store `memory` as a list
                    blocks += [v.get("value", "") for v in memory.values() if isinstance(v, dict)]
                for o in s["outputs"]:
                    for cd in o["conditions"]:
                        blocks += [cd["left"]["value"], cd["right"]["value"]]
                params = s.get("inputParameters", {})
                if isinstance(params, dict):
                    blocks += [v.get("value", "") for v in params.values() if isinstance(v, dict)]
            for text in blocks:
                if isinstance(text, str) and any(token in text for token in (".test(", ".match(", "RegExp", "replace(/", "split(/")):
                    (err if no_regex else warnings.append)("%s/%s: regular expression in a flow block: %s" % (fn, c["name"], text[:60].replace("\n", " ")))
                    break
            count = {}
            for t in m["transitions"]:
                if t["from"] not in outs:
                    err("%s/%s: transition from unknown output %s" % (fn, c["name"], t["from"]))
                if t["to"] not in states:
                    err("%s/%s: transition to unknown state %s" % (fn, c["name"], t["to"]))
                count[t["from"]] = count.get(t["from"], 0) + 1
            for oid, s in outs.items():
                n = count.get(oid, 0)
                if n > 1:
                    err("%s/%s/%s: output wired %d times" % (fn, c["name"], s["name"], n))
                if n == 0 and s["type"] != "redirect":
                    fed_by_start = s["type"] == "context" and any(
                        t["to"] == s["id"] and any(o2["id"] == t["from"] for st in m["states"] if st["type"] == "start" for o2 in st["outputs"])
                        for t in m["transitions"])
                    if not fed_by_start:  # Global Listener parent tree keeps its output unconnected on purpose
                        err("%s/%s/%s: output without transition" % (fn, c["name"], s["name"]))
            targets = {t["to"] for t in m["transitions"]}
            for s in m["states"]:
                if s["type"] != "start" and s["id"] not in targets:
                    err("%s/%s/%s: state has no incoming transition" % (fn, c["name"], s["name"]))
                if s["type"] == "start" and s["id"] in targets:
                    err("%s/%s/%s: start has incoming transition" % (fn, c["name"], s["name"]))
            for s in m["states"]:
                if s["type"] in ("say", "say-conditional", "custom") and len(s["outputs"]) == 0:
                    err("%s/%s/%s: no outputs" % (fn, c["name"], s["name"]))

    for d in os.listdir(nlu_root):
        base = os.path.join(nlu_root, d)
        intents = {r[0] for r in csv.reader(open(os.path.join(base, "intents.csv"), encoding="utf-8")) if r}
        for i, row in enumerate(csv.reader(open(os.path.join(base, "phrases.csv"), encoding="utf-8")), 1):
            if len(row) != 5:
                err("phrases.csv row %d: %d columns" % (i, len(row)))
                continue
            utt, intent, toks = row[0], row[1], json.loads(row[2])
            if intent not in intents:
                err("phrases.csv row %d: unknown intent %s" % (i, intent))
            if utt and not toks:
                err("phrases.csv row %d: empty tokens" % i)
            for t in toks:
                if utt[t["indices"]["startIndex"] : t["indices"]["endIndex"]] != t["value"]:
                    err("phrases.csv row %d: token offsets" % i)

    ts_root = os.path.join(root, "testSuites")
    if os.path.isdir(ts_root):
        for d in os.listdir(ts_root):
            data = json.load(open(os.path.join(ts_root, d, "data.json"), encoding="utf-8"))
            for tc in data["testcases"]:
                p = os.path.join(ts_root, d, tc["filename"] + ".txt")
                if not os.path.exists(p):
                    err("test file missing: %s" % p)
                    continue
                first = open(p, encoding="utf-8").readline()
                if not first.startswith(">"):
                    err("test %s does not start with a user turn" % tc["filename"])

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print("%d error(s), %d warning(s)" % (len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], no_regex="--no-regex" in sys.argv[2:]))
