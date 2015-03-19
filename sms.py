#!/usr/bin/env python

# vim:ts=4

import requests, sys, os, argparse, ConfigParser, signal, stat

baseurl = "http://api.clickatell.com"
sendurl = baseurl + "/http/sendmsg"
authurl = baseurl + "/http/auth/?"
CONF_PERM = "0100600"

# Check config permissions
def check_perms(config):
	conf_perms = str(oct(os.stat(config).st_mode))
	if not (conf_perms == CONF_PERM):
		print "Config file permissions not set to recommended '600'. Please rectify and run again."
		sys.exit(4)

# Trap <Ctrl-C>
def signal_handler(signal, frame):
	print "\nExiting ...\n"
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# Message shell
def get_message_from_shell():
	print "Enter message to send. <Ctrl-D> to finish, <Ctrl-C> to close: "
	return sys.stdin.readlines()

# Parse commandline args
parser = argparse.ArgumentParser(description="Commandline Client for Clickatell SMS API")
contactgroup = parser.add_mutually_exclusive_group()
contactgroup.add_argument("-a", "--abname", help = "Name of contact in address book", required=False, type=str)
contactgroup.add_argument("-n", "--number", help = "Specify number to send text message to.", required=False, type=str)
messagegroup = parser.add_mutually_exclusive_group()
messagegroup.add_argument("-m", "--message", help = "Provide text to send.", required=False, type=str)
messagegroup.add_argument("-s", "--shell", help = "Message shell", required=False, action="store_true")
parser.add_argument("-c", "--conf", help = "Specify config file. (Default: ~/.sms.cfg)", required=False, type=str)
parser.add_argument("-f", "--flash", help = "Send as SMS 'Flash' message type.", required=False, action="store_true")
parser.add_argument("-v", "--verbose", help = "Display additional information.", required=False, action="store_true")
args = parser.parse_args()
if not args.shell:
	message = args.message
else:
	message = get_message_from_shell()

# Flash message?
if args.flash:
	message_type = "SMS_FLASH"
else:
	message_type = "SMS_TEXT"

# Config location
if args.conf:
	config = args.conf
else:
	config = os.environ["HOME"] + "/.sms.cfg"

check_perms(config)

# Settings
settings = ConfigParser.ConfigParser()
settings.read(config)
callback = int(settings.get('settings', 'callback'))
user = settings.get('credentials', 'user')
password = settings.get('credentials', 'password')
api_id = settings.get('credentials', 'api_id')
sender_id = settings.get('credentials', 'sender_id')

# Look up address book
if args.abname:
	destination = settings.get('addressbook', args.abname)
elif args.number:
	destination = args.number
else:
	print "No destination."
	sys.exit(1)

# Concat - message length handling
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

str_message = ''.join(message)
concatNo = getConcat(str_message)

sessionPayload = {\
	'user' : user, \
	'password' : password, \
	'api_id' : api_id, \
	'callback' : callback \
}
auth = requests.get(authurl, params=sessionPayload)
session_id = auth.text.split(' ', 1)[1]
if (auth.text.split(':', 1)[0] != 'OK'):
	print "auth failure"
	if args.verbose:
		print auth.text
	sys.exit(1)

sendPayload = {\
	'session_id': session_id, \
	'to': destination, \
	'text': str_message, \
	'from': sender_id, \
	'concat': concatNo, \
	'msg_type': message_type\
}
send_message = requests.get(sendurl, params=sendPayload)

if (send_message.status_code == 200):
	if args.verbose:
		print "Success!"
		print "Request: '%s', '%s'" % (sendurl, sendPayload)
		print send_message.text
	sys.exit(0)
else:
	if args.verbose:
		print "Fail!"
		print "Request: '%s', '%s'" % (sendurl, sendPayload)
		print send_message.text
	sys.exit(1)
