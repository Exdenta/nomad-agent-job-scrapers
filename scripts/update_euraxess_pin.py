"""Update maintained EURAXESS release pins; run tests before publication."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("old")
parser.add_argument("new")
args = parser.parse_args()
if not all(re.fullmatch(r"1\.0\.[0-9]+", value) for value in (args.old,args.new)):
    parser.error("pins must be exact 1.0.x build numbers")
root=Path(__file__).resolve().parents[1]
for p in root.rglob("*"):
    if not p.is_file() or ".git" in p.parts or p.suffix not in {".md",".html",".json",".yaml",".py"}:
        continue
    if "changelog" in p.parts or "CEO_REPORT" in p.name or p.name in {"implementation-plan.md","SUCCESS_CRITERIA.md"}:
        continue
    text=p.read_text()
    if args.old in text and ("euraxess" in str(p).lower() or "euraxess" in text.lower()):
        p.write_text(text.replace(args.old,args.new))
        print(p.relative_to(root))
