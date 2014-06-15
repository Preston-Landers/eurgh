#!/usr/bin/env python
# -*- coding: utf-8; mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vim: fileencoding=utf-8 tabstop=4 expandtab shiftwidth=4

"""
Eurgh - a translation utility using Microsoft Translate API
"""

from configparser import ConfigParser
import time
from logging import getLogger
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from json import loads
import xml.etree.ElementTree as ET

__author__ = 'Preston Landers (planders@gmail.com)'
__copyright__ = 'Copyright (c) 2014 Preston Landers'
__license__ = 'Proprietary'
__version__ = '0.1'

log = getLogger(__name__)


class Eurgh(object):
    BASE_API = "http://api.microsofttranslator.com/v2/Http.svc/"

    AUTH_URL = "https://datamarket.accesscontrol.windows.net/v2/OAuth2-13"

    def __init__(self, config_file):
        self.config = config = ConfigParser()
        config.read(config_file)
        self._access_token = None
        self._access_token_expires = time.time()

        self.from_lang = config.get("translate", "from_lang")
        self.to_langs = config.get("translate", "to_lang").split(" ")

        self.client_id = config.get("secrets", "client_id")
        self.client_secret = config.get("secrets", "client_secret")
        return

    @property
    def access_token(self):
        if self._access_token and self.is_access_token_ok():
            return self._access_token
        self._access_token = self.get_access_token()
        expires_in = int(self._access_token['expires_in'])
        self._access_token_expires = time.time() + expires_in
        return self._access_token

    def is_access_token_ok(self):
        if time.time() >= self._access_token_expires:
            return False
        return True

    def get_access_token(self):
        data = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope="http://api.microsofttranslator.com",
            grant_type="client_credentials",
        )
        data_bytes = urlencode(data).encode("utf-8")
        request = Request(self.AUTH_URL, data_bytes, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
        response = urlopen(request, data_bytes)
        result = response.read().decode("utf-8")
        result_dict = loads(result)
        return result_dict

    def translate_string(self, tr_string, from_lang=None, to_lang=None):

        if from_lang is None:
            from_lang = self.from_lang
        if to_lang is None:
            to_lang = self.to_langs[0]

        # url = BASE_API + "TranslateArray?"
        url = self.BASE_API + "Translate?"
        data = {
            "from": from_lang,
            "to": to_lang,
            # "texts": dumps(tr_strings),
            "text": tr_string,
        }
        params = urlencode(data)

        request = Request(url + params)
        request.add_header("Authorization", "Bearer %s" % (self.access_token['access_token'],))
        try:
            response = urlopen(request)
        except HTTPError as e:
            print("ERROR")
            print(e)
            # return 1
            raise e
        result = response.read().decode("utf-8")
        # print(result)
        return self.deserialize(result)

    @staticmethod
    def deserialize(result):
        tree = ET.fromstring(result)
        return tree.text


def test():
    test_strings = (
        "Testing",
        "Goodbye."
    )
    eurgh = Eurgh("local.ini")
    for tr_str in test_strings:
        res = eurgh.translate_string(tr_str)
        print("%s ==> %s" % (tr_str, res))


if __name__ == "__main__":
    test()
