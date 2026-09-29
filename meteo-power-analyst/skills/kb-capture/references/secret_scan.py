#!/usr/bin/env python3
"""secret_scan.py — 提交前的密钥/凭据闸门。

用法：
    python skills/kb-capture/references/secret_scan.py            # 检查包内文本文件
    python skills/kb-capture/references/secret_scan.py --strict    # 未跟踪文件里的命中也算失败

两道检查：
  1. 值级比对：若包根或其上一级存在 .env，把其中的值当作已知密钥，在包内逐值精确搜索
     （零误报；这是主力检查）
  2. 形态识别：识别常见密钥形态（赋值型长值、**裸变量名赋值**如 `USER=`/`PWD=`/`USERID=`、
字典键凭据、URL 里的 token、已知前缀、JWT）。
刻意**不**把裸的 64 位十六进制当作密钥——会话摘要的 summary_digest 就是这种形态，会大量误报。

教训（2026-09-30）：只搜 `password|token` 会漏掉 `PWD = "..."` 和 `USER = "..."` 这种写法，
而正是它把一个真实口令带进了远端。裸变量名必须一起覆盖。

分级：
  - 命中位于 **git 已跟踪** 文件 → 失败（退出码 1），因为推送会把它们带出去
  - 命中位于未跟踪/被忽略文件（如 raw/ 本地层）→ 警告（--strict 下也算失败）
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TEXT_EXT = {".md", ".py", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini",
            ".cfg", ".csv", ".tsv", ".js", ".html", ".css", ".sh", ".ps1", ".env", ""}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "data", "output", "dist", "build",
             ".venv", "venv", ".mypy_cache", ".pytest_cache"}

FORM_PATTERNS = [
    ("赋值型长值", re.compile(
        r"(?i)\b(?:api[_-]?key|apikey|access[_-]?key|client[_-]?secret|secret[_-]?key|"
        r"auth[_-]?token|security[_-]?token|password|passwd)\b\s*[\"']?\s*[:=]\s*"
        r"[\"']?([A-Za-z0-9\-_./+]{20,})")),
    ("裸变量名赋值", re.compile(
        r"""(?i)^[ \t]*(?:export[ \t]+)?
        (USER|USERID|USER_ID|USERNAME|EMAIL|PWD|PASS|PASSWORD|PASSWD|APPKEY|APP_KEY|
         SECRET|SECRET_KEY|ACCESS_KEY|CLIENT_SECRET|CREDENTIAL)
        [ \t]*[:=][ \t]*["']([^"'\n]{4,})["']""", re.X | re.M)),
    ("字典键凭据", re.compile(
        r"""(?i)["'](userId|user_id|pwd|password|passwd|secret|apiKey|api_key|appKey|
        accessKey|access_key|token|securityToken)["']\s*:\s*["']([^"'\n]{6,})["']""", re.X)),
    ("URL 中的 token", re.compile(
        r"(?i)[?&](?:securityToken|apikey|api_key|token|access_token|key)=([A-Za-z0-9\-_.]{20,})")),
    ("已知前缀", re.compile(r"\b(EA_[A-Za-z0-9]{16,}|sk-[A-Za-z0-9\-_]{24,}|"
                            r"gh[pousr]_[A-Za-z0-9]{24,}|github_pat_[A-Za-z0-9_]{24,}|"
                            r"AKIA[0-9A-Z]{16})\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}\.[A-Za-z0-9\-_]{10,}")),
]
PLACEHOLDER = ("your_", "your-", "xxx", "<", ">", "example", "placeholder", "sample",
               "todo", "test", "dummy", "redacted", "填入", "你的",
               "os.getenv", "getenv", "environ", "os.environ", "args.", "self.",
               "config[", "config.", "settings.", "none", "null")


def mask(v: str) -> str:
    return v[:4] + "*" * 8 + v[-4:] if len(v) > 10 else v[:2] + "***"


def load_dotenv(root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for cand in (root / ".env", root.parent / ".env"):
        if not cand.is_file():
            continue
        for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip("\"'")
            if len(v) >= 16:
                out.append((k.strip(), v))
        break
    return out


def tracked_files(root: Path) -> set[Path]:
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                           capture_output=True, text=True)
    except Exception:
        return set()
    if r.returncode != 0:
        return set()
    return {(root / p).resolve() for p in r.stdout.split("\0") if p}


def main() -> int:
    here = Path(__file__).resolve()
    root = here.parents[3] if len(here.parents) > 3 else here.parent
    ap = argparse.ArgumentParser(description="提交前的密钥/凭据闸门")
    ap.add_argument("--root", default=str(root), help="包根目录")
    ap.add_argument("--strict", action="store_true", help="未跟踪文件中的命中也算失败")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    keys = load_dotenv(root)
    tracked = tracked_files(root)

    hits: list[tuple[Path, str, str, bool]] = []   # path, 说明, 掩码, 是否已跟踪
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        is_tracked = p.resolve() in tracked
        for name, val in keys:
            if val in txt:
                hits.append((p, "已知密钥 %s" % name, mask(val), is_tracked))
        for name, rx in FORM_PATTERNS:
            for m in rx.finditer(txt):
                val = m.group(m.lastindex) if m.lastindex else m.group(0)
                if any(ph in val.lower() for ph in PLACEHOLDER):
                    continue
                hits.append((p, name, mask(val), is_tracked))

    tracked_hits = [h for h in hits if h[3]]
    local_hits = [h for h in hits if not h[3]]

    print("包根: %s；读入已知密钥 %d 个；已跟踪文件 %d 个" % (root, len(keys), len(tracked)))
    if tracked_hits:
        print("\n⛔ 已跟踪文件中发现 %d 处凭据（推送会带出去）：" % len(tracked_hits))
        for p, what, mk, _ in tracked_hits:
            print("   [%s] %s  %s" % (what, p.relative_to(root), mk))
    if local_hits:
        print("\n⚠ 未跟踪/本地文件中发现 %d 处凭据（不会被推送，但建议脱敏）：" % len(local_hits))
        for p, what, mk, _ in local_hits:
            print("   [%s] %s  %s" % (what, p.relative_to(root), mk))
    if not hits:
        print("\n✅ 未发现凭据形态。")
    if tracked_hits or (args.strict and local_hits):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
