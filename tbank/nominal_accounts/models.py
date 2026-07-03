from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.nominal_accounts.enums import (
    AddressType,
    DealStatus,
    PaymentStatus,
    StepStatus,
    TransferType,
)

# Суммы на запись: Decimal у пользователя, но в JSON уходит числом (T-API ждёт number).
WriteRubles = Annotated[
    Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")
]


class NominalModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class _Paged(NominalModel):
    """Общие поля страничного ответа."""

    offset: int
    limit: int
    size: int
    total: int


# --- Документы бенефициара (дискриминатор `type`) ---


class Passport(NominalModel):
    type: Literal["PASSPORT"] = "PASSPORT"
    serial: str
    number: str
    issued_on: date = Field(alias="date")
    division: str
    organization: Optional[str] = None


class ForeignPassport(NominalModel):
    type: Literal["FOREIGN_PASSPORT"] = "FOREIGN_PASSPORT"
    number: str
    issued_on: date = Field(alias="date")
    organization: str


class ForeignPassportOfForeignCitizens(NominalModel):
    type: Literal["FOREIGN_PASSPORT_OF_FOREIGN_CITIZENS"] = (
        "FOREIGN_PASSPORT_OF_FOREIGN_CITIZENS"
    )
    number: str
    issued_on: date = Field(alias="date")
    organization: str


class OfficialPassport(NominalModel):
    type: Literal["OFFICIAL_PASSPORT"] = "OFFICIAL_PASSPORT"
    number: str
    issued_on: date = Field(alias="date")
    organization: str


class DiplomaticPassport(NominalModel):
    type: Literal["DIPLOMATIC_PASSPORT"] = "DIPLOMATIC_PASSPORT"
    number: str
    issued_on: date = Field(alias="date")
    organization: str


class MigrationCard(NominalModel):
    type: Literal["MIGRATION_CARD"] = "MIGRATION_CARD"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: date


class TemporaryResidencePermit(NominalModel):
    type: Literal["TEMPORARY_RESIDENCE_PERMIT"] = "TEMPORARY_RESIDENCE_PERMIT"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: date


class Visa(NominalModel):
    type: Literal["VISA"] = "VISA"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: date


class Patent(NominalModel):
    type: Literal["PATENT"] = "PATENT"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: date


class ResidencePermit(NominalModel):
    type: Literal["RESIDENCE_PERMIT"] = "RESIDENCE_PERMIT"
    number: str
    issued_on: date = Field(alias="date")
    serial: Optional[str] = None
    expire_date: Optional[date] = None


class Contract(NominalModel):
    type: Literal["CONTRACT"] = "CONTRACT"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: Optional[date] = None


class ContractGPD(NominalModel):
    type: Literal["CONTRACT_GPD"] = "CONTRACT_GPD"
    number: str
    issued_on: date = Field(alias="date")
    expire_date: Optional[date] = None


Document = Annotated[
    Union[
        Passport,
        ForeignPassport,
        ForeignPassportOfForeignCitizens,
        OfficialPassport,
        DiplomaticPassport,
        MigrationCard,
        TemporaryResidencePermit,
        Visa,
        Patent,
        ResidencePermit,
        Contract,
        ContractGPD,
    ],
    Field(discriminator="type"),
]


class Address(NominalModel):
    type: AddressType
    address: str


# --- Бенефициары: запросы (дискриминатор `type`) ---


class _FlBeneficiaryBase(NominalModel):
    first_name: str
    last_name: str
    is_self_employed: bool
    birth_date: date
    citizenship: str
    documents: List[Document]
    addresses: List[Address]
    middle_name: Optional[str] = None
    birth_place: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    inn: Optional[str] = None


class BeneficiaryFlResidentRequest(_FlBeneficiaryBase):
    type: Literal["FL_RESIDENT"] = "FL_RESIDENT"
    snils: Optional[str] = None


class BeneficiaryFlNonresidentRequest(_FlBeneficiaryBase):
    type: Literal["FL_NONRESIDENT"] = "FL_NONRESIDENT"


class _IpBeneficiaryRequestBase(NominalModel):
    first_name: str
    last_name: str
    birth_date: date
    citizenship: str
    documents: List[Document]
    addresses: List[Address]
    registration_date: date
    inn: str
    middle_name: Optional[str] = None
    birth_place: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    ogrn: Optional[str] = None


