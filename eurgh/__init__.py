#!/usr/bin/env python
# -*- coding: utf-8; mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vim: fileencoding=utf-8 tabstop=4 expandtab shiftwidth=4

"""
Eurgh - an application message catalog translation utility using the
Microsoft Translator API.
"""
import copy
import json

import sys
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

        self.use_json = config.getboolean("app", "json", fallback=False)

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
        if self.use_json:
            return self.translate_app_language_json(lang)
        return self.translate_app_language_mc(lang)

    def translate_app_language_json(self, lang):
        domain = self.app_domain
        locale = lang

        targetFile = self.config.get(
            "app", "json_file_template", fallback='', vars=locals())

        sourceFile = self.config.get(
            "app", "json_source_file", fallback='', vars=locals())

        if not targetFile or not sourceFile:
            log.info('No source or target files. source: %s  target: %s' % (sourceFile, targetFile))
            return

        lang_json_file = os.path.join(self.app_locale_dir, targetFile)
        if not os.path.exists(lang_json_file):
            msg = "JSON target language file doesn't exist: %s" % (lang_json_file,)
            log.error(msg)
            raise IOError(msg)

        source_json_file = os.path.join(self.app_locale_dir, sourceFile)
        if not os.path.exists(source_json_file):
            msg = "JSON source language file doesn't exist: %s" % (source_json_file,)
            log.error(msg)
            raise IOError(msg)

        target_fileh = codecs.open(lang_json_file, encoding=self.app_encoding, mode="r")
        target_data = json.load(target_fileh)

        source_fileh = codecs.open(source_json_file, encoding=self.app_encoding, mode="r")
        source_data = json.load(source_fileh)
        source_fileh.close()

        was_changed, new_data = self.translate_json(lang, source_data, target_data)
        if was_changed:
            outfileh = codecs.open(lang_json_file, encoding=self.app_encoding, mode="w")
            json.dump(new_data, outfileh, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': '))
            outfileh.close()

        log.info("Completed translation of %s" % (targetFile,))
        return

    def translate_json(self, locale, source_data, target_data):

        was_changed = False
        out_data = copy.deepcopy(target_data)

        all_keys = sorted(source_data.keys())
        num_keys = len(all_keys)
        for start_index, stop_index in get_blocks(num_keys, self.translator.MAX_API_ARRAY):
            slice_keys = all_keys[start_index:stop_index]
            if not slice_keys:
                continue

            translate_keys = []
            translate_vals = []

            for keyname in slice_keys:
                source_val = source_data[keyname]
                if not source_val:
                    source_val = keyname  # use the key if we have to...?
                target_val = out_data.get(keyname, '')
                if target_val:
                    log.info("already trans: %s -> %s" % (keyname, target_val))
                    continue
                translate_keys.append(keyname)
                translate_vals.append(source_val)

            if not translate_keys:
                log.info("Nothing to translate in this section? %s:%s" % (start_index, stop_index))
                continue

            result_vals = self.translator.translate_strings(
                translate_vals, to_lang=locale)
            log.debug("Got %s new translations for: %s (%s, %s)",
                      len(result_vals), locale, start_index, stop_index)

            for i in range(len(translate_keys)):
                xkey = translate_keys[i]
                source_val = translate_vals[i]
                xval = result_vals.get(source_val, xkey)
                if xkey == xval:
                    log.info("Skipping %s -> %s" % (xkey, xkey))
                    continue
                log.debug("Translating %s: %s -> %s" % (locale, xkey, xval))
                out_data[xkey] = xval
                was_changed = True

        return was_changed, out_data

    def translate_app_language_mc(self, lang):
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
        catalog = read_po(input_file)
        input_file.close()
        log.warn("Opened message catalog: %s", lang_po_file)
        self.translate_catalog(lang, lang_po_file, catalog)

    def translate_catalog(self, lang, lang_po_file, catalog):
        changed_file = False
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

            if not dict_array:
                log.info("No changes to section (%s, %s) for: %s", start_index, stop_index, lang_po_file)
            else:
                result = self.translator.translate_strings([item['msgId'] for item in dict_array], to_lang=lang)
                log.debug("Got %s new translations for: %s (%s, %s)", len(result), lang_po_file, start_index, stop_index)

                for msg_dict in dict_array:
                    msgId = msg_dict['msgId']
                    message = msg_dict['message']
                    this_translation = str(result[msgId])
                    log.info("New trans: %s => %s", msgId, this_translation)
                    message.string = this_translation
                    changed_file = True

        if changed_file:
            log.debug("Finished translating: %s", lang_po_file)
            self.write_out_catalog(lang_po_file, catalog)
        else:
            log.debug("No changes to file: %s", lang_po_file)

    @staticmethod
    def write_out_catalog(lang_po_file, catalog):
        with open(lang_po_file, "wb") as output_file:
            write_po(output_file, catalog)
        log.info("Finished writing new catalog to: %s", lang_po_file)


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


def main():
    try:
        config_file = sys.argv[1]
    except KeyError:
        raise RuntimeError("You must give the config.ini file as the first argument.")
    if not os.path.exists(config_file):
        raise IOError("Can't find config file at: %s" % (config_file,))
    eurgh = EurghApp(config_file)
    eurgh.translate_app_source()


if __name__ == "__main__":
    main()
