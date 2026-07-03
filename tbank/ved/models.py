from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.ved.enums import (
    ApplicationStatus,
    ContractSubject,
    ContractType,
    EstateType,
    SignAffiliation,
    Supply,
)

WriteDecimal = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class VedModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Attachment(VedModel):
    document_id: Union[int, str]
    document_name: Optional[str] = None
    version: Optional[int] = None


class Counterparty(VedModel):
    name: str
    country_code: str
    sign_affiliation: Optional[SignAffiliation] = None


class ResidentInfo(VedModel):
    inn: str
    kpp: Optional[str] = None


class ContractInfo(VedModel):
    """Сведения о валютном контракте для постановки на учёт."""

    contract_subject: ContractSubject
    currency_code: str
    contract_date: date
    exchange_rate_effective_date: date
    contract_type: Optional[ContractType] = None
    supply: Optional[Supply] = None
    estate_type: Optional[EstateType] = None
    amount: Optional[WriteDecimal] = None
    liabilities_finish_date: Optional[date] = None
    contract_number: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    counterparty: Optional[List[Counterparty]] = None


class RegisterContractRequest(VedModel):
    open_api_application_id: str
    contract_info: ContractInfo
    resident_info: Optional[ResidentInfo] = None


class ApplicationResult(VedModel):
    """Ответ на регистрацию/изменение/снятие контракта."""

    open_api_application_id: str


# --- Изменение контракта ---


class AmendmentDocument(VedModel):
    document_date: date
    attachments: List[Attachment]
    document_number: Optional[str] = None


class AmendContractRequest(VedModel):
    open_api_application_id: str
    unique_contract_number: str
    amendments: Dict[str, Any]
    amendment_documents: Optional[List[AmendmentDocument]] = None


# --- Снятие с учёта ---


class ChangeDocument(VedModel):
    document_date: date
    document_number: Optional[str] = None


class AssignmentResidentInfo(VedModel):
    name: str
    ogrn: str
    ogrn_date: date
    inn: str
    kpp: Optional[str] = None
    change_document: Optional[ChangeDocument] = None


class AssignmentNonResidentInfo(VedModel):
    name: str
    country_code: str
    change_document: Optional[ChangeDocument] = None


class DeregisterContractRequest(VedModel):
    open_api_application_id: str
    unique_contract_number: str
    deregistration_reason: int
    attachments: Optional[List[Attachment]] = None
    assignment_resident_info: Optional[AssignmentResidentInfo] = None
    assignment_non_resident_info: Optional[AssignmentNonResidentInfo] = None


# --- Статус заявления ---


class ApplicationStatusMetadata(VedModel):
    unique_contract_number: Optional[str] = None


class ApplicationStatusInfo(VedModel):
    open_api_application_id: str
    status: ApplicationStatus
    datetime: datetime
    metadata: ApplicationStatusMetadata
    description: Optional[str] = None
