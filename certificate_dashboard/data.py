from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from .models import CertificateEntry, CertificateType, ModuleRecord

TypeFilter = Literal["CAS", "DAS", "CAS+DAS"]
DATASET_SCHEMA_VERSION = 1


class DatasetValidationError(ValueError):
    """Raised when the generated certificate dataset violates its schema."""


def load_dataset(path: Path) -> tuple[list[str], dict[str, CertificateEntry]]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatasetValidationError(f"Could not read dataset {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise DatasetValidationError("Dataset root must be an object")
    if payload.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise DatasetValidationError(
            f"Unsupported schema version: {payload.get('schema_version')!r}; "
            f"expected {DATASET_SCHEMA_VERSION}"
        )

    selected_names = _string_list(
        payload.get("selected_certificate_names"), "selected_certificate_names"
    )
    raw_certificates = payload.get("certificates")
    if not isinstance(raw_certificates, list):
        raise DatasetValidationError("certificates must be a list")

    certificates: dict[str, CertificateEntry] = {}
    for index, cert in enumerate(raw_certificates):
        if not isinstance(cert, dict):
            raise DatasetValidationError(f"certificates[{index}] must be an object")
        certificate_name = _required_string(
            cert.get("certificate_name"), f"certificates[{index}].certificate_name"
        )
        if certificate_name in certificates:
            raise DatasetValidationError(f"Duplicate certificate: {certificate_name}")

        raw_modules_by_type = cert.get("modules_by_type")
        if not isinstance(raw_modules_by_type, dict):
            raise DatasetValidationError(f"modules_by_type missing for {certificate_name}")

        modules_by_type: dict[CertificateType, tuple[ModuleRecord, ...]] = {}
        for cert_type in ("CAS", "DAS"):
            typed = cast_cert_type(cert_type)
            raw_modules = raw_modules_by_type.get(cert_type)
            if not isinstance(raw_modules, list):
                raise DatasetValidationError(
                    f"modules_by_type.{cert_type} must be a list for {certificate_name}"
                )

            parsed_modules: list[ModuleRecord] = []
            module_ids: set[str] = set()
            for module_index, module in enumerate(raw_modules):
                if not isinstance(module, dict):
                    raise DatasetValidationError(
                        f"Module {module_index} for {certificate_name} must be an object"
                    )
                module_id = _required_string(module.get("module_id"), "module_id")
                module_name = _required_string(module.get("module_name"), "module_name")
                if module_id in module_ids:
                    raise DatasetValidationError(
                        f"Duplicate module {module_id} in {certificate_name} ({cert_type})"
                    )
                module_ids.add(module_id)
                parsed_modules.append(ModuleRecord(module_id=module_id, module_name=module_name))
            modules_by_type[typed] = tuple(parsed_modules)

        certificates[certificate_name] = CertificateEntry(
            certificate_name=certificate_name,
            modules_by_type=modules_by_type,
        )

    if len(set(selected_names)) != len(selected_names):
        raise DatasetValidationError("selected_certificate_names contains duplicates")
    unknown = [name for name in selected_names if name not in certificates]
    if unknown:
        raise DatasetValidationError(f"Selected certificates missing from dataset: {unknown!r}")

    return selected_names, certificates


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(f"{field} must be a non-empty string")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise DatasetValidationError(f"{field} must be a list of non-empty strings")
    return cast(list[str], value)


def cast_cert_type(value: str) -> CertificateType:
    if value not in ("CAS", "DAS"):
        raise ValueError(f"Unsupported certificate type: {value}")
    return cast(CertificateType, value)


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
