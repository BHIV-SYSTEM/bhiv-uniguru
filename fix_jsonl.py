"""
Strip merge conflict markers from constitutional_semantic_events.jsonl.
Keeps HEAD lines (between <<<<<<< and =======), discards incoming lines
(between ======= and >>>>>>>), and validates every remaining line is valid JSON.
"""
import json
from pathlib import Path

path = Path("review_packets/proof_logs/constitutional_semantic_events.jsonl")
text = path.read_text(encoding="utf-8")

lines = text.splitlines()
cleaned = []
in_conflict = False
keep = True  # True = keep HEAD side, False = discard incoming side

for line in lines:
    if line.startswith("<<<<<<< "):
        in_conflict = True
        keep = True   # HEAD side starts
        continue
    if line.startswith("======="):
        keep = False  # switch to incoming side — discard
        continue
    if line.startswith(">>>>>>> "):
        in_conflict = False
        keep = True
        continue
    if in_conflict and not keep:
        continue
    cleaned.append(line)

# Validate every non-empty line is valid JSON
bad = []
for i, line in enumerate(cleaned, 1):
    if not line.strip():
        continue
    try:
        json.loads(line)
    except json.JSONDecodeError as e:
        bad.append((i, str(e), line[:80]))

if bad:
    print(f"VALIDATION FAILED: {len(bad)} bad lines")
    for lineno, err, preview in bad[:5]:
        print(f"  Line {lineno}: {err} | {preview!r}")
else:
    path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    print(f"OK: wrote {len([l for l in cleaned if l.strip()])} valid JSON lines")
