"""Public field-provenance presentation."""

from typing import Any


def print_field_provenance_summary(result: dict[str, Any]) -> None:
    """Prints aggregate public provenance status without field-level detail."""
    bundle = result.get("field_provenance")
    if not isinstance(bundle, dict):
        return
    result_attachment = bundle["result"]
    coverage = result_attachment["coverage_summary"]
    attachments = [
        result_attachment,
        *[artifact["attachment"] for artifact in bundle["artifacts"]],
    ]
    redacted = any(
        "private_dependencies_redacted" in attachment["ledger"]["limitations"]
        for attachment in attachments
    )
    covered = coverage["provenanced_path_count"] + coverage["exempted_path_count"]
    print()
    print("Field Provenance")
    print("Version:", bundle["provenance_version"])
    print("Status:", result_attachment["ledger"]["status"])
    print("Result attachment:", result_attachment["attachment_name"])
    print("Covered leaves:", f"{covered}/{coverage['leaf_path_count']}")
    print("Private dependencies redacted:", "yes" if redacted else "no")
    print("Artifact attachment count:", len(bundle["artifacts"]))
