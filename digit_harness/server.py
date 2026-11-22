"""Loopback-only HTTP server for the local workbench."""

import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from .sandbox import prepare_sandbox
from .workflow import knowledge, render, run


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, data, **kwargs):
        self.data = data
        super().__init__(*args, **kwargs)

    def send(self, status, body, content_type="application/json"):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def local_request(self):
        expected = f"127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") == expected and self.headers.get("Origin", f"http://{expected}") == f"http://{expected}":
            return True
        self.send(403, render({"error": "Open the workbench on its 127.0.0.1 address."}))
        return False

    def do_GET(self):
        if not self.local_request():
            return
        path = urlsplit(self.path).path
        if path == "/":
            page = files("digit_harness").joinpath("index.html").read_text(encoding="utf-8")
            self.send(200, page, "text/html")
            return
        if path == "/api/knowledge":
            self.send(200, render(knowledge()))
            return
        if path == "/api/sandbox":
            self.send(200, render(prepare_sandbox()))
            return
        if path.startswith("/api/runs/"):
            try:
                run_id = UUID(path.removeprefix("/api/runs/"))
                payload = (self.data / f"{run_id}.json").read_text(encoding="utf-8")
            except (ValueError, FileNotFoundError):
                self.send(404, render({"error": "Run not found."}))
            else:
                self.send(200, payload)
            return
        self.send(404, render({"error": "Page not found."}))

    def do_POST(self):
        if not self.local_request():
            return
        if self.path != "/api/runs":
            self.send(404, render({"error": "Endpoint not found."}))
            return
        if self.headers.get_content_type() != "application/json":
            self.send(415, render({"error": "Use application/json."}))
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 40000:
                raise ValueError("Invalid request size.")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Supply a JSON object.")
            fields = [body.get(key, "") for key in ("requirement", "kind", "code", "label")]
            if any(not isinstance(field, str) for field in fields):
                raise ValueError("Requirement, kind, code and label must be strings.")
            result = run(*fields, model_review=body.get("model_review") is True)
        except ValueError as error:
            self.send(400, render({"error": str(error)}))
            return
        result["run_id"] = str(uuid4())
        try:
            self.data.mkdir(parents=True, exist_ok=True)
            record = self.data / f"{result['run_id']}.json"
            temporary = record.with_suffix(".tmp")
            temporary.write_text(render(result), encoding="utf-8")
            temporary.replace(record)
        except OSError:
            self.send(500, render({"error": "The workbench could not save the run."}))
            return
        self.send(201, render(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--data", type=Path, default=Path(".local/runs"))
    args = parser.parse_args()
    with ThreadingHTTPServer((args.bind, args.port), partial(Handler, data=args.data)) as server:
        print(f"DIGIT Workbench listening on {args.bind}:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
