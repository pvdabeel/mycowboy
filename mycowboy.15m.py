#!/usr/bin/env PYTHONIOENCODING=UTF-8 /opt/local/bin/python3
# -*- coding: utf-8 -*-
#
# <xbar.title>MyCowboy</xbar.title>
# <xbar.version>v1.1</xbar.version>
# <xbar.author>pvdabeel@mac.com</xbar.author>
# <xbar.author.github>pvdabeel</xbar.author.github>
# <xbar.desc>Control your Cowboy Bike from the MacOS menubar</xbar.desc>
# <xbar.dependencies>python</xbar.dependencies>
#
# Licence: GPL v3
"""xbar plugin: display Cowboy bike state in the macOS menubar.

Setup
-----
1. Install dependencies::

       pip install requests tinydb keyring googlemaps

2. Install `xbar`_ and drop this file (and the ``library/`` folder) into your
   plugins folder, then ``chmod +x`` it.

3. The first run will surface a "Login to Cowboy" item. Clicking it launches a
   terminal that prompts for credentials (and optionally Google Maps /
   Geocoding API keys, stored in the macOS keychain).

.. _xbar: https://github.com/matryer/xbar/releases/latest
"""

from __future__ import annotations

import base64
import datetime
import getpass
import json
import math
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import keyring
import keyring.errors
import requests
from tinydb import Query, TinyDB

try:
    from googlemaps import Client as GoogleMapsClient
except ImportError:
    GoogleMapsClient = None  # type: ignore

import library.cowboy as cowboy
from library.cowboy import AuthToken


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

_LOCATION_TRACKING = True
# Only log a new location row when the bike has moved at least this far (m)
# *and/or* the battery charge has changed. Keeps the TinyDB file from growing
# without bound.
_LOCATION_MIN_DELTA_M = 5.0

KEYRING_SERVICE = "mycowboy-bitbar"
ENV_STATIC_MAPS_KEY = "MYCOWBOY_GOOGLE_STATIC_KEY"
ENV_GEOCODE_KEY = "MYCOWBOY_GOOGLE_GEOCODE_KEY"

STATE_DIR = Path.home() / ".state" / "mycowboy"
STATE_DIR.mkdir(parents=True, exist_ok=True)

KEYRING_TOKEN_KEY = "auth_token"
LEGACY_AUTH_FILE = STATE_DIR / "auth.json"
LAST_LOCATION_FILE = STATE_DIR / "last_location.json"

LOCATIONDB = TinyDB(str(STATE_DIR / "mycowboy-locations.json"))
GEOLOCDB = TinyDB(str(STATE_DIR / "mycowboy-geoloc.json"))

CMD_PATH = os.path.realpath(__file__)
DARK_MODE = os.getenv("XBARDarkMode", "false") == "true"

COLOR_FG = "#FFFFFE" if DARK_MODE else "#00000E"
COLOR_INFO = "#C0C0C0" if DARK_MODE else "#616161"

STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
DARK_MAP_STYLE = (
    "&style=feature:all|element:labels|visibility:on"
    "&style=feature:all|element:labels.text.fill|saturation:36|color:0x000000|lightness:40"
    "&style=feature:all|element:labels.text.stroke|visibility:on|color:0x000000|lightness:16"
    "&style=feature:all|element:labels.icon|visibility:off"
    "&style=feature:administrative|element:geometry.fill|color:0x000000|lightness:20"
    "&style=feature:administrative|element:geometry.stroke|color:0x000000|lightness:17|weight:1.2"
    "&style=feature:administrative.country|element:labels.text.fill|color:0x838383"
    "&style=feature:administrative.locality|element:labels.text.fill|color:0xc4c4c4"
    "&style=feature:administrative.neighborhood|element:labels.text.fill|color:0xaaaaaa"
    "&style=feature:landscape|element:geometry|color:0x000000|lightness:20"
    "&style=feature:poi|element:geometry|color:0x000000|lightness:21|visibility:on"
    "&style=feature:poi.business|element:geometry|visibility:on"
    "&style=feature:road.highway|element:geometry.fill|color:0x6e6e6e|lightness:0"
    "&style=feature:road.highway|element:geometry.stroke|visibility:off"
    "&style=feature:road.highway|element:labels.text.fill|color:0xffffff"
    "&style=feature:road.arterial|element:geometry|color:0x000000|lightness:18"
    "&style=feature:road.arterial|element:geometry.fill|color:0x575757"
    "&style=feature:road.arterial|element:labels.text.fill|color:0xffffff"
    "&style=feature:road.arterial|element:labels.text.stroke|color:0x2c2c2c"
    "&style=feature:road.local|element:geometry|color:0x000000|lightness:16"
    "&style=feature:road.local|element:labels.text.fill|color:0x999999"
    "&style=feature:transit|element:geometry|color:0x000000|lightness:19"
    "&style=feature:water|element:geometry|color:0x000000|lightness:17"
)

