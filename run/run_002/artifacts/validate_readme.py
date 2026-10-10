"""Read-only run_002 documentation checks; no private-source reads or solver calls.

Uses only the Python standard library. The Mermaid check recognises the narrow
flowchart grammar used here; it is not a full Mermaid parser or rendering test.
Print JSON to stdout. Run from any directory with the selected research Python.
"""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
PAIRS = [
    ("Project Overview", "项目概述"),
    ("Physical Problem: Small Punch Test", "物理问题：小冲杆试验"),
    ("Research Objectives", "研究目标"),
    ("Proposed Research Architecture", "拟议研究架构"),
    ("Constitutive Model", "本构模型"),
    ("Inverse Identification Formulation", "本构参数反演数学形式"),
    ("Role of Reinforcement Learning", "强化学习在项目中的角色"),
    ("MDP Formulation", "MDP 数学定义"),
    ("Research Questions", "研究问题"),
    ("Research Roadmap", "研究路线图"),
    ("Repository Structure", "仓库结构"),
    ("Computing Environment", "计算环境"),
    ("Current Project Status", "当前项目状态"),
    ("Reproducibility and Data Policy", "可复现性与数据政策"),
    ("Limitations and Research Boundaries", "研究局限与边界"),
    ("Citation and Contact", "引用与联系"),
]


def mermaid_structure(code, kind):
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    assert lines.pop(0) == "flowchart TB", "Expected top-to-bottom flowchart"
    groups, nodes, edges, current = {}, {}, [], None
    for line in lines:
        group = re.fullmatch(r'subgraph ([A-Z])\["([^"\n]+)"\]', line)
        node = re.fullmatch(r'([A-Z]+)\["([^"\n]+)"\]', line)
        edge = re.fullmatch(r'([A-Z]+) (-->|-\.->)\s*(?:\|"([^"\n]+)"\|\s*)?([A-Z]+)', line)
        if group:
            assert current is None and group[1] not in groups
            current = group[1]
            groups[current] = group[2]
        elif line == "end":
            assert current is not None
            current = None
        elif node:
            assert (current is not None or kind == "rl") and node[1] not in nodes and len(node[2]) <= 80
            nodes[node[1]] = current
        elif edge:
            assert current is None
            edges.append((edge[1], edge[4], edge[2]))
        else:
            raise AssertionError("Unsupported Mermaid statement: " + line)
    assert current is None
    assert all(a in nodes and b in nodes for a, b, style in edges)
    if kind == "architecture":
        assert set(groups) == set("ABCDE") and len(nodes) == 9 and len(edges) == 10
        assert ("OBJ", "CTRL", "-->") in edges and ("VALID", "OUT", "-->") in edges
    else:
        assert not groups and len(nodes) == 8 and len(edges) == 9
        assert {(a, b) for a, b, style in edges if style == "-.->"} == {("REWARD", "UPDATE"), ("UPDATE", "POLICY")}
    return {"nodes_by_layer": nodes, "edges": edges}


