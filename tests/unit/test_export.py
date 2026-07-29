from __future__ import annotations

from pathlib import Path

from scripts.export_certificates import build_dataset, json_is_current, write_json


def test_build_dataset_matches_expected_selection() -> None:
    payload = build_dataset(Path("data/Analyse der Zertifikate.xlsx"))
    selected = payload["selected_certificate_names"]

    assert payload["schema_version"] == 1
    assert len(selected) == 85
    assert selected[0] == "Elektromobilität"


def test_build_dataset_includes_both_type_lists() -> None:
    payload = build_dataset(Path("data/Analyse der Zertifikate.xlsx"))
    certificates = payload["certificates"]
    first = certificates[0]

    assert "CAS" in first["modules_by_type"]
    assert "DAS" in first["modules_by_type"]


def test_json_is_current_detects_outdated_file(tmp_path: Path) -> None:
    payload = build_dataset(Path("data/Analyse der Zertifikate.xlsx"))
    output = tmp_path / "certificates.json"

    assert not json_is_current(payload, output)
    write_json(payload, output)
    assert json_is_current(payload, output)

    output.write_text("{}\n", encoding="utf-8")
    assert not json_is_current(payload, output)
