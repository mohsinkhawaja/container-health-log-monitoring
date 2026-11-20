# Container Health and Log Monitoring

This Python utility verifies three independent signals from a containerized service: Docker runtime and health state, an HTTP status and readiness body, and error signatures in recent application logs. A small Compose application provides repeatable healthy and failing scenarios for QA and CI.

```text
Docker SDK -> Compose container -> inspect state + tail logs
HTTP probe -> demo service     -> status + JSON readiness
                                      |
                               JSON report + exit code
```

## Run locally

Use Python 3.12 or later, Docker Engine or Docker Desktop, and Docker Compose v2 with `up --wait` support. Install the dependencies inside a virtual environment.

```bash
python -m venv .venv
# Bash: source .venv/bin/activate
# PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
docker compose up --build --wait
python -m monitor.cli
docker compose down
```

The demo publishes port 8080 on localhost. For a different port, set `DEMO_PORT` before starting and pass `--url http://127.0.0.1:<port>/health` to the CLI. Specify `--project` if you used a custom Compose project name. `--tail` controls the sampled log lines and `--timeout` bounds each HTTP or Docker call.

| Exit | Meaning |
|---|---|
| 0 | All three gates passed |
| 1 | An observed runtime, HTTP or log check failed |
| 2 | CLI configuration, Docker connectivity or unique container selection failed |

## Run the tests

```bash
python -m pytest -q
bash scripts/run_lab.sh
```

The first command verifies routing, parser, HTTP contract, and container selection without Docker. The Bash runner creates a disposable Compose project, waits for health, runs offline and live pytest checks, then starts the same image with a synthetic error event. It requires that the monitor return exit 1 and that logs be the only failed gate.

To run live pytest from PowerShell against an already running default stack, set `$env:MONITOR_LIVE='1'` and run `python -m pytest -q`. Clear the environment variable when finished. To reproduce the error scenario in PowerShell, set `$env:DEMO_EMIT_ERROR='1'`, rerun `docker compose up --wait`, then run the CLI and inspect `$LASTEXITCODE`. Tear down with `docker compose down` and clear the fixture variable.

GitHub Actions uses the Bash runner and uploads JUnit XML, JSON monitor summaries and Compose logs as the `container-checks` artifact. See the [test strategy](docs/test-strategy.md), [execution record](docs/execution.md), and [defect report template](docs/bug-report-template.md).

## Design

- `demo_service.py` defines the synthetic HTTP app and its startup log fixtures.
- `monitor/checks.py` implements independent value checks and the HTTP adapter.
- `monitor/cli.py` selects one non-job Compose container, loads state and logs using the Docker SDK, then generates a machine-readable report.
- `tests/` separates offline test doubles from explicitly enabled real integration.
- `scripts/run_lab.sh` owns its Compose stack from readiness through diagnostics and teardown.

This is a one-shot smoke test for a single Compose replica. The structured report shows matching line positions instead of reproducing raw log content.

References: [Docker Compose services](https://docs.docker.com/reference/compose-file/services/) · [Docker SDK container API](https://docker-py.readthedocs.io/en/stable/containers.html)
