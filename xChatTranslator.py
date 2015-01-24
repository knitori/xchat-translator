# -*- coding: utf-8 -*-

__module_name__ = "translator"
__module_version__ = "0.10"
__module_description__ = "Translates from one language to others using Google Translate via YQL."
__module_author__ = "Chuong Ngo, karona75, briand, knitori"

import hexchat
import json
import urllib.request
import urllib.parse
import queue
import threading
from threading import Thread

AUTOUSER = {}
LAST_ERROR = ''


class TranslateException(Exception):
    pass


class Translator:
    """
    Class that actually communicates with Google Translate to get the translation and parse the return.
    """
    LANGUAGES = {
        'AFRIKAANS': 'af',
        'ALBANIAN': 'sq',
        'AMHARIC': 'am',
        'ARABIC': 'ar',
        'ARMENIAN': 'hy',
        'AZERBAIJANI': 'az',
        'BASQUE': 'eu',
        'BELARUSIAN': 'be',
        'BENGALI': 'bn',
        'BIHARI': 'bh',
        'BULGARIAN': 'bg',
        'BURMESE': 'my',
        'CATALAN': 'ca',
        'CHEROKEE': 'chr',
        'CHINESE': 'zh',
        'CHINESE_SIMPLIFIED': 'zh-CN',
        'CHINESE_TRADITIONAL': 'zh-TW',
        'CROATIAN': 'hr',
        'CZECH': 'cs',
        'DANISH': 'da',
        'DHIVEHI': 'dv',
        'DUTCH': 'nl',
        'ENGLISH': 'en',
        'ESPERANTO': 'eo',
        'ESTONIAN': 'et',
        'FILIPINO': 'tl',
        'FINNISH': 'fi',
        'FRENCH': 'fr',
        'GALICIAN': 'gl',
        'GEORGIAN': 'ka',
        'GERMAN': 'de',
        'GREEK': 'el',
        'GUARANI': 'gn',
        'GUJARATI': 'gu',
        'HEBREW': 'iw',
        'HINDI': 'hi',
        'HUNGARIAN': 'hu',
        'ICELANDIC': 'is',
        'INDONESIAN': 'id',
        'INUKTITUT': 'iu',
        'IRISH': 'ga',
        'ITALIAN': 'it',
        'JAPANESE': 'ja',
        'KANNADA': 'kn',
        'KAZAKH': 'kk',
        'KHMER': 'km',
        'KOREAN': 'ko',
        'KURDISH': 'ku',
        'KYRGYZ': 'ky',
        'LAOTHIAN': 'lo',
        'LATVIAN': 'lv',
        'LITHUANIAN': 'lt',
        'MACEDONIAN': 'mk',
        'MALAY': 'ms',
        'MALAYALAM': 'ml',
        'MALTESE': 'mt',
        'MARATHI': 'mr',
        'MONGOLIAN': 'mn',
        'NEPALI': 'ne',
        'NORWEGIAN': 'no',
        'ORIYA': 'or',
        'PASHTO': 'ps',
        'PERSIAN': 'fa',
        'POLISH': 'pl',
        'PORTUGUESE': 'pt-PT',
        'PUNJABI': 'pa',
        'ROMANIAN': 'ro',
        'RUSSIAN': 'ru',
        'SANSKRIT': 'sa',
        'SERBIAN': 'sr',
        'SINDHI': 'sd',
        'SINHALESE': 'si',
        'SLOVAK': 'sk',
        'SLOVENIAN': 'sl',
        'SPANISH': 'es',
        'SWAHILI': 'sw',
        'SWEDISH': 'sv',
        'TAJIK': 'tg',
        'TAMIL': 'ta',
        'TAGALOG': 'tl',
        'TELUGU': 'te',
        'THAI': 'th',
        'TIBETAN': 'bo',
        'TURKISH': 'tr',
        'UKRAINIAN': 'uk',
        'URDU': 'ur',
        'UZBEK': 'uz',
        'UIGHUR': 'ug',
        'ENGLISH (USA)': 'en-US',
        'VIETNAMESE': 'vi',
        'WELSH': 'cy',
        'YIDDISH': 'yi'
    }

    # Mapping to get the language from the language code
    LANGUAGES_REVERSE = dict([(v, k) for (k, v) in LANGUAGES.items()])

    CODES_SET = set(LANGUAGES.values())

    @classmethod
    def get_url(cls, message, dest_lang, source_lang=None):
        """
            Returns the url string to be used to translate the text.
        """
        src = cls.find_lang_code(source_lang)
        dest = cls.find_lang_code(dest_lang)

        params = {
            'format': ['json'],
            'callback': [],
        }

        # using {!r} should avoid Bad Request errors
        # because of quotation marks
        if src is None and dest is not None:
            params['diagnostics'] = ['true']
            params['env'] = ['http://datatables.org/alltables.env']
            query = 'select * from google.translate where q={!r} ' \
                    'and target={!r};'.format(message, dest)
        elif src is not None and dest is not None:
            params['env'] = ['store://datatables.org/alltableswithkeys']
            query = 'select * from google.translate where q={!r} ' \
                    'and target={!r} and source={!r};' \
                .format(message, dest, src)
        else:
            return None
        params['q'] = [query]
        baseurl = 'http://query.yahooapis.com/v1/public/yql'
        query_string = urllib.parse.urlencode(params, doseq=True,
                                              encoding='utf-8')
        return baseurl + '?' + query_string

    @classmethod
    def find_lang_code(cls, language):
        """
            Checks if the specifed language is in the dict
        """
        if language is None:
            return None

        if language.upper() in cls.LANGUAGES:
            # The language is in the dict LANGUAGES
            return cls.LANGUAGES[language.upper()]

        if language in cls.LANGUAGES_REVERSE:
            # The language code was used.
            return language

        # The language is not in the dict LANGUAGES
        return None

    @classmethod
    def find_lang_name(cls, language):
        if language is None:
            return None

        if language.upper() in cls.LANGUAGES:
            # The language name was used.
            return language.upper()

        if language in cls.LANGUAGES_REVERSE:
            # The language is in dict LANGUAGES_REVERSE
            return cls.LANGUAGES_REVERSE[language]

        return None

    @classmethod
    def translate(cls, message, source_lang, dest_lang):
        """
            Contacts the translation website via
            YQL to translate the message.
        """
        global LAST_ERROR
        url = cls.get_url(message, source_lang, dest_lang)

        if url is None:
            # The Url could not be created
            LAST_ERROR = "No valid destination/target language specified"
            return None, None

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = urllib.request.urlopen(urllib.request.Request(url, None, headers))
        return cls.parse_json_result(response.read().decode('utf-8'))

    @classmethod
    def parse_json_result(cls, result):
        """
            Parse the JSON returned from calling YQL to
            get the translated information.
        """
        data = json.loads(result)

        source_lang = data['query']['lang']
        data_arr = data['query']['results']['json']['sentences']
        translation = ""

        if type(data_arr) is dict:
            translation += data_arr['trans']
        else:
            for subDict in data_arr:
                translation += subDict['trans']

        return cls.LANGUAGES_REVERSE[source_lang], translation


