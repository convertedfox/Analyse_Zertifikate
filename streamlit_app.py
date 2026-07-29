from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import altair as alt
import pandas as pd
import streamlit as st

from certificate_dashboard.data import (
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

DATA_PATH = Path("data/certificates.json")
SELECTED_PAIR_KEY = "selected_pair"
SELECTED_PAIR_FROM_HEATMAP_KEY = "selected_pair_from_heatmap"


@st.cache_data(show_spinner=False)
def load_dashboard_data(path: str) -> tuple[list[str], dict[str, CertificateEntry]]:
    selected_names, certificates = load_dataset(Path(path))
    return selected_names, certificates


def summarize_modules(module_ids: tuple[str, ...], lookup: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Modulnummer": list(module_ids),
            "Modulname": [lookup[module_id] for module_id in module_ids],
        }
    )


def ensure_pair_state(
    pair_candidates: list[tuple[str, str, float]],
) -> tuple[str, str, float]:
    if not pair_candidates:
        raise ValueError("No pair candidates available")

    fallback = pair_candidates[0]
    pair_map = {(a, b): score for a, b, score in pair_candidates}
    selected_pair = st.session_state.get(SELECTED_PAIR_KEY)

    if selected_pair is None:
        st.session_state[SELECTED_PAIR_KEY] = (fallback[0], fallback[1])
        return fallback

    pair_key = tuple(selected_pair)
    if pair_key in pair_map:
        return (pair_key[0], pair_key[1], pair_map[pair_key])

    st.session_state[SELECTED_PAIR_KEY] = (fallback[0], fallback[1])
    return fallback


def pair_label(certificate_a: str, certificate_b: str, score: float) -> str:
    return f"{certificate_a} ↔ {certificate_b} (Jaccard {score:.2f})"


