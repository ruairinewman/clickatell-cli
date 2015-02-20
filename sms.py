#!/usr/bin/env python

# vim:ts=4

import requests, sys

baseurl = "http://api.clickatell.com"
sendurl = baseurl + "/http/sendmsg"
callback = 0
user = ""
password = ""
api_id = ""
sender_id = ""

def getConcat(message):
	messagelen = len(message)
	if (messagelen > 459):
		print "Message length greater than 459 characters."
		sys.exit(1)
	elif (messagelen <= 160):
		concatNo = 1
	elif (messagelen <= 320):
		concatNo = 2
	else:
		concatNo = 3
	return concatNo

concatNo = getConcat(sys.argv[2])

sessRequest = ("/http/auth/?user=%s&password=%s&api_id=%s&callback=%d" % (user, password, api_id, callback))
auth = requests.get(baseurl + sessRequest)
session_id = auth.text.split(' ', 1)[1]
if (auth.text.split(':', 1)[0] != 'OK'):
	print "auth failure"
	sys.exit(1)

sendPayload = {'session_id': session_id, 'to': sys.argv[1], 'text': sys.argv[2], 'from': sender_id, \
	'concat': concatNo}
send_message = requests.get(sendurl, params=sendPayload)

if (send_message.status_code == 200):
	print send_message.text
	sys.exit(0)
else:
	print send_message.text
	sys.exit(1)
