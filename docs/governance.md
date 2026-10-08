# Prototype Governance Boundary

## Permitted use

This is a local teaching prototype for de-identified, synthetic cases only. It
does not diagnose, prescribe, change a medication, connect to an EHR, or issue
an autonomous discharge order.

## Human accountability

Only a typed `clinician` or `pharmacist` reviewer role may record a decision in
the prototype. This is an audit field and input constraint, **not** production
authentication or authorization. Every final plan requires explicit approval.

## External data minimisation

When enabled, external medication lookups send only a medication name and a
confirmed RxCUI. They do not send patient identifiers, age, diagnosis, notes,
allergies, doses, discharge summaries, or reviewer identifiers. Public-service
responses are locally cached and audited. PubMed results remain unapproved
curation candidates until a human adds a reviewed source to the knowledge base.

## Retention and release

SQLite snapshots, external cache records, and generated exports are local
prototype artifacts. Do not store real patient data in them. Any deployment
would require institutional privacy review, authenticated identity, access
control, encryption, formal retention policy, clinical validation, and legal/
regulatory approval.
