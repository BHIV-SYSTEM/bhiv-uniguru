# Dependency Graph — Code Review Guide

**Owner:** Isha Singh

---

## 1. Module Dependency Map

```
uniguru_runtime_api.py
 ├── ontology/sanskrit_decoder.py
 │    ├── ontology/sanskrit/schema.py
 │    ├── ontology/sanskrit/registry.py
 │    ├── ontology/sanskrit/evidence.py
 │    └── ontology/sanskrit/provenance.py
 ├── convergence/convergence_runtime.py
 │    ├── convergence/authority_contract.py
 │    ├── convergence/canonical_object.py
 │    └── convergence/retrieval_evidence_contract.py
 └── kosha/deterministic_pipeline.py
      └── memory/constitutional_semantic_memory.py
```

---

## 2. External Dependencies

- **FastAPI**: API framework
- **Pydantic**: Input validation
- **Pytest**: Automated test runner
- **React 18 & Vite**: Frontend runtime & bundler
- **Three.js / Lucide-React / FontAwesome**: Visual UI components
