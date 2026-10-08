# Evaluation Results

## Test environment

- Python 3.11.15 in the `aai` environment
- LangGraph 1.2.11
- Pydantic 2.13.5
- Test command: `D:\\miniconda3\\envs\\aai\\python.exe -m pytest -q`

## Automated test result

The current suite completed with **21 passed** tests. The only emitted warning
is a third-party Starlette TestClient deprecation warning and does not affect
the workflow result.

| Area | Verified behavior |
|---|---|
| Retrieval | Hypertension-specific guidance ranks above unrelated documents. |
| Safety | An allergy-medication conflict is high risk. |
| Safety | Workflow-bypass text in untrusted notes is escalated. |
| Medication schedule | A reminder carries its reconciled source fields and optional RxNorm identifier. |
| Medication schedule | PRN medication without an indication and maximum frequency is high risk. |
| Medication schedule | A reviewer cannot introduce a medication reminder through free-text editing. |
| Public tools | Mocked RxNorm, DailyMed, openFDA, and PubMed responses are handled without network-dependent tests. |
| Public tools | An ambiguous RxNorm result never assigns an RxCUI; PubMed results remain curation-only. |
| Output grounding | A reviewer edit that introduces a free-text dose is rechecked and escalated. |
| Output grounding | Medication-action detection requires a known reconciled drug name, avoiding ordinary education-text false positives. |
| Knowledge curation | Candidate evidence is absent from RAG until approved; retired evidence is excluded again. |
| LLM boundary | The LLM context excludes patient ID, medications, allergies, and free-text notes. |
| LLM resilience | API/model failure falls back to deterministic drafting without breaking the workflow. |
| API/UI and mapping | The reviewer dashboard renders and a submitted synthetic case exports a FHIR-shaped Bundle. |
| Routing | Invalid input and high risk cannot enter a finalization path. |
| Review | A complete case pauses until an explicit approval is resumed. |
| End to end | An approved synthetic case finalizes with a reviewer ID. |
| End to end | A high-risk allergy conflict escalates without a reviewer interrupt. |
| API | Submit, inspect, review, and SQLite snapshot persistence work together. |
| Restart recovery | A new application instance resumes the same pending reviewer interrupt from its SQLite checkpoint. |

## Synthetic-case evaluation

Run with:

```bash
python -m app.evaluation.run_cases
```

| Case | Expected safe outcome | Observed outcome |
|---|---|---|
| `complete_case.json` | Wait for mandatory human review | `awaiting_review`, low risk |
| `allergy_conflict_case.json` | Block automatic progress and escalate | `escalated`, high risk |
| `untrusted_note_case.json` | Ignore bypass text and escalate | `escalated`, high risk |
| `prn_missing_details_case.json` | Block finalization for missing PRN indication and maximum frequency | `escalated`, high risk |

## Evaluation limits

These results demonstrate workflow correctness for synthetic teaching cases;
they do not establish clinical effectiveness, medical accuracy, production
safety, or suitability for real patient data. Before any broader evaluation,
the project needs clinician-authored test cases, a formal evidence review, and
approval from the relevant governance process.