class BeneficiaryIpResidentRequest(_IpBeneficiaryRequestBase):
    type: Literal["IP_RESIDENT"] = "IP_RESIDENT"


class BeneficiaryIpNonresidentRequest(_IpBeneficiaryRequestBase):
    type: Literal["IP_NONRESIDENT"] = "IP_NONRESIDENT"


class BeneficiaryUlResidentRequest(NominalModel):
    type: Literal["UL_RESIDENT"] = "UL_RESIDENT"
    inn: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    addresses: Optional[List[Address]] = None
    registration_date: Optional[date] = None
    opf: Optional[str] = None
    ogrn: Optional[str] = None


class BeneficiaryUlNonresidentRequest(NominalModel):
    type: Literal["UL_NONRESIDENT"] = "UL_NONRESIDENT"
    name: str
    addresses: List[Address]
    registration_date: date
    registration_number: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    nza: Optional[str] = None
    opf: Optional[str] = None
    inn: Optional[str] = None
    kio: Optional[str] = None


class BeneficiaryLiteContactRequest(NominalModel):
    type: Literal["LITE_CONTACT"] = "LITE_CONTACT"


BeneficiaryRequest = Annotated[
    Union[
        BeneficiaryFlResidentRequest,
        BeneficiaryFlNonresidentRequest,
        BeneficiaryIpResidentRequest,
        BeneficiaryIpNonresidentRequest,
        BeneficiaryUlResidentRequest,
        BeneficiaryUlNonresidentRequest,
        BeneficiaryLiteContactRequest,
    ],
    Field(discriminator="type"),
]


# --- Бенефициары: ответы (дискриминатор `type`) ---


class BeneficiaryFlResidentResponse(NominalModel):
    type: Literal["FL_RESIDENT"] = "FL_RESIDENT"
    beneficiary_id: str
    first_name: str
    last_name: str
    is_self_employed: bool
    birth_date: date
    middle_name: Optional[str] = None
    birth_place: Optional[str] = None
    citizenship: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    documents: Optional[List[Document]] = None
    addresses: Optional[List[Address]] = None
    inn: Optional[str] = None
    snils: Optional[str] = None


class BeneficiaryFlNonresidentResponse(NominalModel):
    type: Literal["FL_NONRESIDENT"] = "FL_NONRESIDENT"
    beneficiary_id: str
    first_name: str
    last_name: str
    is_self_employed: bool
    birth_date: date
    middle_name: Optional[str] = None
    birth_place: Optional[str] = None
    citizenship: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    documents: Optional[List[Document]] = None
    addresses: Optional[List[Address]] = None
    inn: Optional[str] = None


class _IpBeneficiaryResponseBase(NominalModel):
    beneficiary_id: str
    first_name: str
    last_name: str
    birth_date: date
    registration_date: date
    middle_name: Optional[str] = None
    birth_place: Optional[str] = None
    citizenship: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    documents: Optional[List[Document]] = None
    addresses: Optional[List[Address]] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None


class BeneficiaryIpResidentResponse(_IpBeneficiaryResponseBase):
    type: Literal["IP_RESIDENT"] = "IP_RESIDENT"


class BeneficiaryIpNonresidentResponse(_IpBeneficiaryResponseBase):
    type: Literal["IP_NONRESIDENT"] = "IP_NONRESIDENT"


class BeneficiaryUlResidentResponse(NominalModel):
    type: Literal["UL_RESIDENT"] = "UL_RESIDENT"
    beneficiary_id: str
    inn: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    addresses: Optional[List[Address]] = None
    registration_date: Optional[date] = None
    opf: Optional[str] = None
    ogrn: Optional[str] = None


class BeneficiaryUlNonresidentResponse(NominalModel):
    type: Literal["UL_NONRESIDENT"] = "UL_NONRESIDENT"
    beneficiary_id: str
    name: str
    registration_date: date
    registration_number: str
    phone_number: Optional[str] = None
    email: Optional[str] = None
    addresses: Optional[List[Address]] = None
    nza: Optional[str] = None
    opf: Optional[str] = None
    inn: Optional[str] = None
    kio: Optional[str] = None


