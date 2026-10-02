import json
from pathlib import Path

path = Path("backend/ontology/seed_entities.json")
entities = json.loads(path.read_text(encoding="utf-8"))

# Add Om / AUM entity
om_entity = {
    "canonical": "Om",
    "domain": "upanishads",
    "type": "concept",
    "aliases": ["AUM", "Aum", "Pranava", "OM", "om", "aum"],
    "concepts": ["primordial sound", "brahman", "meditation", "mantra"]
}

# Only add if not already present
if not any(e.get("canonical", "").lower() == "om" for e in entities):
    entities.append(om_entity)
    path.write_text(json.dumps(entities, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Added Om entity. Total entities: {len(entities)}")
else:
    print("Om entity already present")
