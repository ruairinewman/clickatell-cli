# clickatell-cli
Simple Python-based Clickatell CLI.

$ ./sms.py -h
usage: sms.py [-h] [-a ABNAME | -n NUMBER] -m MESSAGE [-c CONF] [-f]

Commandline Client for Clickatell SMS API

optional arguments:
 * -h, --help            			   Show this help message and exit
 * -a ABNAME, --abname ABNAME          Name of contact in address book
 * -n NUMBER, --number NUMBER          Specify number to send text message to.
 * -m MESSAGE, --message MESSAGE       Provide text to send.
 * -s --shell                          Message shell - use to avoid issues with shell parsing of text
 * -c CONF, --conf CONF                Specify config file. (Default: ~/.sms.cfg)
 * -f, --flash                         Send as SMS 'Flash' message type.
 * -v --verbose						   Show more details

Note: the destination phone number should omit the international dialling prefix but include the destination 
country code. For example, for an Irish phone number, locally 088-765-4321, the number specified would be 353887654321.
(353 is the international dialling code for Ireland.)

 * Uses the Clickatell HTTP Specification: https://www.clickatell.com/downloads/http/Clickatell_HTTP.pdf
 * Long (> 160 character) messages handled.
 * Reads configuration from .sms.cfg in users home directory by default, or from file specified.
 * Supports name=number mapping in addressbook (config file)
 * Supports SMS Flash messages
