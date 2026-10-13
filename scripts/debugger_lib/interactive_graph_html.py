from __future__ import annotations

import json
from pathlib import Path


CYTOSCAPE_CDN_URL = "https://cdn.jsdelivr.net/npm/cytoscape@3.34.0/dist/cytoscape.min.js"
OPEN_SANS_STYLESHEET_URL = "https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap"


def _load_logo_svg() -> str:
    logo_path = Path(__file__).with_name("img") / "logo_en_15_dark.svg"
    try:
        return logo_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "<div style='font-weight:800;font-size:20px;'>SentiOne Automate</div>"


def write_interactive_graph_html(
    *,
    output_path: Path,
    title: str,
    graph_kind_label: str,
    node_metric_label: str,
    node_metric_key: str,
    total_sessions: int,
    total_nodes: int,
    total_edges: int,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    sample_conversations: dict[str, object] | None = None,
    sample_sessions: dict[str, object] | None = None,
) -> None:
    def is_number(value: object) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    has_drop_rate_nodes = any(is_number(node.get("dropRate")) for node in nodes)
    has_fallback_rate_nodes = any(is_number(node.get("fallbackRate")) for node in nodes)
    if has_drop_rate_nodes:
        node_border_metric = {
            "key": "dropRate",
            "title": "Tag drop rate border",
            "note": "Higher tag drop rate makes the node border redder and thicker. Purple means low drop rate; red means users often stop after this tag.",
        }
    elif has_fallback_rate_nodes:
        node_border_metric = {
            "key": "fallbackRate",
            "title": "Block fallback rate border",
            "note": "Higher fallback rate makes the node border redder and thicker. Purple means low fallback rate; red means users often repeat answers in this block.",
        }
    else:
        node_border_metric = None

    payload = {
        "title": title,
        "graphKindLabel": graph_kind_label,
        "nodeMetricLabel": node_metric_label,
        "nodeMetricKey": node_metric_key,
        "nodeBorderMetric": node_border_metric,
        "summary": {
            "totalSessions": total_sessions,
            "totalNodes": total_nodes,
            "totalEdges": total_edges,
        },
        "nodes": nodes,
        "edges": edges,
        "sampleConversations": sample_conversations or {},
        "sampleSessions": sample_sessions or {},
    }
    logo_svg = _load_logo_svg()
    node_border_legend_html = (
        f"""
        <div class="node-border-legend" id="node-border-legend" hidden>
          <div class="node-border-title">{node_border_metric["title"]}</div>
          <div class="node-border-scale" aria-hidden="true"></div>
          <div class="node-border-ticks">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
          <div class="node-border-note">
            {node_border_metric["note"]}
          </div>
        </div>"""
        if node_border_metric is not None
        else ""
    )
    legend_section_html = (
        f"""
      <section class="section">
        <h2>Legend</h2>
        {node_border_legend_html}
      </section>"""
        if node_border_legend_html
        else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{OPEN_SANS_STYLESHEET_URL}" rel="stylesheet">
  <style>
    :root {{
      --bg: #eaf3ff;
      --bg-2: #dbe9ff;
      --panel: rgba(244, 249, 255, 0.97);
      --ink: #162235;
      --muted: #5f6f86;
      --line: #c9d8ec;
      --accent: #285ea8;
      --accent-2: #7C6DFD;
      --accent-3: #49a6ff;
      --warn: #c05621;
      --shadow: 0 22px 44px rgba(36, 79, 145, 0.14);
      --font-sans: "Open Sans", "Segoe UI", sans-serif;
      --font-mono: "SFMono-Regular", "Consolas", monospace;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      height: 100vh;
      overflow: hidden;
      min-height: 100vh;
      font-family: var(--font-sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(73, 166, 255, 0.18), transparent 30%),
        radial-gradient(circle at bottom right, rgba(124, 109, 253, 0.14), transparent 28%),
        linear-gradient(135deg, #f7fbff 0%, var(--bg) 52%, var(--bg-2) 100%);
    }}

    .shell {{
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      height: 100vh;
      min-height: 0;
      overflow: hidden;
    }}

    .sidebar {{
      padding: 22px 20px;
      background: var(--panel);
      border-right: 1px solid var(--line);
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 18px;
      z-index: 1;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
    }}

    .hero {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}

    .brandmark {{
      display: inline-flex;
      align-items: center;
      width: fit-content;
      padding: 10px 12px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.84);
      border: 1px solid rgba(124, 109, 253, 0.18);
      box-shadow: 0 10px 28px rgba(40, 94, 168, 0.08);
    }}

    .brandmark svg {{
      display: block;
      width: 170px;
      height: auto;
    }}

    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--accent-2);
      font-weight: 700;
    }}

    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.05;
    }}

    .summary {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
    }}

    .stat {{
      padding: 12px;
      border: 1px solid rgba(124, 109, 253, 0.16);
      border-radius: 14px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(240, 247, 255, 0.86));
    }}

    .stat-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      margin-bottom: 4px;
    }}

    .stat-value {{
      font-size: 20px;
      font-weight: 700;
    }}

    .section {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .section h2 {{
      margin: 0;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}

    .field {{
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}

    label {{
      font-size: 13px;
      font-weight: 600;
    }}

    input[type="search"],
    input[type="number"],
    select {{
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.92);
      color: var(--ink);
      font: inherit;
    }}

    input[type="search"]:focus,
    input[type="number"]:focus,
    select:focus {{
      outline: 2px solid rgba(124, 109, 253, 0.22);
      outline-offset: 1px;
      border-color: rgba(124, 109, 253, 0.45);
    }}

    input[type="range"] {{
      width: 100%;
      accent-color: var(--accent-2);
    }}

    .range-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 82px;
      gap: 10px;
      align-items: center;
    }}

    .actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}

    button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      background: linear-gradient(135deg, var(--accent-2), #5f9dff);
      color: white;
      box-shadow: 0 10px 22px rgba(124, 109, 253, 0.24);
    }}

    button.secondary {{
      background: #edf3ff;
      color: var(--ink);
      box-shadow: none;
    }}

    .legend {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.45;
    }}

    .node-border-legend {{
      margin-top: 12px;
      padding: 12px;
      border-radius: 14px;
      border: 1px solid rgba(124, 109, 253, 0.16);
      background: rgba(255, 255, 255, 0.66);
    }}

    .node-border-legend[hidden] {{
      display: none;
    }}

    .node-border-title {{
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 800;
      color: var(--ink);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .node-border-scale {{
      height: 10px;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent-2) 0%, #f59e0b 50%, #dc2626 100%);
      box-shadow: inset 0 0 0 1px rgba(22, 34, 53, 0.10);
    }}

    .node-border-ticks {{
      display: flex;
      justify-content: space-between;
      margin-top: 5px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--muted);
    }}

    .node-border-note {{
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
    }}

    .details {{
      border: 1px solid rgba(124, 109, 253, 0.12);
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(239, 246, 255, 0.88));
      padding: 14px;
      min-height: 180px;
      overflow: auto;
    }}

    .details h3 {{
      margin: 0 0 10px 0;
      font-size: 18px;
    }}

    .details dl {{
      margin: 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 8px;
    }}

    .details dt {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}

    .metric-heading {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}

    .details dd {{
      margin: 2px 0 0 0;
      font-family: var(--font-mono);
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .details-section {{
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
    }}

    .details-section summary {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      cursor: pointer;
      list-style: none;
      margin: 0;
      padding: 2px 0;
    }}

    .details-section summary::-webkit-details-marker {{
      display: none;
    }}

    .details-section summary::after {{
      content: '+';
      flex: 0 0 auto;
      font-size: 16px;
      line-height: 1;
      color: var(--accent-2);
      font-weight: 700;
    }}

    .details-section[open] summary::after {{
      content: '−';
    }}

    .details-section h4 {{
      margin: 0;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }}

    .section-heading {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }}

    .section-help-wrap {{
      display: inline-flex;
      align-items: center;
      flex: 0 0 auto;
    }}

    .section-help {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border-radius: 999px;
      border: 1px solid rgba(124, 109, 253, 0.28);
      background: rgba(124, 109, 253, 0.10);
      color: var(--accent-2);
      font-size: 11px;
      font-weight: 800;
      line-height: 1;
      cursor: help;
      outline: none;
    }}

    .section-help:focus-visible {{
      box-shadow: 0 0 0 3px rgba(124, 109, 253, 0.18);
    }}

    .section-help-floating {{
      position: fixed;
      width: 270px;
      max-width: min(270px, calc(100vw - 32px));
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(124, 109, 253, 0.18);
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(238, 245, 255, 0.96));
      box-shadow: 0 18px 36px rgba(27, 53, 98, 0.18);
      color: var(--ink);
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transition: opacity 140ms ease, visibility 140ms ease;
      z-index: 200;
    }}

    .section-help-floating.is-visible {{
      opacity: 1;
      visibility: visible;
    }}

    .section-help-floating[data-placement="right"]::before,
    .section-help-floating[data-placement="left"]::before {{
      content: '';
      position: absolute;
      top: 50%;
      width: 14px;
      height: 14px;
      transform: translateY(-50%) rotate(45deg);
      background: rgba(248, 251, 255, 0.98);
    }}

    .section-help-floating[data-placement="right"]::before {{
      left: -7px;
      border-left: 1px solid rgba(124, 109, 253, 0.18);
      border-bottom: 1px solid rgba(124, 109, 253, 0.18);
    }}

    .section-help-floating[data-placement="left"]::before {{
      right: -7px;
      border-top: 1px solid rgba(124, 109, 253, 0.18);
      border-right: 1px solid rgba(124, 109, 253, 0.18);
    }}

    .section-help-title {{
      display: block;
      margin: 0 0 6px 0;
      font-size: 12px;
      font-weight: 800;
      color: var(--accent-2);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}

    .section-help-body {{
      display: block;
      font-size: 13px;
      line-height: 1.45;
      color: var(--ink);
    }}

    .details-list {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}

    .details-list-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: start;
      border: 1px solid rgba(201, 216, 236, 0.85);
      border-radius: 10px;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.72);
    }}

    .details-list-row--clickable {{
      border-color: rgba(124, 109, 253, 0.28);
      background: rgba(255, 255, 255, 0.86);
    }}

    .details-list-row--stacked {{
      grid-template-columns: minmax(0, 1fr);
      gap: 6px;
    }}

    .details-list-label {{
      font-size: 13px;
      line-height: 1.35;
      word-break: break-word;
    }}

    .details-list-click {{
      all: unset;
      display: block;
      width: 100%;
      color: var(--accent);
      font-size: 13px;
      line-height: 1.35;
      word-break: break-word;
      cursor: pointer;
      text-decoration: underline;
      text-decoration-color: rgba(124, 109, 253, 0.42);
      text-underline-offset: 2px;
    }}

    .details-list-click:focus-visible {{
      outline: 2px solid rgba(124, 109, 253, 0.32);
      outline-offset: 2px;
      border-radius: 6px;
    }}

    .details-list-value {{
      font-family: var(--font-mono);
      font-size: 12px;
      color: var(--accent-2);
      white-space: nowrap;
    }}

    .details-list-value--stacked {{
      white-space: pre-wrap;
      word-break: break-word;
      color: var(--ink);
    }}

    .graph-wrap {{
      position: relative;
      height: 100vh;
      min-height: 0;
      overflow: hidden;
    }}

    #cy {{
      width: 100%;
      height: 100%;
      min-height: 0;
    }}

    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(124, 109, 253, 0.12);
      color: var(--accent-2);
      font-size: 12px;
      font-weight: 700;
    }}

    .conversation-modal {{
      position: fixed;
      inset: 0;
      z-index: 500;
      display: grid;
      place-items: center;
      padding: 24px;
    }}

    .conversation-modal[hidden] {{
      display: none;
    }}

    .conversation-modal-backdrop {{
      position: absolute;
      inset: 0;
      background: rgba(16, 31, 52, 0.46);
      backdrop-filter: blur(5px);
    }}

    .conversation-modal-panel {{
      position: relative;
      z-index: 1;
      width: min(1180px, calc(100vw - 48px));
      max-height: min(860px, calc(100vh - 48px));
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(124, 109, 253, 0.22);
      border-radius: 24px;
      background:
        radial-gradient(circle at top left, rgba(73, 166, 255, 0.14), transparent 34%),
        linear-gradient(180deg, rgba(248, 251, 255, 0.98), rgba(235, 245, 255, 0.98));
      box-shadow: 0 26px 70px rgba(20, 42, 78, 0.28);
    }}

    .conversation-modal-header {{
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px;
      border-bottom: 1px solid rgba(201, 216, 236, 0.88);
    }}

    .conversation-modal-title {{
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
    }}

    .conversation-modal-subtitle {{
      margin: 4px 0 0 0;
      color: var(--muted);
      font-size: 13px;
    }}

    .conversation-modal-close {{
      flex: 0 0 auto;
    }}

    .conversation-modal-body {{
      overflow: auto;
      padding: 18px 20px 22px;
    }}

    .conversation-sample-tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
      padding: 6px;
      border: 1px solid rgba(201, 216, 236, 0.88);
      border-radius: 18px;
      background: rgba(244, 249, 255, 0.72);
    }}

    .conversation-sample-tab {{
      flex: 1 1 180px;
      cursor: pointer;
      border: 1px solid transparent;
      border-radius: 14px;
      padding: 9px 11px;
      background: transparent;
      color: var(--text);
      text-align: left;
      font: inherit;
      transition: border-color 120ms ease, background 120ms ease, box-shadow 120ms ease;
    }}

    .conversation-sample-tab:hover {{
      background: rgba(255, 255, 255, 0.66);
    }}

    .conversation-sample-tab:focus-visible {{
      outline: 3px solid rgba(124, 109, 253, 0.32);
      outline-offset: 2px;
    }}

    .conversation-sample-tab.is-active {{
      border-color: rgba(124, 109, 253, 0.38);
      background: rgba(255, 255, 255, 0.92);
      box-shadow: 0 10px 28px rgba(31, 65, 112, 0.12);
    }}

    .conversation-sample-tab-label {{
      display: block;
      font-size: 13px;
      font-weight: 800;
    }}

    .conversation-sample-tab-meta {{
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 10px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .conversation-sample {{
      border: 1px solid rgba(201, 216, 236, 0.9);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.72);
      overflow: hidden;
    }}

    .conversation-sample + .conversation-sample {{
      margin-top: 16px;
    }}

    .conversation-sample-panel[hidden] {{
      display: none;
    }}

    .conversation-sample-panel + .conversation-sample-panel {{
      margin-top: 0;
    }}

    .conversation-sample-header {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 14px;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(201, 216, 236, 0.86);
      background: rgba(244, 249, 255, 0.88);
      font-size: 12px;
      color: var(--muted);
    }}

    .conversation-turn {{
      padding: 14px;
    }}

    .conversation-turn + .conversation-turn {{
      border-top: 1px solid rgba(201, 216, 236, 0.74);
    }}

    .conversation-turn-header {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      margin-bottom: 10px;
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--muted);
    }}

    .conversation-message {{
      margin: 8px 0;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(201, 216, 236, 0.9);
      background: rgba(255, 255, 255, 0.82);
      line-height: 1.45;
    }}

    .conversation-message--user {{
      border-left: 4px solid var(--accent-2);
    }}

    .conversation-message--bot {{
      border-left: 4px solid var(--accent-3);
    }}

    .conversation-message--selected {{
      border-color: rgba(220, 38, 38, 0.7);
      background: rgba(255, 238, 238, 0.94);
      box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.12);
    }}

    .conversation-message-role {{
      display: block;
      margin-bottom: 4px;
      font-size: 11px;
      font-weight: 800;
      color: var(--accent-2);
      text-transform: uppercase;
      letter-spacing: 0.07em;
    }}

    .conversation-message-text {{
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .conversation-reply-context {{
      margin-bottom: 10px;
    }}

    .conversation-meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}

    .conversation-meta-item {{
      padding: 8px 10px;
      border: 1px solid rgba(201, 216, 236, 0.76);
      border-radius: 12px;
      background: rgba(248, 251, 255, 0.76);
      font-size: 12px;
    }}

    .conversation-meta-label {{
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .conversation-json {{
      margin-top: 8px;
      border: 1px solid rgba(201, 216, 236, 0.76);
      border-radius: 12px;
      background: rgba(248, 251, 255, 0.76);
      overflow: hidden;
    }}

    .conversation-json summary {{
      cursor: pointer;
      padding: 8px 10px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .conversation-json pre {{
      margin: 0;
      padding: 0 10px 10px;
      max-height: 220px;
      overflow: auto;
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .conversation-chip-section {{
      margin-top: 8px;
      padding: 8px 10px;
      border: 1px solid rgba(201, 216, 236, 0.76);
      border-radius: 12px;
      background: rgba(248, 251, 255, 0.76);
    }}

    .conversation-chip-list {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .conversation-chip {{
      display: inline-flex;
      align-items: center;
      max-width: 100%;
      padding: 5px 9px;
      border: 1px solid rgba(124, 109, 253, 0.28);
      border-radius: 999px;
      background: rgba(124, 109, 253, 0.1);
      color: var(--accent-2);
      font-size: 11px;
      font-weight: 800;
      line-height: 1.25;
      word-break: break-word;
    }}

    .conversation-chip:disabled {{
      opacity: 1;
    }}

    .conversation-quick-reply-button {{
      border-color: rgba(31, 121, 184, 0.26);
      background: rgba(73, 166, 255, 0.1);
      color: var(--accent);
      font-family: inherit;
    }}

    .conversation-diagnostics {{
      margin-top: 8px;
      border: 1px solid rgba(201, 216, 236, 0.76);
      border-radius: 12px;
      background: rgba(248, 251, 255, 0.76);
      overflow: hidden;
    }}

    .conversation-diagnostics summary {{
      cursor: pointer;
      padding: 8px 10px;
      color: var(--muted);
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}

    .conversation-diagnostics-body {{
      padding: 0 10px 10px;
    }}

    @media (max-width: 980px) {{
      body {{
        height: auto;
        overflow: auto;
      }}

      .shell {{
        grid-template-columns: 1fr;
        height: auto;
        min-height: 100vh;
        overflow: visible;
      }}

      .sidebar {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
        overflow: visible;
      }}

      .graph-wrap, #cy {{
        min-height: 70vh;
        height: 70vh;
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="hero">
        <div class="brandmark" aria-label="SentiOne Automate logo">{logo_svg}</div>
        <div class="eyebrow">Debugger HTML Graph</div>
        <h1>{title}</h1>
        <div class="badge">{graph_kind_label}</div>
      </div>

      <section class="summary">
        <div class="stat">
          <div class="stat-label">Sessions</div>
          <div class="stat-value" id="summary-sessions"></div>
        </div>
        <div class="stat">
          <div class="stat-label">Nodes</div>
          <div class="stat-value" id="summary-nodes"></div>
        </div>
        <div class="stat">
          <div class="stat-label">Edges</div>
          <div class="stat-value" id="summary-edges"></div>
        </div>
      </section>

      <section class="section">
        <h2>Explore</h2>
        <div class="field">
          <label for="search">Search nodes</label>
          <input id="search" type="search" placeholder="Filter by label, id, or tag">
        </div>
        <div class="field">
          <label for="layout">Layout</label>
          <select id="layout">
            <option value="breadthfirst">Breadthfirst</option>
            <option value="cose">CoSE</option>
            <option value="concentric">Concentric</option>
            <option value="circle">Circle</option>
          </select>
        </div>
      </section>

      <section class="section">
        <h2>Visibility</h2>
        <div class="field">
          <label>{node_metric_label}</label>
          <div class="range-row">
            <input id="min-node-range" type="range" min="0" max="1" step="1" value="0">
            <input id="min-node-value" type="number" min="0" step="1" value="0">
          </div>
        </div>
        <div class="field">
          <label>Minimum edge count</label>
          <div class="range-row">
            <input id="min-edge-count-range" type="range" min="0" max="1" step="1" value="0">
            <input id="min-edge-count-value" type="number" min="0" step="1" value="0">
          </div>
        </div>
        <div class="field">
          <label>Minimum edge percentage</label>
          <div class="range-row">
            <input id="min-edge-percent-range" type="range" min="0" max="100" step="0.1" value="0">
            <input id="min-edge-percent-value" type="number" min="0" max="100" step="0.1" value="0">
          </div>
        </div>
      </section>

      <section class="section">
        <h2>Actions</h2>
        <div class="actions">
          <button id="fit-view">Fit view</button>
          <button id="reset-filters" class="secondary">Reset filters</button>
          <button id="clear-focus" class="secondary">Clear focus</button>
        </div>
      </section>

      {legend_section_html}

      <section class="section">
        <h2>Details</h2>
        <div class="details" id="details"></div>
      </section>
    </aside>

    <main class="graph-wrap">
      <div id="cy"></div>
    </main>
  </div>

  <div class="section-help-floating" id="section-help-floating" role="tooltip" aria-hidden="true">
    <span class="section-help-title" id="section-help-title"></span>
    <span class="section-help-body" id="section-help-body"></span>
  </div>

  <div class="conversation-modal" id="conversation-modal" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="conversation-modal-title">
    <div class="conversation-modal-backdrop" data-modal-close="true"></div>
    <section class="conversation-modal-panel">
      <header class="conversation-modal-header">
        <div>
          <h2 class="conversation-modal-title" id="conversation-modal-title">Conversation samples</h2>
          <p class="conversation-modal-subtitle" id="conversation-modal-subtitle"></p>
        </div>
        <button type="button" class="conversation-modal-close secondary" id="conversation-modal-close">Close</button>
      </header>
      <div class="conversation-modal-body" id="conversation-modal-body"></div>
    </section>
  </div>

  <script type="application/json" id="graph-data">{json.dumps(payload, ensure_ascii=False)}</script>
  <script src="{CYTOSCAPE_CDN_URL}"></script>
  <script>
    const payload = JSON.parse(document.getElementById('graph-data').textContent);
    const summary = payload.summary;
    const rawNodes = payload.nodes;
    const rawEdges = payload.edges;
    const sampleConversations = payload.sampleConversations || {{}};
    const sampleSessions = payload.sampleSessions || {{}};
    const borderMetricKey = payload.nodeBorderMetric ? payload.nodeBorderMetric.key : null;
    const hasNumericBorderMetric = node =>
      borderMetricKey && node[borderMetricKey] !== undefined && node[borderMetricKey] !== null && Number.isFinite(Number(node[borderMetricKey]));
    const hasBorderMetric = rawNodes.some(node => hasNumericBorderMetric(node));

    document.getElementById('summary-sessions').textContent = String(summary.totalSessions);
    document.getElementById('summary-nodes').textContent = String(summary.totalNodes);
    document.getElementById('summary-edges').textContent = String(summary.totalEdges);
    const nodeBorderLegend = document.getElementById('node-border-legend');
    if (nodeBorderLegend) {{
      nodeBorderLegend.hidden = !hasBorderMetric;
    }}

    const allNodeValues = rawNodes.map(node => Number(node[payload.nodeMetricKey] || 0));
    const allEdgeCounts = rawEdges.map(edge => Number(edge.count || 0));
    const maxNodeValue = Math.max(...allNodeValues, 1);
    const maxEdgeCount = Math.max(...allEdgeCounts, 1);

    const minNodeRange = document.getElementById('min-node-range');
    const minNodeValue = document.getElementById('min-node-value');
    minNodeRange.max = String(maxNodeValue);
    minNodeValue.max = String(maxNodeValue);

    const minEdgeCountRange = document.getElementById('min-edge-count-range');
    const minEdgeCountValue = document.getElementById('min-edge-count-value');
    minEdgeCountRange.max = String(maxEdgeCount);
    minEdgeCountValue.max = String(maxEdgeCount);

    const minEdgePercentRange = document.getElementById('min-edge-percent-range');
    const minEdgePercentValue = document.getElementById('min-edge-percent-value');

    const nodeMap = new Map(rawNodes.map(node => [node.id, node]));
    const edgeMap = new Map(rawEdges.map(edge => [`${{edge.source}}->${{edge.target}}`, edge]));

    function clamp(value, min, max) {{
      return Math.min(Math.max(value, min), max);
    }}

    function mixHexColor(startHex, endHex, ratio) {{
      const start = startHex.match(/[a-f0-9]{{2}}/gi).map(part => parseInt(part, 16));
      const end = endHex.match(/[a-f0-9]{{2}}/gi).map(part => parseInt(part, 16));
      const mixed = start.map((channel, index) => {{
        const value = Math.round(channel + (end[index] - channel) * ratio);
        return value.toString(16).padStart(2, '0');
      }});
      return `#${{mixed.join('')}}`;
    }}

    function borderRateColor(value) {{
      const rate = clamp(Number(value) || 0, 0, 100);
      if (rate <= 50) {{
        return mixHexColor('#7C6DFD', '#f59e0b', rate / 50);
      }}
      return mixHexColor('#f59e0b', '#dc2626', (rate - 50) / 50);
    }}

    function borderRateWidth(value) {{
      const rate = clamp(Number(value) || 0, 0, 100);
      return 2 + (rate / 100) * 5;
    }}

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: [
        ...rawNodes.map(node => ({{
          data: {{
            id: node.id,
            label: node.label,
            detail: node.detail,
            metricValue: Number(node[payload.nodeMetricKey] || 0),
            hasBorderMetric: hasNumericBorderMetric(node),
            borderRate: hasNumericBorderMetric(node) ? Number(node[borderMetricKey]) : 0,
            raw: node,
            isStart: Boolean(node.isStart)
          }}
        }})),
        ...rawEdges.map(edge => ({{
          data: {{
            id: `${{edge.source}}->${{edge.target}}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            count: edge.count,
            percent: edge.percent,
            raw: edge
          }}
        }}))
      ],
      style: [
        {{
          selector: 'node',
          style: {{
            'background-color': ele => ele.data('isStart') ? '#dbe9ff' : '#4d7cff',
            'border-width': ele => {{
              const borderRate = Number(ele.data('borderRate'));
              if (ele.data('isStart') || !ele.data('hasBorderMetric')) {{
                return 2;
              }}
              return borderRateWidth(borderRate);
            }},
            'border-color': ele => {{
              const borderRate = Number(ele.data('borderRate'));
              if (ele.data('isStart')) {{
                return '#6b84bf';
              }}
              if (!ele.data('hasBorderMetric')) {{
                return '#244f97';
              }}
              return borderRateColor(borderRate);
            }},
            'label': 'data(label)',
            'font-family': 'Open Sans, Segoe UI, sans-serif',
            'font-size': 11,
            'text-wrap': 'wrap',
            'text-max-width': 180,
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#0f1c2f',
            'text-background-color': '#f8fbff',
            'text-background-opacity': 0.56,
            'text-background-shape': 'round-rectangle',
            'text-background-padding': 4,
            'text-border-width': 0.75,
            'text-border-color': '#dde8f8',
            'width': `mapData(metricValue, 0, ${{maxNodeValue}}, 58, 184)`,
            'height': `mapData(metricValue, 0, ${{maxNodeValue}}, 58, 184)`,
            'overlay-padding': 8,
            'z-index': 10
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'curve-style': 'bezier',
            'width': `mapData(count, 0, ${{maxEdgeCount}}, 2, 10)`,
            'line-color': '#7a89a8',
            'target-arrow-color': '#7a89a8',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 1.1,
            'label': 'data(label)',
            'font-size': 10,
            'font-family': 'Open Sans, Segoe UI, sans-serif',
            'text-background-color': '#f8fbff',
            'text-background-opacity': 0.62,
            'text-background-shape': 'round-rectangle',
            'text-background-padding': 2,
            'text-border-width': 0.6,
            'text-border-color': '#dbe6f5',
            'text-rotation': 'autorotate',
            'color': '#162235'
          }}
        }},
        {{
          selector: '.dimmed',
          style: {{
            'opacity': 0.12
          }}
        }},
        {{
          selector: '.hidden-by-filter',
          style: {{
            'display': 'none'
          }}
        }},
        {{
          selector: '.focused',
          style: {{
            'border-width': 4,
            'border-color': '#7C6DFD',
            'line-color': '#7C6DFD',
            'target-arrow-color': '#7C6DFD'
          }}
        }}
      ],
      layout: {{
        name: 'breadthfirst',
        directed: true,
        padding: 50,
        spacingFactor: 1.22
      }}
    }});

    const details = document.getElementById('details');
    const helpTooltip = document.getElementById('section-help-floating');
    const helpTooltipTitle = document.getElementById('section-help-title');
    const helpTooltipBody = document.getElementById('section-help-body');
    const conversationModal = document.getElementById('conversation-modal');
    const conversationModalTitle = document.getElementById('conversation-modal-title');
    const conversationModalSubtitle = document.getElementById('conversation-modal-subtitle');
    const conversationModalBody = document.getElementById('conversation-modal-body');
    const conversationModalClose = document.getElementById('conversation-modal-close');
    let activeHelpIcon = null;

    function renderDetails(html) {{
      details.innerHTML = html;
      hideSectionHelpTooltip();
      bindSectionHelp();
      bindSampleLinks();
    }}

    function getSectionHelpText(title) {{
      const helpTexts = {{
        'Meaning': {{
          title: 'Meaning',
          body: 'Shows what the Start node means in this graph.',
        }},
        'Previous blocks': {{
          title: 'Previous blocks',
          body: 'Blocks that usually came before this block.',
        }},
        'Previous user messages': {{
          title: 'Previous user messages',
          body: 'User messages that appeared just before this block became active.',
        }},
        'Next blocks': {{
          title: 'Next blocks',
          body: 'Blocks that usually came after this block.',
        }},
        'Bot messages': {{
          title: 'Bot messages',
          body: 'Bot messages that users replied to while they were in this block.',
        }},
        'User replies': {{
          title: 'User replies',
          body: 'User messages sent as replies to this block.',
        }},
        'Next bot messages': {{
          title: 'Next bot messages',
          body: 'Bot messages sent after those user replies.',
        }},
        'Non-fallback user messages': {{
          title: 'Non-fallback user messages',
          body: 'User replies that were followed by a different next block.',
        }},
        'Tags': {{
          title: 'Tags',
          body: 'Tags recorded while this block was active.',
        }},
        'Fallback user messages': {{
          title: 'Fallback user messages',
          body: 'User replies after which the conversation appears to stay in this block instead of moving forward.',
        }},
        'Fallback bot replies': {{
          title: 'Fallback bot replies',
          body: 'Bot replies emitted after user replies in repeated same-dialogState runs. In block graphs this indicates likely retry or circular behavior, but the export does not prove the exact runtime state.',
        }},
        'Bot messages before transition': {{
          title: 'Bot messages before transition',
          body: 'Bot messages shown before the user took this transition.',
        }},
        'User messages before transition': {{
          title: 'User messages before transition',
          body: 'User messages that led to this transition.',
        }},
        'Bot replies in destination block': {{
          title: 'Bot replies in destination block',
          body: 'Bot replies shown after this transition.',
        }},
        'Details': {{
          title: 'Details',
          body: 'Additional details for the selected item.',
        }},
      }};
      return helpTexts[title] || {{
        title: title,
        body: 'Summary details for this subsection.',
      }};
    }}

    function getMetricHelpText(title) {{
      const isTagGraph = payload.graphKindLabel === 'Tags';
      const helpTexts = {{
        'Block id': {{
          title: 'Block id',
          body: 'Stable block identifier used for grouping.',
        }},
        'Context name': {{
          title: 'Context name',
          body: 'Name of the flow context where this block was observed.',
        }},
        'Turns': {{
          title: 'Turns',
          body: 'Number of exported turns recorded for this block.',
        }},
        'Runs': {{
          title: 'Runs',
          body: 'Number of separate visits to this block.',
        }},
        'Sessions': {{
          title: 'Sessions',
          body: 'Number of conversations that included this item.',
        }},
        'Fallback rate': {{
          title: 'Fallback rate',
          body: isTagGraph
            ? 'Share of tag runs where the same tag appeared consecutively in the ordered tag sequence.'
            : 'Share of block runs where the same dialogState.id appeared on consecutive user-turn rows. Because dialogState.id identifies the input-requesting block, treat this as a fallback/circular heuristic rather than exact runtime truth.',
        }},
        'Quick Reply offers': {{
          title: 'Quick Reply offers',
          body: 'Number of times this block could be inferred as the block that offered quick replies and there was a following exported user turn.',
        }},
        'Quick Reply Rate': {{
          title: 'Quick Reply Rate',
          body: 'Share of inferred quick-reply offers from this block where the next exported user message exactly matched one offered quick reply. Because dialogState.id is shifted, the offer is attributed to the following row dialogState.id: the block that requested that reply.',
        }},
        'Drop rate': {{
          title: 'Drop rate',
          body: 'In tag graphs, share of tag visits after which there is no later user message and no Disconnect or Redirect command. Explicit channel endings are terminal, but not treated as drops.',
        }},
        'Terminal rate': {{
          title: 'Terminal rate',
          body: 'In tag graphs, share of tag sessions where the tag is the final tag run before no later user message appears.',
        }},
        'Occurrences': {{
          title: 'Occurrences',
          body: 'Number of times this tag appeared.',
        }},
        'Transitions': {{
          title: 'Transitions',
          body: 'Number of times this exact edge appeared.',
        }},
        'Sessions with transition': {{
          title: 'Sessions with transition',
          body: 'Number of conversations that used this edge.',
        }},
        'Outgoing percentage': {{
          title: 'Outgoing percentage',
          body: 'Share of source-block visits that used this edge.',
        }},
        'Source': {{
          title: 'Source',
          body: 'Where this transition starts.',
        }},
        'Target': {{
          title: 'Target',
          body: 'Where this transition leads.',
        }},
      }};
      return helpTexts[title] || {{
        title: title,
        body: 'Summary for this graph item.',
      }};
    }}

    function bindSectionHelp() {{
      details.querySelectorAll('.section-help').forEach(helpIcon => {{
        helpIcon.addEventListener('mouseenter', () => showSectionHelpTooltip(helpIcon));
        helpIcon.addEventListener('focus', () => showSectionHelpTooltip(helpIcon));
        helpIcon.addEventListener('mouseleave', hideSectionHelpTooltip);
        helpIcon.addEventListener('blur', hideSectionHelpTooltip);
        helpIcon.addEventListener('mousedown', event => {{
          event.preventDefault();
          event.stopPropagation();
        }});
        helpIcon.addEventListener('click', event => {{
          event.preventDefault();
          event.stopPropagation();
        }});
      }});
    }}

    function showSectionHelpTooltip(helpIcon) {{
      const title = helpIcon.dataset.helpTitle || '';
      const body = helpIcon.dataset.helpBody || '';
      const preferredWidth = 270;
      const gap = 12;
      const viewportPadding = 16;

      helpTooltipTitle.textContent = title;
      helpTooltipBody.textContent = body;
      helpTooltip.classList.add('is-visible');
      helpTooltip.setAttribute('aria-hidden', 'false');

      const iconRect = helpIcon.getBoundingClientRect();
      const tooltipRect = helpTooltip.getBoundingClientRect();
      const tooltipWidth = Math.min(preferredWidth, tooltipRect.width || preferredWidth);
      const placeRight = iconRect.right + gap + tooltipWidth <= window.innerWidth - viewportPadding;
      const left = placeRight
        ? iconRect.right + gap
        : Math.max(viewportPadding, iconRect.left - gap - tooltipWidth);
      const top = Math.min(
        Math.max(viewportPadding, iconRect.top + (iconRect.height / 2) - (tooltipRect.height / 2)),
        window.innerHeight - tooltipRect.height - viewportPadding,
      );

      helpTooltip.dataset.placement = placeRight ? 'right' : 'left';
      helpTooltip.style.left = `${{left}}px`;
      helpTooltip.style.top = `${{top}}px`;
      activeHelpIcon = helpIcon;
    }}

    function hideSectionHelpTooltip() {{
      activeHelpIcon = null;
      helpTooltip.classList.remove('is-visible');
      helpTooltip.setAttribute('aria-hidden', 'true');
      helpTooltip.style.left = '';
      helpTooltip.style.top = '';
      helpTooltip.dataset.placement = 'right';
    }}

    function bindSampleLinks() {{
      details.querySelectorAll('[data-sample-key]').forEach(button => {{
        button.addEventListener('click', event => {{
          event.preventDefault();
          const sampleKey = button.dataset.sampleKey || '';
          openConversationModal(sampleKey);
        }});
      }});
    }}

    function openConversationModal(sampleKey) {{
      const sampleGroup = sampleConversations[sampleKey];
      if (!sampleGroup) {{
        return;
      }}

      conversationModalTitle.textContent = `Samples: ${{sampleGroup.section || 'Messages'}}`;
      conversationModalSubtitle.textContent = sampleGroup.message || '';
      conversationModalBody.innerHTML = renderSampleConversationGroup(sampleGroup);
      conversationModalBody.scrollTop = 0;
      bindConversationSampleTabs();
      conversationModal.hidden = false;
      conversationModal.setAttribute('aria-hidden', 'false');
      conversationModalClose.focus();
    }}

    function closeConversationModal() {{
      conversationModal.hidden = true;
      conversationModal.setAttribute('aria-hidden', 'true');
      conversationModalBody.innerHTML = '';
    }}

    conversationModalClose.addEventListener('click', closeConversationModal);
    conversationModal.addEventListener('click', event => {{
      if (event.target && event.target.dataset && event.target.dataset.modalClose) {{
        closeConversationModal();
      }}
    }});
    document.addEventListener('keydown', event => {{
      if (event.key === 'Escape' && !conversationModal.hidden) {{
        closeConversationModal();
      }}
    }});

    function bindConversationSampleTabs() {{
      const tabs = Array.from(conversationModalBody.querySelectorAll('[data-sample-tab]'));
      const panels = Array.from(conversationModalBody.querySelectorAll('[data-sample-panel]'));
      if (!tabs.length || !panels.length) {{
        return;
      }}

      const activateTab = sampleIndex => {{
        tabs.forEach(tab => {{
          const isActive = tab.dataset.sampleTab === sampleIndex;
          tab.classList.toggle('is-active', isActive);
          tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
          tab.tabIndex = isActive ? 0 : -1;
        }});
        panels.forEach(panel => {{
          panel.hidden = panel.dataset.samplePanel !== sampleIndex;
        }});
        conversationModalBody.scrollTop = 0;
      }};

      tabs.forEach((tab, index) => {{
        tab.addEventListener('click', () => activateTab(tab.dataset.sampleTab || '0'));
        tab.addEventListener('keydown', event => {{
          if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {{
            return;
          }}
          event.preventDefault();
          const offset = event.key === 'ArrowRight' ? 1 : -1;
          const nextTab = tabs[(index + offset + tabs.length) % tabs.length];
          nextTab.focus();
          activateTab(nextTab.dataset.sampleTab || '0');
        }});
      }});
    }}

    function renderSampleConversationGroup(sampleGroup) {{
      const samples = Array.isArray(sampleGroup.samples) ? sampleGroup.samples : [];
      if (!samples.length) {{
        return '<div class="legend">No sample conversations are available for this message.</div>';
      }}

      const tabs = samples
        .map((sample, index) => renderConversationSampleTab(sample, index))
        .join('');
      const panels = samples
        .map((sample, index) => renderConversationSample(sample, index))
        .join('');

      return `
        <div class="conversation-sample-tabs" role="tablist" aria-label="Conversation samples">
          ${{tabs}}
        </div>
        <div class="conversation-sample-panels">
          ${{panels}}
        </div>
      `;
    }}

    function renderConversationSampleTab(sample, index) {{
      const session = sampleSessions[sample.internalSessionId] || {{}};
      const sessionId = session.sessionId || sample.sessionId || '';
      const rows = Array.isArray(session.rows) ? session.rows : [];
      const active = index === 0;

      return `
        <button
          type="button"
          class="conversation-sample-tab${{active ? ' is-active' : ''}}"
          id="conversation-sample-tab-${{index}}"
          role="tab"
          aria-selected="${{active ? 'true' : 'false'}}"
          aria-controls="conversation-sample-panel-${{index}}"
          data-sample-tab="${{index}}"
          tabindex="${{active ? '0' : '-1'}}"
        >
          <span class="conversation-sample-tab-label">Sample ${{index + 1}}</span>
          <span class="conversation-sample-tab-meta">${{escapeHtml(sessionId || 'No public session id')}} · ${{rows.length}} turns</span>
        </button>
      `;
    }}

    function renderConversationSample(sample, index) {{
      const session = sampleSessions[sample.internalSessionId] || {{}};
      const rows = Array.isArray(session.rows) ? session.rows : [];
      const selected = sample.selected || {{}};
      const sessionId = session.sessionId || sample.sessionId || '';
      const internalSessionId = session.internalSessionId || sample.internalSessionId || '';

      return `
        <article
          class="conversation-sample conversation-sample-panel"
          id="conversation-sample-panel-${{index}}"
          role="tabpanel"
          aria-labelledby="conversation-sample-tab-${{index}}"
          data-sample-panel="${{index}}"
          ${{index === 0 ? '' : 'hidden'}}
        >
          <header class="conversation-sample-header">
            <span>Sample ${{index + 1}}</span>
            <span>Session ID: ${{escapeHtml(sessionId)}}</span>
            <span>Internal session ID: ${{escapeHtml(internalSessionId)}}</span>
            <span>Turns: ${{rows.length}}</span>
          </header>
          <div>
            ${{rows.map(row => renderConversationTurn(row, selected)).join('')}}
          </div>
        </article>
      `;
    }}

    function renderConversationTurn(row, selected) {{
      const rowId = Number(row.rowId);
      const selectedUser = selected.kind === 'user' && Number(selected.rowId) === rowId;
      const botMessages = Array.isArray(row.botMessages) ? row.botMessages : [];
      const botCreatedAt = Array.isArray(row.botMessagesCreatedAt) ? row.botMessagesCreatedAt : [];
      const userMessage = row.userMessage ? row.userMessage : '(empty user message)';

      return `
        <section class="conversation-turn">
          <div class="conversation-turn-header">
            <span>Row: ${{escapeHtml(row.rowId)}}</span>
            <span>Time: ${{escapeHtml(formatTimestamp(row.time))}}</span>
          </div>
          ${{renderReplyContext(row)}}
          <div class="conversation-message conversation-message--user${{selectedUser ? ' conversation-message--selected' : ''}}">
            <span class="conversation-message-role">User message</span>
            <div class="conversation-message-text">${{escapeHtml(userMessage)}}</div>
          </div>
          ${{botMessages.map((message, botIndex) => {{
            const selectedBot = selected.kind === 'bot' && Number(selected.rowId) === rowId && Number(selected.botMessageIndex) === botIndex;
            const createdAt = botCreatedAt[botIndex] ? ` · created ${{formatTimestamp(botCreatedAt[botIndex])}}` : '';
            return `
              <div class="conversation-message conversation-message--bot${{selectedBot ? ' conversation-message--selected' : ''}}">
                <span class="conversation-message-role">Bot reply ${{botIndex + 1}}${{escapeHtml(createdAt)}}</span>
                <div class="conversation-message-text">${{escapeHtml(message)}}</div>
              </div>
            `;
          }}).join('')}}
          ${{renderQuickReplies(row.quickReplies)}}
          ${{renderTags(row.tags)}}
          ${{renderTurnDiagnostics(row)}}
        </section>
      `;
    }}

    function renderReplyContext(row) {{
      const dialogState = row.dialogState || null;
      const blockLabel = dialogState
        ? `${{dialogState.name || ''}} (${{dialogState.id || ''}})`
        : 'No dialogState';
      const contextLabel = dialogState && dialogState.context
        ? `${{dialogState.context}}${{dialogState.contextUuid ? ` (${{dialogState.contextUuid}})` : ''}}`
        : 'None';

      return `
        <div class="conversation-reply-context">
          <div class="conversation-meta-grid">
            ${{renderMetaItem('Block that requested this reply', blockLabel)}}
            ${{renderMetaItem('Context that requested this reply', contextLabel)}}
          </div>
        </div>
      `;
    }}

    function renderTurnDiagnostics(row) {{
      return `
        <details class="conversation-diagnostics">
          <summary>Technical details</summary>
          <div class="conversation-diagnostics-body">
            <div class="conversation-meta-grid">
              ${{renderMetaItem('Timing metrics', formatTiming(row.timing || {{}}))}}
            </div>
            ${{renderJsonDetails('Commands', row.commands)}}
            ${{renderJsonDetails('NLU results', row.nluModels)}}
            ${{renderJsonDetails('Extra data', row.extraData)}}
            ${{renderJsonDetails('Conversation metadata', row.conversationMetadata)}}
            ${{renderJsonDetails('Error', row.error)}}
          </div>
        </details>
      `;
    }}

    function renderMetaItem(label, value) {{
      return `
        <div class="conversation-meta-item">
          <span class="conversation-meta-label">${{escapeHtml(label)}}</span>
          <span>${{escapeHtml(value)}}</span>
        </div>
      `;
    }}

    function renderTags(tags) {{
      const tagValues = Array.isArray(tags)
        ? tags.filter(tag => typeof tag === 'string' && tag.length)
        : [];
      if (!tagValues.length) {{
        return renderMetaItem('Tags', 'None');
      }}

      return `
        <div class="conversation-chip-section conversation-tag-section">
          <span class="conversation-meta-label">Tags</span>
          <div class="conversation-chip-list conversation-tag-list" aria-label="Tags">
            ${{tagValues.map(tag => `<span class="conversation-chip conversation-tag-button">${{escapeHtml(tag)}}</span>`).join('')}}
          </div>
        </div>
      `;
    }}

    function flattenStringArray(value) {{
      if (!Array.isArray(value)) {{
        return [];
      }}

      return value.flatMap(item => {{
        if (Array.isArray(item)) {{
          return flattenStringArray(item);
        }}
        return typeof item === 'string' && item.length ? [item] : [];
      }});
    }}

    function renderQuickReplies(quickReplies) {{
      const replyValues = flattenStringArray(quickReplies);
      if (!replyValues.length) {{
        return renderMetaItem('Quick replies', 'None');
      }}

      return `
        <div class="conversation-chip-section conversation-quick-reply-section">
          <span class="conversation-meta-label">Quick replies</span>
          <div class="conversation-chip-list conversation-quick-reply-list" aria-label="Quick replies">
            ${{replyValues.map(reply => `<button type="button" class="conversation-chip conversation-quick-reply-button" disabled>${{escapeHtml(reply)}}</button>`).join('')}}
          </div>
        </div>
      `;
    }}

    function renderJsonDetails(label, value) {{
      if (!hasData(value)) {{
        return renderMetaItem(label, 'None');
      }}

      return `
        <details class="conversation-json">
          <summary>${{escapeHtml(label)}}</summary>
          <pre>${{escapeHtml(formatJson(value))}}</pre>
        </details>
      `;
    }}

    function hasData(value) {{
      if (value === null || value === undefined) {{
        return false;
      }}
      if (Array.isArray(value)) {{
        return value.length > 0;
      }}
      if (typeof value === 'object') {{
        return Object.keys(value).length > 0;
      }}
      return Boolean(value);
    }}

    function formatJson(value) {{
      try {{
        return JSON.stringify(value, null, 2);
      }} catch (error) {{
        return String(value);
      }}
    }}

    function formatTiming(timing) {{
      const processTime = timing.processTime ?? 'n/a';
      const nluTime = timing.nluTime ?? 'n/a';
      const integrationsTime = timing.integrationsTime ?? 'n/a';
      return `process=${{processTime}}ms, nlu=${{nluTime}}ms, integrations=${{integrationsTime}}ms`;
    }}

    function formatTimestamp(value) {{
      const numericValue = Number(value);
      if (!Number.isFinite(numericValue)) {{
        return String(value || '');
      }}
      const date = new Date(numericValue);
      if (Number.isNaN(date.getTime())) {{
        return String(value);
      }}
      return `${{date.toLocaleString()}} (${{numericValue}})`;
    }}

    function renderSections(sections) {{
      return (sections || [])
        .map(section => {{
          const help = getSectionHelpText(section.title);
          const helpTitle = escapeHtml(help.title);
          const helpBody = escapeHtml(help.body);
          return `
            <details class="details-section">
              <summary>
                <div class="section-heading">
                  <h4>${{escapeHtml(section.title)}}</h4>
                  <span class="section-help-wrap">
                    <span class="section-help" tabindex="0" role="button" data-help-title="${{helpTitle}}" data-help-body="${{helpBody}}" aria-label="${{helpTitle}}. ${{helpBody}}">i</span>
                  </span>
                </div>
              </summary>
              <div class="details-list">
                ${{(section.rows || []).map(row => {{
                  const labelText = String(row.label ?? '');
                  const valueText = String(row.value ?? '');
                  const sampleKey = row.sampleKey && sampleConversations[row.sampleKey] ? String(row.sampleKey) : '';
                  const isPlaceholder = labelText.startsWith('No ');
                  const isStacked = isPlaceholder || valueText.length > 48;
                  const rowClass = [
                    'details-list-row',
                    isStacked ? 'details-list-row--stacked' : '',
                    sampleKey ? 'details-list-row--clickable' : '',
                  ].filter(Boolean).join(' ');
                  const valueClass = isStacked ? 'details-list-value details-list-value--stacked' : 'details-list-value';
                  const labelHtml = sampleKey
                    ? `<button type="button" class="details-list-click" data-sample-key="${{escapeAttribute(sampleKey)}}" aria-label="Show sample conversations for ${{escapeAttribute(labelText)}}">${{escapeHtml(row.label)}}</button>`
                    : `<div class="details-list-label">${{escapeHtml(row.label)}}</div>`;
                  return `
                  <div class="${{rowClass}}">
                    ${{labelHtml}}
                    <div class="${{valueClass}}">${{escapeHtml(row.value)}}</div>
                  </div>
                `;
                }}).join('')}}
              </div>
            </details>
          `;
        }})
        .join('');
    }}

    function renderMetrics(metricsObject) {{
      return Object.entries(metricsObject || {{}})
        .map(([key, value]) => {{
          const help = getMetricHelpText(key);
          const helpTitle = escapeHtml(help.title);
          const helpBody = escapeHtml(help.body);
          return `
            <dt>
              <span class="metric-heading">
                <span>${{escapeHtml(key)}}</span>
                <span class="section-help-wrap">
                  <span class="section-help" tabindex="0" role="button" data-help-title="${{helpTitle}}" data-help-body="${{helpBody}}" aria-label="${{helpTitle}}. ${{helpBody}}">i</span>
                </span>
              </span>
            </dt>
            <dd>${{escapeHtml(value)}}</dd>
          `;
        }})
        .join('');
    }}

    function describeNode(node) {{
      const raw = node.data('raw');
      const metrics = renderMetrics(raw.metrics);
      const sections = renderSections(raw.sections);
      return `
        <h3>${{escapeHtml(raw.title)}}</h3>
        <dl>
          ${{metrics}}
        </dl>
        ${{sections}}
      `;
    }}

    function describeEdge(edge) {{
      const raw = edge.data('raw');
      const metrics = renderMetrics(raw.metrics);
      const sections = renderSections(raw.sections);
      return `
        <h3>${{escapeHtml(raw.title)}}</h3>
        <dl>
          ${{metrics}}
        </dl>
        ${{sections}}
      `;
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}

    function escapeAttribute(value) {{
      return escapeHtml(value).replaceAll('"', '&quot;').replaceAll("'", '&#39;');
    }}

    function syncInputs(rangeInput, numberInput) {{
      const syncFromRange = () => {{ numberInput.value = rangeInput.value; applyFilters(); }};
      const syncFromNumber = () => {{ rangeInput.value = numberInput.value; applyFilters(); }};
      rangeInput.addEventListener('input', syncFromRange);
      numberInput.addEventListener('input', syncFromNumber);
    }}

    syncInputs(minNodeRange, minNodeValue);
    syncInputs(minEdgeCountRange, minEdgeCountValue);
    syncInputs(minEdgePercentRange, minEdgePercentValue);

    function runLayout() {{
      cy.layout({{
        name: document.getElementById('layout').value,
        directed: true,
        padding: 40,
        spacingFactor: 1.1,
        animate: true,
        fit: true
      }}).run();
    }}

    document.getElementById('layout').addEventListener('change', runLayout);
    document.getElementById('fit-view').addEventListener('click', () => cy.fit(undefined, 40));
    document.getElementById('reset-filters').addEventListener('click', () => {{
      minNodeRange.value = '0';
      minNodeValue.value = '0';
      minEdgeCountRange.value = '0';
      minEdgeCountValue.value = '0';
      minEdgePercentRange.value = '0';
      minEdgePercentValue.value = '0';
      document.getElementById('search').value = '';
      applyFilters();
      clearFocus();
      cy.fit(undefined, 40);
    }});

    function clearFocus() {{
      cy.elements().removeClass('dimmed focused');
      renderDetails('<h3>No selection</h3><div class="legend">Click a node or edge to inspect it. Use search and sliders to focus the graph.</div>');
    }}

    document.getElementById('clear-focus').addEventListener('click', clearFocus);

    function applyFilters() {{
      const minNode = Number(minNodeValue.value || 0);
      const minEdgeCount = Number(minEdgeCountValue.value || 0);
      const minEdgePercent = Number(minEdgePercentValue.value || 0);
      const searchText = document.getElementById('search').value.trim().toLowerCase();

      const visibleNodeIds = new Set(
        rawNodes
          .filter(node => node.isStart || Number(node[payload.nodeMetricKey] || 0) >= minNode)
          .filter(node => {{
            if (!searchText) {{
              return true;
            }}
            const haystack = `${{node.label}} ${{node.detail}}`.toLowerCase();
            return haystack.includes(searchText);
          }})
          .map(node => node.id)
      );

      let visibleEdges = rawEdges.filter(edge =>
        visibleNodeIds.has(edge.source) &&
        visibleNodeIds.has(edge.target) &&
        Number(edge.count || 0) >= minEdgeCount &&
        Number(edge.percent || 0) >= minEdgePercent
      );

        const incomingTargets = new Set(visibleEdges.map(edge => edge.target));
        for (const nodeId of visibleNodeIds) {{
        if (nodeId === '__start__' || incomingTargets.has(nodeId)) {{
            continue;
          }}

        const candidateEdges = rawEdges
          .filter(edge =>
            edge.target === nodeId &&
            visibleNodeIds.has(edge.source) &&
            Number(edge.count || 0) >= minEdgeCount &&
            Number(edge.percent || 0) >= minEdgePercent
          )
          .sort((a, b) => b.count - a.count || a.source.localeCompare(b.source));

        if (candidateEdges.length > 0) {{
          const selected = candidateEdges[0];
          if (!visibleEdges.some(edge => edge.source === selected.source && edge.target === selected.target)) {{
            visibleEdges.push(selected);
            incomingTargets.add(nodeId);
          }}
        }}
      }}

      const visibleEdgeIds = new Set(visibleEdges.map(edge => `${{edge.source}}->${{edge.target}}`));

      cy.nodes().forEach(node => {{
        node.toggleClass('hidden-by-filter', !visibleNodeIds.has(node.id()));
      }});
      cy.edges().forEach(edge => {{
        edge.toggleClass('hidden-by-filter', !visibleEdgeIds.has(edge.id()));
      }});
    }}

    document.getElementById('search').addEventListener('input', applyFilters);

    cy.on('tap', 'node', event => {{
      const node = event.target;
      cy.elements().addClass('dimmed').removeClass('focused');
      const neighborhood = node.closedNeighborhood();
      neighborhood.removeClass('dimmed').addClass('focused');
      renderDetails(describeNode(node));
    }});

    cy.on('tap', 'edge', event => {{
      const edge = event.target;
      cy.elements().addClass('dimmed').removeClass('focused');
      edge.connectedNodes().union(edge).removeClass('dimmed').addClass('focused');
      renderDetails(describeEdge(edge));
    }});

    cy.on('tap', event => {{
      if (event.target === cy) {{
        clearFocus();
      }}
    }});

    applyFilters();
    clearFocus();
  </script>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
