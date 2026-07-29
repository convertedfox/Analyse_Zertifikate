from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CertificateType = Literal["CAS", "DAS"]


@dataclass(frozen=True)
class ModuleRecord:
    module_id: str
    module_name: str


@dataclass(frozen=True)
class CertificateEntry:
    certificate_name: str
    modules_by_type: dict[CertificateType, tuple[ModuleRecord, ...]]


@dataclass(frozen=True)
class PairComparison:
    certificate_a: str
    certificate_b: str
    shared_module_ids: tuple[str, ...]
    only_a_module_ids: tuple[str, ...]
    only_b_module_ids: tuple[str, ...]
    jaccard: float
