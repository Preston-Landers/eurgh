#!/usr/bin/env python
# -*- coding: utf-8; mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vim: fileencoding=utf-8 tabstop=4 expandtab shiftwidth=4

"""
Eurgh - an application message catalog translation utility using the
Microsoft Translator API.
"""

import os
from configparser import ConfigParser
from logging import getLogger
from logging.config import fileConfig
import codecs

from babel.messages.pofile import read_po, write_po
from eurgh.translator import EurghTranslator


__author__ = 'Preston Landers (planders@gmail.com)'
__copyright__ = 'Copyright (c) 2014 Preston Landers'
__license__ = 'Proprietary'
__version__ = '0.1'

log = getLogger("eurgh")


class EurghApp(object):
    """
    This class can translate message catalogs compiled from source code.
    """

    def __init__(self, config_file):
        global log
        self.config = config = ConfigParser()
        config.read(config_file)
        fileConfig(config_file, disable_existing_loggers=False)

        self.from_lang = config.get("translate", "from_lang")
        self.to_langs = config.get("translate", "to_lang").split(" ")
        self.app_locale_dir = config.get("app", "locale_dir", fallback=None)
        self.app_domain = config.get("app", "domain", fallback="messages")
        self.app_encoding = config.get("app", "encoding", fallback="utf-8")
        self.blank_only = config.getboolean("app", "blank_only", fallback=True)

        self.translator = EurghTranslator(config_file)

    def translate_app_source(self):
        if not self.app_locale_dir:
            raise ValueError("You must set app.locale_dir in the config file to use this feature.")
        if not os.path.exists(self.app_locale_dir):
            raise ValueError("Can't find your app.locale_dir at %s" % (self.app_locale_dir,))
        if not self.from_lang:
            raise ValueError("No from_lang specified in config file.")
        if not self.to_langs:
            raise ValueError("No to_lang specified in config file.")
        for lang in self.to_langs:
            self.translate_app_language(lang)
        log.info("Finished.")
        return

    def translate_app_language(self, lang):
        lang_dir = os.path.join(self.app_locale_dir, lang, "LC_MESSAGES")
        lang_po_file = os.path.join(lang_dir, "%s.po" % (self.app_domain,))

        def bad_path(pth):
            msg = """Can't find %s. Maybe you need to run:
pybabel init -l ja -i /path/to/app/src/locale/myapp.pot -d /path/to/app/src/locale -D myapp""" % (pth,)
            raise IOError(msg)

        if not os.path.exists(lang_dir):
            bad_path(lang_dir)
        if not os.path.exists(lang_po_file):
            bad_path(lang_po_file)

        input_file = codecs.open(lang_po_file, encoding=self.app_encoding, mode="rb")
        # file_data = input_file.read()
        # log.info(file_data)

        catalog = read_po(input_file)
        input_file.close()
        log.warn("Opened message catalog: %s", lang_po_file)
        self.translate_catalog(lang, lang_po_file, catalog)

    def translate_catalog(self, lang, lang_po_file, catalog):
        for start_index, stop_index in get_blocks(len(catalog), self.translator.MAX_API_ARRAY):

            # noinspection PyProtectedMember
            def m_slice(cat, start, stop):
                all_keys = cat._messages.keys()
                for i in range(start, stop):
                    key = all_keys[i]
                    yield key, cat._messages[key]

            dict_array = []
            for msgId, msg in m_slice(catalog, start_index, stop_index):
                # log.warn("Message %s", msgId)
                msg_dict = {
                    'msgId': msgId,
                    'message': msg,
                }
                if msg.string:
                    if self.blank_only:
                        log.warn("Skipping existing: %s => %s", msgId, msg.string)
                    else:
                        log.warn("Overwriting existing: %s => %s", msgId, msg.string)
                        dict_array.append(msg_dict)
                else:
                    dict_array.append(msg_dict)

            result = self.translator.translate_strings([item['msgId'] for item in dict_array], to_lang=lang)
            log.debug("Got %s new translations", len(result))

            for msg_dict in dict_array:
                msgId = msg_dict['msgId']
                message = msg_dict['message']
                this_translation = str(result[msgId])
                log.info("New trans: %s => %s", msgId, this_translation)
                message.string = this_translation

        log.debug("Finished translating: %s", lang_po_file)
        self.write_out_catalog(lang_po_file, catalog)

    @staticmethod
    def write_out_catalog(lang_po_file, catalog):
        # output_file = codecs.open(lang_po_file, encoding=self.app_encoding, mode="wb")
        with open(lang_po_file, "wb") as output_file:
            write_po(output_file, catalog)
        log.info("Finished writing new catalog to: %s", lang_po_file)
        # output_file.close()


def get_blocks(seq_len, block_size):
    """
    >>> get_blocks(6450, 2000)
    [(0, 1999), (2000, 3999), (4000, 5999), (6000, 6450)]

    :return:
    """
    num_blocks = int(seq_len / block_size)
    if num_blocks == 0:
        return [(0, seq_len)]
    rv = []
    i = 0
    for block_num in range(num_blocks):
        rv.append((i, ((block_num + 1) * block_size - 1)))
        i += block_size
    new_len = num_blocks * block_size
    if new_len < seq_len:
        rv.append((new_len, (seq_len - new_len) + new_len))
    return rv


def test():
    # test_strings = (
    # "Testing",
    # "Goodbye."
    # )
    # eurgh = EurghApp("local.ini")

    # for tr_str in test_strings:
    # res = eurgh.translate_string(tr_str)
    # print("%s ==> %s" % (tr_str, res))
    # print(eurgh.translator.translate_strings(test_strings))

    eurgh = EurghApp("local.ini")
    eurgh.translate_app_source()


if __name__ == "__main__":
    test()
