from __future__ import annotations

from pathlib import Path

from certificate_dashboard.data import load_dataset, merged_modules, names_with_modules


def test_load_dataset_contains_selected_certificates() -> None:
    selected_names, certificates = load_dataset(Path("data/certificates.json"))
    assert len(selected_names) == 85
    assert selected_names[0] == "Elektromobilität"
    assert "Künstliche Intelligenz" in certificates


def test_names_with_modules_filters_missing_type() -> None:
    selected_names, certificates = load_dataset(Path("data/certificates.json"))
    cas_only = names_with_modules(selected_names, certificates, "CAS")
    das_only = names_with_modules(selected_names, certificates, "DAS")

    assert len(cas_only) > len(das_only)
    assert "Sales Management" in cas_only
    assert "Sales Management" not in das_only


def test_merged_modules_union_mode_merges_types() -> None:
    _selected_names, certificates = load_dataset(Path("data/certificates.json"))
    entry = certificates["Digitalisierung"]

    cas_ids = {module.module_id for module in merged_modules(entry, "CAS")}
    das_ids = {module.module_id for module in merged_modules(entry, "DAS")}
    union_ids = {module.module_id for module in merged_modules(entry, "CAS+DAS")}

    assert union_ids == cas_ids | das_ids
    assert len(union_ids) == 15
