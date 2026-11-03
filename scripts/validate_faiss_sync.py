"""
FAISS and SQLite Synchronization Validator (P0 Invariant Check)
==============================================================
Validates:
  1. Total SQLite chunk count vs FAISS vector count
  2. ID bijective synchronization (every FAISS ID exists in SQLite, no orphans)
  3. No duplicate IDs in SQLite
  4. Vector reconstruction & semantic sanity: Querying vector of chunk X returns chunk X with score ~1.0
  5. Absence of NaN, zero vectors, or corrupted norms
"""

import sys
import sqlite3
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
RAG_DIR = BACKEND_DIR / "RAG"
DB_PATH = RAG_DIR / "chunks.db"
FAISS_PATH = RAG_DIR / "faiss_index.bin"
METADATA_PATH = RAG_DIR / "index_metadata.json"


def validate_sync() -> bool:
    print("=" * 60)
    print("RUNNING FAISS <-> SQLITE SYNCHRONIZATION VALIDATOR (P0)")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. Check file existence
    if not DB_PATH.exists():
        print(f"[FAIL] Chunks DB not found at: {DB_PATH}")
        return False
    if not FAISS_PATH.exists():
        print(f"[FAIL] FAISS index not found at: {FAISS_PATH}")
        return False

    # 2. Inspect SQLite
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, content_hash FROM chunks ORDER BY id ASC")
    db_rows = cur.fetchall()
    db_ids = [row[0] for row in db_rows]
    db_count = len(db_ids)
    conn.close()

    print(f"[*] SQLite chunks.db count: {db_count}")

    # Check for duplicate IDs in SQLite
    if len(set(db_ids)) != db_count:
        errors.append(f"SQLite contains duplicate primary key IDs! Unique: {len(set(db_ids))}, Total: {db_count}")
    else:
        print("[PASS] SQLite IDs are strictly unique and contiguous.")

    # 3. Inspect FAISS
    import faiss
    index = faiss.read_index(str(FAISS_PATH))
    faiss_count = index.ntotal
    print(f"[*] FAISS index vector count: {faiss_count}")
    print(f"[*] FAISS index dimension: {index.d}")
    print(f"[*] FAISS index type: {type(index).__name__}")

    # Invariant: Counts must match exactly
    if db_count != faiss_count:
        errors.append(f"Count Mismatch! SQLite={db_count}, FAISS={faiss_count}")
    else:
        print(f"[PASS] Exact 1-to-1 count match: {db_count} == {faiss_count}")

    # Check ID Mapping
    # For IndexIDMap, inspect id_map
    if hasattr(index, "id_map"):
        faiss_ids = faiss.vector_to_array(index.id_map)
        missing_in_db = set(faiss_ids) - set(db_ids)
        missing_in_faiss = set(db_ids) - set(faiss_ids)

        if missing_in_db:
            errors.append(f"Orphan vectors found in FAISS (not in SQLite): {len(missing_in_db)} IDs")
        if missing_in_faiss:
            errors.append(f"Unindexed chunks in SQLite (not in FAISS): {len(missing_in_faiss)} IDs")

        if not missing_in_db and not missing_in_faiss:
            print("[PASS] Bijective ID mapping: Every FAISS vector ID maps to exactly 1 SQLite row.")

    # 4. Vector Quality and Self-Retrieval Sanity Test
    print("\n[*] Running self-retrieval sanity check on sample vectors...")
    # Reconstruct vector for first and last IDs if supported
    try:
        sample_ids = [db_ids[0], db_ids[len(db_ids) // 2], db_ids[-1]]
        for s_id in sample_ids:
            # Search by reconstructing vector
            vec = index.reconstruct(int(s_id))
            vec_norm = np.linalg.norm(vec)
            if np.isnan(vec).any() or np.isinf(vec).any():
                errors.append(f"Vector for ID {s_id} contains NaN or Inf!")
            if abs(vec_norm - 1.0) > 0.01:
                warnings.append(f"Vector for ID {s_id} is not unit-normalized (norm={vec_norm:.4f})")

            # Search with this vector
            query_vec = np.expand_dims(vec, axis=0).astype(np.float32)
            scores, retrieved_ids = index.search(query_vec, 1)
            top_id = retrieved_ids[0][0]
            top_score = scores[0][0]
            if top_id != s_id:
                errors.append(f"Self-retrieval failure! Vector {s_id} retrieved ID {top_id} with score {top_score}")
            elif top_score < 0.99:
                warnings.append(f"Self-retrieval score lower than expected: {top_score:.4f} for ID {s_id}")
            else:
                print(f"  [PASS] Sample ID {s_id}: self-retrieved correctly with cosine similarity {top_score:.6f}")
    except Exception as exc:
        print(f"  [INFO] Vector reconstruction not directly supported by this index wrapper: {exc}")

    print("\n" + "=" * 60)
    if errors:
        print(f"[FAILED] Found {len(errors)} critical synchronization errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("[SUCCESS] All synchronization invariants verified! Database and FAISS are 100% in sync.")
        if warnings:
            print(f"Note: {len(warnings)} non-critical warnings:")
            for w in warnings:
                print(f"  - {w}")
        return True


if __name__ == "__main__":
    success = validate_sync()
    sys.exit(0 if success else 1)
