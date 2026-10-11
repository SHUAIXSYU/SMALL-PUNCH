"""Check the run_003 bilingual documentation with Python 3.11 standard library.

No private files, environment probes, solvers or network are accessed.
Mermaid validation covers the existing diagram grammar, not rendered layout.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
FILES = ["README.md", "README.zh-CN.md", "docs/Inverse_Identification.md",
         "docs/Inverse_Identification.zh-CN.md"]


class TagCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in {"br", "img", "hr"}:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in {"br", "img", "hr"}:
            return
        if not self.stack or self.stack.pop() != tag:
            self.errors.append(tag)


def main():
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    texts = {name: (ROOT / name).read_text(encoding="utf-8") for name in FILES}
    check("utf8", all("\ufffd" not in t for t in texts.values()), FILES)
    links, html, blocks = [], [], []
    for name, text in texts.items():
        anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
                   for h in re.findall(r"^##+ (.+)$", text, re.M)}
        for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if re.match(r"https?://", link):
                continue
            if link.startswith("#"):
                if link[1:] not in anchors:
                    links.append(name + ": " + link)
                continue
            target = (ROOT / name).parent / link.split("#")[0]
            if not target.resolve().is_relative_to(ROOT) or not target.exists():
                links.append(name + ": " + link)
        if len(re.findall(r"^```", text, re.M)) % 2 or len(re.findall(r"^\$\$$", text, re.M)) % 2:
            blocks.append(name)
        clean = re.sub(r"```.*?```", "", text, flags=re.S)
        parser = TagCheck()
        parser.feed(clean)
        if parser.errors or parser.stack:
            html.append(name)
    check("relative_links_images_anchors", not links, links)
    check("html_tags", not html, html)
    check("code_math_fences", not blocks, blocks)
    headings = [[len(h) for h in re.findall(r"^(#{1,6}) ", t, re.M)] for t in texts.values()]
    check("heading_levels", all(all(b <= a + 1 for a, b in zip(h, h[1:])) for h in headings), headings)
    en, zh = texts[FILES[0]], texts[FILES[1]]
    expected_en = ["Physical problem", "What is available", "Start here", "Research workflow",
                   "Baselines first, learning second", "Scientific boundaries and data", "Documentation",
                   "Roadmap", "Citation, contact and licensing"]
    expected_zh = ["物理问题", "当前可用内容", "从这里开始", "研究工作流", "基线先行，学习方法随后",
                   "科研边界与数据", "文档导航", "研究路线图", "引用、联系与授权"]
    check("bilingual_home_structure", re.findall(r"^## (.+)$", en, re.M) == expected_en
          and re.findall(r"^## (.+)$", zh, re.M) == expected_zh,
          "Nine semantically mapped homepage sections, plus matching language navigation")
    check("language_navigation", all(text.startswith("[English]") and "[简体中文]" in text.splitlines()[0] for text in texts.values()), "Reciprocal language links")
    check("concise_homepages", all(150 <= len(t.splitlines()) <= 250 for t in [en, zh]),
          {p: len(texts[p].splitlines()) for p in FILES[:2]})
    math = lambda t: re.findall(r"^\$\$\n(.*?)^\$\$", t, re.M | re.S)
    check("bilingual_equations", math(en) == math(zh) and math(texts[FILES[2]]) == math(texts[FILES[3]]),
          "Homepage and detailed guide formula pairs identical")
    old = (ROOT / "run/run_003/checkpoints/before/README.md.snapshot").read_text(encoding="utf-8")
    old_material = old[old.index("## 5. "):old.index("## 10. ")]
    check("detailed_math_preserved", math(old_material) == math(texts[FILES[2]]), "All seven constitutive/inverse/MDP display formulas preserved")
    diagrams = lambda t: re.findall(r"```mermaid\n(.*?)\n```", t, re.S)
    graphcheck = runpy.run_path(str(ROOT / "run/run_002/artifacts/validate_readme.py"))["mermaid_structure"]
    for diagram, kind in zip(diagrams(en), ["architecture", "rl"]):
        graphcheck(diagram, kind)
    check("mermaid_subset_and_parity", len(diagrams(en)) == 2 and diagrams(en) == diagrams(zh),
          "Two matching English diagrams; existing subset parser, not a full renderer")
    expected_image = "docs/figures/spt_setup.svg"
    check("shared_original_svg", all(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", t) == [expected_image] for t in [en, zh]), expected_image)
    check("public_path_privacy", not any(re.search(r"\b[A-Za-z]:[\\/]|file://|artifacts/private/", t) for t in texts.values()),
          "No machine paths or private evidence links")
    check("honest_scope_markers", all(all(token in t for token in ["WARNING", "Planned", "Blocked", "PPO", "SAC", "RQ1", "RQ2", "RQ3"]) for t in [en, zh]),
          "Status/algorithm markers; semantic review still required")
    baseline = json.loads((ROOT / "run/run_003/checkpoints/initial_state.json").read_text(encoding="utf-8"))
    changed = [p for p, digest in baseline["public_tracked_sha256"].items()
               if p not in baseline["allowed_updates"] and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    check("unrelated_tracked_files_preserved", not changed, changed)
    check("user_kickoff_preserved", hashlib.sha256((ROOT / "docs/SP-InvOpt_Project_Kickoff.md").read_bytes()).hexdigest() == baseline["kickoff_sha256"],
          "User-provided source remains unmodified")
    ok = all(c["status"] == "PASS" for c in checks)
    print(json.dumps({"status": "PASS" if ok else "FAIL", "checks": checks,
                      "limits": "Local structural checks; no live GitHub Mermaid/MathJax rendering or scientific validation."}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