class BeneficiaryLiteContactResponse(NominalModel):
    type: Literal["LITE_CONTACT"] = "LITE_CONTACT"
    beneficiary_id: str


BeneficiaryResponse = Annotated[
    Union[
        BeneficiaryFlResidentResponse,
        BeneficiaryFlNonresidentResponse,
        BeneficiaryIpResidentResponse,
        BeneficiaryIpNonresidentResponse,
        BeneficiaryUlResidentResponse,
        BeneficiaryUlNonresidentResponse,
        BeneficiaryLiteContactResponse,
    ],
    Field(discriminator="type"),
]


class BeneficiaryListResponse(_Paged):
    results: List[BeneficiaryResponse] = Field(default_factory=list)


# --- Бенефициары: скоринг (дискриминатор `status`) ---


class BeneficiaryScoringError(NominalModel):
    code: str
    description: str


class ScoringInProgress(NominalModel):
    status: Literal["IN_PROGRESS"] = "IN_PROGRESS"
    beneficiary_id: str


class ScoringSucceeded(NominalModel):
    status: Literal["SUCCEEDED"] = "SUCCEEDED"
    beneficiary_id: str
    warnings: Optional[List[BeneficiaryScoringError]] = None


class ScoringFailed(NominalModel):
    status: Literal["FAILED"] = "FAILED"
    beneficiary_id: str
    warnings: Optional[List[BeneficiaryScoringError]] = None
    errors: Optional[List[BeneficiaryScoringError]] = None


BeneficiaryScoringInfo = Annotated[
    Union[ScoringInProgress, ScoringSucceeded, ScoringFailed],
    Field(discriminator="status"),
]


class BeneficiaryScoringListResponse(_Paged):
    results: List[BeneficiaryScoringInfo] = Field(default_factory=list)


# --- Реквизиты для добавления карты (дискриминатор `status`) ---


class AddCardRequest(NominalModel):
    terminal_key: str


class PendingAddCardResponse(NominalModel):
    status: Literal["PENDING"] = "PENDING"
    beneficiary_id: str
    add_card_request_id: str
    terminal_key: str
    add_card_url: str


class ReadyAddCardResponse(NominalModel):
    status: Literal["READY"] = "READY"
    beneficiary_id: str
    add_card_request_id: str
    terminal_key: str
    bank_details_id: str


class FailedAddCardResponse(NominalModel):
    status: Literal["FAILED"] = "FAILED"
    beneficiary_id: str
    add_card_request_id: str
    terminal_key: str
    error_message: str


AddCardRequestResponse = Annotated[
    Union[PendingAddCardResponse, ReadyAddCardResponse, FailedAddCardResponse],
    Field(discriminator="status"),
]


# --- Банковские реквизиты бенефициара (дискриминатор `type`) ---


class RkcBankDetailsRequest(NominalModel):
    type: Literal["PAYMENT_DETAILS"] = "PAYMENT_DETAILS"
    bik: str
    bank_name: str
    account_number: str
    corr_account_number: str
    is_default: Optional[bool] = None
    kpp: Optional[str] = None
    inn: Optional[str] = None
    name: Optional[str] = None


class CardBankDetailsRequest(NominalModel):
    type: Literal["CARD"] = "CARD"
    terminal_key: str
    card_data: str
    is_default: Optional[bool] = None


class SbpBankDetailsRequest(NominalModel):
    type: Literal["SBP"] = "SBP"
    terminal_key: str
    phone_number: str
    bank_id: str
    is_default: Optional[bool] = None


BankDetailsRequest = Annotated[
    Union[RkcBankDetailsRequest, CardBankDetailsRequest, SbpBankDetailsRequest],
    Field(discriminator="type"),
]


class RkcBankDetailsResponse(NominalModel):
    type: Literal["PAYMENT_DETAILS"] = "PAYMENT_DETAILS"
    beneficiary_id: str
    bank_details_id: str
    bik: str
    bank_name: str
    account_number: str
    corr_account_number: str
    is_default: Optional[bool] = None
    kpp: Optional[str] = None
    inn: Optional[str] = None
    name: Optional[str] = None


