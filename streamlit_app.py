from __future__ import annotations

from pathlib import Path
from typing import cast

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from certificate_dashboard.data import (
    TypeFilter,
    load_dataset,
    merged_modules,
    module_name_lookup,
    names_with_modules,
)
from certificate_dashboard.models import CertificateEntry
from certificate_dashboard.similarity import build_similarity_matrix, compare_pair

DATA_PATH = Path("data/certificates.json")


@st.cache_data(show_spinner=False)
def load_dashboard_data(path: str) -> tuple[list[str], dict[str, CertificateEntry]]:
    selected_names, certificates = load_dataset(Path(path))
    return selected_names, certificates


def palette_hex(value: float) -> str:
    value = max(0.0, min(1.0, value))
    # Neutral paper -> rust scale
    start = (247, 245, 241)
    end = (121, 53, 33)
    red = int(start[0] + (end[0] - start[0]) * value)
    green = int(start[1] + (end[1] - start[1]) * value)
    blue = int(start[2] + (end[2] - start[2]) * value)
    return f"#{red:02x}{green:02x}{blue:02x}"


def text_color(value: float) -> str:
    return "#f8f7f4" if value >= 0.55 else "#2e2a26"


def render_heatmap_table(matrix: pd.DataFrame, threshold: float) -> Styler:
    def style_cell(value: float) -> str:
        if pd.isna(value):
            return "background-color: #ece8e0; color: #2e2a26;"

        if value < threshold:
            return "background-color: #ece8e0; color: #5e574f;"

        background = palette_hex(value)
        return f"background-color: {background}; color: {text_color(value)};"

    return matrix.style.format("{:.2f}").map(style_cell)


def pair_options(similarity_matrix: pd.DataFrame, threshold: float) -> list[tuple[str, str, float]]:
    options: list[tuple[str, str, float]] = []
    names = list(similarity_matrix.index)
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            score = float(similarity_matrix.loc[left_name, right_name])
            if score >= threshold:
                options.append((left_name, right_name, score))

    options.sort(key=lambda item: item[2], reverse=True)
    return options


def summarize_modules(module_ids: tuple[str, ...], lookup: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Modulnummer": list(module_ids),
            "Modulname": [lookup[module_id] for module_id in module_ids],
        }
    )


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
    if not active_names:
        st.warning("Mit diesem Typfilter gibt es keine Zertifikate mit Modulen.")
        st.stop()

    similarity_matrix = build_similarity_matrix(active_names, certificates, selected_type_filter)
    modules_per_certificate = {
        name: len(merged_modules(certificates[name], selected_type_filter)) for name in active_names
    }

    left_col, right_col, third_col = st.columns(3)
    left_col.metric("Zertifikate", len(active_names), border=True)
    right_col.metric(
        "Durchschnittliche Module", f"{pd.Series(modules_per_certificate).mean():.1f}", border=True
    )
    third_col.metric("Mindestähnlichkeit", f"{threshold:.2f}", border=True)

    st.subheader("Ähnlichkeitsmatrix")
    st.dataframe(
        render_heatmap_table(similarity_matrix, threshold),
        use_container_width=True,
        height=640,
    )

    candidate_pairs = pair_options(similarity_matrix, threshold)
    if not candidate_pairs:
        st.info("Kein Zertifikatspaar erreicht den aktuellen Schwellwert.")
        st.stop()

    st.subheader("Zertifikatspaar auswählen")
    options = [f"{a} ↔ {b} (Jaccard {score:.2f})" for a, b, score in candidate_pairs]
    selected_label = st.selectbox(
        "Paar",
        options=options,
    )
    selected_index = options.index(selected_label)
    certificate_a, certificate_b, _score = candidate_pairs[selected_index]

    comparison = compare_pair(certificate_a, certificate_b, certificates, selected_type_filter)

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
