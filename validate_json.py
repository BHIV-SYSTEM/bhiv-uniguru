import json, os, sys

d = "review_packets/integration_proof"
files = [f for f in os.listdir(d) if f.endswith(".json")]
bad = []
for f in files:
    path = os.path.join(d, f)
    try:
        with open(path, encoding="utf-8") as fh:
            json.load(fh)
    except Exception as e:
        bad.append((f, str(e)))

print(f"Total JSON files: {len(files)}")
if bad:
    for f, e in bad:
        print(f"FAIL: {f}: {e}")
    sys.exit(1)
else:
    print("All JSON files parse OK")
