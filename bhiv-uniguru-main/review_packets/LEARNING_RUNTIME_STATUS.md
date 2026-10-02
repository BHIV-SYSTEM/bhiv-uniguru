# LEARNING Runtime Status

## Sprint Goal
Build the student learning intelligence layer on top of the canonical UniGuru runtime so each curriculum query returns grounded answers, follow-up guidance, and practice recommendations.

## Current Status
- Added learning intelligence modules under `learning_runtime/`.
- Added curriculum retrieval modules under `retrieval/` with grade-aware, medium-aware, subject-aware, chapter/concept scoring.
- Learning output includes:
  - curriculum mapping
  - concept identification
  - learning outcome
  - follow-up concepts
  - practice recommendations
  - remediation suggestions
  - learning path suggestions
  - concept dependency mapping
- The canonical runtime now extends `backend/service/uniguru_runtime_api.py` with curriculum-aware retrieval and student learning guidance.
- Demonstration proof covers five student-style scenarios: Grade 2 Marathi/Mathematics, Grade 5 History, Grade 7 Geography, Grade 10 Science, and Grade 8 English.

## Key Assets
- `learning_runtime/learning_intelligence.py`
- `learning_runtime/learning_path_generator.py`
- `learning_runtime/learning_gap_detector.py`
- `learning_runtime/practice_recommender.py`
- `learning_runtime/runtime.py`
- `retrieval/retrieval_engine.py`
- `retrieval/retrieval_ranking.py`
- `retrieval/curriculum_graph.json`
- `review_packets/proof_logs/retrieval_quality_report.json`
- `review_packets/proof_logs/learning_intelligence_demo.json`

## Known Limitations
- Student history and personalized progress tracking are not yet implemented.
- The system uses a synthetic curriculum expansion seed rather than fully verified Balbharti textbook extracts.
- Learning recommendations are based on matched curriculum records and related concept guidance only.