class TranslatorThread(Thread):
    """
        Performs the translations in threads so as not to lock up XChat.
    """
    def __init__(self, q):
        threading.Thread.__init__(self, target=self.run)
        self.queue = q
        self.kill = False

    def run(self):
        global LAST_ERROR

        while True:
            job = self.queue.get()

            if self.kill or job is None:
                break
            try:
                context, user, src_lang, dest_lang, text = job

                lang, translated_text = \
                    Translator.translate(text, dest_lang, src_lang)

                if translated_text.strip().lower() != text.strip().lower():
                    context.emit_print("Channel Message",
                                       "[%s][%s]" % (user, lang),
                                       translated_text)
            except TranslateException as e:
                LAST_ERROR = "[TE: %s] <%s> %s" % (e, user, text)
            except urllib.request.URLError as e:
                LAST_ERROR = "[URL] %s" % e
            except UnicodeError as e:
                LAST_ERROR = "[Encode: %s] <%s> %s" % (e, user, text)


class ThreadController:
    """
        Controls the threads
    """
    jobs = queue.Queue()
    worker = TranslatorThread(jobs)
    worker.setDaemon(True)
    worker.start()

    @classmethod
    def add_job(cls, job):
        cls.jobs.put(job)


def translate_detect_lang(word, word_eol, userdata):
    """
        Translates the message to the specified language
        with source language detection
    """
    dest_lang = word[1]

    src, text = Translator.translate(word_eol[2], dest_lang, None)

    if src is None or text is None:
        hexchat.prnt("Error occurred during translation.")
    else:
        hexchat.command("say " + text)

    return hexchat.EAT_ALL


def translate_no_detect(word, word_eol, userdata):
    """
        Translates the message to the specified language assuming that
        the source language is the one specified.
    """
    src_lang = word[1]
    dest_lang = word[2]
    message = word_eol[3]

    src, text = Translator.translate(message, dest_lang, src_lang)

    if src is None or text is None:
        hexchat.prnt("Error occurred during translation.")
    else:
        hexchat.prnt("Translated from " + Translator.find_lang_name(src_lang)
                     + " to " + Translator.find_lang_name(dest_lang)
                     + ": " + text)
    return hexchat.EAT_ALL


