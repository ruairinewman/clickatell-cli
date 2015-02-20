# clickatell-cli
Simple Python-based Clickatell CLI.

Syntax: $ ./sms.py -n "Destination Phone Number" -m "Text message" [-c "Path to config file"]

Note: the destination phone number should omit the international dialling prefix but include the destination 
country code. For example, for an Irish phone number, locally 088-765-4321, the number specified would be 353887654321.
(353 is the international dialling code for Ireland.)

 * Uses the Clickatell HTTP Specification: https://www.clickatell.com/downloads/http/Clickatell_HTTP.pdf
 * Long (> 160 character) messages handled.
 * Reads configuration from .sms.cfg in users home directory by default, or from file specified.

