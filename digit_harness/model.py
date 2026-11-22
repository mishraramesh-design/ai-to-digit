"""Opt-in Langflow client. Model output is advisory."""

import json
import os
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def summarize(requirement, evidence):
    base = os.environ.get("HARNESS_LANGFLOW_URL")
    flow = os.environ.get("HARNESS_LANGFLOW_FLOW_ID")
    if not base or not flow:
        return {"status": "unconfigured"}
    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Invalid Langflow URL")
    message = {
        "task": "Draft a concise functional and technical review. Cite supplied evidence IDs. Do not invent DIGIT capabilities.",
        "requirement": requirement,
        "evidence": evidence,
    }
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("HARNESS_LANGFLOW_API_KEY")
    if key:
        headers["x-api-key"] = key
    request = Request(
        f"{base.rstrip('/')}/api/v1/run/{quote(flow, safe='')}",
        data=json.dumps({
            "input_value": json.dumps(message),
            "input_type": "chat",
            "output_type": "chat",
        }).encode(),
        headers=headers,
    )
    try:
        with build_opener(RejectRedirects).open(request, timeout=30) as response:
            payload = json.loads(response.read(1_000_001))
        answer = payload["outputs"][0]["outputs"][0]["results"]["message"]["text"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Empty Chat Output")
    except (URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
        return {"status": "failed", "detail": "Check the Langflow endpoint and Chat Output component."}
    return {"status": "completed", "flow": flow, "advice": answer[:10000]}
