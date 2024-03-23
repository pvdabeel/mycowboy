#!/usr/bin/python
# Published Jul 2019
# Author : Samuel Dumont, samuel@dumont.info
# Python 2.7 compatibility modifications by Pieter Van den Abeele, pvdabeel@mac.com
# License : MIT
"""
This module provides access to the Cowboy Bike's API (https://cowboy.bike)
"""
from sys import version_info
from os import getenv
from os.path import expanduser, exists
import json
import time
import warnings
import sys
import logging

try:   # Python 3 dependencies
    from urllib.parse import urlencode 
    from urllib.request import Request, urlopen, build_opener
    from urllib.request import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError
except: # Python 2 dependencies
    from urllib import urlencode
    from urllib2 import Request, urlopen, build_opener
    from urllib2 import ProxyHandler, HTTPBasicAuthHandler, HTTPHandler, HTTPError, URLError

import requests

import pprint

logger = logging.getLogger("cowboy-bike")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

COWBOY_URL = "https://app-api.cowboy.bike/"
CHECK_ENDPOINT = "/users/check"
ME_ENDPOINT = "users/me"
AUTH_ENDPOINT = "/auth/sign_in"
WEATHER_URL = "/weather"
BIKES_ENDPOINT = "/bikes/{}"


class Bike:
    """Represents a Cowboy Bike

    Args:
        bike (dict): The bike object fetched from the api.
    """

    def __init__(self, bike):
        self.id = bike["id"]
        self.nickname = bike["nickname"]
        self.total_distance = bike["total_distance"]
        self.total_duration = bike["total_duration"]
        self.total_co2_saved = bike["total_co2_saved"]
        self.stolen = bike["stolen"]
        self.state_of_charge = bike["battery_state_of_charge"]
        self.state_of_charge_internal = bike["pcb_battery_state_of_charge"]
        self.firmware_version = bike["firmware_version"]
        self.position = bike["position"]
        self.model = bike["model"]["description"]
        self.mac_address = bike["mac_address"]
        self.serial = bike["serial_number"]


    def getId(self):
        return self.id

    def getNickname(self):
        return self.nickname

    def isStolen(self):
        return self.stolen

    def getStateOfCharge(self):
        return self.state_of_charge

    def getStateOfChargeInternal(self):
        return self.state_of_charge_internal

    def getFirmwareVersion(self):
        return self.firmware_version

    def getTotalDistance(self):
        return self.total_distance

    def getTotalDuration(self):
        return self.total_duration

    def getTotalCO2Saved(self):
        return self.total_co2_saved

    def getPosition(self):
        return self.position

    def getModel(self):
        return self.model

    def getMacAddress(self):
        return self.mac_address

    def getSerial(self):
        return self.serial 


class Cowboy:
    """Represents the

    Args:
        email (str): The user's email.
        password (str): The users's password.
    """

    def __init__(self, auth):
        self.auth = auth
        self.bike = None
        self.total_distance = None
        self.total_duration = None
        self.total_co2_saved = None
 
    @classmethod
    def with_auth(cls, email, password):
        return cls(Authentication(email, password))

    def refreshData(self):
        data = _getRequest(urljoin(COWBOY_URL, ME_ENDPOINT),
                           authenticated=True,
                           client=self.auth.getclient(),
                           accesstoken=self.auth.getaccesstoken(),
                           uid=self.auth.getuid())

        self.total_distance = data["json"]["total_distance"]
        self.total_duration = data["json"]["total_duration"]
        self.total_co2_saved = data["json"]["total_co2_saved"]

        self.bike = Bike(_getRequest(urljoin(COWBOY_URL, BIKES_ENDPOINT.format(data["json"]["bike"]["id"])),
                                     authenticated=True,
                                     client=self.auth.getclient(),
                                     accesstoken=self.auth.getaccesstoken(),
                                     uid=self.auth.getuid())["json"])


    def getBike(self):
        return self.bike

    def getTotalDistance(self):
        return self.total_distance

    def getTotalDuration(self):
        return self.total_duration

    def getTotalCO2Saved(self):
        return self.total_co2_saved


class Authentication:
    """Represents a Cowboy API authentication

    Args:
        email (str): The user's email.
        password (str): The users's password.
    """

    def __init__(self, email, password):
        data = {"email": email, "password": password}
        login = _postRequest(urljoin(COWBOY_URL, AUTH_ENDPOINT), data)

        self.uid = login["headers"]["Uid"]
        self.accesstoken = login["headers"]["Access-Token"]
        self.client = login["headers"]["Client"]
        self.expiry = float(login["headers"]["Expiry"])

    def getaccesstoken(self):
        """Returns the user's access token"""
        if self.expiry < time.time():
            raise ValueError("TBD, Renew token")
        return self.accesstoken

    def getuid(self):
        """Returns the user's uid (should be the same as the user's email)"""
        if self.expiry < time.time():
            raise ValueError("TBD, Renew token")
        return self.uid

    def getclient(self):
        """Returns the user's client identifier"""
        if self.expiry < time.time():
            raise ValueError("TBD, Renew token")
        return self.client


def _getRequest(url, authenticated=False, client="Android-App", uid=None, accesstoken=None, timeout=10):

    response = dict()

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-Cowboy-App-Token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "Client": client,
        "Client-Type": "Android-App"
    }

    if authenticated:
        if not uid or not accesstoken:
            raise ValueError("Missing Uid or Access-Token")
        headers.update({"Uid": uid})
        headers.update({"Access-Token": accesstoken})

    resp = requests.get(url, headers=headers)

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(err)

    try:
        response["json"] = resp.json()
    except:
        response["json"] = None
    response["headers"] = resp.headers

    return response


def _postRequest(url, data=None, authenticated=False, client="Android-App", uid=None, accesstoken=None, timeout=10):

    response = dict()

    headers = {
        "Content-Type": "application/json;charset=utf-8",
        "X-Cowboy-App-Token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "Client": client,
        "Client-Type": "Android-App"
    }

    if authenticated:
        if not uid or not accesstoken:
            raise ValueError("Missing Uid or Access-Token")
        headers.update({"Uid": uid})
        headers.update({"Access-Token": accesstoken})

    resp = requests.post(url, json=data, headers=headers)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(err)

    try:
        response["json"] = resp.json()
    except:
        response["json"] = None
    response["headers"] = resp.headers

    return response


def userExists(email):
    """Checks that a user exists

    Args:
        email (str): The user email to check
    Returns:
        bool: User exists
    """

    data = {"email": email}
    login = _postRequest(urljoin(COWBOY_URL, CHECK_ENDPOINT), data)

    return True if login["json"]["exists"] == "true" else False
