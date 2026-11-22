# DIGIT Engineering Workbench

The local prototype takes a structured PGR complaint subtype request through FRS and SRS drafts, evidence-backed routing, a configuration diff, a citizen selector preview and acceptance checks.

## Run locally

From the repository root with Python 3.11 or newer:

```powershell
python -m digit_harness.server
```

Open [the local workbench](http://127.0.0.1:8090/) and select **Run workflow** for the supplied missed garbage pickup example. The run record can be downloaded and is stored under `.local/runs`, which Git ignores.

```powershell
python -m unittest discover -s tests -v
```

## Langflow

Create a review flow with Chat Input, a prompt/model component, and Chat Output. The flow receives JSON in the chat message with a task, the requirement and source evidence. Set these environment variables in the terminal before launching the workbench:

```powershell
$env:HARNESS_LANGFLOW_URL = 'http://127.0.0.1:7860'
$env:HARNESS_LANGFLOW_FLOW_ID = '<flow ID>'
$env:HARNESS_LANGFLOW_API_KEY = '<key, if required>'
python -m digit_harness.server
```

Configure an on-prem endpoint or a SaaS provider such as OpenAI or OpenRouter in Langflow. The checkbox explicitly sends the requirement to the configured flow. Its response appears as advisory text. Routing and fixture validation run in Python. Use an unmarked checkbox to run locally without inference.

## Implementation status

| Part | Local prototype |
| --- | --- |
| Knowledge | Three versioned evidence records and a synthetic PGR catalog. Upstream source and tenant ingestion are pending. |
| Requirements | A structured form and generated FRS/SRS drafts. Conversational intake and document/image ingestion are pending. |
| Decision | Python rules accept a supported catalog change and route extensions or new modules for review. OPA and KEV integration are pending. |
| Execution | A local fixture renders the resulting catalog and persists the run. The diff targets the fixture format. A real DIGIT deployment adapter and integration checks are pending. |
| Model | Optional Langflow Chat Output integration. Live on-prem and SaaS flows require configuration and verification. |
| GitHub | Local Git history and a Windows/Linux test workflow. |

## Repository layout

- `digit_harness/knowledge.json` holds baseline claims with their source and scope.
- `digit_harness/workflow.py` owns deterministic routing and fixture checks.
- `digit_harness/model.py` calls the optional advisory flow.
- `digit_harness/server.py` owns local HTTP and run persistence.
- `digit_harness/index.html` is the workbench UI.
- `tests/` covers routing, validation, and HTTP persistence.
- `.github/workflows/ci.yml` runs the suite on GitHub.

## Publish the workbench and deploy on Hostinger

Set GitHub Actions secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` with push access. A push to `main` runs **Build and publish workbench**, which can also be started manually. The workflow runs the tests, builds the Linux container, smoke-tests a persisted fixture run, and pushes `mishramesh/ai-to-digit` tagged with the commit SHA.

Use [deploy/compose.yaml](deploy/compose.yaml) in Hostinger Docker Manager and set `WORKBENCH_IMAGE` to the published image including its SHA tag. A private image requires registry pull access on the VPS. Run records are stored in a Docker volume. The published port is loopback-only and the app expects requests addressed to `127.0.0.1:8090`. An SSH local forward with that port is sufficient for private testing. Public access needs authentication and a separately configured ingress.

This image packages the workbench and its fixture. The real DIGIT complaint stack has its own services, database, and identity deployment. Langflow is also deployed independently when model review is needed.

## DIGIT sandbox integration

See [local sandbox setup and baseline verification](docs/digit-sandbox.md).

Pin the actual DIGIT 2.9 deployment manifest and PGR release. Capture the tenant's effective subtype configuration and localization schema. Map the internal change to that exact schema, then verify the new option against the actual citizen and employee journeys. Keep that execution result distinct from the local fixture result. Hosting the workbench also needs an authenticated application server and project-scoped run storage.