class CardBankDetailsResponse(NominalModel):
    type: Literal["CARD"] = "CARD"
    beneficiary_id: str
    bank_details_id: str
    card_id: str
    terminal_key: str
    is_default: Optional[bool] = None


class SbpBankDetailsResponse(NominalModel):
    type: Literal["SBP"] = "SBP"
    beneficiary_id: str
    bank_details_id: str
    phone_number: str
    bank_id: str
    terminal_key: str
    is_default: Optional[bool] = None


BankDetailsResponse = Annotated[
    Union[RkcBankDetailsResponse, CardBankDetailsResponse, SbpBankDetailsResponse],
    Field(discriminator="type"),
]


class BankDetailsListResponse(_Paged):
    results: List[BankDetailsResponse] = Field(default_factory=list)


# --- Банковские реквизиты в карточке платежа (дискриминатор `type`) ---


class RkcBankDetails(NominalModel):
    type: Literal["PAYMENT_DETAILS"] = "PAYMENT_DETAILS"
    bik: str
    bank_name: str
    account_number: str
    corr_account_number: str
    kpp: Optional[str] = None
    inn: Optional[str] = None
    name: Optional[str] = None


class CardBankDetails(NominalModel):
    type: Literal["CARD"] = "CARD"
    card_id: str
    terminal_key: str


class SbpBankDetails(NominalModel):
    type: Literal["SBP"] = "SBP"
    phone_number: str
    bank_id: str
    terminal_key: str


BankDetails = Annotated[
    Union[RkcBankDetails, CardBankDetails, SbpBankDetails],
    Field(discriminator="type"),
]


# --- Сделки ---


class DealRequest(NominalModel):
    account_number: str


class DealResponse(NominalModel):
    deal_id: str
    account_number: str
    status: DealStatus


class DealListResponse(_Paged):
    results: List[DealResponse] = Field(default_factory=list)


class DealValidityReason(NominalModel):
    code: Optional[str] = None
    description: Optional[str] = None
    details: Optional[Dict[str, str]] = None


class DealValidity(NominalModel):
    is_valid: bool
    reasons: Optional[List[DealValidityReason]] = None


# --- Этапы сделки ---


class StepRequest(NominalModel):
    description: str


class StepResponse(NominalModel):
    deal_id: str
    step_id: str
    step_number: int
    description: str
    status: StepStatus


class StepListResponse(_Paged):
    results: List[StepResponse] = Field(default_factory=list)


# --- Депоненты ---


class DeponentRequest(NominalModel):
    amount: WriteRubles


class DeponentResponse(NominalModel):
    deal_id: str
    step_id: str
    beneficiary_id: str
    amount: Rubles


class DeponentListResponse(_Paged):
    results: List[DeponentResponse] = Field(default_factory=list)


# --- Реципиенты ---


class RecipientRequest(NominalModel):
    beneficiary_id: str
    amount: WriteRubles
    tax: Optional[WriteRubles] = None
    purpose: Optional[str] = None
    bank_details_id: Optional[str] = None
    keep_on_virtual_account: Optional[bool] = None


class RecipientResponse(NominalModel):
    deal_id: str
    step_id: str
    beneficiary_id: str
    recipient_id: str
    amount: Rubles
    tax: Optional[Rubles] = None
    purpose: Optional[str] = None
    bank_details_id: Optional[str] = None
    keep_on_virtual_account: Optional[bool] = None


class RecipientListResponse(_Paged):
    results: List[RecipientResponse] = Field(default_factory=list)


class UpdateRecipientBankDetailsRequest(NominalModel):
    bank_details_id: str


# --- Платежи (биллинг), дискриминатор `type` ---


class TaxThirdParty(NominalModel):
    inn: str
    kpp: str


class TaxPaymentParameters(NominalModel):
    payer_status: str
    kbk: str
    oktmo: str
    evidence: str
    period: str
    doc_number: str
    doc_date: str
    third_party: Optional[TaxThirdParty] = None


class CreateRegularPaymentRequest(NominalModel):
    type: Literal["REGULAR"] = "REGULAR"
    beneficiary_id: str
    account_number: str
    amount: WriteRubles
    purpose: str
    bank_details_id: Optional[str] = None


