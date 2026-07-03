from __future__ import annotations

from enum import Enum


class RequestType(str, Enum):
    """Тип заявки на налоговую консультацию."""

    COMMENT = "Comment"
    DECLARATION = "Declaration"


class RequestStatus(str, Enum):
    """Статус заявки на налоговую консультацию."""

    ASSIGNED = "Assigned"
    IN_PROGRESS = "InProgress"
    ANSWERED = "Answered"
    SEEN_BY_CLIENT = "SeenByClient"
    NEEDS_CLARIFICATION = "NeedsClarification"
    CLOSED = "Closed"
    SENT_TO_PARTNER = "SentToPartner"
    DRAFT = "Draft"
    NEW = "New"
    PREPROCESS = "Preprocess"
    PARTNER_GENERATING_REPORT_DATA = "PartnerGeneratingReportData"
    PARTNER_IN_PROGRESS = "PartnerInProgress"
    PENDING_PASSPORT = "PendingPassport"
    PENDING_PAYMENT = "PendingPayment"
    PAYMENT_DONE = "PaymentDone"
    READY = "Ready"
    PARTNER_READY = "PartnerReady"
    ACKNOWLEDGE = "Acknowledge"
    CANCELLED = "Cancelled"
    DECLINED = "Declined"
    CLARIFICATION = "Clarification"


class ChatAuthorType(str, Enum):
    """Тип автора сообщения в чате."""

    MANAGER = "Manager"
    CLIENT = "Client"
