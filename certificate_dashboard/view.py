from __future__ import annotations

import pandas as pd


def resolve_pair(
    visible_pairs: list[tuple[str, str, float]],
    selected_pair: object,
) -> tuple[str, str]:
    if not visible_pairs:
        raise ValueError("No visible pairs available")

    available = {(left, right) for left, right, _score in visible_pairs}
    if (
        isinstance(selected_pair, tuple)
        and len(selected_pair) == 2
        and all(isinstance(name, str) for name in selected_pair)
        and selected_pair in available
    ):
        return selected_pair

    return visible_pairs[0][0], visible_pairs[0][1]


def focus_names(
    active_names: list[str],
    pair_frame: pd.DataFrame,
    focus: str,
    limit: int = 20,
) -> list[str]:
    if focus == "Alle Zertifikate":
        return active_names

    relevant = pair_frame[
        (pair_frame["certificate_a"] == focus) | (pair_frame["certificate_b"] == focus)
    ].sort_values(
        by=["jaccard", "shared_module_count"],
        ascending=[False, False],
    )
    neighbors: list[str] = []
    for row in relevant.itertuples(index=False):
        neighbor = row.certificate_b if row.certificate_a == focus else row.certificate_a
        if neighbor not in neighbors:
            neighbors.append(neighbor)
        if len(neighbors) == limit - 1:
            break

    selected = {focus, *neighbors}
    return [name for name in active_names if name in selected]


def add_axis_codes(pair_frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    code_by_name = {name: f"{index + 1:02d}" for index, name in enumerate(names)}
    coded = pair_frame.copy()
    coded["certificate_a_code"] = coded["certificate_a"].map(code_by_name)
    coded["certificate_b_code"] = coded["certificate_b"].map(code_by_name)
    return coded
