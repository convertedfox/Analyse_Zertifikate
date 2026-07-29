from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .data import TypeFilter, merged_modules
from .models import CertificateEntry, PairComparison


def jaccard_similarity(module_ids_a: set[str], module_ids_b: set[str]) -> float:
    if not module_ids_a and not module_ids_b:
        return 1.0

    union = module_ids_a | module_ids_b
    if not union:
        return 0.0
    return len(module_ids_a & module_ids_b) / len(union)


def build_similarity_matrix(
    ordered_names: Iterable[str],
    certificates: dict[str, CertificateEntry],
    type_filter: TypeFilter,
) -> pd.DataFrame:
    names = list(ordered_names)
    matrix = pd.DataFrame(0.0, index=names, columns=names)
    module_sets = {
        name: {module.module_id for module in merged_modules(certificates[name], type_filter)}
        for name in names
    }

    for left_name in names:
        for right_name in names:
            matrix.loc[left_name, right_name] = jaccard_similarity(
                module_sets[left_name], module_sets[right_name]
            )

    return matrix


def compare_pair(
    certificate_a: str,
    certificate_b: str,
    certificates: dict[str, CertificateEntry],
    type_filter: TypeFilter,
) -> PairComparison:
    modules_a = {
        module.module_id for module in merged_modules(certificates[certificate_a], type_filter)
    }
    modules_b = {
        module.module_id for module in merged_modules(certificates[certificate_b], type_filter)
    }

    shared = tuple(sorted(modules_a & modules_b))
    only_a = tuple(sorted(modules_a - modules_b))
    only_b = tuple(sorted(modules_b - modules_a))

    return PairComparison(
        certificate_a=certificate_a,
        certificate_b=certificate_b,
        shared_module_ids=shared,
        only_a_module_ids=only_a,
        only_b_module_ids=only_b,
        jaccard=jaccard_similarity(modules_a, modules_b),
    )


def to_long_dataframe(matrix: pd.DataFrame, threshold: float) -> pd.DataFrame:
    frame = (
        matrix.stack()
        .rename("jaccard")
        .reset_index()
        .rename(columns={"level_0": "certificate_a", "level_1": "certificate_b"})
    )
    frame["visible_score"] = frame["jaccard"].where(frame["jaccard"] >= threshold)
    return frame
