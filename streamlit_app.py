from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import altair as alt
import pandas as pd
import streamlit as st

from certificate_dashboard.data import (
    DatasetValidationError,
    TypeFilter,
    load_dataset,
    merged_modules,
    module_name_lookup,
    names_with_modules,
)
from certificate_dashboard.models import CertificateEntry
from certificate_dashboard.similarity import (
    build_upper_triangle_pairs,
    compare_pair,
    top_pairs,
)
from certificate_dashboard.ui_helpers import extract_pair_from_event
from certificate_dashboard.view import add_axis_codes, focus_names, resolve_pair

ROOT_DIR = Path(__file__).resolve().parent
DATA_PATH = ROOT_DIR / "data" / "certificates.json"
SELECTED_PAIR_KEY = "selected_pair"
PAIR_SELECT_KEY = "pair_select"
CHART_GENERATION_KEY = "chart_generation"


@st.cache_data(show_spinner=False)
def load_dashboard_data(
    path: str,
    modified_ns: int,
) -> tuple[list[str], dict[str, CertificateEntry]]:
    del modified_ns
    return load_dataset(Path(path))


def summarize_modules(module_ids: tuple[str, ...], lookup: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Modulnummer": list(module_ids),
            "Modulname": [lookup[module_id] for module_id in module_ids],
        }
    )


def pair_label(pair: tuple[str, str], score_lookup: dict[tuple[str, str], float]) -> str:
    score = score_lookup[pair]
    return f"{pair[0]} ↔ {pair[1]} (Jaccard {score:.2f})"


def update_pair_from_selectbox() -> None:
    st.session_state[SELECTED_PAIR_KEY] = st.session_state[PAIR_SELECT_KEY]
    st.session_state[CHART_GENERATION_KEY] = st.session_state.get(CHART_GENERATION_KEY, 0) + 1


def resolve_selected_pair(
    visible_pairs: list[tuple[str, str, float]],
) -> tuple[str, str]:
    selected = resolve_pair(visible_pairs, st.session_state.get(SELECTED_PAIR_KEY))
    st.session_state[SELECTED_PAIR_KEY] = selected
    return selected


def build_heatmap(
    pair_frame: pd.DataFrame,
    threshold: float,
    selected_pair: tuple[str, str],
    certificate_count: int,
) -> Any:
    visible = pair_frame[pair_frame["jaccard"] >= threshold].copy()
    hidden = pair_frame[pair_frame["jaccard"] < threshold].copy()
    axis = alt.Axis(title="Zertifikat (Nr.)", labelAngle=0, labelOverlap="greedy")
    tooltip = [
        alt.Tooltip("certificate_a:N", title="Zertifikat A"),
        alt.Tooltip("certificate_b:N", title="Zertifikat B"),
        alt.Tooltip("jaccard:Q", title="Jaccard", format=".3f"),
        alt.Tooltip("shared_module_count:Q", title="Gemeinsame Module"),
    ]

    neutral = (
        alt.Chart(hidden)
        .mark_rect(stroke="#d6cec2", strokeWidth=0.2, color="#ece8e0")
        .encode(
            x=alt.X("certificate_b_code:O", title="Zertifikat (Nr.)", axis=axis),
            y=alt.Y("certificate_a_code:O", title="Zertifikat (Nr.)", axis=axis),
            tooltip=tooltip,
        )
        .properties(height=max(520, certificate_count * 15))
    )

    click_selection = alt.selection_point(
        name="selected_pair",
        fields=["certificate_a", "certificate_b"],
        on="click",
        clear=False,
        empty=False,
        toggle=False,
    )
    active = (
        alt.Chart(visible)
        .mark_rect(stroke="#d6cec2", strokeWidth=0.2)
        .encode(
            x=alt.X("certificate_b_code:O", title="Zertifikat (Nr.)", axis=axis),
            y=alt.Y("certificate_a_code:O", title="Zertifikat (Nr.)", axis=axis),
            color=alt.Color(
                "jaccard:Q",
                title="Jaccard",
                scale=alt.Scale(domain=[0, 1], range=["#efeae1", "#793521"]),
            ),
            tooltip=tooltip,
        )
        .add_params(click_selection)
    )
    selected_overlay = (
        alt.Chart(
            visible[
                (visible["certificate_a"] == selected_pair[0])
                & (visible["certificate_b"] == selected_pair[1])
            ]
        )
        .mark_rect(stroke="#2e2a26", strokeWidth=2, fillOpacity=0)
        .encode(
            x=alt.X("certificate_b_code:O", axis=axis),
            y=alt.Y("certificate_a_code:O", axis=axis),
        )
    )
    return neutral + active + selected_overlay


