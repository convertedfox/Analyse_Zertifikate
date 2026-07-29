from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from .models import CertificateEntry, CertificateType, ModuleRecord

TypeFilter = Literal["CAS", "DAS", "CAS+DAS"]


def load_dataset(path: Path) -> tuple[list[str], dict[str, CertificateEntry]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected_names = payload["selected_certificate_names"]

    certificates: dict[str, CertificateEntry] = {}
    for cert in payload["certificates"]:
        modules_by_type: dict[CertificateType, tuple[ModuleRecord, ...]] = {}
        for cert_type, modules in cert["modules_by_type"].items():
            typed = cast_cert_type(cert_type)
            modules_by_type[typed] = tuple(
                ModuleRecord(module_id=module["module_id"], module_name=module["module_name"])
                for module in modules
            )

        certificates[cert["certificate_name"]] = CertificateEntry(
            certificate_name=cert["certificate_name"],
            modules_by_type=modules_by_type,
        )

    return selected_names, certificates


def cast_cert_type(value: str) -> CertificateType:
    if value not in ("CAS", "DAS"):
        raise ValueError(f"Unsupported certificate type: {value}")
    return cast(CertificateType, value)


def available_types(entry: CertificateEntry) -> set[CertificateType]:
    return set(entry.modules_by_type.keys())


def merged_modules(entry: CertificateEntry, type_filter: TypeFilter) -> tuple[ModuleRecord, ...]:
    if type_filter == "CAS":
        return entry.modules_by_type.get("CAS", tuple())
    if type_filter == "DAS":
        return entry.modules_by_type.get("DAS", tuple())

    by_id: dict[str, ModuleRecord] = {}
    for cert_type in ("CAS", "DAS"):
        for module in entry.modules_by_type.get(cert_type, tuple()):
            by_id[module.module_id] = module
    return tuple(sorted(by_id.values(), key=lambda module: module.module_id))


def module_name_lookup(certificates: dict[str, CertificateEntry]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for entry in certificates.values():
        for modules in entry.modules_by_type.values():
            for module in modules:
                lookup[module.module_id] = module.module_name
    return lookup


def names_with_modules(
    ordered_names: list[str],
    certificates: dict[str, CertificateEntry],
    type_filter: TypeFilter,
) -> list[str]:
    return [
        name
        for name in ordered_names
        if name in certificates and merged_modules(certificates[name], type_filter)
    ]