def add_user(word, word_eol, userdata):
    """
        Adds a user to the watch list to automatically translate.
    """
    if len(word) < 2:
        hexchat.prnt("You must specify a user.")
        return hexchat.EAT_ALL

    user = hexchat.strip(word[1])
    dest = get_default_language()
    src = None

    if len(word) > 2 and Translator.find_lang_code(word[2]) is not None:
        dest = word[2]

    if len(word) > 3 and Translator.find_lang_code(word[3]) is not None:
        src = word[3]

    AUTOUSER[hexchat.get_info('channel') + ' ' + user.lower()] = (dest, src)
    hexchat.prnt("Added user %s to the watch list." % user)

    return hexchat.EAT_ALL


def remove_user(word, word_eol, userdata):
    """
        Removes a user from the watch list to automatically translate.
    """
    if len(word) < 2:
        hexchat.prnt("You must specify a user.")
        return hexchat.EAT_ALL

    user = word[1]

    if AUTOUSER.pop(hexchat.get_info('channel') + ' ' + user.lower(), None)\
            is not None:
        hexchat.prnt("User %s has been removed from the watch list." % user)

    return hexchat.EAT_ALL


def print_watch_list(word, word_eol, userdata):
    """
        Prints automatic translations watch list.
    """
    users = [key.split(' ')[1] for key in AUTOUSER.keys()]

    hexchat.prnt("WatchList: %s" % (" ".join(users)))
    return hexchat.EAT_ALL


def read_error(word, word_eol, userdata):
    """
        Prints out the last error.
    """
    hexchat.prnt("Last error: " + LAST_ERROR)


def add_job(word, word_eol, userdata):
    """
        Adds a new translation job to the queue.
    """
    channel = hexchat.get_info('channel')
    key = channel + " " + hexchat.strip(word[0].lower())

    if key in AUTOUSER:
        dest, src = AUTOUSER[key]
        ThreadController.add_job((hexchat.get_context(), word[0],
                                 src, dest, word[1]))

    return hexchat.EAT_NONE


def unload_translator(userdata):
    """
        Shuts down the threads and thread controller
        when unloading the module.
    """
    ThreadController.worker.kill = True
    ThreadController.add_job(None)
    hexchat.prnt('Translator is unloaded')


def set_default_language(word, word_eol, userdata):

    if len(word) < 2:
        hexchat.prnt("You must specify a language.")
        return hexchat.EAT_ALL

    lang = Translator.find_lang_code(word[1])
    if lang is not None:
        hexchat.set_pluginpref('default_language', word[1])
        hexchat.prnt("Succesfully set language to {}".format(Translator.find_lang_name(lang)))
    else:
        hexchat.prnt("Invalid language.")

    return hexchat.EAT_ALL


def get_default_language():
    language = hexchat.get_pluginpref('default_language')
    if language is None:
        return 'en'
    return language


hexchat.hook_command(
    "TR", translate_detect_lang,
    help="/TR <target language> <message> - translates message into the "
         "language specified.  This auto detects the source language.  "
         "This is not threaded.")

hexchat.hook_command(
    "TM", translate_no_detect,
    help="/TM <source_language> <target_language> <message> - translates "
         "message into the language specified.  This is not threaded.")

hexchat.command('MENU ADD "$NICK/[+] AutoTranslate" "ADDTR %s"')
hexchat.hook_command(
    "ADDTR", add_user,
    help="/ADDTR <user_nick> <target_language> <source_language> - adds the "
         "user to the watch list for automatic translations.  If "
         "target_language is not specified, then the DEFAULT_LANG set will "
         "be used.  If source_language is not specified, then language "
         "detection will be used.")

hexchat.command('MENU ADD "$NICK/[-] AutoTranslate" "RMTR %s"')
hexchat.hook_command(
    "RMTR", remove_user,
    help="/RMTR <user_nick> - removes user_nick from "
         "the watch list for automatic translations.")

hexchat.hook_command(
    "LSUSERS", print_watch_list,
    help="/LSUSERS - prints out all users on the watch list for automatic "
         "translations to the screen locally.")

hexchat.hook_command(
    "LASTERROR", read_error,
    help="/LASTERROR - prints out the last error "
         "message to screen locally.")

hexchat.hook_print("Channel Message", add_job)

hexchat.hook_unload(unload_translator)

hexchat.hook_command(
    'TRDEFAULT', set_default_language,
    help="/TRDEFAULT <language> - set the default language.")

# Load successful, print message
hexchat.prnt('Translator script loaded successfully.')
