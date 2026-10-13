# Contributing

Contributions are welcome. Before opening a pull request, there is one thing
about this repository you need to know, because it changes how your change
gets in.

## This repository is a published snapshot

The source of truth is an internal SentiOne repository. What you see here is a
filtered snapshot of it, pushed periodically as a single commit:

```
Sync from internal repository @ <revision> (<date>)
```

The sync is **one-way**. Nothing travels from GitHub back to the internal
repository automatically, which means **we do not press the Merge button**: a
change merged here would be silently overwritten by the next snapshot and would
show up as an unexplained deletion. Instead:

1. You open a pull request. We review and discuss it here, in the open.
2. If we accept it, we apply the change to the internal repository, preserving
   your authorship on the commit.
3. We close the pull request with a note, and the change arrives with the next
   snapshot.

Nothing is lost along the way — it is bookkeeping, not a judgement on the
change. But it does mean:

- **Keep pull requests small and focused.** A sprawling PR is harder to
  re-apply, and it will sit longer.
- **Do not build long-lived work on a pull-request branch.** Rebase onto the
  default branch after each snapshot lands.

## Licensing of contributions

This project is licensed under the Apache License 2.0. Under section 5 of that
licence, anything you deliberately submit for inclusion is licensed under the
same terms, with no additional conditions. There is no CLA to sign.

If you cannot make that grant — for instance your employer owns the copyright
and has not cleared it — say so in the pull request instead of submitting
anyway.

## What is useful here

- **Corrections to the rules in `AGENTS.md` and
  `AUTOMATE_EXPORT_PLAYBOOK.md`.** This repository's value is that its rules
  were verified on a live platform rather than inferred. If platform behaviour
  differs from what is written here, that is the most valuable report we can
  get — say which Automate version you saw it on and how you confirmed it.
- **Helper scripts** in `scripts/`, or improvements to the existing ones.
- **Fixes to `flows.schema.json` / `integrations.schema.json`** where a real
  export is rejected by a schema that should accept it, or accepted by one that
  should not.
- **Documentation and wording fixes**, including in the agent skills.

## What will not be accepted

- **Unverified claims about platform behaviour.** A rule that merely sounds
  right is worse than no rule, because an agent will follow it.
- **Reference exports containing real material** — client names, real people in
  `createdBy`/`updatedBy`, credentials, production URLs, personal data of any
  kind. Everything in a reference project must be fictional.
- **A copy of the product documentation.** This repository deliberately does
  not ship one; it points at <https://automate.help.sentione.com>, which is
  maintained separately and does not go stale here.

## Reporting a problem

Ordinary bugs and questions: open an issue.

If you find something that should not be public — a credential, personal data,
a real client's name in a reference export — **do not open a public issue**.
Use GitHub's private vulnerability reporting ("Report a vulnerability" on the
Security tab) so it can be fixed before it is pointed at.
