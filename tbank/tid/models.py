from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from tbank.tid.enums import (
    AddressType,
    BundleCode,
    CardType,
    CounterRepeatability,
    DocumentCheckStatus,
    Grade,
    IdDocumentType,
    IdentificationResult,
    LegalStatus,
    TaxationScheme,
)


class TidModel(BaseModel):
    """Базовая модель данных T-ID: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- T-Business ID: информация о компании ---


class CompanyRequisites(TidModel):
    full_name: str
    foreign_name: Optional[str] = None
    address: str
    legal_address: str
    inn: str
    kpp: Optional[str] = None
    ogrn: Optional[str] = None


class CompanyBank(TidModel):
    bank_name: str
    bank_address: str
    corr_account: str
    bank_inn: str
    bank_bic: str


class CompanyInfo(TidModel):
    name: str
    city: str
    requisites: CompanyRequisites
    bank: CompanyBank
    legal_status: LegalStatus
    registration_date: Optional[date] = None
    opf: Optional[str] = None
    taxation_scheme: Optional[TaxationScheme] = None


class SignerStatus(TidModel):
    is_signer: bool


# --- Информация о пользователе ---


class UserAccountInfo(TidModel):
    """Учётные данные пользователя (userinfo T-ID data endpoint)."""

    sub: str
    phone_number: Optional[str] = None
    given_name: Optional[str] = None
    middle_name: Optional[str] = None
    family_name: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None


class InnResponse(TidModel):
    inn: Optional[str] = None


class SnilsResponse(TidModel):
    snils: Optional[str] = None


class PassportData(TidModel):
    birth_date: Optional[date] = None
    birth_place: Optional[str] = None
    citizenship: Optional[str] = None
    issue_date: Optional[date] = None
    marital_status: Optional[str] = None
    marriage_date: Optional[date] = None
    number_of_children: Optional[int] = None
    resident: Optional[bool] = None
    serial_number: Optional[str] = None
    unit_code: Optional[str] = None
    unit_name: Optional[str] = None
    valid_to: Optional[date] = None
    id_type: Optional[IdDocumentType] = None


class DriverLicense(TidModel):
    doc_number: str
    issue_date: Optional[date] = None


class DriverLicensesResponse(TidModel):
    licenses: List[DriverLicense] = Field(default_factory=list)


class Address(TidModel):
    address_type: AddressType
    primary: bool
    apartment: Optional[str] = None
    building: Optional[str] = None
    city: Optional[str] = None
    claddr_code: Optional[str] = None
    country: Optional[str] = None
    district: Optional[str] = None
    fias_code: Optional[str] = None
    house: Optional[str] = None
    housing: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region: Optional[str] = None
    settlement: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None


class AddressesResponse(TidModel):
    addresses: List[Address] = Field(default_factory=list)


class DebitAccountBank(TidModel):
    bik: str
    cor_account: str
    name: str


class DebitAccount(TidModel):
    name: str
    account_number: str
    bank: DebitAccountBank


class DebitAccountsResponse(TidModel):
    accounts: List[DebitAccount] = Field(default_factory=list)


# --- Статусы физлица ---


class IdentificationStatus(TidModel):
    is_identified: bool


class SelfEmployedStatus(TidModel):
    is_self_employed: bool


class ForeignAgentStatus(TidModel):
    is_foreign_agent: bool


class PdlStatus(TidModel):
    is_public_official_person: bool


class BlacklistStatus(TidModel):
    is_blacklisted: bool


# --- Кобренд ---


class CobrandAccount(TidModel):
    card_type: CardType
    loyalty_id: Optional[str] = None


class CobrandResponse(TidModel):
    program_status: bool
    accounts: List[CobrandAccount] = Field(default_factory=list)


# --- Счётчики услуг ---


class CounterClientInfo(TidModel):
    grade: Grade
    is_fulfill_conditions: bool


class CounterPeriod(TidModel):
    valid_from: str
    valid_until: str
    repeatability: CounterRepeatability


class CounterInfo(TidModel):
    count: int
    is_infinity: bool
    period: CounterPeriod


class DetailCounters(TidModel):
    client_info: CounterClientInfo
    counter_info: CounterInfo


class SetCounterExtraFields(TidModel):
    description: str


class SetCounterRequest(TidModel):
    count: int
    extra_fields: Optional[SetCounterExtraFields] = None
    request_id: Optional[str] = None


class SetCounterResponse(TidModel):
    count: int
    is_infinity: bool


# --- Подписки ---


class SubscriptionResponse(TidModel):
    type: BundleCode


class SubscriptionGrade(TidModel):
    bundle_code: Optional[str] = None
    grade_code: Optional[str] = None


# --- Делегированная идентификация ---


class DelegatedIdentification(TidModel):
    date_time_delegated_identified: datetime
    sub: str
    phone_number: str
    family_name: str
    given_name: str
    passport_birth_date: date
    issue_date: date
    serial_number: str
    unit_code: str
    unit_name: str
    id_type: str
    address_type: str
    middle_name: Optional[str] = None
    apartment: Optional[str] = None
    city: Optional[str] = None
    claddr_code: Optional[str] = None
    country: Optional[str] = None
    fias_code: Optional[str] = None
    house: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: Optional[bool] = None
    region: Optional[str] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    inn: Optional[str] = None
    snils: Optional[str] = None
    is_foreign_agent: Optional[bool] = None
    is_public_official_person: Optional[bool] = None
    is_blacklisted: Optional[bool] = None


class IdentificationAddress(TidModel):
    address_type: Optional[AddressType] = None
    country: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    settlement: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    housing: Optional[str] = None
    building: Optional[str] = None
    apartment: Optional[str] = None
    zip_code: Optional[str] = None
    claddr_code: Optional[str] = None
    fias_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_primary: Optional[bool] = None


class IdentificationDocument(TidModel):
    document_type: Optional[str] = None
    ser_no: Optional[str] = None
    issued_by: Optional[str] = None
    issue_date: Optional[date] = None
    subdivision_code: Optional[str] = None
    document_check_status: Optional[DocumentCheckStatus] = None


class PersonalInfo(TidModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    address: Optional[IdentificationAddress] = None
    document: List[IdentificationDocument] = Field(default_factory=list)
    phone: Optional[str] = None
    inn: Optional[str] = None
    snils: Optional[str] = None
    sub: Optional[str] = None


class IdentificationData(TidModel):
    """Результат удалённой идентификации (web/app сценарии)."""

    result: Optional[IdentificationResult] = None
    personal_info: Optional[PersonalInfo] = None


class RemoteIdentificationRequest(TidModel):
    res_secret: str


# --- OAuth 2.0 / OIDC (id.tbank.ru) ---
# Провод OAuth — snake_case по RFC 6749/OIDC, поэтому без alias_generator.


class OAuthModel(BaseModel):
    """Базовая модель OAuth-ответа: snake_case; полный сырой ответ — в ``raw``."""

    model_config = ConfigDict(extra="ignore")

    raw: Dict[str, Any] = Field(default_factory=dict, repr=False)

    @model_validator(mode="before")
    @classmethod
    def _capture_raw(cls, data: Any) -> Any:
        # Сохраняем нестандартные claim'ы (кастомные поля токена/introspect/userinfo).
        if isinstance(data, dict) and "raw" not in data:
            return {**data, "raw": dict(data)}
        return data


class TokenResponse(OAuthModel):
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    id_token: Optional[str] = None
    scope: Optional[str] = None


class IntrospectionResponse(OAuthModel):
    """Ответ /auth/introspect (RFC 7662). Кастомные claim'ы — в model_extra."""

    active: bool
    scope: Optional[str] = None
    client_id: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    sub: Optional[str] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    jti: Optional[str] = None

    @property
    def scopes(self) -> List[str]:
        """Скоупы токена списком (пусто, если токен неактивен)."""
        return self.scope.split() if self.scope else []


class OidcUserInfo(OAuthModel):
    """Claim'ы пользователя из userinfo-эндпоинта id.tbank.ru."""

    sub: str
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    middle_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
