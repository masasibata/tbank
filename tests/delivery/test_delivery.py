import json

import httpx
import pytest

from tbank.core.auth import BearerAuth
from tbank.core.errors import ForbiddenError, TBankAPIError
from tbank.core.transport import AsyncTransport, SyncTransport
from tbank.delivery.aio import PROD_URL, DeliveryClient
from tbank.delivery.enums import PhoneType
from tbank.delivery.models import (
    Address,
    CancelTaskRequest,
    Contact,
    CreateMeetingRequest,
    CreateTaskRequest,
    GetIntervalsRequest,
    Passport,
    Phone,
    UpdateTaskRequest,
)
from tbank.delivery.sync import DeliveryClient as SyncClient


def _transport(handler, *, sync=False):
    cls = SyncTransport if sync else AsyncTransport
    client = (httpx.Client if sync else httpx.AsyncClient)(
        transport=httpx.MockTransport(handler)
    )
    return cls(base_url=PROD_URL, client=client, auth=BearerAuth("T"))


def _client(handler):
    return DeliveryClient(token="T", transport=_transport(handler))


# --- Задания ---


async def test_create_task_idempotency_and_body():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "business.tbank.ru"
        assert request.url.path == "/openapi/api/v1/delivery/tasks"
        assert request.headers.get("Idempotency-Key")
        body = json.loads(request.content)
        assert body["template"] == "COURIER"
        assert body["contacts"][0]["phones"][0]["type"] == "MOBILE"
        assert body["contacts"][0]["documents"][0]["type"] == "PASSPORT"
        return httpx.Response(200, json={"id": "task-1"})

    client = _client(handler)
    res = await client.create_task(
        CreateTaskRequest(
            template="COURIER",
            contacts=[
                Contact(
                    id="c-1",
                    first_name="Иван",
                    phones=[Phone(type=PhoneType.MOBILE, number="+79001112233")],
                    documents=[Passport(number="123456", series="4509")],
                )
            ],
        )
    )
    assert res.id == "task-1"


async def test_get_update_cancel_task():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "task-1",
                    "status": "COMPLETED",
                    "template": "COURIER",
                    "resolution": "DELIVERED",
                    "attachments": [{"id": "a-1", "type": "ACT"}],
                },
            )
        if request.method == "PUT":
            assert json.loads(request.content)["template"] == "COURIER"
            return httpx.Response(200, json={})
        assert request.url.path.endswith("/cancel")
        assert json.loads(request.content)["reason"] == "client_declined"
        return httpx.Response(200, json={})

    client = _client(handler)
    task = await client.get_task("task-1")
    assert task.status == "COMPLETED"
    assert task.attachments[0].id == "a-1"
    assert (
        await client.update_task("task-1", UpdateTaskRequest(template="COURIER"))
        is None
    )
    assert (
        await client.cancel_task("task-1", CancelTaskRequest(reason="client_declined"))
        is None
    )


# --- Встречи ---


async def test_intervals_and_meeting():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/intervals"):
            body = json.loads(request.content)
            assert body["address"]["fullAddress"] == "Москва, Тверская 1"
            return httpx.Response(
                200,
                json={
                    "appointmentId": "ap-1",
                    "timeOffset": "+03:00",
                    "intervals": [{"startInterval": "10:00", "endInterval": "12:00"}],
                },
            )
        return httpx.Response(200, json={"meetingId": "m-1"})

    client = _client(handler)
    intervals = await client.get_intervals(
        GetIntervalsRequest(address=Address(full_address="Москва, Тверская 1"))
    )
    assert intervals.appointment_id == "ap-1"
    assert intervals.intervals[0].start_interval == "10:00"
    meeting = await client.create_meeting(
        CreateMeetingRequest(
            appointment_id="ap-1",
            interval_start_time="10:00",
            interval_end_time="12:00",
        )
    )
    assert meeting.meeting_id == "m-1"


# --- Документы ---


async def test_upload_and_download_document():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path == "/openapi/api/v1/delivery/documents"
            ct = request.headers.get("content-type", "")
            assert ct.startswith("multipart/form-data")
            assert b'name="taskId"' in request.content
            assert b"PDFBYTES" in request.content
            return httpx.Response(200, json={"id": "doc-1"})
        return httpx.Response(
            200,
            content=b"PDFBYTES",
            headers={"content-type": "application/octet-stream"},
        )

    client = _client(handler)
    uploaded = await client.upload_document(
        "task-1", "ACT", b"PDFBYTES", filename="act.pdf"
    )
    assert uploaded.id == "doc-1"
    content = await client.download_document("doc-1")
    assert content == b"PDFBYTES"


async def test_error_mapping():
    client = _client(
        lambda r: httpx.Response(
            403, json={"errorId": "e", "errorMessage": "no", "errorCode": "403"}
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await client.get_task("x")
    assert exc.value.error_id == "e"


# --- Синхронный клиент ---


def test_sync_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/tasks"):
            return httpx.Response(200, json={"id": "task-1"})
        if request.method == "GET":
            return httpx.Response(
                200, json={"id": "task-1", "status": "NEW", "template": "COURIER"}
            )
        return httpx.Response(500, text="boom")

    client = SyncClient(token="T", transport=_transport(handler, sync=True))
    assert client.create_task(CreateTaskRequest(template="COURIER")).id == "task-1"
    assert client.get_task("task-1").status == "NEW"
    with pytest.raises(TBankAPIError):
        client.cancel_task("task-1", CancelTaskRequest(reason="x"))
    client.close()


def _surface_handler(request: httpx.Request) -> httpx.Response:
    p, m = request.url.path.replace("/openapi", ""), request.method
    if p == "/api/v1/delivery/tasks" and m == "POST":
        return httpx.Response(200, json={"id": "task"})
    if p.endswith("/cancel"):
        return httpx.Response(200, json={})
    if p.startswith("/api/v1/delivery/tasks/") and m == "GET":
        return httpx.Response(
            200, json={"id": "task", "status": "NEW", "template": "C"}
        )
    if p.startswith("/api/v1/delivery/tasks/") and m == "PUT":
        return httpx.Response(200, json={})
    if p.endswith("/meetings/intervals"):
        return httpx.Response(200, json={"appointmentId": "ap", "timeOffset": "+03:00"})
    if p == "/api/v1/delivery/meetings":
        return httpx.Response(200, json={"meetingId": "m"})
    if p == "/api/v1/delivery/documents" and m == "POST":
        return httpx.Response(200, json={"id": "doc"})
    return httpx.Response(200, content=b"BYTES")


def test_sync_full_surface():
    client = SyncClient(token="T", transport=_transport(_surface_handler, sync=True))
    assert client.create_task(CreateTaskRequest(template="C")).id == "task"
    assert client.get_task("task").status == "NEW"
    assert client.update_task("task", UpdateTaskRequest(template="C")) is None
    assert client.cancel_task("task", CancelTaskRequest(reason="x")) is None
    assert (
        client.get_intervals(
            GetIntervalsRequest(address=Address(full_address="A"))
        ).appointment_id
        == "ap"
    )
    assert (
        client.create_meeting(
            CreateMeetingRequest(
                appointment_id="ap", interval_start_time="10", interval_end_time="12"
            )
        ).meeting_id
        == "m"
    )
    assert client.upload_document("task", "ACT", b"X").id == "doc"
    assert client.download_document("doc") == b"BYTES"
    client.close()
