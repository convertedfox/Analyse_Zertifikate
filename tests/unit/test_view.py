from __future__ import annotations

import pandas as pd

from certificate_dashboard.view import add_axis_codes, focus_names, resolve_pair


def pair_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "certificate_a": ["A", "A", "B"],
            "certificate_b": ["B", "C", "C"],
            "jaccard": [0.8, 0.2, 0.5],
            "shared_module_count": [4, 1, 2],
        }
    )


def test_resolve_pair_keeps_available_selection() -> None:
    visible = [("A", "B", 0.8), ("B", "C", 0.5)]
    assert resolve_pair(visible, ("B", "C")) == ("B", "C")


def test_resolve_pair_falls_back_after_filter_change() -> None:
    visible = [("A", "B", 0.8)]
    assert resolve_pair(visible, ("B", "C")) == ("A", "B")


def test_focus_names_keeps_original_order() -> None:
    names = ["A", "B", "C"]
    assert focus_names(names, pair_frame(), "A", limit=2) == ["A", "B"]


def test_add_axis_codes() -> None:
    coded = add_axis_codes(pair_frame(), ["A", "B", "C"])
    assert list(coded["certificate_a_code"]) == ["01", "01", "02"]
    assert list(coded["certificate_b_code"]) == ["02", "03", "03"]
