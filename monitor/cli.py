"""CLI that samples one explicitly named Compose service."""

import argparse
import json
from contextlib import closing
from dataclasses import asdict
from urllib.parse import urlsplit

from monitor.checks import check_http, check_logs, check_state


def compose_container(client, project, service):
    labels = [f"com.docker.compose.project={project}",
              f"com.docker.compose.service={service}",
              "com.docker.compose.oneoff=False"]
    containers = client.containers.list(all=True, filters={"label": labels})
    if len(containers) != 1:
        raise ValueError(f"Expected one {project}/{service} container, found {len(containers)}")
    container = containers[0]
    container.reload()
    return container


def inspect(client, args):
    container = compose_container(client, args.project, args.service)
    return [
        check_state(container.attrs.get("State") or {}),
        check_http(args.url, args.expected_code, args.timeout),
        check_logs(container.logs(tail=args.tail, stdout=True, stderr=True)),
    ]


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


def status_code(value):
    number = int(value)
    if not 100 <= number <= 599:
        raise argparse.ArgumentTypeError("must be an HTTP status code between 100 and 599")
    return number


def http_url(value):
    url = urlsplit(value)
    if url.scheme not in {"http", "https"} or not url.hostname or url.username is not None:
        raise argparse.ArgumentTypeError("use an HTTP(S) URL without embedded credentials")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="qa-health-lab")
    parser.add_argument("--service", default="demo")
    parser.add_argument("--url", type=http_url, default="http://127.0.0.1:8080/health")
    parser.add_argument("--expected-code", type=status_code, default=200)
    parser.add_argument("--timeout", type=positive_int, default=5)
    parser.add_argument("--tail", type=positive_int, default=200)
    args = parser.parse_args(argv)
    try:
        import docker
    except ImportError:
        print(json.dumps({"configuration_error": "Install requirements.txt for Docker SDK"}))
        return 2

    try:
        with closing(docker.from_env(timeout=args.timeout)) as client:
            results = inspect(client, args)
    except (docker.errors.DockerException, OSError, ValueError) as exc:
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({"inspection_error": detail}))
        return 2

    passed = all(check.passed for check in results)
    print(json.dumps({"passed": passed, "checks": [asdict(check) for check in results]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
