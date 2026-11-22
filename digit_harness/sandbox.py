"""Read-only PGR v2.20 sandbox discovery."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from .model import RejectRedirects

MODULE = "RAINMAKER-PGR"
MASTERS = ("ComplaintHierarchyDefinition", "ComplaintHierarchy")


def read_document(base, path, payload=None):
    request = Request(
        base.rstrip("/") + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with build_opener(RejectRedirects).open(request, timeout=5) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("Response exceeds the discovery limit.")
    return json.loads(body)


def check(label, operation):
    try:
        return {"name": label, "status": "passed", "detail": operation()}
    except HTTPError as error:
        error.close()
        return {"name": label, "status": "blocked", "detail": f"HTTP {error.code} from the configured service."}
    except (URLError, OSError):
        return {"name": label, "status": "blocked", "detail": "The configured service could not be reached."}
    except (ValueError, AttributeError, TypeError):
        return {"name": label, "status": "blocked", "detail": "The response did not match the expected PGR v2.20 contract."}


def check_pgr(base):
    status = read_document(base, "/pgr-services/health")
    if status.get("status") != "UP":
        raise ValueError("PGR health check is not UP.")
    return "PGR reports UP."


def check_hierarchy(base, tenant):
    payload = {
        "RequestInfo": {"apiId": "digit-studio"},
        "MdmsCriteria": {
            "tenantId": tenant,
            "moduleDetails": [{"moduleName": MODULE, "masterDetails": [{"name": name} for name in MASTERS]}],
        },
    }
    document = read_document(base, "/mdms-v2/v1/_search", payload)
    records = document.get("MdmsRes", {}).get(MODULE, {})
    definitions, nodes = (records.get(name) for name in MASTERS)
    if not isinstance(definitions, list) or not isinstance(nodes, list):
        raise ValueError("Expected hierarchy lists.")
    active_types = {
        row.get("hierarchyType") for row in definitions
        if isinstance(row, dict) and row.get("active") is not False and isinstance(row.get("hierarchyType"), str)
    }
    eligible_nodes = [
        row for row in nodes if isinstance(row, dict) and isinstance(row.get("hierarchyType"), str)
        and row["hierarchyType"] in active_types and row.get("active") is not False
    ]
    if not eligible_nodes:
        raise ValueError("No active hierarchy has rows for this tenant.")
    return f"MDMS returned {len(eligible_nodes)} active nodes across {len(active_types)} active hierarchy type(s)."


def prepare_sandbox():
    tenant = os.environ.get("HARNESS_DIGIT_TENANT", "").strip()
    pgr = os.environ.get("HARNESS_DIGIT_PGR_URL", "").strip()
    mdms = os.environ.get("HARNESS_DIGIT_MDMS_URL", "").strip()
    report = {"profile": "PGR v2.20", "tenant": tenant or None, "checks": []}
    if not all((tenant, pgr, mdms)):
        return {
            **report, "status": "unconfigured",
            "message": "Set the sandbox tenant, PGR URL and MDMS URL in the Studio deployment.",
        }
    try:
        for base in (pgr, mdms):
            url = urlsplit(base)
            if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.query or url.fragment:
                raise ValueError("Invalid service URL.")
            _ = url.port
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*)*", tenant):
            raise ValueError("Invalid tenant code.")
    except ValueError:
        return {**report, "status": "blocked", "message": "Check the configured sandbox URLs and tenant code."}
    checks = [
        check("PGR service", lambda: check_pgr(pgr)),
        check("Complaint hierarchy", lambda: check_hierarchy(mdms, tenant)),
    ]
    return {**report, "status": "readable" if all(item["status"] == "passed" for item in checks) else "blocked",
            "checks": checks}
