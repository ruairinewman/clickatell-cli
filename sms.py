#!/usr/bin/env python3

"""
Clickatell SMS CLI - A command-line interface for sending SMS via Clickatell API.

This module provides a refactored, Python 3.14-compatible implementation with
improved performance, error handling, and code organization.
"""

import argparse
import configparser
import datetime
import logging
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Constants
BASE_URL = "https://api.clickatell.com"
SEND_URL = f"{BASE_URL}/http/sendmsg"
AUTH_URL = f"{BASE_URL}/http/auth/?"
CONF_PERM = 0o100600
DEFAULT_CONFIG_FILE = "~/.sms.cfg"
DEFAULT_LOG_FILE = "~/.sms.log"

# Configure module-level logger
logger = logging.getLogger(__name__)


class ClickatellError(Exception):
    """Base exception for Clickatell-related errors."""
    pass


class AuthenticationError(ClickatellError):
    """Raised when authentication with Clickatell API fails."""
    pass


class ConfigurationError(ClickatellError):
    """Raised when there's an issue with configuration."""
    pass


class MessageError(ClickatellError):
    """Raised when there's an issue with the message."""
    pass


class Config:
    """Handles configuration file loading and validation."""

    def __init__(self, config_path: str, force_perms: bool = False):
        """
        Initialize configuration handler.

        Args:
            config_path: Path to configuration file
            force_perms: If True, ignore permission checks
        """
        self.config_path = Path(config_path).expanduser()
        self.force_perms = force_perms
        self.parser = configparser.ConfigParser()
        self._load_config()

    def _check_permissions(self) -> None:
        """Verify config file has secure permissions."""
        if self.force_perms:
            return

        try:
            stat_info = self.config_path.stat()
            current_perms = stat_info.st_mode

            if current_perms != CONF_PERM:
                raise ConfigurationError(
                    f"Config file permissions not set to recommended '600'. "
                    f"Current: {oct(current_perms)}, Expected: {oct(CONF_PERM)}. "
                    f"Use --force to override."
                )
        except FileNotFoundError:
            raise ConfigurationError(f"Config file not found: {self.config_path}")

    def _load_config(self) -> None:
        """Load and parse configuration file."""
        self._check_permissions()

        try:
            self.parser.read(self.config_path)
        except configparser.Error as e:
            raise ConfigurationError(f"Failed to parse config file: {e}")

    def get(self, section: str, option: str, fallback: Any = None) -> str:
        """
        Get configuration value.

        Args:
            section: Configuration section
            option: Configuration option
            fallback: Default value if not found

        Returns:
            Configuration value
        """
        try:
            value = self.parser.get(section, option)
            # If value is empty and fallback is provided, use fallback
            if (not value or value.strip() == '') and fallback is not None:
                return fallback
            # If value is empty and no fallback, raise error
            if not value or value.strip() == '':
                raise ConfigurationError(f"Empty config value: [{section}] {option}")
            return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise ConfigurationError(f"Missing config: [{section}] {option}")

    def get_int(self, section: str, option: str, fallback: int = None) -> int:
        """Get integer configuration value."""
        try:
            value = self.parser.get(section, option)
            if not value or value.strip() == '':
                if fallback is not None:
                    return fallback
                raise ConfigurationError(f"Empty config value: [{section}] {option}")
            return int(value)
        except (configparser.NoSectionError, configparser.NoOptionError):
            if fallback is not None:
                return fallback
            raise ConfigurationError(f"Missing config: [{section}] {option}")
        except ValueError:
            if fallback is not None:
                return fallback
            raise ConfigurationError(f"Invalid integer value for: [{section}] {option}")

    def get_addressbook_entry(self, name: str) -> str:
        """
        Get phone number from address book.

        Args:
            name: Contact name

        Returns:
            Phone number

        Raises:
            ConfigurationError: If contact not found
        """
        try:
            return self.parser.get('addressbook', name)
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ConfigurationError(f"Contact '{name}' not found in address book")


