# Execution record

Tested with Python 3.14 on Windows. `python -m pytest -q` reported **19 passed, 2 skipped, 9 subtests passed**. The skipped cases require Docker. Bash syntax validation passed for `scripts/run_lab.sh`. With the Docker SDK installed and no Docker Engine accessible, the CLI returned exit 2 and a JSON diagnostic.

The two live pytest cases and the intentional error scenario are configured to run in GitHub Actions on a Docker-enabled runner. The local verification did not execute the containerized scenarios.
