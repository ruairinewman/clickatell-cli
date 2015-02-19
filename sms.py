#!/usr/bin/env python

import requests, sys

baseurl = "http://api.clickatell.com"
sendurl = baseurl + "/http/sendmsg"
callback = 7
user = ""
password = ""
api_id = ""
sender_id = ""

sessRequest = ("/http/auth/?user=%s&password=%s&api_id=%s&callback=%d" % (user, password, api_id, callback))
auth = requests.get(baseurl + sessRequest)
session_id = auth.text.split(' ', 1)[1]
if (auth.text.split(':', 1)[0] != 'OK'):
    print "auth failure"
    sys.exit(1)

reqPayload = {'session_id': session_id, 'to': sys.argv[1], 'text': sys.argv[2], 'from': sender_id}
send_message = requests.get(sendurl, params=reqPayload)

if (send_message.status_code == 200):
    sys.exit(0)
else:
    print send_message.text
    sys.exit(1)
