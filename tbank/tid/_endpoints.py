"""Data-эндпоинты T-ID (общие для sync- и aio-клиентов)."""

from __future__ import annotations

from tbank.core.endpoint import Endpoint
from tbank.tid.models import (
    BlacklistStatus,
    CompanyInfo,
    DebitAccountsResponse,
    DelegatedIdentification,
    DetailCounters,
    DriverLicensesResponse,
    ForeignAgentStatus,
    IdentificationData,
    IdentificationStatus,
    InnResponse,
    PdlStatus,
    RemoteIdentificationRequest,
    SelfEmployedStatus,
    SetCounterRequest,
    SetCounterResponse,
    SignerStatus,
    SnilsResponse,
    SubscriptionGrade,
    SubscriptionResponse,
    UserAccountInfo,
)

# Data-эндпоинты берём в максимальной доступной версии (v2 там, где она есть).
COMPANY = Endpoint("GET", "/api/v2/company", CompanyInfo)
SIGNER = Endpoint("GET", "/api/v2/company/signer/status", SignerStatus)
USERINFO = Endpoint("GET", "/api/v1/individual/userinfo", UserAccountInfo)
INN = Endpoint("GET", "/api/v2/individual/documents/inn", InnResponse)
SNILS = Endpoint("GET", "/api/v2/individual/documents/snils", SnilsResponse)
DRIVER_LICENSES = Endpoint(
    "GET", "/api/v2/individual/documents/driver-licenses", DriverLicensesResponse
)
DEBIT_ACCOUNTS = Endpoint(
    "GET", "/api/v2/individual/accounts/debit", DebitAccountsResponse
)
IDENTIFICATION_STATUS = Endpoint(
    "GET", "/api/v2/individual/identification/status", IdentificationStatus
)
SELF_EMPLOYED = Endpoint(
    "GET", "/api/v2/individual/self-employed/status", SelfEmployedStatus
)
FOREIGN_AGENT = Endpoint(
    "GET", "/api/v2/individual/foreignagent/status", ForeignAgentStatus
)
PDL = Endpoint("GET", "/api/v2/individual/pdl/status", PdlStatus)
BLACKLIST = Endpoint("GET", "/api/v2/individual/blacklist/status", BlacklistStatus)
DETAIL_COUNTERS = Endpoint("GET", "/api/v1/individual/detail-counters", DetailCounters)
SET_COUNTERS = Endpoint(
    "POST", "/api/v1/individual/detail-counters", SetCounterResponse, SetCounterRequest
)
SUBSCRIPTION = Endpoint("GET", "/api/v1/individual/subscription", SubscriptionResponse)
SUBSCRIPTION_GRADE = Endpoint(
    "GET", "/api/v1/individual/subscription/grade", SubscriptionGrade
)
DELEGATED = Endpoint(
    "GET", "/api/v1/individual/delegated-identification", DelegatedIdentification
)
REMOTE_ID = Endpoint(
    "POST",
    "/api/v1/bio/remote-identification/result",
    IdentificationData,
    RemoteIdentificationRequest,
)

PASSPORT_PATH = "/api/v2/individual/documents/passport"
ADDRESSES_PATH = "/api/v2/individual/addresses"


def cobrand_path(program_id: int) -> str:
    return f"/api/v1/individual/cobrand/{program_id}"


def personal_data_path(request_id: str) -> str:
    return f"/api/v1/identification/personalData/{request_id}"
