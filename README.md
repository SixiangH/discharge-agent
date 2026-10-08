# Discharge Planning Agent

This project is a LangGraph-based, simulated discharge-planning prototype. It is
an assistive teaching demonstration, not clinical decision support, and must not
be used with real patient data.

## Project Structure

- `app/graph` - workflow and graph nodes
- `app/tools` - deterministic retrieval and safety tools
- `app/schemas` - Pydantic schemas
- `app/data/knowledge_base` - simulated knowledge data
- `app/data/synthetic_cases` - positive and safety-focused demo cases
- `app/api` - local reviewer API and OpenAPI interface
- `app/persistence` - SQLite case and audit snapshots
- `tests` - test cases

## Quick Start

1. Create a virtual environment
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the demo. It pauses at an explicit human-review checkpoint and resumes
   only with the demo review decision:
   ```bash
   python app/graph/demo.py
   ```

4. Run all synthetic safety cases:
   ```bash
   python -m app.evaluation.run_cases
   ```

5. Start the local reviewer API, then open `http://127.0.0.1:8000/docs`:
   ```bash
   uvicorn app.api.main:app --reload
   ```

   Open `http://127.0.0.1:8000/` for the structured reviewer dashboard. It
   provides case-list/risk filtering, evidence and safety cards, limited draft
   editing, and explicit review actions. Choose **one** input method: upload a
   local synthetic `.json` case or paste JSON. Both wait for the same **Create
   draft** confirmation button and use the validated case-submission workflow;
   mixing both inputs is blocked. Medication reminders remain read-only.

## Current Status

The prototype includes:
- Pydantic-validated simulated cases and structured final output
- a stateful LangGraph workflow with a resumable reviewer interrupt
- transparent local retrieval with evidence metadata
- deterministic checks for medication reconciliation, allergy conflicts,
  duplicate medication entries, missing evidence, and workflow-bypass text
- a deterministic medication reconciliation and reminder tool: it produces
  traceable schedule items only from supplied discharge-order fields, flags
  missing PRN indication/limit, and never calculates a dose or administration time
- high-risk escalation that cannot auto-finalize
- append-only in-memory audit events and positive/negative unit tests
- SQLite persistence for case snapshots and audit events
- a local reviewer dashboard with submit, inspect, evidence, safety, and review controls
- FHIR R4-shaped synthetic Bundle export for MedicationRequest, AllergyIntolerance, and CarePlan mapping drafts
- six versioned simulated guidance documents and three synthetic demo cases

## Optional controlled LLM mode

The default draft generator is deterministic. To opt in to structured OpenAI
generation, copy `.env.example` to `.env`, set `DISCHARGE_LLM_ENABLED=true`,
and provide your own `OPENAI_API_KEY`. The default model is `gpt-4.1-mini`,
with a 500-output-token and 20-second limit. The LLM receives only a minimized
synthetic discharge context and approved local evidence; it may write only care
and warning text. Medication schedules and follow-up tasks always come from
validated input. An API/model/validation failure automatically falls back to the
deterministic generator, and every output still passes grounding, safety checks,
and mandatory human review.

## Optional public external evidence tools

Set `EXTERNAL_EVIDENCE_ENABLED=true` to make the medication workflow perform
real, read-only calls to public **RxNav/RxNorm**, **DailyMed**, and **openFDA**
services. Only the medication name and a confirmed RxCUI are sent externally;
the system never sends patient identifiers, notes, diagnoses, allergies, doses,
or discharge summaries. Results are cached locally in
`app/data/external_evidence_cache.db` and presented as reviewer evidence, not
as prescribing advice. Service failure, ambiguity, or no terminology match
requires reviewer confirmation and never causes a guessed result.

The local API also exposes `POST /evidence/literature-search` for a generic
topic-only PubMed bibliography search. Its results are explicitly unapproved
curation candidates and are never added directly to runtime RAG or discharge
instructions.

## Safety boundary

The system only restates the supplied medication and follow-up plan. It does not
diagnose, prescribe, alter dosages, calculate administration times, modify
records, or infer missing clinical facts. Medication reminders cannot be edited
as free text: they must be regenerated from reconciled source fields. A reviewer
must explicitly approve every finalized plan.

## Project documentation

- [Architecture](docs/architecture.md)
- [Evaluation results](docs/evaluation_results.md)
- [Project report](docs/project_report.md)
- [Prototype governance boundary](docs/governance.md)
- [Knowledge curation workflow](docs/knowledge_curation_workflow.md)
