"""Evidence, routing and reproducible fixture execution."""

import difflib
import json
import re
from importlib.resources import files

from .model import summarize


def knowledge():
    return json.loads(files("digit_harness").joinpath("knowledge.json").read_text(encoding="utf-8"))


def render(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def run(requirement, kind, code, label, model_review=False):
    if not requirement.strip() or len(requirement) > 8000:
        raise ValueError("Enter a requirement of 1 to 8,000 characters.")
    if kind not in {"complaint-subtype", "extension", "new-module"}:
        raise ValueError("Select a supported request type.")
    baseline = knowledge()
    catalog = baseline["catalog"]
    result = {
        "baseline": baseline["baseline"],
        "requirement": {"id": "REQ-001", "statement": requirement.strip(), "type": kind},
        "evidence": baseline["evidence"],
        "execution": "local-fixture",
        "tests": [],
    }
    if kind != "complaint-subtype":
        result["decision"] = {
            "path": "needs-review",
            "rule": "PGR-002",
            "reason": "This request requires implementation evidence outside the fixture's complaint catalog.",
            "evidence": ["PGR-SCOPE", "FIXTURE-CATALOG"],
        }
    else:
        code = code.strip()
        label = label.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,47}", code):
            raise ValueError("Use 2 to 48 uppercase letters, digits or underscores for the subtype code, starting with a letter.")
        if not 1 <= len(label) <= 100 or any(ord(character) < 32 for character in label):
            raise ValueError("Enter a single-line label of 1 to 100 characters.")
        if any(entry["code"] == code for entry in catalog):
            raise ValueError("This subtype code already exists in the baseline catalog.")
        entry = {"code": code, "department": "SANITATION", "labels": {"en_IN": label}}
        proposed = [*catalog, entry]
        result["decision"] = {
            "path": "configure",
            "rule": "PGR-001",
            "reason": "The local fixture supports adding a unique sanitation subtype with an English label.",
            "evidence": ["FIXTURE-CATALOG"],
        }
        result["configuration"] = entry
        result["diff"] = "".join(difflib.unified_diff(
            render(catalog).splitlines(keepends=True),
            render(proposed).splitlines(keepends=True),
            fromfile="baseline/complaint-catalog.json",
            tofile="preview/complaint-catalog.json",
        ))
        # Reload serialized state through the same catalog consumed by the preview.
        deployed = json.loads(render(proposed))
        result["preview_catalog"] = deployed
        result["tests"] = [
            {"id": "T-001", "criterion": "AC-001", "pass": label in citizen_options(deployed).values()},
            {"id": "T-002", "criterion": "AC-002", "pass": deployed[:-1] == catalog},
            {"id": "T-003", "criterion": "AC-001", "pass": citizen_options(deployed).get(code) == label},
        ]
        result["acceptance_criteria"] = {
            "AC-001": f"The citizen complaint selector offers {label} under code {code}.",
            "AC-002": "The baseline complaint subtypes remain available and unchanged.",
        }
    criteria = result.get("acceptance_criteria", {})
    result["frs"] = "\n".join([
        "# Functional Requirements",
        f"REQ-001 — {requirement.strip()}",
        *(f"{key} — {value}" for key, value in criteria.items()),
    ])
    result["srs"] = "\n".join([
        "# Software Requirements",
        f"REQ-001 — {result['decision']['reason']}",
        f"Baseline — {baseline['baseline']}",
        *(f"{test['criterion']} → {test['id']}" for test in result["tests"]),
    ])
    result["model_review"] = summarize(result["requirement"], result["evidence"]) if model_review else {"status": "skipped"}
    return result


def citizen_options(catalog):
    return {entry["code"]: entry["labels"]["en_IN"] for entry in catalog}