# Menubar icons (base64 PNG, generated once and embedded so the plugin has no
# runtime image dependency).
LOGO_DARK = (
    "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"
)
LOGO_LIGHT = (
    "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"
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _round_coord(value: float) -> str:
    """Stringify ``value`` to 4 decimals (~11 m precision).

    Used as a cache key so GPS jitter doesn't bust the map and geocode caches
    on every refresh.
    """
    return f"{float(value):.4f}"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon pairs."""
    radius = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------- #
# Auth token caching
# --------------------------------------------------------------------------- #

def _migrate_legacy_token_file() -> Optional[str]:
    """Read (and delete) a pre-keychain ``auth.json`` if one exists."""
    if not LEGACY_AUTH_FILE.exists():
        return None
    try:
        blob = LEGACY_AUTH_FILE.read_text()
    except OSError:
        return None
    try:
        LEGACY_AUTH_FILE.unlink()
    except OSError:
        pass
    return blob


def _load_cached_token() -> Optional[AuthToken]:
    blob = keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
    if not blob:
        blob = _migrate_legacy_token_file()
        if not blob:
            return None
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY, blob)
        except keyring.errors.KeyringError:
            pass
    try:
        token = AuthToken(**json.loads(blob))
    except (json.JSONDecodeError, TypeError, KeyError, ValueError):
        return None
    return token if token.is_valid else None


def _save_token(token: AuthToken) -> None:
    try:
        keyring.set_password(
            KEYRING_SERVICE, KEYRING_TOKEN_KEY, json.dumps(asdict(token))
        )
    except keyring.errors.KeyringError:
        pass


def _clear_cached_token() -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
    except keyring.errors.PasswordDeleteError:
        pass
    except keyring.errors.KeyringError:
        pass


def _connect_to_cowboy() -> Optional[cowboy.Cowboy]:
    """Return an authenticated, refreshed :class:`cowboy.Cowboy`, or ``None``.

    Strategy:
        1. If a cached, non-expired token exists, use it.
        2. Otherwise (or on 401/403), re-login with credentials from keychain.
    """
    cached = _load_cached_token()
    if cached is not None:
        try:
            client = cowboy.Cowboy.from_token(cached)
            client.refresh()
            return client
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (401, 403):
                _clear_cached_token()
        except (requests.RequestException, ValueError, KeyError):
            pass

    username = keyring.get_password(KEYRING_SERVICE, "username")
    password = keyring.get_password(KEYRING_SERVICE, "password")
    if not username or not password:
        return None

    try:
        client = cowboy.Cowboy.login(username, password)
        _save_token(client.token)
        client.refresh()
        return client
    except (requests.RequestException, ValueError, KeyError):
        return None


# --------------------------------------------------------------------------- #
# Google Maps / Geocode caching
# --------------------------------------------------------------------------- #

def _get_static_maps_key() -> Optional[str]:
    return (
        os.environ.get(ENV_STATIC_MAPS_KEY)
        or keyring.get_password(KEYRING_SERVICE, "google_static_key")
    )


def _get_geocode_key() -> Optional[str]:
    return (
        os.environ.get(ENV_GEOCODE_KEY)
        or keyring.get_password(KEYRING_SERVICE, "google_geocode_key")
    )


def _build_static_map_url(lat: str, lon: str, key: str, *, satellite: bool) -> str:
    base = (
        f"{STATIC_MAP_URL}?center={lat},{lon}&key={key}"
        f"&zoom=17&size=360x315&markers=color:red%7C{lat},{lon}"
    )
    if satellite:
        return base + "&maptype=hybrid"
    if DARK_MODE:
        return base + DARK_MAP_STYLE
    return base


def retrieve_google_maps(latitude: float, longitude: float) -> tuple[Optional[str], Optional[str]]:
    """Return (map_b64, sat_b64) PNGs for ``(latitude, longitude)``.

    Both images are cached on disk per (rounded coordinate, YYYYMM) tuple so
    the plugin doesn't hit Google's quota every refresh, and the cache rolls
    over monthly so seasonal map style updates eventually take effect.
    """
    lat_s, lon_s = _round_coord(latitude), _round_coord(longitude)
    month = datetime.date.today().strftime("%Y%m")
    map_file = STATE_DIR / f"mycowboy-location-map-{month}-{lat_s}-{lon_s}.png"
    sat_file = STATE_DIR / f"mycowboy-location-sat-{month}-{lat_s}-{lon_s}.png"

    if map_file.exists() and sat_file.exists():
        try:
            return (
                base64.b64encode(map_file.read_bytes()).decode("ascii"),
                base64.b64encode(sat_file.read_bytes()).decode("ascii"),
            )
        except OSError:
            pass

    key = _get_static_maps_key()
    if not key:
        return None, None

    try:
        with requests.Session() as s:
            map_resp = s.get(_build_static_map_url(lat_s, lon_s, key, satellite=False), timeout=8)
            map_resp.raise_for_status()
            sat_resp = s.get(_build_static_map_url(lat_s, lon_s, key, satellite=True), timeout=8)
            sat_resp.raise_for_status()
        map_file.write_bytes(map_resp.content)
        sat_file.write_bytes(sat_resp.content)
        return (
            base64.b64encode(map_resp.content).decode("ascii"),
            base64.b64encode(sat_resp.content).decode("ascii"),
        )
    except requests.RequestException:
        return None, None


def retrieve_geo_loc(latitude: float, longitude: float) -> Optional[str]:
    """Return a human-readable address for ``(latitude, longitude)`` or ``None``."""
    lat_s, lon_s = _round_coord(latitude), _round_coord(longitude)

    Q = Query()
    hits = GEOLOCDB.search((Q.latitude == lat_s) & (Q.longitude == lon_s))
    if hits:
        return hits[-1].get("geoloc")

    key = _get_geocode_key()
    if not key or GoogleMapsClient is None:
        return None

    try:
        gmaps = GoogleMapsClient(key)
        result = gmaps.reverse_geocode((float(lat_s), float(lon_s)))
    except Exception:
        return None
    if not result:
        return None
    address = result[0].get("formatted_address")
    if address and _LOCATION_TRACKING:
        GEOLOCDB.insert({"latitude": lat_s, "longitude": lon_s, "geoloc": address})
    return address


# --------------------------------------------------------------------------- #
# Location history (TinyDB) with de-duplication
# --------------------------------------------------------------------------- #

def _maybe_insert_location(position: dict, charge: int, distance: float) -> None:
    """Insert a location row only when the bike has actually moved.

    The previous version inserted one row every 15 minutes forever; this one
    skips writes when the bike is parked, which keeps the TinyDB file small
    enough that linear scans (e.g. by ``retrieve_geo_loc``) stay fast.
    """
    if not _LOCATION_TRACKING:
        return

    try:
        lat = position["latitude"]
        lon = position["longitude"]
    except (KeyError, TypeError):
        return

    last = None
    if LAST_LOCATION_FILE.exists():
        try:
            last = json.loads(LAST_LOCATION_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            last = None

    if last:
        try:
            moved = _haversine_m(
                last["position"]["latitude"], last["position"]["longitude"], lat, lon,
            )
        except (KeyError, TypeError):
            moved = float("inf")
        if moved < _LOCATION_MIN_DELTA_M and last.get("charge") == charge:
            return

    now = datetime.datetime.now().isoformat()
    LOCATIONDB.insert({
        "date": now,
        "bike_position": position,
        "bike_charge": charge,
        "bike_distance": distance,
    })
    try:
        LAST_LOCATION_FILE.write_text(json.dumps({
            "position": position,
            "charge": charge,
            "date": now,
        }))
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# xbar rendering
# --------------------------------------------------------------------------- #

def app_print_logo() -> None:
    print(f"|image={LOGO_DARK if DARK_MODE else LOGO_LIGHT}")
    print("---")


def _print_login_prompt() -> None:
    app_print_logo()
    print(
        f'Login to Cowboy | refresh=true terminal=true shell="{CMD_PATH}" '
        f'param1="init" color={COLOR_FG}'
    )


def _print_offline() -> None:
    app_print_logo()
    print(f"No connection to Cowboy | color={COLOR_FG}")


# --------------------------------------------------------------------------- #
# Init flow
# --------------------------------------------------------------------------- #

def _prompt_api_key(label: str, account: str) -> None:
    """Prompt for an API key, showing a redacted preview of the current one."""
    current = keyring.get_password(KEYRING_SERVICE, account)
    suffix = f" (current ends in ...{current[-4:]})" if current else " (none set)"
    print(f"\n{label}{suffix}")
    print("Enter a new key, or leave blank to keep the current value:")
    value = input().strip()
    if not value:
        return
    keyring.set_password(KEYRING_SERVICE, account, value)
    print(f"  -> stored in keychain ({KEYRING_SERVICE}/{account})")


def init() -> None:
    """Interactive first-run setup. Stores creds + (optional) API keys."""
    print("Enter your Cowboy username:")
    username = input().strip()
    print("Enter your Cowboy password:")
    password = getpass.getpass()

    try:
        client = cowboy.Cowboy.login(username, password)
    except requests.RequestException as exc:
        print(f"Error contacting Cowboy servers: {exc}")
        return
    except (KeyError, ValueError) as exc:
        print(f"Login failed: {exc}")
        return

    keyring.set_password(KEYRING_SERVICE, "username", username)
    keyring.set_password(KEYRING_SERVICE, "password", password)
    _save_token(client.token)

    _prompt_api_key("Google Maps Static API key (for the map preview)", "google_static_key")
    _prompt_api_key("Google Geocoding API key (for address lookup)", "google_geocode_key")

    print("\nLogin OK. You can close this window.")


def setup_keys() -> None:
    """Re-set just the Google API keys in the keychain (no Cowboy re-login)."""
    print("Update Google API keys stored in the macOS keychain.")
    _prompt_api_key("Google Maps Static API key", "google_static_key")
    _prompt_api_key("Google Geocoding API key", "google_geocode_key")
    print("\nDone. You can close this window.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main(argv: list[str]) -> None:
    if "init" in argv:
        init()
        return
    if "keys" in argv:
        setup_keys()
        return

    username = keyring.get_password(KEYRING_SERVICE, "username")
    if not username:
        _print_login_prompt()
        return

    client = _connect_to_cowboy()
    if client is None or client.bike is None:
        # Could be a credential problem (re-init) or a network problem. We
        # can't tell with certainty without a network probe, so prefer the
        # actionable "Login to Cowboy" affordance.
        _print_login_prompt()
        return

    bike = client.bike
    co2_kg = (bike.total_co2_saved or 0) / 1000
    _maybe_insert_location(bike.position, bike.state_of_charge, bike.total_distance)

    if "debug" in argv:
        for label, value in [
            ("id", bike.id),
            ("nickname", bike.nickname),
            ("firmware", bike.firmware_version),
            ("position", bike.position),
            ("charge", bike.state_of_charge),
            ("distance", bike.total_distance),
            ("duration", bike.total_duration),
            ("co2", co2_kg),
            ("mac", bike.mac_address),
            ("serial", bike.serial),
            ("model", bike.model),
            ("stolen", bike.stolen),
        ]:
            print(f">>> {label}:\n{value}\n")
        return

    app_print_logo()
    print(f"Bike:\t\t\t\t\t{bike.nickname} | color={COLOR_FG}")
    print(f"Battery:\t\t\t\t\t{bike.state_of_charge}% | color={COLOR_FG}")
    print("---")
    print(f"Odometer:\t\t\t\t{(bike.total_distance or 0):.2f} km | color={COLOR_INFO}")
    print(f"CO2 saved:\t\t\t\t{co2_kg} kg | color={COLOR_INFO}")
    print("---")
    print(f"Bike ID:\t\t\t\t\t#{bike.id} | color={COLOR_INFO}")
    print(f"Model:\t\t\t\t\t{bike.model} | color={COLOR_INFO}")
    print(f"Firmware:\t\t\t\t{bike.firmware_version} | color={COLOR_INFO}")
    print("---")

    security_label = "Stolen" if bike.stolen else "Not Stolen"
    print(f"Security:\t\t\t\t\t{security_label} | color={COLOR_INFO}")
    print(f"--Serial:\t\t\t{bike.serial}| color={COLOR_INFO}")
    print(f"--Mac address:\t\t{bike.mac_address}| color={COLOR_INFO}")
    print("-----")

    lat = bike.position.get("latitude")
    lon = bike.position.get("longitude")
    if lat is not None and lon is not None:
        address = retrieve_geo_loc(lat, lon) or "Unknown"
        print(f"--Address:\t\t\t{address}| color={COLOR_FG}")
        print(f"--Lat:\t\t\t\t{lat}| color={COLOR_INFO}")
        print(f"--Lon:\t\t\t\t{lon}| color={COLOR_INFO}")
        print("---")

        map_img, sat_img = retrieve_google_maps(lat, lon)
        maps_url = f"https://maps.google.com?q={lat},{lon}"
        if map_img:
            print(f'|image={map_img} href="{maps_url}" color={COLOR_FG}')
        if sat_img:
            print(f'|image={sat_img} alternate=true href="{maps_url}" color={COLOR_FG}')
        print("---")

    print(f"Settings | color={COLOR_INFO}")
    print(
        f'--Update Google API keys | refresh=true terminal=true '
        f'shell="{CMD_PATH}" param1="keys" color={COLOR_INFO}'
    )
    print(
        f'--Sign out & re-login | refresh=true terminal=true '
        f'shell="{CMD_PATH}" param1="init" color={COLOR_INFO}'
    )


if __name__ == "__main__":
    main(sys.argv)
