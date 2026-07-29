from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_exception() -> None:
    app = AppTest.from_file("streamlit_app.py")
    app.run()

    assert not app.exception
    assert app.title[0].value == "Zertifikatsähnlichkeiten nach Modulen"
