from __future__ import annotations

from pathlib import Path

from scripts.export_certificates import build_dataset


def test_build_dataset_matches_expected_selection() -> None:
    payload = build_dataset(Path("data/Analyse der Zertifikate.xlsx"))
    selected = payload["selected_certificate_names"]

    assert len(selected) == 85
    assert selected[0] == "Elektromobilität"


def test_build_dataset_includes_both_type_lists() -> None:
    payload = build_dataset(Path("data/Analyse der Zertifikate.xlsx"))
    certificates = payload["certificates"]
    first = certificates[0]

    assert "CAS" in first["modules_by_type"]
    assert "DAS" in first["modules_by_type"]
