# clickatell-cli
Simple Python 3 based Clickatell CLI - refactored for performance and ease of use.

**Python 3.7+ compatible** (tested up to Python 3.14)

## Installation

```bash
pip install requests
chmod +x sms.py
```

## Requirements
- Python 3.7 or higher
- requests library

## Usage

$ ./sms.py -h
usage: sms.py [-h] [-a ABNAME | -n NUMBER] -m MESSAGE [-c CONF] [-f] [--force]

Commandline Client for Clickatell SMS API

optional arguments:
 * -h, --help            			   Show this help message and exit
 * -a ABNAME, --abname ABNAME          Name of contact in address book
 * -n NUMBER, --number NUMBER          Specify number to send text message to.
 * -m MESSAGE, --message MESSAGE       Provide text to send.
 * -s --shell                          Message shell - use to avoid issues with shell parsing of text
 * -c CONF, --conf CONF                Specify config file. (Default: ~/.sms.cfg)
 * -f, --flash                         Send as SMS 'Flash' message type.
 * --force								Override built-in permissions check on config file
 * -v --verbose						   Show more details

Note: the destination phone number should omit the international dialling prefix but include the destination 
country code. For example, for an Irish phone number, locally 088-765-4321, the number specified would be 353887654321.
(353 is the international dialling code for Ireland.)

 * Uses the Clickatell HTTP Specification: https://www.clickatell.com/downloads/http/Clickatell_HTTP.pdf
 * Long (> 160 character) messages handled.
 * Reads configuration from .sms.cfg in users home directory by default, or from file specified.
 * Supports name=number mapping in addressbook (config file)
 * Supports SMS Flash messages

## Recent Refactoring (2024)

This codebase has been refactored for improved performance and maintainability:
- ✅ Python 3.14 compatible with type hints
- ✅ Connection pooling for better performance
- ✅ Automatic retry logic with exponential backoff
- ✅ Better error handling with custom exceptions
- ✅ Organized class-based structure
- ✅ Improved logging with Python logging module
- ✅ All existing functionality preserved

See [REFACTORING.md](REFACTORING.md) for complete details.
