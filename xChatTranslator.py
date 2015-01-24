# -*- coding: utf-8 -*-

__module_name__ = "translator"
__module_version__ = "0.9"
__module_description__ = "Translates from one language to others using Google Translate via YQL."
__module_author__ = "Chuong Ngo, karona75, briand"

import xchat
import json
import urllib.request
import queue
import threading
from threading import Thread
import traceback

DEFAULT_LANG = 'en'

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

    def get_url(cls, message, dest_lang, source_lang=None):
        """
            Returns the url string to be used to translate the text.
        """
        src = cls.find_lang_code(source_lang)
        dest = cls.find_lang_code(dest_lang)

        if src is None and dest is not None:
            # No source language was provided, automatically detect the language
            return "http://query.yahooapis.com/v1/public/yql?q=select%20*" \
                   "%20from%20google.translate%20where%20q%3D%22" + \
                   urllib.request.quote(message) + "%22%20and%20target%3D%22" +\
                   dest + "%22%3B&format=json&diagnostics=true&env=http%" \
                   "3A%2F%2Fdatatables.org%2Falltables.env&callback="

        if src is not None and dest is not None:
            # Source language was provided, don't detect the language
            return "http://query.yahooapis.com/v1/public/yql?q=select%20*" \
                   "%20from%20google.translate%20where%20q%3D%22"\
                   + urllib.request.quote(message) + "%22%20and%20target%3D%22"\
                   + dest + "%22%20and%20source%3D%22" + src\
                   + "%22%3B&format=json&env=store%3A%2F%2Fdatatables.org" \
                     "%2Falltableswithkeys&callback="

        return None
    get_url = classmethod(get_url)

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
    find_lang_code = classmethod(find_lang_code)

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
    find_lang_name = classmethod(find_lang_name)

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

        return cls.parse_json_result(response.read())
    translate = classmethod(translate)

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

        return (cls.LANGUAGES_REVERSE[source_lang],
                translation.encode("utf-8"))
    parse_json_result = classmethod(parse_json_result)


class TranslatorThread(Thread):
    """
        Performs the translations in threads so as not to lock up XChat.
    """
    def __init__(self, queue):
        threading.Thread.__init__(self, target=self.run)
        self.queue = queue
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

    def add_job(cls, job):
        cls.jobs.put(job)
    add_job = classmethod(add_job)


def translate_detect_lang(word, word_eol, userdata):
    """
        Translates the message to the specified language
        with source language detection
    """
    dest_lang = word[1]

    src, text = Translator.translate(word_eol[2], dest_lang, None)

    if src is None or text is None:
        xchat.prnt("Error occurred during translation.")
    else:
        xchat.command("say " + text)

    return xchat.EAT_ALL

xchat.hook_command(
    "TR", translate_detect_lang,
    help="/TR <target language> <message> - translates message into the "
         "language specified.  This auto detects the source language.  "
         "This is not threaded.")


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
        xchat.prnt("Error occurred during translation.")
    else:
        xchat.prnt("Translated from " + Translator.find_lang_name(src_lang)
                   + " to " + Translator.find_lang_name(dest_lang)
                   + ": " + text)
    return xchat.EAT_ALL

xchat.hook_command(
    "TM", translate_no_detect,
    help="/TM <source_language> <target_language> <message> - translates "
         "message into the language specified.  This is not threaded.")


def add_user(word, word_eol, userdata):
    """
        Adds a user to the watch list to automatically translate.
    """
    if len(word) < 2:
        xchat.prnt("You must specify a user.")
        return xchat.EAT_ALL

    user = word[1]
    dest = DEFAULT_LANG
    src = None

    if len(word) > 2 and Translator.find_lang_code(word[2]) is not None:
        dest = word[2]

    if len(word) > 3 and Translator.find_lang_code(word[3]) is not None:
        src = word[3]

    AUTOUSER[xchat.get_info('channel') + ' ' + user.lower()] = (dest, src)
    xchat.prnt("Added user %s to the watch list." % user)

    return xchat.EAT_ALL

xchat.command('MENU ADD "$NICK/[+] AutoTranslate" "ADDTR %s"')
xchat.hook_command(
    "ADDTR", add_user,
    help="/ADDTR <user_nick> <target_language> <source_language> - adds the "
         "user to the watch list for automatic translations.  If "
         "target_language is not specified, then the DEFAULT_LANG set will "
         "be used.  If source_language is not specified, then language "
         "detection will be used.")


def remove_user(word, word_eol, userdata):
    """
        Removes a user from the watch list to automatically translate.
    """
    if len(word) < 2:
        xchat.prnt("You must specify a user.")
        return xchat.EAT_ALL

    user = word[1]

    if AUTOUSER.pop(xchat.get_info('channel') + ' ' + user.lower(), None)\
            is not None:
        xchat.prnt("User %s has been removed from the watch list." % user)

    return xchat.EAT_ALL

xchat.command('MENU ADD "$NICK/[-] AutoTranslate" "RMTR %s"')
xchat.hook_command(
    "RMTR", remove_user,
    help="/RMTR <user_nick> - removes user_nick from "
         "the watch list for automatic translations.")


def print_watch_list(word, word_eol, userdata):
    """
        Prints automatic translations watch list.
    """
    users = [key.split(' ')[1] for key in AUTOUSER.keys()]

    xchat.prnt("WatchList: %s" % (" ".join(users)))
    return xchat.EAT_ALL

xchat.hook_command(
    "LSUSERS", print_watch_list,
    help="/LSUSERS - prints out all users on the watch list for automatic "
         "translations to the screen locally.")


def read_error(word, word_eol, userdata):
    """
        Prints out the last error.
    """
    xchat.prnt("Last error: " + LAST_ERROR)

xchat.hook_command(
    "LASTERROR", read_error, help="/LASTERROR - prints out the last error "
                                  "message to screen locally.")


def add_job(word, word_eol, userdata):
    """
        Adds a new translation job to the queue.
    """
    channel = xchat.get_info('channel')
    key = channel + " " + word[0].lower()

    if key in AUTOUSER:
        dest, src = AUTOUSER[key]
        ThreadController.add_job((xchat.get_context(), word[0],
                                 src, dest, word[1]))

    return xchat.EAT_NONE

xchat.hook_print("Channel Message", add_job)


def unload_translator(userdata):
    """
        Shuts down the threads and thread controller
        when unloading the module.
    """
    ThreadController.worker.kill = True
    ThreadController.add_job(None)
    print('Translator is unloaded')

xchat.hook_unload(unload_translator)

# Load successful, print message
print('Translator script loaded successfully.')
