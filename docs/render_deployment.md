# Render presentation deployment

The root render.yaml defines a free Python web service in Singapore. Import
the SixiangH/discharge-agent repository as a Render Blueprint and deploy main.
The private repository must be accessible to the Render GitHub integration.
The Blueprint explicitly uses the free plan and creates no paid database or disk.

Manual Web Service settings, if not using the Blueprint:

| Setting | Value |
|---|---|
| Language | Python 3 |
| Branch | main |
| Root directory | Leave blank |
| Build command | pip install -r requirements-render.txt |
| Start command | uvicorn app.api.main:app --host 0.0.0.0 --port $PORT --workers 1 |
| Health check path | / |
| Instance type | Free |
| Region | Singapore |
| PYTHON_VERSION | 3.11.15 |
| DISCHARGE_LLM_ENABLED | false |
| EXTERNAL_EVIDENCE_ENABLED | false |

The presentation baseline uses deterministic drafting and local evidence.
No API key or local .env file is uploaded. Optional LLM and public evidence
remain available in code, but are disabled for the baseline to avoid relying
on third-party API availability during a live demonstration. The deployment
pins direct runtime dependencies; it is not a complete transitive lockfile.

Use one worker: the current SQLite/checkpoint setup is a single-process prototype.
The dashboard is served at / and API documentation at /docs. Once the service
is live, verify a complete synthetic case pauses at awaiting_review, explicit
approval produces finalized, final-plan export succeeds only after approval,
and an allergy-conflict case terminates as escalated.

## Presentation preparation

Open the service a few minutes before presenting and wait for the reviewer
dashboard to appear. Render Free services spin down after 15 minutes without
inbound traffic and can take about a minute to wake up. Keep the four input
fixtures from app/data/synthetic_cases available locally for JSON upload.
Download approved outputs if you need to retain them. Do not deploy new commits
during the demonstration; automatic deploys are disabled in the Blueprint.

The SQLite case database, checkpoints, cache, and locally curated changes use
ephemeral storage on this free configuration. They are lost on restart,
redeploy, or spin-down. Re-submit the synthetic input after a fresh start.
There is no authentication: the public URL is a shared teaching demo, not a
private clinical workspace. Use synthetic cases only, as for the local prototype.

Official references:

- https://render.com/docs/deploy-fastapi
- https://render.com/docs/free
- https://render.com/docs/blueprint-spec
- https://render.com/docs/python-version
