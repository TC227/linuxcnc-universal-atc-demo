"""Deterministic logical-to-physical I/O assignment."""

from __future__ import annotations

from typing import Any


RESOURCE_TYPE = {"input": "digital_input", "output": "digital_output"}


def auto_map(
    signal_specs: list[dict[str, str]],
    resources: list[dict[str, Any]],
    existing_mapping: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Preserve valid existing assignments, then map remaining signals.

    A saved assignment is retained only when its signal still exists, its
    resource has the correct direction, it is available and verified, it is
    not reserved, its polarity is supported, and no other signal uses it.
    """
    existing = existing_mapping or {}
    resource_by_id = {resource["id"]: resource for resource in resources}
    candidates: dict[str, list[dict[str, Any]]] = {
        direction: sorted(
            (
                resource for resource in resources
                if resource.get("type") == RESOURCE_TYPE[direction]
                and resource.get("available") is True
                and resource.get("verified") is True
                and not resource.get("reserved_by")
                and resource.get("status", "available") == "available"
            ),
            key=lambda resource: resource["id"],
        )
        for direction in RESOURCE_TYPE
    }

    ordered = sorted(
        signal_specs,
        key=lambda signal: (
            _requirement_rank(signal.get("requirement", "required")),
            signal["id"],
        ),
    )
    mapping: dict[str, dict[str, str]] = {}
    used: set[str] = set()

    # Retain only compatible old assignments, in deterministic priority order.
    for signal in ordered:
        signal_id = signal["id"]
        old = existing.get(signal_id)
        if not old:
            continue
        resource_id = old.get("resource_id")
        resource = resource_by_id.get(resource_id)
        if resource is None or resource not in candidates[signal["direction"]]:
            continue
        if resource_id in used:
            continue
        supported_levels = resource.get("electrical", {}).get("supported_active_levels", [])
        active_level = old.get("active_level", "high")
        if supported_levels and active_level not in supported_levels:
            continue
        mapping[signal_id] = {"resource_id": resource_id, "active_level": active_level}
        used.add(resource_id)

    unmapped_required: list[str] = []
    unmapped_optional: list[str] = []
    for signal in ordered:
        signal_id = signal["id"]
        if signal_id in mapping:
            continue
        pool = candidates[signal["direction"]]
        resource = next((item for item in pool if item["id"] not in used), None)
        if resource is None:
            target = (
                unmapped_required
                if signal.get("requirement", "required") in ("required", "conditional")
                else unmapped_optional
            )
            target.append(signal_id)
            continue
        used.add(resource["id"])
        supported_levels = resource.get("electrical", {}).get("supported_active_levels", [])
        active_level = "high" if not supported_levels or "high" in supported_levels else "low"
        mapping[signal_id] = {"resource_id": resource["id"], "active_level": active_level}

    return {
        "mapping": mapping,
        "unmapped_required": unmapped_required,
        "unmapped_optional": unmapped_optional,
    }


def _requirement_rank(requirement: str) -> int:
    return {"required": 0, "conditional": 1, "recommended": 2, "optional": 3}.get(requirement, 4)
