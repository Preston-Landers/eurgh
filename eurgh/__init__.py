#!/usr/bin/env python
# -*- coding: utf-8; mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vim: fileencoding=utf-8 tabstop=4 expandtab shiftwidth=4

"""
Eurgh - a translation utility using Microsoft Translate API
"""

import re
import time
from configparser import ConfigParser
from logging import getLogger
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from json import loads
import xml.etree.ElementTree as ET

from eurgh.languages import LANGUAGES


__author__ = 'Preston Landers (planders@gmail.com)'
__copyright__ = 'Copyright (c) 2014 Preston Landers'
__license__ = 'Proprietary'
__version__ = '0.1'

log = getLogger(__name__)


class Eurgh(object):
    BASE_API = "http://api.microsofttranslator.com/v2/Http.svc/"

    AUTH_URL = "https://datamarket.accesscontrol.windows.net/v2/OAuth2-13"

    # Max size of string array for TranslateArray
    MAX_API_ARRAY = 2000

    def __init__(self, config_file):
        self.config = config = ConfigParser()
        config.read(config_file)
        self._access_token = None
        self._access_token_expires = time.time()

        self.from_lang = config.get("translate", "from_lang")
        self.to_langs = config.get("translate", "to_lang").split(" ")

        for lang in self.to_langs:
            if lang not in LANGUAGES:
                raise ValueError("Unsupported language: %s" % (lang,))

        self.client_id = config.get("secrets", "client_id")
        self.client_secret = config.get("secrets", "client_secret")

        self.api_category = config.get("translate", "category", fallback="general")
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

        url = self.BASE_API + "Translate?"
        # Must be in this order!
        params = urlencode([
            ("text", tr_string),
            ("from", from_lang),
            ("to", to_lang),
            ("contentType", "text/plain"),
            ("category", self.api_category),
        ])
        request = Request(url + params)
        result = self.run_request(request)
        return self.deserialize(result)

    def translate_strings(self, str_array, from_lang=None, to_lang=None):
        if len(str_array) > self.MAX_API_ARRAY:
            raise ValueError(
                "List is too big to translate, %s is greater than %s" % (len(str_array), self.MAX_API_ARRAY))
        if from_lang is None:
            from_lang = self.from_lang
        if to_lang is None:
            to_lang = self.to_langs[0]
        url = self.BASE_API + "TranslateArray?"
        # Must be in this order!
        data = [("from", from_lang)]
        data.extend([("texts", thing) for thing in str_array])
        data.extend([("to", to_lang)])

        strings_enc = "\n".join([self.serialize(thing) for thing in str_array])
        category = self.api_category
        content_type = "text/plain"

        data = """\
<TranslateArrayRequest>
  <AppId />
  <From>%(from_lang)s</From>
  <Options>
    <Category xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2" >%(category)s</Category>
    <ContentType xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2">%(content_type)s</ContentType>
    <ReservedFlags xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2" />
    <State xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2" />
    <Uri xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2" />
    <User xmlns="http://schemas.datacontract.org/2004/07/Microsoft.MT.Web.Service.V2" />
  </Options>
  <Texts>
    %(strings_enc)s
  </Texts>
  <To>%(to_lang)s</To>
</TranslateArrayRequest>""" % locals()

        data_bytes = bytes(data.encode("utf-8"))
        request = Request(url, data_bytes, method="POST")
        request.add_header("Content-Type", "text/xml")
        result = self.run_request(request)
        result_list = self.deserialize_array(result)
        result_dict = self.simplify_array_result(str_array, result_list)
        return result_list

    @staticmethod
    def simplify_array_result(orig_array, result_list):
        res = {}
        for i in range(len(orig_array)):
            orig_str = orig_array[i]
            result_entry = result_list[i]
            res[orig_str] = result_entry["TranslatedText"]
        return res

    @staticmethod
    def serialize(thing):
        return '<string xmlns="http://schemas.microsoft.com/2003/10/Serialization/Arrays">%s</string>' % (thing,)

    def run_request(self, request):
        request.add_header("Authorization", "Bearer %s" % (self.access_token['access_token'],))
        try:
            response = urlopen(request)
        except HTTPError as e:
            print("ERROR")
            print(e)
            # return 1
            raise e
        result = response.read().decode("utf-8")
        return result

    @staticmethod
    def deserialize(result):
        tree = ET.fromstring(result)
        return tree.text

    @staticmethod
    def deserialize_array(array_response):
        tree = ET.fromstring(array_response)
        res = []
        for response in tree:
            d = {}
            for part in response:
                tag = strip_tag(part.tag)
                d[tag] = part.text
            res.append(d)
        return res


def strip_tag(atag):
    return re.sub(r"{.*?}", "", atag)


def test():
    test_strings = (
        "Testing",
        "Goodbye."
    )
    eurgh = Eurgh("local.ini")
    # for tr_str in test_strings:
    # res = eurgh.translate_string(tr_str)
    # print("%s ==> %s" % (tr_str, res))
    print(eurgh.translate_strings(test_strings))


if __name__ == "__main__":
    test()
