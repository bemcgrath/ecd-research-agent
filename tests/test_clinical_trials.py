"""Tests for ClinicalTrials.gov API v2 client parsing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ecd_research.tools.clinical_trials import (
    get_clinical_trial,
    parse_clinical_trial,
    search_clinical_trials,
)

SAMPLE_STUDY = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT05001828",
            "briefTitle": "Example ECD Trial",
            "officialTitle": "A Study of Targeted Therapy in Erdheim-Chester Disease",
        },
        "statusModule": {
            "overallStatus": "RECRUITING",
            "startDateStruct": {"date": "2022-01-15"},
            "completionDateStruct": {"date": "2027-12-01"},
            "lastUpdatePostDateStruct": {"date": "2026-03-01"},
        },
        "designModule": {"phases": ["PHASE2"]},
        "armsInterventionsModule": {
            "interventions": [{"name": "Cobimetinib", "type": "DRUG"}]
        },
        "conditionsModule": {"conditions": ["Erdheim-Chester Disease"]},
        "eligibilityModule": {
            "eligibilityCriteria": "Inclusion: adults with ECD.",
            "minimumAge": "18 Years",
            "maximumAge": "N/A",
        },
        "contactsLocationsModule": {
            "locations": [
                {
                    "facility": "Example Cancer Center",
                    "city": "Boston",
                    "country": "United States",
                }
            ],
            "overallOfficials": [{"name": "Jane Investigator", "role": "PRINCIPAL_INVESTIGATOR"}],
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {"name": "Example Sponsor", "class": "OTHER"}
        },
    }
}


def test_parse_clinical_trial_full_record() -> None:
    trial = parse_clinical_trial(SAMPLE_STUDY)
    assert trial is not None
    assert trial.nct_id == "NCT05001828"
    assert trial.title.startswith("A Study of Targeted Therapy")
    assert trial.status == "RECRUITING"
    assert trial.phase == "PHASE2"
    assert trial.interventions == ["Cobimetinib"]
    assert trial.conditions == ["Erdheim-Chester Disease"]
    assert trial.eligibility == "Inclusion: adults with ECD."
    assert trial.minimum_age == "18 Years"
    assert trial.sponsor == "Example Sponsor"
    assert trial.investigators == ["Jane Investigator"]
    assert trial.start_date == "2022-01-15"
    assert trial.url == "https://clinicaltrials.gov/study/NCT05001828"


def test_parse_skips_missing_nct() -> None:
    assert parse_clinical_trial({"protocolSection": {"identificationModule": {}}}) is None


def test_search_clinical_trials_uses_condition_and_status() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"studies": [SAMPLE_STUDY]}

    with patch(
        "ecd_research.tools.clinical_trials.requests.get",
        return_value=mock_response,
    ) as mock_get:
        trials = search_clinical_trials(
            "Erdheim-Chester disease", status="RECRUITING", page_size=5
        )

    assert len(trials) == 1
    assert trials[0].nct_id == "NCT05001828"
    kwargs = mock_get.call_args.kwargs
    assert kwargs["params"]["query.cond"] == "Erdheim-Chester disease"
    assert kwargs["params"]["filter.overallStatus"] == "RECRUITING"
    assert kwargs["params"]["pageSize"] == 5


def test_search_invalid_input() -> None:
    with pytest.raises(ValueError, match="condition"):
        search_clinical_trials("")
    with pytest.raises(ValueError, match="page_size"):
        search_clinical_trials("ECD", page_size=0)


def test_get_clinical_trial_by_id() -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = SAMPLE_STUDY

    with patch(
        "ecd_research.tools.clinical_trials.requests.get",
        return_value=mock_response,
    ) as mock_get:
        trial = get_clinical_trial("nct05001828")

    assert trial is not None
    assert trial.nct_id == "NCT05001828"
    assert mock_get.call_args.args[0].endswith("/studies/NCT05001828")


def test_get_clinical_trial_invalid_id() -> None:
    with pytest.raises(ValueError, match="nct_id"):
        get_clinical_trial("not-an-nct")