class CreateTaxPaymentRequest(NominalModel):
    type: Literal["TAX"] = "TAX"
    beneficiary_id: str
    account_number: str
    bank_details: BankDetails
    amount: WriteRubles
    purpose: str
    uin: str
    tax: TaxPaymentParameters


CreatePaymentRequest = Annotated[
    Union[CreateRegularPaymentRequest, CreateTaxPaymentRequest],
    Field(discriminator="type"),
]


class RegularPaymentResponse(NominalModel):
    type: Literal["REGULAR"] = "REGULAR"
    payment_id: str
    beneficiary_id: str
    account_number: str
    bank_details: BankDetails
    amount: Rubles
    status: PaymentStatus
    purpose: str
    deal_id: Optional[str] = None
    step_id: Optional[str] = None
    recipient_id: Optional[str] = None
    error_message: Optional[str] = None
    operation_id: Optional[str] = None


class TaxPaymentResponse(NominalModel):
    type: Literal["TAX"] = "TAX"
    payment_id: str
    beneficiary_id: str
    account_number: str
    bank_details: BankDetails
    amount: Rubles
    status: PaymentStatus
    purpose: str
    uin: str
    tax: TaxPaymentParameters
    error_message: Optional[str] = None
    operation_id: Optional[str] = None


PaymentResponse = Annotated[
    Union[RegularPaymentResponse, TaxPaymentResponse],
    Field(discriminator="type"),
]


class PaymentListResponse(_Paged):
    results: List[PaymentResponse] = Field(default_factory=list)


class RetryPaymentResponse(NominalModel):
    retry_payment_id: str


# --- Неидентифицированные пополнения ---


class IncomingTransactionListItem(NominalModel):
    account_number: str
    operation_id: str
    amount: Rubles
    currency: Optional[str] = None
    operation_amount: Optional[Rubles] = None
    operation_currency: Optional[str] = None
    payer_bik: Optional[str] = None
    payer_kpp: Optional[str] = None
    payer_inn: Optional[str] = None
    payer_bank_name: Optional[str] = None
    payer_bank_swift_code: Optional[str] = None
    payer_account_number: Optional[str] = None
    payer_corr_account_number: Optional[str] = None
    payer_name: Optional[str] = None
    payment_purpose: Optional[str] = None
    document_number: Optional[str] = None
    charge_date: Optional[datetime] = None
    authorization_date: Optional[datetime] = None
    transaction_date: Optional[datetime] = None
    draw_date: Optional[datetime] = None


class IncomingTransactionListResponse(_Paged):
    results: List[IncomingTransactionListItem] = Field(default_factory=list)


class AmountDistributionItem(NominalModel):
    beneficiary_id: str
    amount: WriteRubles


class IdentifyIncomingTransactionRequest(NominalModel):
    amount_distribution: Optional[List[AmountDistributionItem]] = None


# --- Виртуальные счета: балансы и холды ---


class BalanceListItem(NominalModel):
    beneficiary_id: str
    account_number: str
    amount: Rubles
    amount_on_hold: Rubles


class BalanceListResponse(_Paged):
    results: List[BalanceListItem] = Field(default_factory=list)


class HoldListItem(NominalModel):
    beneficiary_id: str
    account_number: str
    hold_id: str
    amount: Rubles
    deal_id: Optional[str] = None
    step_id: Optional[str] = None
    recipient_id: Optional[str] = None
    payment_id: Optional[str] = None


class HoldListResponse(_Paged):
    results: List[HoldListItem] = Field(default_factory=list)


# --- Виртуальные счета: переводы ---


class TransferParty(NominalModel):
    beneficiary_id: str


class CreateTransferRequest(NominalModel):
    account_number: str
    from_: TransferParty = Field(alias="from")
    to: TransferParty
    amount: WriteRubles
    purpose: Optional[str] = None


class TransferResponse(NominalModel):
    transfer_id: str
    account_number: str
    from_: TransferParty = Field(alias="from")
    to: TransferParty
    amount: Rubles
    type: Optional[TransferType] = None
    purpose: Optional[str] = None


class TransferListResponse(_Paged):
    results: List[TransferResponse] = Field(default_factory=list)
