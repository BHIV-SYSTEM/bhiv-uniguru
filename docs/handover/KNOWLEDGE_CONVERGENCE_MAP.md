# Knowledge Convergence Map

## Runtime paths

```text
Curriculum request
  -> backend/service/uniguru_runtime_api.py
  -> retrieval/retrieval_engine.py
  -> masterdb/balbharti/canonical_dataset.json
  -> filters + ranking + evidence handle
  -> governed runtime response

Kosha/ecosystem request
  -> backend/service/api.py or backend/service/uniguru_runtime_api.py
  -> backend/kosha/deterministic_pipeline.py
  -> KoshaLoader -> backend/data/kosha/*.json / kosha_entries.jsonl
  -> KoshaRetriever + deterministic evidence selection
  -> backend/convergence/convergence_runtime.py
  -> authority tiering, deduplication, sentence claim binding, replay record

Sanskrit request
  -> /runtime/sanskrit/decode
  -> backend/ontology/sanskrit_decoder.py
  -> in-memory SanskritRegistry from backend/knowledge/sanskrit/*.md
  -> deterministic reads of Kosha JSON/JSONL, master_index.json, and MASTERDB
  -> eight source-scoped stages + civilizational graph + provenance/hash

General Markdown knowledge
  -> backend/core/rules/retrieval.py
  -> backend/retrieval/retriever.py
  -> backend/knowledge/**/*.md
  -> lexical retrieval and optional derived FAISS/SQLite candidate search
  -> ontology resolver/graph reasoner + trace
```

The first three paths have distinct source scopes and should remain distinct adapters. Convergence contracts can standardize evidence representation without making their underlying datasets interchangeable.

## Registries and graph boundaries

| Component | State/authority boundary | Convergence relationship |
|---|---|---|
| `backend/ontology/sanskrit/schema.py` + `SanskritRegistry` | Immutable lexical concepts held in memory. | Decoder reads source Markdown and serializes the concept using the existing dictionary schema. Nested relations are now immutable tuples in memory. |
| `backend/ontology/registry.py` + `OntologyGraph` | Snapshot-bound concepts, domain IDs, versions, and hashes. | Used for canonical ontology references and graph reasoning; separate from Sanskrit lexical concepts. |
| `backend/knowledge/civilizational_graph_expansion.json` | Static Sanskrit/civilizational expansion input. | Read by the knowledge-object builder/decoder; should not be confused with the domain snapshot graph. |
| MasterDB curriculum graph | Built from the current MasterDB rows at retrieval time. | Captures grade/chapter relationships; it is not the civilizational graph. |
| `backend/convergence/` | Generic evidence contract, source authority, deduplication, sentence claims, and replay. | The runtime pipeline is called by the local ecosystem API. The unmatched-sentence binding defect was corrected without changing the response shape. |
| `retrieval/knowledge_convergence.py` | MasterDB record adapter and deterministic retrieval-run helper. | Separate utility; a repository-wide call-site search found no production runtime caller. Its answer-level claim helper still binds a whole summary to only the first evidence item and needs an owner-approved claim policy before being made active. |

## Authority labels versus physical stores

- `MASTERDB` resolves to the canonical dataset path, but the validator cannot currently grant canonical authority because `source_reference` is absent from every row.
- `AKASHIC` and `KOSHA_JSON` are separate keys in the policy map but share the `backend/data/kosha/` source family. Preserve the keys for compatibility; do not replicate or double-count their records.
- `MARKDOWN_CORPUS` is a set of primary text files; the FAISS index is derived from a subset of those files and must not be elevated to an independent authority.
- `FAISS_VECTOR_INDEX` now points to the real builder, `backend/scripts/build_rag_index.py`. That builder reads only Markdown below `backend/knowledge/`, stores file/chunk metadata, and does not create the canonical-object mapping described by the older policy document.
- `LLM_FALLBACK` is a fallback tier, not a primary knowledge source. An unmatched sentence with unrelated selected evidence now receives an explicit unverified binding in `backend/convergence/convergence_runtime.py`.

## Archive-specific retrieval discrepancy

The ZIP includes a primary `UnifiedRAGEngine_v3` dispatch in `backend/retrieval/retriever.py` and `backend/retrieval/unified_rag_engine.py`. The checked-out branch has neither that module nor the dispatch. The archive's `retrieval/retrieval_engine.py` also differs from the checked-out scoring implementation. This audit did not transplant either implementation: doing so would overwrite branch behavior and could silently change runtime contracts. Reconcile the branch/archive version before release-level retrieval claims.