def build_heatmap(
    pair_frame: pd.DataFrame,
    threshold: float,
    selected_pair: tuple[str, str],
) -> Any:
    visible = pair_frame[pair_frame["jaccard"] >= threshold].copy()
    hidden = pair_frame[pair_frame["jaccard"] < threshold].copy()

    base = (
        alt.Chart(hidden)
        .mark_rect(stroke="#d6cec2", strokeWidth=0.2)
        .encode(
            x=alt.X("col_index:O", axis=None),
            y=alt.Y("row_index:O", axis=None),
            tooltip=[
                alt.Tooltip("certificate_a:N", title="Zertifikat A"),
                alt.Tooltip("certificate_b:N", title="Zertifikat B"),
                alt.Tooltip("jaccard:Q", title="Jaccard", format=".3f"),
            ],
        )
        .properties(height=650)
    )

    neutral = base.encode(color=alt.value("#ece8e0"))

    click_selection = alt.selection_point(
        name="selected_pair",
        fields=["certificate_a", "certificate_b"],
        on="click",
        clear=False,
        empty=False,
    )

    active = (
        alt.Chart(visible)
        .mark_rect(stroke="#d6cec2", strokeWidth=0.2)
        .encode(
            x=alt.X("col_index:O", axis=None),
            y=alt.Y("row_index:O", axis=None),
            color=alt.Color(
                "jaccard:Q",
                title="Jaccard",
                scale=alt.Scale(
                    domain=[threshold, 1],
                    range=["#efeae1", "#793521"],
                ),
            ),
            tooltip=[
                alt.Tooltip("certificate_a:N", title="Zertifikat A"),
                alt.Tooltip("certificate_b:N", title="Zertifikat B"),
                alt.Tooltip("jaccard:Q", title="Jaccard", format=".3f"),
                alt.Tooltip("shared_module_count:Q", title="Gemeinsame Module"),
            ],
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
            x=alt.X("col_index:O", axis=None),
            y=alt.Y("row_index:O", axis=None),
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
        st.error(
            "Daten fehlen: Bitte zuerst `uv run python scripts/export_certificates.py` ausführen."
        )
        st.stop()

    ordered_names, certificates = load_dashboard_data(str(DATA_PATH))
    module_lookup = module_name_lookup(certificates)

    with st.sidebar:
        st.subheader("Filter")

        type_filter = st.segmented_control(
            "Zertifikatstyp",
            options=["CAS", "DAS", "CAS+DAS"],
            default="CAS+DAS",
        )
        if type_filter is None:
            type_filter = "CAS+DAS"
        selected_type_filter = cast(TypeFilter, type_filter)

        threshold = st.slider(
            "Mindestähnlichkeit", min_value=0.0, max_value=1.0, value=0.3, step=0.01
        )

        st.caption(
            "Bei gleichnamigen Zertifikaten folgt das Modulset dem Typfilter: "
            "CAS, DAS oder Vereinigung."
        )

    active_names = names_with_modules(ordered_names, certificates, selected_type_filter)
    if len(active_names) < 2:
        st.warning("Mit diesem Typfilter gibt es weniger als zwei analysierbare Zertifikate.")
        st.stop()

    pair_frame = build_upper_triangle_pairs(active_names, certificates, selected_type_filter)
    visible_pairs = top_pairs(pair_frame, threshold, limit=5000)
    if not visible_pairs:
        st.info("Kein Zertifikatspaar erreicht den aktuellen Schwellwert.")
        st.stop()

    top_20_pairs = top_pairs(pair_frame, threshold, limit=20)

    modules_per_certificate = {
        name: len(merged_modules(certificates[name], selected_type_filter)) for name in active_names
    }
    metric_one, metric_two, metric_three = st.columns(3)
    metric_one.metric("Zertifikate", len(active_names), border=True)
    metric_two.metric(
        "Durchschnittliche Module", f"{pd.Series(modules_per_certificate).mean():.1f}", border=True
    )
    metric_three.metric("Paare über Schwelle", len(visible_pairs), border=True)

    st.subheader("Ähnlichkeitsmatrix (oberes Dreieck)")

    current_pair = ensure_pair_state(visible_pairs)
    chart = build_heatmap(pair_frame, threshold, (current_pair[0], current_pair[1]))
    event = st.altair_chart(
        chart,
        width="stretch",
        on_select="rerun",
        selection_mode=["selected_pair"],
        key="similarity_heatmap",
    )

    pair_from_chart = extract_pair_from_event(event)
    if pair_from_chart and pair_from_chart != st.session_state.get(SELECTED_PAIR_FROM_HEATMAP_KEY):
        st.session_state[SELECTED_PAIR_FROM_HEATMAP_KEY] = pair_from_chart
        st.session_state[SELECTED_PAIR_KEY] = pair_from_chart
        st.rerun()

    st.subheader("Top-20-Paare")
    option_labels = [pair_label(a, b, score) for a, b, score in top_20_pairs]

    top_map = {(a, b): score for a, b, score in top_20_pairs}
    selected_pair_key = cast(tuple[str, str], st.session_state[SELECTED_PAIR_KEY])

    selected_label_default: str
    if selected_pair_key not in top_map:
        score_map = {(a, b): score for a, b, score in visible_pairs}
        selected_score = score_map[selected_pair_key]
        selected_label_default = (
            "Aktuelle Heatmap-Auswahl: "
            f"{pair_label(selected_pair_key[0], selected_pair_key[1], selected_score)}"
        )
        option_labels = [selected_label_default, *option_labels]
    else:
        selected_score = top_map[selected_pair_key]
        selected_label_default = pair_label(
            selected_pair_key[0], selected_pair_key[1], selected_score
        )

    selected_label = st.selectbox(
        "Paar (Top 20)",
        options=option_labels,
        index=option_labels.index(selected_label_default),
    )

    if selected_label.startswith("Aktuelle Heatmap-Auswahl:"):
        selected_lookup = {pair_label(a, b, score): (a, b, score) for a, b, score in visible_pairs}
        selected_key = selected_label.replace("Aktuelle Heatmap-Auswahl: ", "")
        chosen_pair = selected_lookup[selected_key]
    else:
        selected_lookup = {pair_label(a, b, score): (a, b, score) for a, b, score in top_20_pairs}
        chosen_pair = selected_lookup[selected_label]

    st.session_state[SELECTED_PAIR_KEY] = (chosen_pair[0], chosen_pair[1])

    comparison = compare_pair(
        chosen_pair[0],
        chosen_pair[1],
        certificates,
        selected_type_filter,
    )

    st.markdown(
        f"**{comparison.certificate_a} ↔ {comparison.certificate_b}** · "
        f"Jaccard: **{comparison.jaccard:.3f}** · "
        f"Gemeinsam: **{len(comparison.shared_module_ids)}**"
    )

    shared_col, only_a_col, only_b_col = st.columns(3)
    with shared_col:
        st.markdown("**Gemeinsame Module**")
        st.dataframe(
            summarize_modules(comparison.shared_module_ids, module_lookup),
            use_container_width=True,
            hide_index=True,
            height=320,
        )
    with only_a_col:
        st.markdown(f"**Nur in {comparison.certificate_a}**")
        st.dataframe(
            summarize_modules(comparison.only_a_module_ids, module_lookup),
            use_container_width=True,
            hide_index=True,
            height=320,
        )
    with only_b_col:
        st.markdown(f"**Nur in {comparison.certificate_b}**")
        st.dataframe(
            summarize_modules(comparison.only_b_module_ids, module_lookup),
            use_container_width=True,
            hide_index=True,
            height=320,
        )


render_app()
