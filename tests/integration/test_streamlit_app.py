from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_exception() -> None:
    app = AppTest.from_file("streamlit_app.py")
    app.run()

    assert not app.exception
    assert app.title[0].value == "Zertifikatsähnlichkeiten nach Modulen"


def test_type_filter_and_threshold_interactions() -> None:
    app = AppTest.from_file("streamlit_app.py").run()

    app.segmented_control[0].set_value("CAS").run()
    assert not app.exception
    assert app.segmented_control[0].value == "CAS"

    app.slider[0].set_value(0.5).run()
    assert not app.exception
    assert app.slider[0].value == 0.5


def test_pair_selectbox_updates_detail_comparison() -> None:
    app = AppTest.from_file("streamlit_app.py").run()
    pair_select = app.selectbox[0]
    assert len(pair_select.options) > 1

    expected_certificate = pair_select.options[1].split(" ↔ ")[0]
    pair_select.select(pair_select.options[1]).run()

    assert not app.exception
    assert expected_certificate in app.markdown[-4].value
