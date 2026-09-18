```powershell
codebase/
├── pyproject.toml
├── src/
│   └── skynet_core/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── transcript.py
│       │   ├── meeting.py
│       │   └── review.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── audio/
│       │   │   ├── __init__.py
│       │   │   └── base.py
│       │   └── text/
│       │       ├── __init__.py
│       │       └── base.py
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── contracts.py
│       │   ├── meeting_analyzer.py
│       │   └── evidence_checker.py
│       ├── agents/
│       │   ├── __init__.py
│       │   └── clarification.py
│       ├── tools/
│       │   ├── __init__.py
│       │   └── contracts.py
│       ├── review.py
│       └── pipeline/
│           ├── __init__.py
│           └── meeting.py
└── tests/
    ├── test_pipeline.py
    ├── test_review_state.py
    └── test_clarification_agent.py
```
