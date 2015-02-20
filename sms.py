#!/usr/bin/env python

# vim:ts=4

import requests, sys, argparse

baseurl = "http://api.clickatell.com"
sendurl = baseurl + "/http/sendmsg"

# Settings - TODO: move to config file
callback = 0
user = ""
password = ""
api_id = ""
sender_id = ""

# Parse commandline args
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--number", help = "Specify number to send text message to.", required=True, type=str)
parser.add_argument("-m", "--message", help = "Provide text to send.", required=True, type=str)
args = parser.parse_args()
destination = args.number
message = args.message


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

sendPayload = {'session_id': session_id, 'to': destination, 'text': message, 'from': sender_id, \
	'concat': concatNo}
send_message = requests.get(sendurl, params=sendPayload)

if (send_message.status_code == 200):
	print send_message.text
	sys.exit(0)
else:
	print send_message.text
	sys.exit(1)