class ClickatellAPI:
    """Handles communication with Clickatell API."""

    def __init__(
        self,
        user: str,
        password: str,
        api_id: str,
        sender_id: str,
        callback: int = 0,
        timeout: int = 7
    ):
        """
        Initialize Clickatell API client.

        Args:
            user: Clickatell username
            password: Clickatell password
            api_id: Clickatell API ID
            sender_id: Sender ID for messages
            callback: Callback setting
            timeout: Request timeout in seconds
        """
        self.user = user
        self.password = password
        self.api_id = api_id
        self.sender_id = sender_id
        self.callback = callback
        self.timeout = timeout
        self.session_id: Optional[str] = None

        # Create session with connection pooling and retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create requests session with connection pooling and retry logic.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        # Mount adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def authenticate(self) -> str:
        """
        Authenticate with Clickatell API.

        Returns:
            Session ID

        Raises:
            AuthenticationError: If authentication fails
        """
        payload = {
            'user': self.user,
            'password': self.password,
            'api_id': self.api_id,
            'callback': self.callback
        }

        try:
            response = self.session.get(
                AUTH_URL,
                params=payload,
                timeout=self.timeout,
                verify=True
            )
            response.raise_for_status()

            # Parse response
            response_text = response.text.strip()
            parts = response_text.split(' ', 1)

            if parts[0] != 'OK:':
                raise AuthenticationError(f"Authentication failed: {response_text}")

            if len(parts) < 2:
                raise AuthenticationError("Invalid authentication response format")

            self.session_id = parts[1]
            logger.info("Successfully authenticated with Clickatell API")
            return self.session_id

        except requests.RequestException as e:
            raise AuthenticationError(f"Authentication request failed: {e}")

    def send_message(
        self,
        destination: str,
        message: str,
        message_type: str = "SMS_TEXT",
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """
        Send SMS message.

        Args:
            destination: Destination phone number
            message: Message text
            message_type: Type of message (SMS_TEXT or SMS_FLASH)
            dry_run: If True, don't actually send

        Returns:
            Tuple of (success, response_text)

        Raises:
            MessageError: If message validation fails
        """
        if not self.session_id:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        # Validate and calculate concat
        concat_no = self._calculate_concat(message)

        if dry_run:
            logger.info("Dry run mode - message not sent")
            return True, "Dry run - no message sent"

        payload = {
            'session_id': self.session_id,
            'to': destination,
            'text': message,
            'from': self.sender_id,
            'concat': concat_no,
            'msg_type': message_type
        }

        try:
            response = self.session.get(
                SEND_URL,
                params=payload,
                timeout=self.timeout,
                verify=True
            )

            success = response.status_code == 200

            if success:
                logger.info(f"Message sent successfully to {destination}")
            else:
                logger.error(f"Failed to send message. Status: {response.status_code}")

            return success, response.text.strip()

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return False, str(e)

    @staticmethod
    def _calculate_concat(message: str) -> int:
        """
        Calculate concat number based on message length.

        Args:
            message: Message text

        Returns:
            Concat number (1-3)

        Raises:
            MessageError: If message is too long or empty
        """
        length = len(message)

        if length == 0:
            raise MessageError("Message length is 0 (zero)")

        if length > 459:
            raise MessageError(
                f"Message length ({length}) greater than 459 characters"
            )

        if length <= 160:
            return 1
        elif length <= 320:
            return 2
        else:
            return 3

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()


class MessageInput:
    """Handles message input from various sources."""

    @staticmethod
    def from_editor(verbose: bool = False) -> str:
        """
        Get message from external editor.

        Args:
            verbose: If True, show debug information

        Returns:
            Message text
        """
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
            temp_file = f.name

        try:
            if verbose:
                print(f"Message editor temp file: {temp_file}")

            editor = os.environ.get('EDITOR', 'vi')
            subprocess.call([editor, temp_file])

            with open(temp_file, 'r', encoding='utf-8') as f:
                return f.read()
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass

    @staticmethod
    def from_stdin() -> str:
        """
        Get message from stdin.

        Returns:
            Message text
        """
        print("Enter message to send. <Ctrl-D> to finish, <Ctrl-C> to cancel:")
        try:
            lines = sys.stdin.readlines()
            return ''.join(lines)
        except KeyboardInterrupt:
            print("\nInput cancelled")
            sys.exit(0)


class SMSLogger:
    """Handles SMS logging to file."""

    def __init__(self, log_file: str, enabled: bool = True):
        """
        Initialize SMS logger.

        Args:
            log_file: Path to log file
            enabled: Whether logging is enabled
        """
        self.log_file = Path(log_file).expanduser()
        self.enabled = enabled

    def log_message(
        self,
        destination: str,
        message: str,
        success: bool,
        response: str = ""
    ) -> None:
        """
        Log SMS details to file.

        Args:
            destination: Destination number
            message: Message text
            success: Whether send was successful
            response: API response
        """
        if not self.enabled:
            return

        timestamp = datetime.datetime.now().isoformat()
        status = "SUCCESS" if success else "FAIL"

        # Truncate message for logging
        msg_preview = message[:50] + "..." if len(message) > 50 else message

        log_entry = (
            f"\n{timestamp} [{status}] "
            f"To: {destination}, "
            f"Message: {msg_preview}, "
            f"Response: {response}"
        )

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except IOError as e:
            logger.warning(f"Failed to write to log file: {e}")


def setup_logging(verbose: bool = False) -> None:
    """
    Configure logging.

    Args:
        verbose: If True, set DEBUG level
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl-C)."""
    print("\nCtrl-C or SIGINT received, exiting...")
    sys.exit(0)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Command-line Client for Clickatell SMS API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Send message to number:
    %(prog)s -n 353876543210 -m "Hello World"

  Send message to contact:
    %(prog)s -a contact_alias -m "Hello World"

  Compose in editor:
    %(prog)s -n 353876543210 -s -e

  Send flash message:
    %(prog)s -n 353876543210 -m "Alert!" -f
        """
    )

    # Contact specification
    contact_group = parser.add_mutually_exclusive_group()
    contact_group.add_argument(
        "-a", "--abname",
        help="Name of contact in address book",
        type=str
    )
    contact_group.add_argument(
        "-n", "--number",
        help="Specify number to send text message to",
        type=str
    )

    # Message specification
    message_group = parser.add_mutually_exclusive_group()
    message_group.add_argument(
        "-m", "--message",
        help="Provide text to send",
        type=str
    )
    message_group.add_argument(
        "-s", "--shell",
        help="Message shell - read from stdin or editor",
        action="store_true"
    )

    # Optional arguments
    parser.add_argument(
        "-c", "--conf",
        help=f"Specify config file (Default: {DEFAULT_CONFIG_FILE})",
        type=str,
        default=os.path.expanduser(DEFAULT_CONFIG_FILE)
    )
    parser.add_argument(
        "-f", "--flash",
        help="Send as SMS 'Flash' message type",
        action="store_true"
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Display additional information",
        action="store_true"
    )
    parser.add_argument(
        "--force",
        help="Ignore bad permissions on config file",
        action="store_true"
    )
    parser.add_argument(
        "--dummy",
        help="Dummy mode - no message will be sent",
        action="store_true"
    )
    parser.add_argument(
        "-e", "--editor",
        help="Use $EDITOR to edit text message",
        action="store_true"
    )
    parser.add_argument(
        "-l", "--log-enabled",
        help="Enable/disable logging (true/false, default: true)",
        type=str,
        choices=['true', 'false'],
        default='true'
    )

    return parser.parse_args()


def get_message(args: argparse.Namespace) -> str:
    """
    Get message from appropriate source.

    Args:
        args: Parsed command-line arguments

    Returns:
        Message text
    """
    if args.message:
        return args.message
    elif args.shell:
        if args.editor:
            return MessageInput.from_editor(args.verbose)
        else:
            return MessageInput.from_stdin()
    else:
        print("Error: Must specify message with -m or use -s for shell input")
        sys.exit(1)


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code
    """
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(args.verbose)

    try:
        # Load configuration
        config = Config(args.conf, force_perms=args.force)

        # Get credentials from config
        user = config.get('credentials', 'user')
        password = config.get('credentials', 'password')
        api_id = config.get('credentials', 'api_id')
        sender_id = config.get('credentials', 'sender_id')
        callback = config.get_int('settings', 'callback', fallback=0)

        # Determine destination
        if args.abname:
            destination = config.get_addressbook_entry(args.abname)
        elif args.number:
            destination = args.number
        else:
            print("Error: No destination specified. Use -a or -n")
            return 1

        # Get message
        message = get_message(args)

        # Validate message length early (before sending)
        concat_no = ClickatellAPI._calculate_concat(message)

        if args.verbose:
            print(f"Message length: {len(message)} chars, Concat: {concat_no}")

        # Determine message type
        message_type = "SMS_FLASH" if args.flash else "SMS_TEXT"

        # Setup logging
        log_enabled = args.log_enabled == 'true'
        sms_logger = SMSLogger(DEFAULT_LOG_FILE, enabled=log_enabled)

        # Send message
        with ClickatellAPI(user, password, api_id, sender_id, callback) as api:
            # Authenticate only if not in dummy mode
            if not args.dummy:
                api.authenticate()

                # Send message
                success, response = api.send_message(
                    destination,
                    message,
                    message_type,
                    dry_run=False
                )
            else:
                # Dummy mode - skip authentication and sending
                logger.info("Dummy mode enabled - skipping authentication and send")
                success = True
                response = "Dummy mode - no message sent"
                print("Dummy mode set. No message sent.")

            # Log the message
            sms_logger.log_message(destination, message, success, response)

            # Display results
            if args.verbose:
                print(f"Status: {'Success' if success else 'Failed'}")
                print(f"Response: {response}")

            return 0 if success else 1

    except ClickatellError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
