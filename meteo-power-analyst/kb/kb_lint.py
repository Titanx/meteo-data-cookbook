#!/usr/bin/env python3
"""kb_lint.py — 知识库引用可达性 + 索引一致性检查（领域无关）。

七项检查：
  1. 失效知识 ID     引用了 PIT-...-... 但条目文件不存在
  2. 失效链接        markdown 相对链接指向不存在的文件
  3. 失效裸路径      反引号里的 skills/...py 之类路径不存在
  4. 漏登记         条目存在但分类 catalog 没收录（静默失效主因）
  5. 孤儿条目       条目只在 catalog 里列着，没有任何 skill 或条目实质引用
  6. 统计漂移       总目录声称的条目数/成熟度分布与实际不符
  7. 缺字段         条目缺成熟度头部字段（或 id 与文件名不符）

退出码：0=通过、1=有问题。可挂 agent hook 或 CI。
放置位置：<kb>/kb_lint.py，则包根=上一级目录。可用 --kb/--skills/--root 显式指定。
要增删知识类型：改 PREFIX_DIR 并同步 catalog 模板。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from collections import Counter

PREFIX_DIR = {
    "MTD": "methods",
    "DEC": "decisions",
    "EXP": "experiments",
    "PIT": "pitfalls",
    "RCP": "recipes",
}
DIR_PREFIX = {v: k for k, v in PREFIX_DIR.items()}
ID_RE = re.compile(r"\b(MTD|DEC|EXP|PIT|RCP)-(\d{8})-(\d{3})\b")
ENTRY_NAME_RE = re.compile(r"^(MTD|DEC|EXP|PIT|RCP)-\d{8}-\d{3}\.md$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
MD_EXT = (".md", ".py", ".html", ".csv", ".json", ".js", ".txt", ".docx")
PATH_ROOTS = ("skills", "kb", "data", "raw", "references", "templates", "examples")


class Problems:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, check: str, msg: str) -> None:
        self.items.append(f"[{check}] {msg}")

    def __bool__(self) -> bool:
        return bool(self.items)


def is_placeholder(s: str) -> bool:
    return "<" in s or ">" in s


def load_md_files(root: Path, kb_dir: Path, skills_dir: Path) -> list[Path]:
    files: list[Path] = []
    for base in (root, kb_dir, skills_dir):
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            files.append(p)
    files = sorted(set(files))
    return files


def entry_files(kb_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for prefix, sub in PREFIX_DIR.items():
        d = kb_dir / sub
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            if ENTRY_NAME_RE.match(p.name):
                out[p.stem] = p
    return out


def parse_maturity(text: str) -> str | None:
    m = re.search(r"^maturity:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


def parse_id_field(text: str) -> str | None:
    m = re.search(r"^id:\s*(\S+)", text, re.M)
    return m.group(1) if m else None


def main() -> int:
    here = Path(__file__).resolve().parent
    default_root = here.parent
    ap = argparse.ArgumentParser(description="知识库 lint：引用可达性 + 索引一致性")
    ap.add_argument("--root", default=str(default_root), help="包根目录")
    ap.add_argument("--kb", default=None, help="知识库目录名（默认脚本所在目录名）")
    ap.add_argument("--skills", default="skills", help="能力层目录名")
    ap.add_argument("--allow-orphans", action="store_true",
                    help="跳过孤儿条目检查（知识库刚起步、还没有 skill 引用时）")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    kb_name = args.kb or here.name
    kb_dir = root / kb_name
    skills_dir = root / args.skills
    templates_dir = kb_dir / "templates"
    problems = Problems()

    if not kb_dir.is_dir():
        print(f"错误：知识库目录不存在: {kb_dir}", file=sys.stderr)
        return 1

    entries = entry_files(kb_dir)
    md_files = load_md_files(root, kb_dir, skills_dir)
    # raw/ 是只读原始材料：其内部路径描述的是原属包的结构，不适用本包检查；
    # 仅检查本包自己维护的登记表 raw/README.md
    raw_dir = root / "raw"
    md_files = [f for f in md_files
                if not (raw_dir in f.parents and f.name != "README.md")]

    # ---- 7. 缺字段（先做，后面统计要用） ----
    for eid, path in sorted(entries.items()):
        text = path.read_text(encoding="utf-8", errors="replace")
        if parse_maturity(text) is None:
            problems.add("缺字段", f"{eid} 缺 maturity 头部字段: {path}")
        id_field = parse_id_field(text)
        if id_field != eid:
            problems.add("缺字段", f"{eid} frontmatter id ({id_field}) 与文件名不符: {path}")

    # ---- 1. 失效知识 ID ----
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in ID_RE.finditer(text):
            eid = m.group(0)
            if eid not in entries:
                problems.add("失效知识 ID", f"{f.relative_to(root)} 引用了不存在的 {eid}")

    # ---- 2. 失效链接 ----
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            if is_placeholder(target):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (f.parent / path_part).resolve()
            if not resolved.exists():
                problems.add("失效链接",
                             f"{f.relative_to(root)} 链接指向不存在的文件: {target}")

    # ---- 3. 失效裸路径 ----
    for f in md_files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in INLINE_CODE_RE.finditer(text):
            for token in m.group(1).split():
                if "/" not in token or is_placeholder(token):
                    continue
                if token.startswith(("http://", "https://")) or "*" in token:
                    continue
                if not (token.endswith(MD_EXT) or token.split("/")[0] in PATH_ROOTS
                        or token.endswith("/")):
                    continue
                if (root / token).exists() or (f.parent / token).exists():
                    continue
                problems.add("失效裸路径",
                             f"{f.relative_to(root)} 反引号路径不存在: {token}")

    # ---- 4. 漏登记 ----
    for eid, path in sorted(entries.items()):
        prefix = eid.split("-", 1)[0]
        catalog = kb_dir / PREFIX_DIR[prefix] / "catalog.md"
        if not catalog.exists():
            problems.add("漏登记", f"分类 catalog 不存在: {catalog}")
            continue
        if eid not in catalog.read_text(encoding="utf-8", errors="replace"):
            problems.add("漏登记", f"{eid} 存在但未登记进 {catalog.relative_to(root)}")

    # ---- 5. 孤儿条目 ----
    if not args.allow_orphans:
        catalog_files = {kb_dir / sub / "catalog.md" for sub in PREFIX_DIR.values()}
        catalog_files.add(kb_dir / "catalog.md")
        # 自引用不算：条目从自身文件中收集到的引用需剔除
        referenced: set[str] = set()
        for f in md_files:
            if f in catalog_files or (templates_dir in f.parents):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in ID_RE.finditer(text):
                rid = m.group(0)
                if f == entries.get(rid):
                    continue
                referenced.add(rid)
        for eid in sorted(entries):
            if eid not in referenced:
                problems.add("孤儿条目", f"{eid} 没有被任何 skill 或条目实质引用")

    # ---- 6. 统计漂移 ----
    master = kb_dir / "catalog.md"
    if master.exists():
        text = master.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(
            r"^\|\s*(\w+)\s*\((MTD|DEC|EXP|PIT|RCP)\)\s*\|\s*(\d+)\s*\|\s*"
            r"(?:—|-|draft\s*(\d+)\s*/\s*verified\s*(\d+)\s*/\s*proven\s*(\d+))",
            text, re.M,
        ):
            name, prefix, count, d, v, p = m.groups()
            actual = [e for e in entries if e.startswith(prefix + "-")]
            if int(count) != len(actual):
                problems.add("统计漂移",
                             f"总目录声称 {name} {count} 条，实际 {len(actual)} 条")
            if d is not None:
                mat = Counter(
                    parse_maturity(entries[e].read_text(encoding="utf-8",
                                                        errors="replace")) or "MISSING"
                    for e in actual
                )
                for level, claimed in (("draft", int(d)), ("verified", int(v)),
                                       ("proven", int(p))):
                    if mat.get(level, 0) != claimed:
                        problems.add(
                            "统计漂移",
                            f"{name} {level} 声称 {claimed}，实际 {mat.get(level, 0)}")
        m_ex = re.search(r"^\|\s*examples\s*\|\s*(\d+)\s*\|", text, re.M)
        if m_ex:
            ex_dir = kb_dir / "examples"
            actual_ex = [p for p in ex_dir.glob("*.md")
                         if p.name != "README.md"] if ex_dir.is_dir() else []
            if int(m_ex.group(1)) != len(actual_ex):
                problems.add("统计漂移",
                             f"总目录声称 examples {m_ex.group(1)} 条，实际 {len(actual_ex)} 条")

    # ---- 汇总 ----
    if problems:
        print(f"kb_lint 发现 {len(problems.items)} 个问题：\n")
        for item in problems.items:
            print(f"  {item}")
        print("\n修复后重跑：python kb/kb_lint.py")
        return 1
    print(f"kb_lint 通过：{len(entries)} 条知识，{len(md_files)} 个 md 文件检查完毕。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