def render_app() -> None:
    st.set_page_config(
        page_title="Zertifikatsähnlichkeiten",
        page_icon="▦",
        layout="wide",
    )
    st.title("Zertifikatsähnlichkeiten nach Modulen")
    st.caption(
        "Vergleich über Jaccard-Ähnlichkeit: "
        "gemeinsame Module geteilt durch alle unterschiedlichen Module."
    )

    if not DATA_PATH.exists():
        st.error("Daten fehlen: Bitte `uv run python scripts/export_certificates.py` ausführen.")
        st.stop()

    try:
        ordered_names, certificates = load_dashboard_data(
            str(DATA_PATH),
            DATA_PATH.stat().st_mtime_ns,
        )
    except DatasetValidationError as exc:
        st.error(f"Der Datenbestand ist ungültig: {exc}")
        st.stop()
    module_lookup = module_name_lookup(certificates)

    with st.sidebar:
        st.subheader("Filter")
        type_filter = st.segmented_control(
            "Zertifikatstyp",
            options=["CAS", "DAS", "CAS+DAS"],
            default="CAS+DAS",
            selection_mode="single",
            required=True,
        )
        selected_type_filter = cast(TypeFilter, type_filter)
        threshold = st.slider(
            "Mindestähnlichkeit", min_value=0.0, max_value=1.0, value=0.3, step=0.01
        )

    active_names = names_with_modules(ordered_names, certificates, selected_type_filter)
    if len(active_names) < 2:
        st.warning("Mit diesem Typfilter gibt es weniger als zwei analysierbare Zertifikate.")
        st.stop()

    all_pair_frame = build_upper_triangle_pairs(active_names, certificates, selected_type_filter)
    with st.sidebar:
        focus = st.selectbox(
            "Fokuszertifikat",
            options=["Alle Zertifikate", *active_names],
            help="Zeigt im Fokusmodus das Zertifikat und seine 19 ähnlichsten Nachbarn.",
        )
        st.caption(
            "Bei gleichnamigen Zertifikaten folgt das Modulset dem Typfilter: "
            "CAS, DAS oder Vereinigung."
        )

    matrix_names = focus_names(active_names, all_pair_frame, focus)
    pair_frame = build_upper_triangle_pairs(matrix_names, certificates, selected_type_filter)
    pair_frame = add_axis_codes(pair_frame, matrix_names)
    visible_pairs = top_pairs(pair_frame, threshold, limit=len(pair_frame))
    if not visible_pairs:
        st.info("Kein Zertifikatspaar erreicht den aktuellen Schwellwert.")
        st.stop()

    top_20_pairs = top_pairs(pair_frame, threshold, limit=20)
    score_lookup = {(left, right): score for left, right, score in visible_pairs}
    selected_pair = resolve_selected_pair(visible_pairs)
    select_options = [(left, right) for left, right, _score in top_20_pairs]
    if selected_pair not in select_options:
        select_options.insert(0, selected_pair)
    if st.session_state.get(PAIR_SELECT_KEY) != selected_pair:
        st.session_state[PAIR_SELECT_KEY] = selected_pair

    st.subheader("Top-20-Paare")
    st.selectbox(
        "Paar auswählen",
        options=select_options,
        key=PAIR_SELECT_KEY,
        format_func=lambda pair: pair_label(pair, score_lookup),
        on_change=update_pair_from_selectbox,
    )
    selected_pair = cast(tuple[str, str], st.session_state[SELECTED_PAIR_KEY])

    modules_per_certificate = {
        name: len(merged_modules(certificates[name], selected_type_filter)) for name in matrix_names
    }
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Zertifikate", len(matrix_names), border=True)
    metric_two.metric(
        "Durchschnittliche Module", f"{pd.Series(modules_per_certificate).mean():.1f}", border=True
    )
    metric_three.metric("Paare über Schwelle", len(visible_pairs), border=True)

    st.subheader("Ähnlichkeitsmatrix (oberes Dreieck)")
    chart = build_heatmap(pair_frame, threshold, selected_pair, len(matrix_names))
    generation = st.session_state.get(CHART_GENERATION_KEY, 0)
    event = st.altair_chart(
        chart,
        width="stretch",
        on_select="rerun",
        selection_mode=["selected_pair"],
        key=f"similarity_heatmap_{generation}",
    )
    pair_from_chart = extract_pair_from_event(event)
    if pair_from_chart and pair_from_chart != selected_pair:
        st.session_state[SELECTED_PAIR_KEY] = pair_from_chart
        st.session_state[CHART_GENERATION_KEY] = generation + 1
        st.rerun()

    with st.expander("Nummern der Zertifikate"):
        st.dataframe(
            pd.DataFrame(
                {
                    "Nr.": [f"{index + 1:02d}" for index in range(len(matrix_names))],
                    "Zertifikat": matrix_names,
                }
            ),
            width="stretch",
            hide_index=True,
        )

    comparison = compare_pair(
        selected_pair[0], selected_pair[1], certificates, selected_type_filter
    )
    st.markdown(
        f"**{comparison.certificate_a} ↔ {comparison.certificate_b}** · "
        f"Jaccard: **{comparison.jaccard:.3f}** · "
        f"Gemeinsam: **{len(comparison.shared_module_ids)}**"
    )

    shared_col, only_a_col, only_b_col = st.columns(3)
    tables = (
        (shared_col, "Gemeinsame Module", comparison.shared_module_ids),
        (only_a_col, f"Nur in {comparison.certificate_a}", comparison.only_a_module_ids),
        (only_b_col, f"Nur in {comparison.certificate_b}", comparison.only_b_module_ids),
    )
    for column, title, module_ids in tables:
        with column:
            st.markdown(f"**{title}**")
            st.dataframe(
                summarize_modules(module_ids, module_lookup),
                width="stretch",
                hide_index=True,
                height=320,
            )


render_app()
