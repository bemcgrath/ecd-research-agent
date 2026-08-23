"""ClinicalTrials.gov access via official API v2 only."""

from __future__ import annotations

import re
from typing import Any

import requests

from ecd_research.models import ClinicalTrial

CTGOV_BASE = "https://clinicaltrials.gov/api/v2"
DEFAULT_TIMEOUT = 30
NCT_PATTERN = re.compile(r"^NCT\d{8}$", re.IGNORECASE)


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(
        f"{CTGOV_BASE}/{path}",
        params=params or {},
        timeout=DEFAULT_TIMEOUT,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("ClinicalTrials.gov response was not a JSON object")
    return payload


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _date_from_struct(node: Any) -> str | None:
    if not isinstance(node, dict):
        return _as_str(node)
    return _as_str(node.get("date")) or _as_str(node.get("dateStruct", {}).get("date"))


def _parse_phase(status_module: dict[str, Any] | None, design_module: dict[str, Any] | None) -> str | None:
    for module in (status_module, design_module):
        if not module:
            continue
        phases = module.get("phases") or module.get("phaseList", {}).get("phases")
        if isinstance(phases, list) and phases:
            parts = [_as_str(p) for p in phases]
            joined = ", ".join(p for p in parts if p)
            return joined or None
        single = _as_str(module.get("phase"))
        if single:
            return single
    return None


def parse_clinical_trial(study: dict[str, Any]) -> ClinicalTrial | None:
    """Map one API v2 study object to ClinicalTrial; skip if NCT ID missing."""
    protocol = study.get("protocolSection")
    if not isinstance(protocol, dict):
        return None

    ident = protocol.get("identificationModule") or {}
    status_mod = protocol.get("statusModule") or {}
    design_mod = protocol.get("designModule") or {}
    arms_mod = protocol.get("armsInterventionsModule") or {}
    conditions_mod = protocol.get("conditionsModule") or {}
    eligibility_mod = protocol.get("eligibilityModule") or {}
    contacts_mod = protocol.get("contactsLocationsModule") or {}
    sponsor_mod = protocol.get("sponsorCollaboratorsModule") or {}

    nct_id = _as_str(ident.get("nctId"))
    if not nct_id:
        return None

    interventions: list[str] = []
    for item in arms_mod.get("interventions") or []:
        if not isinstance(item, dict):
            continue
        name = _as_str(item.get("name"))
        if name:
            interventions.append(name)

    conditions: list[str] = []
    for cond in conditions_mod.get("conditions") or []:
        text = _as_str(cond)
        if text:
            conditions.append(text)

    locations: list[str] = []
    for loc in contacts_mod.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        facility = _as_str(loc.get("facility"))
        city = _as_str(loc.get("city"))
        country = _as_str(loc.get("country"))
        parts = [p for p in (facility, city, country) if p]
        if parts:
            locations.append(", ".join(parts))

    investigators: list[str] = []
    for person in contacts_mod.get("overallOfficials") or []:
        if not isinstance(person, dict):
            continue
        name = _as_str(person.get("name"))
        if name:
            investigators.append(name)

    lead = sponsor_mod.get("leadSponsor") or {}
    sponsor = _as_str(lead.get("name")) if isinstance(lead, dict) else None

    title = _as_str(ident.get("officialTitle")) or _as_str(ident.get("briefTitle"))

    return ClinicalTrial(
        nct_id=nct_id.upper(),
        title=title,
        status=_as_str(status_mod.get("overallStatus")),
        phase=_parse_phase(status_mod, design_mod),
        interventions=interventions,
        conditions=conditions,
        eligibility=_as_str(eligibility_mod.get("eligibilityCriteria")),
        minimum_age=_as_str(eligibility_mod.get("minimumAge")),
        maximum_age=_as_str(eligibility_mod.get("maximumAge")),
        locations=locations,
        sponsor=sponsor,
        investigators=investigators,
        start_date=_date_from_struct(status_mod.get("startDateStruct")),
        completion_date=_date_from_struct(
            status_mod.get("completionDateStruct")
            or status_mod.get("primaryCompletionDateStruct")
        ),
        last_update_date=_date_from_struct(status_mod.get("lastUpdatePostDateStruct")),
        url=f"https://clinicaltrials.gov/study/{nct_id.upper()}",
    )


def search_clinical_trials(
    condition: str,
    status: str | None = None,
    *,
    page_size: int = 20,
) -> list[ClinicalTrial]:
    """Search ClinicalTrials.gov by condition; optionally filter overall status."""
    if not isinstance(condition, str) or not condition.strip():
        raise ValueError("condition must be a non-empty string")
    if not isinstance(page_size, int) or page_size < 1:
        raise ValueError("page_size must be an integer >= 1")

    params: dict[str, Any] = {
        "query.cond": condition.strip(),
        "pageSize": page_size,
        "format": "json",
    }
    if status is not None:
        if not isinstance(status, str) or not status.strip():
            raise ValueError("status must be a non-empty string when provided")
        params["filter.overallStatus"] = status.strip()

    payload = _get("studies", params)
    studies = payload.get("studies") or []
    if not isinstance(studies, list):
        return []

    results: list[ClinicalTrial] = []
    for study in studies:
        if not isinstance(study, dict):
            continue
        parsed = parse_clinical_trial(study)
        if parsed is not None:
            results.append(parsed)
    return results


def get_clinical_trial(nct_id: str) -> ClinicalTrial | None:
    """Fetch one study by NCT ID. Returns None if not found."""
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id.strip()):
        raise ValueError("nct_id must look like NCT12345678")

    cleaned = nct_id.strip().upper()
    try:
        payload = _get(f"studies/{cleaned}")
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return None
        raise

    # Single-study endpoint may return the study object directly or wrapped.
    if "protocolSection" in payload:
        return parse_clinical_trial(payload)
    studies = payload.get("studies")
    if isinstance(studies, list) and studies and isinstance(studies[0], dict):
        return parse_clinical_trial(studies[0])
    return parse_clinical_trial(payload)
