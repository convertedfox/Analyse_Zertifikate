from __future__ import annotations


def extract_pair_from_event(event: object) -> tuple[str, str] | None:
    selection = getattr(event, "selection", None)
    if selection is None:
        return None

    selected = getattr(selection, "selected_pair", None)
    if not selected:
        return None

    if isinstance(selected, list) and selected:
        selected = selected[0]

    if isinstance(selected, dict):
        certificate_a = selected.get("certificate_a")
        certificate_b = selected.get("certificate_b")
        if isinstance(certificate_a, list):
            certificate_a = certificate_a[0] if certificate_a else None
        if isinstance(certificate_b, list):
            certificate_b = certificate_b[0] if certificate_b else None

        if isinstance(certificate_a, str) and isinstance(certificate_b, str):
            return certificate_a, certificate_b

    return None
