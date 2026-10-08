# Knowledge Curation Workflow

Only `approved` evidence can be retrieved by the runtime RAG tool.

```text
Public source or PubMed metadata candidate
        ↓
POST /knowledge/candidates
        ↓
status = candidate (never available to RAG)
        ↓
clinician/pharmacist reviews source, scope, expiry and reason
        ↓
POST /knowledge/{evidence_id}/review
        ↓
approve → approved → available to the next retrieval
retire/reject → retired → unavailable to retrieval
```

## Required candidate fields

- title and concise, bounded content;
- public `source_url`;
- keywords used for retrieval;
- review scope, explicitly stating what the content can and cannot support;
- optional expiry date.

## Required review record

- typed reviewer role (`clinician` or `pharmacist`);
- reviewer identifier;
- approval, retirement, or rejection decision;
- review reason;
- replacement evidence ID when retiring a source.

The repository is a local JSON store for this teaching prototype. It is not a
substitute for a production content-governance platform, formal clinical
literature appraisal, authenticated identity, or change-control process.
