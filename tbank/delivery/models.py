from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from tbank.delivery.enums import IdentificationDocumentType, PhoneType


class DeliveryModel(BaseModel):
    """Базовая модель домена: snake_case в Python, camelCase на проводе."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


# --- Контакты ---


class Passport(DeliveryModel):
    """Документ, удостоверяющий личность (паспорт)."""

    number: str
    series: str
    type: IdentificationDocumentType = IdentificationDocumentType.PASSPORT
    division_name: Optional[str] = None
    issue_date: Optional[date] = None


class Phone(DeliveryModel):
    type: PhoneType
    number: str


class Contact(DeliveryModel):
    id: str
    role: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[date] = None
    phones: Optional[List[Phone]] = None
    documents: Optional[List[Passport]] = None


# --- Задания ---


class Attachment(DeliveryModel):
    id: str
    type: str
    meta: Optional[Dict[str, Any]] = None


class Photo(DeliveryModel):
    id: str
    type: Optional[str] = None
    sub_type: Optional[str] = None
    sheet_number: Optional[int] = None
    review: Optional[Dict[str, Any]] = None


class CreateTaskRequest(DeliveryModel):
    template: str
    comment_for_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    contacts: Optional[List[Contact]] = None


class CreateTaskResult(DeliveryModel):
    id: str


class UpdateTaskRequest(DeliveryModel):
    template: str
    comment_for_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    contacts: Optional[List[Contact]] = None
    photos: Optional[List[Photo]] = None


class CancelTaskRequest(DeliveryModel):
    reason: str


class DeliveryTask(DeliveryModel):
    """Карточка задания на доставку/встречу."""

    id: str
    status: str
    template: str
    meet_result: Optional[str] = None
    resolution: Optional[str] = None
    sub_resolution: Optional[str] = None
    parent_task_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Attachment]] = None
    photos: Optional[List[Photo]] = None


# --- Встречи и интервалы ---


class Address(DeliveryModel):
    full_address: str
    zip_code: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    area: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    building: Optional[str] = None
    flat: Optional[str] = None
    construction: Optional[str] = None
    settlement: Optional[str] = None


class GetIntervalsRequest(DeliveryModel):
    address: Address
    task_ids: Optional[List[str]] = None


class Interval(DeliveryModel):
    start_interval: str
    end_interval: str


class GetIntervalsResult(DeliveryModel):
    appointment_id: str
    time_offset: str
    intervals: Optional[List[Interval]] = None


class CreateMeetingRequest(DeliveryModel):
    appointment_id: str
    interval_start_time: str
    interval_end_time: str
    comment_for_agent: Optional[str] = None


class CreateMeetingResult(DeliveryModel):
    meeting_id: str


# --- Документы ---


class UploadDocumentResult(DeliveryModel):
    id: str = Field(alias="id")
