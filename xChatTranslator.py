__module_name__ = "translator"
__module_version__ = "0.1"
__module_description__ = "Translates from one language to other using Google Translate via YQL."
__module_author__ = "drag"

import xchat

import json
import urllib2

DEST_LANG = 'en'
AUTOUSER = {}

def getPage(words,src,dest):
	url = "http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20google.translate%20where%20q%3D%22" + words +"%22%20and%20target%3D%22" + dest + "%22%20and%20source%3D%22" + src +"%22	3B&format=json&env=store%3A%2F%2Fdatatables.org%2Falltableswithkeys&callback="
	headers = { 'User-Agent' : 'Mozilla/5.0' }
	req = urllib2.Request(url, None, headers)
	response = urllib2.urlopen(req)
	return response.read()

def parseJsonResult(resultStr):
	result = json.loads(resultStr)
	resultArray = result['query']['results']['json']['json'][0]['json']
	str=""
	if type(resultArray) is dict:
		str+=resultArray['json'][0]
	else:
		for subDict in resultArray:
			str+=subDict['json'][0]	
	return str

def translateTo(word, word_eo1, userdata):
	xchat.prnt("Starting translate");
	srcStr = "this is just a test"
	destLanguage = "ru"
	srcLanguage = "en"

	page = getPage(urllib2.quote(srcStr.encode('utf8')), srcLanguage, destLanguage)
	result = json.loads(page)
	str = parseJsonResult(result)

	print(str)
	xchat.command('say Translation complete.')
	
	return xchat.EAT_ALL

xchat.hook_command("tr", translateTo, help="/tr <message> translates message into the language specified.")