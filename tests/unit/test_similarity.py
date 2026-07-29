from __future__ import annotations

from certificate_dashboard.models import CertificateEntry, ModuleRecord
from certificate_dashboard.similarity import (
    build_similarity_matrix,
    compare_pair,
    jaccard_similarity,
)


def build_entry(name: str, cas: tuple[str, ...], das: tuple[str, ...]) -> CertificateEntry:
    return CertificateEntry(
        certificate_name=name,
        modules_by_type={
            "CAS": tuple(ModuleRecord(module_id=module, module_name=module) for module in cas),
            "DAS": tuple(ModuleRecord(module_id=module, module_name=module) for module in das),
        },
    )


def test_jaccard_similarity() -> None:
    assert jaccard_similarity({"A", "B"}, {"A", "B"}) == 1.0
    assert jaccard_similarity({"A", "B"}, {"A", "C"}) == 1 / 3
    assert jaccard_similarity(set(), set()) == 1.0


def test_build_similarity_matrix_respects_type_filter() -> None:
    certificates = {
        "Alpha": build_entry("Alpha", ("M1", "M2"), ("M1", "M2", "M3")),
        "Beta": build_entry("Beta", ("M2",), ("M4",)),
    }

    matrix_cas = build_similarity_matrix(["Alpha", "Beta"], certificates, "CAS")
    assert matrix_cas.loc["Alpha", "Beta"] == 0.5

    matrix_union = build_similarity_matrix(["Alpha", "Beta"], certificates, "CAS+DAS")
    assert matrix_union.loc["Alpha", "Beta"] == 0.25


def test_compare_pair_shared_and_exclusive_modules() -> None:
    certificates = {
        "Alpha": build_entry("Alpha", ("M1", "M2"), tuple()),
        "Beta": build_entry("Beta", ("M2", "M3"), tuple()),
    }

    comparison = compare_pair("Alpha", "Beta", certificates, "CAS")

    assert comparison.shared_module_ids == ("M2",)
    assert comparison.only_a_module_ids == ("M1",)
    assert comparison.only_b_module_ids == ("M3",)
    assert comparison.jaccard == 1 / 3
