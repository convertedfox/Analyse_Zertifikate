from __future__ import annotations

from certificate_dashboard.ui_helpers import extract_pair_from_event


class DummySelection:
    def __init__(self, selected_pair: object) -> None:
        self.selected_pair = selected_pair


class DummyEvent:
    def __init__(self, selected_pair: object) -> None:
        self.selection = DummySelection(selected_pair)


def test_extract_pair_from_event_list_payload() -> None:
    payload = [{"certificate_a": "A", "certificate_b": "B"}]
    event = DummyEvent(payload)

    assert extract_pair_from_event(event) == ("A", "B")


def test_extract_pair_from_event_scalar_payload() -> None:
    payload = {"certificate_a": ["A"], "certificate_b": ["B"]}
    event = DummyEvent(payload)

    assert extract_pair_from_event(event) == ("A", "B")


def test_extract_pair_from_event_invalid_payload() -> None:
    event = DummyEvent([])

    assert extract_pair_from_event(event) is None
