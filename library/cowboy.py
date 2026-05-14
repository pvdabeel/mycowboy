#!/usr/bin/env python3
# Published Jul 2019
# Author : Samuel Dumont, samuel@dumont.info
# Refactor: Pieter Van den Abeele, pvdabeel@mac.com
# License : MIT
"""Access to the Cowboy Bike API (https://cowboy.bike).

This module exposes:
    * ``Bike``          - a dataclass describing a bike's current state
    * ``AuthToken``     - the credentials returned by ``/auth/sign_in``
    * ``Cowboy``        - a high-level client built around a cached token
    * ``user_exists``   - convenience helper around ``/users/check``
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:  # urllib3 < 1.26
    from requests.packages.urllib3.util.retry import Retry  # type: ignore


COWBOY_URL = "https://app-api.cowboy.bike/"
CHECK_ENDPOINT = "users/check"
ME_ENDPOINT = "users/me"
AUTH_ENDPOINT = "auth/sign_in"
BIKES_ENDPOINT = "bikes/{}"

_APP_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
_DEFAULT_TIMEOUT = 8
_TOKEN_LEEWAY_SECONDS = 60

logger = logging.getLogger("cowboy-bike")


def _make_session() -> requests.Session:
    """Return a process-wide ``requests.Session`` with sensible retries."""
    session = requests.Session()
    retries = Retry(
        total=1,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=2, pool_maxsize=4)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = _make_session()


def _headers(
    client: str = "Android-App",
    uid: Optional[str] = None,
    access_token: Optional[str] = None,
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-Cowboy-App-Token": _APP_TOKEN,
        "Client": client,
        "Client-Type": "Android-App",
    }
    if uid and access_token:
        headers["Uid"] = uid
        headers["Access-Token"] = access_token
    return headers


def _request(
    method: str,
    url: str,
    *,
    data: Optional[dict] = None,
    client: str = "Android-App",
    uid: Optional[str] = None,
    access_token: Optional[str] = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict:
    headers = _headers(client, uid, access_token)
    if method == "GET":
        resp = _SESSION.get(url, headers=headers, timeout=timeout)
    elif method == "POST":
        resp = _SESSION.post(url, json=data, headers=headers, timeout=timeout)
    else:
        raise ValueError(f"unsupported HTTP method: {method}")

    resp.raise_for_status()
    try:
        body: Any = resp.json()
    except ValueError:
        body = None
    return {"json": body, "headers": resp.headers}


@dataclass
class Bike:
    id: int
    nickname: str
    total_distance: float
    total_duration: float
    total_co2_saved: float
    stolen: bool
    state_of_charge: int
    state_of_charge_internal: Optional[int]
    firmware_version: str
    position: dict
    model: str
    mac_address: str
    serial: str

    @classmethod
    def from_api(cls, data: dict) -> "Bike":
        return cls(
            id=data["id"],
            nickname=data.get("nickname", ""),
            total_distance=data.get("total_distance", 0),
            total_duration=data.get("total_duration", 0),
            total_co2_saved=data.get("total_co2_saved", 0),
            stolen=bool(data.get("stolen", False)),
            state_of_charge=data.get("battery_state_of_charge", 0),
            state_of_charge_internal=data.get("pcb_battery_state_of_charge"),
            firmware_version=data.get("firmware_version", ""),
            position=data.get("position", {}),
            model=data.get("model", {}).get("description", ""),
            mac_address=data.get("mac_address", ""),
            serial=data.get("serial_number", ""),
        )


@dataclass
class AuthToken:
    uid: str
    access_token: str
    client: str
    expiry: float

    @property
    def is_valid(self) -> bool:
        return self.expiry > time.time() + _TOKEN_LEEWAY_SECONDS


class Cowboy:
    """High-level Cowboy API client.

    Construct via :meth:`login` (with username/password) or :meth:`from_token`
    (with a previously cached :class:`AuthToken`).
    """

    def __init__(self, token: AuthToken) -> None:
        self.token = token
        self.bike: Optional[Bike] = None
        self.total_distance: Optional[float] = None
        self.total_duration: Optional[float] = None
        self.total_co2_saved: Optional[float] = None

    @classmethod
    def login(cls, email: str, password: str) -> "Cowboy":
        token = _login(email, password)
        return cls(token)

    @classmethod
    def from_token(cls, token: AuthToken) -> "Cowboy":
        return cls(token)

    def refresh(self) -> None:
        """Fetch fresh user + bike data from the API."""
        if not self.token.is_valid:
            raise ValueError("auth token expired")

        me = _request(
            "GET",
            urljoin(COWBOY_URL, ME_ENDPOINT),
            uid=self.token.uid,
            access_token=self.token.access_token,
            client=self.token.client,
        )["json"]
        if not me:
            raise ValueError("empty /users/me response")

        self.total_distance = me.get("total_distance")
        self.total_duration = me.get("total_duration")
        self.total_co2_saved = me.get("total_co2_saved")

        bike_id = me["bike"]["id"]
        bike_payload = _request(
            "GET",
            urljoin(COWBOY_URL, BIKES_ENDPOINT.format(bike_id)),
            uid=self.token.uid,
            access_token=self.token.access_token,
            client=self.token.client,
        )["json"]
        if not bike_payload:
            raise ValueError("empty /bikes response")
        self.bike = Bike.from_api(bike_payload)


def _login(email: str, password: str) -> AuthToken:
    resp = _request(
        "POST",
        urljoin(COWBOY_URL, AUTH_ENDPOINT),
        data={"email": email, "password": password},
    )
    headers = resp["headers"]
    return AuthToken(
        uid=headers["Uid"],
        access_token=headers["Access-Token"],
        client=headers["Client"],
        expiry=float(headers["Expiry"]),
    )


def user_exists(email: str) -> bool:
    """Return whether an account exists for ``email``."""
    resp = _request(
        "POST",
        urljoin(COWBOY_URL, CHECK_ENDPOINT),
        data={"email": email},
    )
    body = resp.get("json") or {}
    return str(body.get("exists")).lower() == "true"
