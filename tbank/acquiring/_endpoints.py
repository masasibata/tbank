"""Эндпоинты интернет-эквайринга (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from typing import List

from pydantic import TypeAdapter

from tbank.acquiring.models import (
    AddAccountQrRequest,
    AddAccountQrResponse,
    AddAccountQrState,
    AddCardRequest,
    AddCardResponse,
    AddCardState,
    AddCustomerRequest,
    CancelRequest,
    CancelResponse,
    Card,
    ChargeQrRequest,
    ChargeQrResponse,
    ChargeRequest,
    ChargeResponse,
    ConfirmRequest,
    ConfirmResponse,
    Customer,
    CustomerRequest,
    GetAddAccountQrStateRequest,
    GetAddCardStateRequest,
    GetQrRequest,
    GetQrResponse,
    GetQrStateRequest,
    GetStateRequest,
    GetStateResponse,
    InitRequest,
    InitResponse,
    QrMembersListRequest,
    QrMembersListResponse,
    QrState,
    RemoveCardRequest,
    RemoveCardResponse,
    SendClosingReceiptRequest,
    SendClosingReceiptResponse,
)
from tbank.core.endpoint import Endpoint

BASE_URL = "https://securepay.tinkoff.ru/v2"

INIT = Endpoint("POST", "/Init", InitResponse, InitRequest)
GET_STATE = Endpoint("POST", "/GetState", GetStateResponse, GetStateRequest)
CONFIRM = Endpoint("POST", "/Confirm", ConfirmResponse, ConfirmRequest)
CANCEL = Endpoint("POST", "/Cancel", CancelResponse, CancelRequest)
CHARGE = Endpoint("POST", "/Charge", ChargeResponse, ChargeRequest)
ADD_CUSTOMER = Endpoint("POST", "/AddCustomer", Customer, AddCustomerRequest)
GET_CUSTOMER = Endpoint("POST", "/GetCustomer", Customer, CustomerRequest)
REMOVE_CUSTOMER = Endpoint("POST", "/RemoveCustomer", Customer, CustomerRequest)
REMOVE_CARD = Endpoint("POST", "/RemoveCard", RemoveCardResponse, RemoveCardRequest)
GET_QR = Endpoint("POST", "/GetQr", GetQrResponse, GetQrRequest)
QR_MEMBERS = Endpoint(
    "POST", "/QrMembersList", QrMembersListResponse, QrMembersListRequest
)
ADD_ACCOUNT_QR = Endpoint(
    "POST", "/AddAccountQr", AddAccountQrResponse, AddAccountQrRequest
)
ADD_ACCOUNT_QR_STATE = Endpoint(
    "POST", "/GetAddAccountQrState", AddAccountQrState, GetAddAccountQrStateRequest
)
CHARGE_QR = Endpoint("POST", "/ChargeQr", ChargeQrResponse, ChargeQrRequest)
SEND_CLOSING_RECEIPT = Endpoint(
    "POST", "/SendClosingReceipt", SendClosingReceiptResponse, SendClosingReceiptRequest
)
ADD_CARD = Endpoint("POST", "/AddCard", AddCardResponse, AddCardRequest)
ADD_CARD_STATE = Endpoint(
    "POST", "/GetAddCardState", AddCardState, GetAddCardStateRequest
)
GET_QR_STATE = Endpoint("POST", "/GetQrState", QrState, GetQrStateRequest)

CARDS_ADAPTER: TypeAdapter[List[Card]] = TypeAdapter(List[Card])