def main():
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    names = ["README.md", "README.zh-CN.md"]
    texts = [(ROOT / name).read_text(encoding="utf-8") for name in names]
    check("files_utf8", all(t and "\ufffd" not in t for t in texts), names)
    check("language_switch", all(t.startswith("[English](README.md) | [简体中文](README.zh-CN.md)") for t in texts), "Reciprocal top links")
    h2 = [re.findall(r"^## (.+)$", text, re.M) for text in texts]
    expected = [[str(i + 1) + ". " + pair[lang] for i, pair in enumerate(PAIRS)] for lang in range(2)]
    check("bilingual_sections", h2 == expected, {"count": 16, "mapping": PAIRS})
    errors = []
    for name, text in zip(names, texts):
        prev, fence, math = 0, False, False
        for line in text.splitlines():
            if line.startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            if line == "$$":
                math = not math
                continue
            heading = re.match(r"^(#{1,6}) ", line)
            if heading:
                level = len(heading[1])
                if level > prev + 1:
                    errors.append(name + ": heading jump")
                prev = level
        if fence or math:
            errors.append(name + ": unclosed block")
        if len(re.findall(r"^# ", text, re.M)) != 1:
            errors.append(name + ": H1 count")
    check("heading_and_fence_structure", not errors, errors)
    equations = [re.findall(r"^\$\$\n(.*?)^\$\$", t, re.M | re.S) for t in texts]
    check("identical_display_equations", equations[0] == equations[1] and len(equations[0]) == 8,
          "Eight matching blocks: forward model, constitutive laws, parameters, objective, MDP state/action/reward")
    check("latex_braces", all(e.count("{") == e.count("}") for e in equations[0]),
          "Delimiter check only; not a MathJax rendering test")
    diagrams = [re.findall(r"```mermaid\n(.*?)\n```", t, re.S) for t in texts]
    assert all(len(d) == 2 for d in diagrams)
    structures = [[mermaid_structure(d[0], "architecture"), mermaid_structure(d[1], "rl")] for d in diagrams]
    check("mermaid_subset_syntax", True, "Architecture: 5 layers/9 nodes/10 edges; RL: 8 nodes/9 edges, training updates dashed")
    check("identical_mermaid_topology", structures[0] == structures[1] and diagrams[0] == diagrams[1],
          "Both diagrams have identical English source in both README files")
    links = []
    for name, text in zip(names, texts):
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if re.match(r"https?://", link):
                continue
            target = (ROOT / link).resolve()
            if not target.is_relative_to(ROOT) or not target.exists():
                links.append(name + ": " + link)
    check("relative_links", not links, links)
    image_paths = [re.findall(r"!\[[^\]]+\]\(([^)]+)\)", text) for text in texts]
    check("shared_spt_image_path", image_paths == [["docs/figures/spt_setup.svg"]] * 2,
          "Both language versions reference the same existing local SVG")
    svg_path = ROOT / "docs/figures/spt_setup.svg"
    svg = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    allowed_tags = {"svg", "title", "desc", "defs", "marker", "path", "rect", "g", "text"}
    safe = all(node.tag.split("}")[-1] in allowed_tags and
               all(not key.lower().startswith("on") and "href" not in key.lower()
                   and not re.search(r"https?://|javascript:|data:", value)
                   for key, value in node.attrib.items()) for node in svg.iter())
    check("svg_self_contained", safe and "<!DOCTYPE" not in svg_path.read_text(encoding="utf-8"),
          "Whitelisted vector/text elements; no scripts, events, external resources, raster image, or external font")
    labels = " ".join(node.text or "" for node in svg.iter() if node.tag.endswith("}text"))
    required_labels = ["Spherical punch", "Upper clamping die", "Lower supporting die", "Thin circular disc",
                       "Specimen", "Punch displacement u", "Measured force F", "Axis of symmetry"]
    white = any(node.tag.endswith("}rect") and node.get("width") == "1120"
                and node.get("height") == "650" and node.get("fill") == "#ffffff" for node in svg)
    check("svg_labels_and_theme", labels.isascii() and all(label in labels for label in required_labels) and white,
          "English physical labels and explicit white background; visual review recorded separately")
    check("public_readme_privacy", all(not re.search(r"\b[A-Za-z]:[\\/]|file://|artifacts/private/", t) for t in texts),
          "No absolute machine paths or links to private evidence; private source area not opened")
    tokens = ["run_001 = WARNING", "17", "2026-10-10", "3.11.13", "3.10.5", "Abaqus 2024", "PPO", "SAC", "RQ1", "RQ2", "RQ3"]
    check("shared_factual_markers", all(all(token in t for token in tokens) for t in texts), tokens)
    counts = [[re.findall(r"\b(Planned|In Progress|Completed|Blocked)\b", row) for row in t.splitlines()
               if re.match(r"\| \*\*[1-4]|\| \*\*Stage", row)] for t in texts]
    # English uses '1 —' in the first cell, matching Chinese numeric stage IDs.
    check("roadmap_status_parity", counts[0] == counts[1] and len(counts[0]) == 4, counts)
    prohibited = [r"RL (?:always )?outperforms", r"RL 必然优于", r"paper accepted", r"build passing",
                  r"10\.\d{4,9}/", r"```bibtex", r"successfully integrated with AbqJobPilot"]
    found = [p for p in prohibited if any(re.search(p, t, re.I) for t in texts)]
    check("unsupported_claim_screen", not found, {"matches": found, "limit": "Heuristic screen; semantic review is recorded separately"})
    baseline = json.loads((ROOT / "run/run_002/checkpoints/initial_state.json").read_text(encoding="utf-8"))
    allowed = set(baseline["approved_shared_file_updates"])
    changed = [p for p, digest in baseline["public_file_sha256"].items()
               if p not in allowed and (not (ROOT / p).is_file()
               or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest)]
    check("prior_work_preserved", not changed, {"unexpected_changes": changed, "approved_updates": sorted(allowed)})
    snapshots_ok = all(hashlib.sha256((ROOT / "run/run_002/checkpoints/before" / (p + ".snapshot")).read_bytes()).hexdigest()
                       == baseline["public_file_sha256"][p] for p in allowed)
    check("pre_edit_snapshots", snapshots_ok, "Exact original bytes for four shared files")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    staged = subprocess.check_output(["git", "diff", "--cached", "--name-status"], cwd=ROOT, text=True).strip()
    check("git_head_and_index", head == baseline["head"] and staged == baseline["index_diff"], "No commit or staging; baseline retained")
    ignored = ["references_private/probe.dat", "materials/probe.dat", "Materials/probe.dat", "run/run_002/artifacts/private/probe.json"]
    check("private_ignore_rules", all(subprocess.run(["git", "check-ignore", "-q", "--", p], cwd=ROOT).returncode == 0 for p in ignored), ignored)
    print(json.dumps({"checked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
                      "checks": checks,
                      "limitations": ["Mermaid checked against the used syntax subset, not rendered by GitHub.",
                                      "LaTeX delimiters and bilingual identity checked, not rendered by MathJax.",
                                      "Semantic equivalence and scientific claims also require the recorded manual review."]},
                     indent=2, ensure_ascii=True))
    return 0 if all(c["status"] == "PASS" for c in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
