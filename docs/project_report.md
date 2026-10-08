# Discharge Planning Agent Project Report

## Executive summary

The project implements a bounded agentic workflow for simulated discharge
planning. It uses LangGraph state transitions, local retrieval, deterministic
safety checks, mandatory human review, and an auditable final output. The
system is deliberately assistive: it produces a draft for review and cannot
make a final clinical decision by itself.

## Delivered capabilities

1. Structured simulated-case intake through Pydantic validation.
2. Stateful LangGraph orchestration with conditional routing.
3. Local, versioned RAG evidence retrieval.
4. Deterministic drafting of medication reminders and follow-up tasks from
   validated case facts.
5. Optional structured-output LLM drafting for general care and warning text.
6. Safety escalation for high-risk or unsupported situations.
7. Mandatory reviewer approval, edit, reject, and escalate actions.
8. SQLite storage of case snapshots and audit events.
9. FastAPI endpoints and OpenAPI documentation for demonstration.
10. Automated tests and synthetic positive/negative evaluation cases.

## Requirements traceability

| Requirement | Implementation |
|---|---|
| Stateful agent workflow | `app/graph/workflow.py` and `app/graph/state.py` |
| RAG grounding | `app/tools/retrieval_tool.py` and `app/data/knowledge_base/` |
| Structured outputs | `app/schemas/patient_schema.py` |
| Safety and escalation | `app/tools/safety_tool.py` |
| Human-in-the-loop | LangGraph interrupt in `app/graph/nodes.py` |
| Auditability | timestamped graph events plus `app/persistence/` |
| Usable demonstration | `app/api/main.py`, `app/graph/demo.py`, and `app/evaluation/` |

## How to demonstrate

1. Run `python -m pytest -q` to show automated verification.
2. Run `python app/graph/demo.py` to show review interruption and explicit
   approval.
3. Run `python -m app.evaluation.run_cases` to show safe handling of complete,
   allergy-conflict, and untrusted-note cases.
4. Start `uvicorn app.api.main:app --reload`, open `/docs`, submit a synthetic
   case, inspect retrieved evidence and audit data, then post a reviewer action.

## Next development priorities

1. Replace the demo lexical retriever with an evaluated embedding or hybrid
   retriever while preserving evidence metadata and version control.
2. Add clinician-authored synthetic test cases and evaluate citation coverage,
   unsafe-output capture, reviewer workload, and readability.
3. Improve the reviewer-facing UI beyond OpenAPI documentation, including
   evidence-to-instruction links and edit diffs.
4. Keep the safety boundary unchanged unless an approved clinical governance
   process expands the scope.
