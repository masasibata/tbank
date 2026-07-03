from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from tbank.core.models import Rubles
from tbank.special_accounts.enums import EtpArrestStatus


class SpecialAccountModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class Recipient(SpecialAccountModel):
    inn: str
    name: Optional[str] = None
    account: Optional[str] = None


class Bank(SpecialAccountModel):
    bik: Optional[str] = None
    cor_account: Optional[str] = None
    name: Optional[str] = None


class Etp(SpecialAccountModel):
    """Списание по картотеке ЭТП / за нарушение контракта."""

    id: str
    amount: Rubles
    currency: str
    status: EtpArrestStatus
    date: datetime
    payed_amount: Rubles
    sender_inn: str
    recipient: Recipient
    bank: Bank
    external_id: Optional[str] = None
    payment_purpose: Optional[str] = None
    office_name: Optional[str] = None


class Arrest(SpecialAccountModel):
    """Арест средств на специальном счёте."""

    id: str
    amount: Rubles
    currency: str
    status: EtpArrestStatus
    date: datetime
    unblock_date: datetime
    external_id: Optional[str] = None
    circumstances: Optional[str] = None
    office_name: Optional[str] = None


class ArrestList(SpecialAccountModel):
    sum: Rubles
    values: Optional[List[Arrest]] = None


class OperationsResponse(SpecialAccountModel):
    """Операции по специальному счёту: аресты, картотеки ЭТП, списания."""

    arrests: ArrestList
    etp_fees: Optional[List[Etp]] = Field(default=None, alias="etpFees")
    contract_breaches: Optional[List[Etp]] = None
