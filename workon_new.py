"""
CJ World Login and Authentication Script (External Network)

This script logs into CJ World using external network authentication method.
"""

import os
import re
import time
import email
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from imapclient import IMAPClient

load_dotenv()


class CJWorldAuthenticator:
    """CJ World Authentication Class for External Network"""

    def __init__(self, username: str, password: str):
        """
        Args:
            username: CJ World user ID
            password: CJ World password
        """
        self.session = requests.Session()
        self.username = username
        self.password = password

        # CJ World URLs for external network authentication
        self.mail_cert_url = "https://cj.cj.net/PT/Anonymity/Account/mail_certification_main.aspx?sLang=KOR"
        self.sms_cert_issue_url = "https://cj.cj.net/PT/Anonymity/Account/sms_certification_issue.aspx?itype=mail&sLang=KOR"

    def authenticate(self) -> requests.Session:
        """
        Performs CJ World login via external network authentication.

        Returns:
            Authenticated requests.Session object

        Raises:
            Exception: On login failure
        """
        print("[1/4] Initializing session...")
        self._init_session()

        print("[2/4] Submitting credentials...")
        self._submit_credentials()

        print("[3/4] Requesting authentication code...")
        # Store timestamp before requesting code
        self.request_timestamp = time.time()
        self._request_auth_code()

        return self.session

    def _init_session(self):
        """Initialize session by accessing mail certification page"""
        response = self.session.get(self.mail_cert_url)

        # Parse ASP.NET state tokens
        soup = BeautifulSoup(response.text, 'html.parser')
        self.viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        self.viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        self.event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        print(f"  ✓ Session initialized")

    def _submit_credentials(self):
        """Submit credentials to mail certification page"""
        # Payload for credential submission using parsed tokens
        payload = {
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstate_generator,
            "__EVENTVALIDATION": self.event_validation,
            "hid_chk_flag": "N",
            "txtEmailAlias": self.username,
            "txtPWD": self.password,
            "__EVENTTARGET": "tbtnConfirm",
            "__EVENTARGUMENT": ""
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.mail_cert_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = self.session.post(
            self.mail_cert_url,
            data=payload,
            headers=headers,
            allow_redirects=True
        )

        if response.status_code not in [200, 302]:
            raise Exception(f"Credential submission failed: HTTP {response.status_code}")

        # Parse new tokens from response
        soup = BeautifulSoup(response.text, 'html.parser')
        viewstate_input = soup.find('input', {'name': '__VIEWSTATE'})
        if viewstate_input:
            self.viewstate = viewstate_input['value']
            self.viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
            self.event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        print(f"  ✓ Credentials submitted")

    def _request_auth_code(self):
        """Request authentication code via email"""
        # Payload for authentication code request using parsed tokens
        payload = {
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstate_generator,
            "__EVENTVALIDATION": self.event_validation,
            "txtAnswer": "",
            "MailtxtAnswer": "",
            "mcjw_txtAnswer": "",
            "hid_email_alias": self.username,
            "hid_user_chk": self.password,
            "bHighScreen": "",
            "hid_chk_flag": "N",
            "hid_typechk": "1",
            "hid_mcjwuser": "0",
            "hid_smstext": "+82-10-2777-0962",
            "hid_mailtext": f"{self.username}@mnetplus.world",
            "hid_smschk": "1",
            "hid_mailchk": "1",
            "__EVENTTARGET": "MailtbtnSubmit2",
            "__EVENTARGUMENT": ""
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.mail_cert_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = self.session.post(
            self.sms_cert_issue_url,
            data=payload,
            headers=headers
        )

        if response.status_code != 200:
            raise Exception(f"Authentication code request failed: HTTP {response.status_code}")

        # Parse tokens from the response for auth code submission
        soup = BeautifulSoup(response.text, 'html.parser')
        viewstate_input = soup.find('input', {'name': '__VIEWSTATE'})
        if viewstate_input:
            self.viewstate = viewstate_input['value']
            self.viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
            self.event_validation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        print(f"  ✓ Code requested")

    def get_auth_code_from_gmail(self, gmail_address: str, gmail_app_password: str, max_wait_seconds: int = 60) -> str:
        """
        Fetch authentication code from Gmail using IMAP

        Args:
            gmail_address: Gmail email address
            gmail_app_password: Gmail app password (16-digit)
            max_wait_seconds: Maximum seconds to wait for email (default: 60)

        Returns:
            6-digit authentication code

        Raises:
            Exception: If email not found or code extraction fails
        """
        print(f"Waiting for email (max {max_wait_seconds} seconds)...")

        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            try:
                # Connect to Gmail IMAP server
                with IMAPClient('imap.gmail.com', ssl=True) as client:
                    client.login(gmail_address, gmail_app_password)
                    client.select_folder('INBOX')

                    # Search for emails from jeongjhs@cj.net with "Certification Number" in subject
                    messages = client.search(['FROM', 'jeongjhs@cj.net', 'SUBJECT', 'Certification Number'])

                    if messages:
                        # Check messages from newest to oldest
                        for msg_id in reversed(messages):
                            raw_message = client.fetch([msg_id], ['INTERNALDATE', 'RFC822'])

                            # Get email received time
                            email_date = raw_message[msg_id][b'INTERNALDATE']
                            email_timestamp = email_date.timestamp()

                            # Only process emails received after request timestamp
                            if email_timestamp > self.request_timestamp:
                                # Parse email properly using email library
                                email_bytes = raw_message[msg_id][b'RFC822']
                                email_message = email.message_from_bytes(email_bytes)

                                # Extract email body (handle both single part and multipart)
                                email_body = ""
                                if email_message.is_multipart():
                                    for part in email_message.walk():
                                        content_type = part.get_content_type()
                                        content_disposition = str(part.get("Content-Disposition"))

                                        if "attachment" not in content_disposition:
                                            if content_type == "text/plain" or content_type == "text/html":
                                                try:
                                                    body = part.get_payload(decode=True)
                                                    if body:
                                                        email_body += body.decode('utf-8', errors='ignore')
                                                except:
                                                    pass
                                else:
                                    # Single part email
                                    body = email_message.get_payload(decode=True)
                                    if body:
                                        email_body = body.decode('utf-8', errors='ignore')

                                # Extract 6-digit code using regex
                                match = re.search(r'External Mail Certification Number\s*[:：]\s*(\d{6})', email_body)

                                if match:
                                    auth_code = match.group(1)
                                    print(f"  ✓ Found authentication code: {auth_code}")
                                    return auth_code

            except Exception as e:
                print(f"  Error: {e}")

            # Wait before retrying
            time.sleep(5)
            elapsed = int(time.time() - start_time)
            print(f"  Waiting... ({elapsed}s)")

        raise Exception("Timeout: Could not retrieve authentication code from Gmail")

    def _submit_auth_code(self, auth_code: str):
        """Submit authentication code to complete login"""
        print("Submitting authentication code...")

        # Use the tokens from _request_auth_code response
        # Prepare payload with authentication code
        payload = {
            "__VIEWSTATE": self.viewstate,
            "__VIEWSTATEGENERATOR": self.viewstate_generator,
            "__EVENTVALIDATION": self.event_validation,
            "txtAnswer": "",
            "MailtxtAnswer": auth_code,  # Insert the authentication code here
            "mcjw_txtAnswer": "",
            "hid_email_alias": self.username,
            "hid_user_chk": self.password,
            "bHighScreen": "1",
            "hid_chk_flag": "N",
            "hid_typechk": "1",
            "hid_mcjwuser": "0",
            "hid_smstext": "+82-10-2777-0962",
            "hid_mailtext": f"{self.username}@mnetplus.world",
            "hid_smschk": "1",
            "hid_mailchk": "1",
            "__EVENTTARGET": "MailtbtnSubmit",
            "__EVENTARGUMENT": ""
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.sms_cert_issue_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = self.session.post(
            self.sms_cert_issue_url,
            data=payload,
            headers=headers
        )

        print(f"  Response code: {response.status_code}")

        if response.status_code != 200:
            raise Exception(f"Auth code submission failed: HTTP {response.status_code}")

        print("  ✓ Authentication completed!")

    def reserve_seat(self, days_ahead: int = 14, start_time: str = "08:00", end_time: str = "15:00"):
        """
        Reserve autonomous seat

        Args:
            days_ahead: How many days ahead to reserve (default: 14 days)
            start_time: Start time
            end_time: End time

        Returns:
            Reservation success status
        """
        from datetime import datetime, timedelta, timezone
        import json
        import holidays

        # Calculate reservation date using KST (UTC+9)
        kst = timezone(timedelta(hours=9))
        reserve_date = datetime.now(kst) + timedelta(days=days_ahead)
        date_str = reserve_date.strftime("%Y-%m-%d")
        day = reserve_date.day

        print(f"\n=== Starting Seat Reservation ===")

        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday = reserve_date.weekday()
        weekday_name = weekday_names[weekday]

        print(f"Reservation date: {date_str} ({weekday_name}, {days_ahead} days ahead)")

        # 1. Check weekday (only Wed/Thu/Fri)
        if weekday not in [2, 3, 4]:  # Wednesday=2, Thursday=3, Friday=4
            print(f"Skipping: {date_str} is {weekday_name}. Only reserving Wed/Thu/Fri.")
            return False

        # 2. Check Korean holidays
        kr_holidays = holidays.KR()
        if reserve_date.date() in kr_holidays:
            holiday_name = kr_holidays.get(reserve_date.date())
            print(f"Skipping: {date_str} is a holiday ({holiday_name}).")
            return False

        # 3. Check 2nd and 4th Friday of the month
        if weekday == 4:  # Friday
            # Calculate which Friday of the month
            week_of_month = (reserve_date.day - 1) // 7 + 1
            if week_of_month in [2, 4]:
                print(f"Skipping: {date_str} is the {week_of_month}th Friday of the month.")
                return False

        print(f"Time: {start_time} ~ {end_time}")

        # Define seats in priority order
        seats_to_try = ["004-001", "004-005", "004-002", "004-006", "004-003", "004-007", "004-004", "004-008"]

        print(f"Will try seats in order: {', '.join(seats_to_try)}")

        # Access base office page
        print("\nAccessing base office page...")
        base_office_url = "https://cj.cj.net/conf/autonomousseat/user/baseoffice.aspx"
        self.session.get(base_office_url)

        # Try each seat in order
        for i, seat_id in enumerate(seats_to_try, 1):
            print(f"\n[{i}/{len(seats_to_try)}] Attempting to reserve seat {seat_id}...")
            success = self._try_reserve(date_str, seat_id, start_time, end_time)

            if success:
                print(f"Successfully reserved seat {seat_id}!")
                return True

        print(f"Failed to reserve any of the {len(seats_to_try)} seats")
        return False

    def _try_reserve(self, date: str, seat_id: str, start_time: str, end_time: str) -> bool:
        """Attempt to reserve a seat"""
        import json

        # Pad seatID to 36 characters with spaces
        padded_seat_id = seat_id.ljust(36)

        payload = {
            "email_alias": self.username,
            "reserveID": "",
            "seatID": padded_seat_id,
            "r_day": date,
            "r_st": start_time,
            "r_et": end_time,
            "cel1": "010",
            "cel2": "2777",
            "cel3": "0962",
            "toShare": "",
            "type": "C"
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }

        reserve_api_url = "https://cj.cj.net/CONF/Common/WebService/WSBaseOffice.asmx/setSeatReserve"

        try:
            response = self.session.post(
                reserve_api_url,
                json=payload,
                headers=headers
            )

            print(f"  Response code: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"  Response: {json.dumps(result, ensure_ascii=False)}")

                    # Check success: {"d": "Y"} means success
                    if result.get("d") == "Y":
                        return True

                    return False
                except json.JSONDecodeError:
                    print(f"  Response text: {response.text[:200]}")
                    return "success" in response.text.lower() or "Y" in response.text
            else:
                print(f"  Error: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"  Exception: {e}")
            return False


def main():
    """Main execution function"""
    # Load credentials from environment variables
    username = os.getenv('CJ_USERNAME')
    password = os.getenv('CJ_PASSWORD')
    gmail_address = os.getenv('GMAIL_ADDRESS')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')

    if not username or not password:
        print("Error: Please set CJ_USERNAME and CJ_PASSWORD environment variables")
        print("\n.env file example:")
        print("CJ_USERNAME=your_username")
        print("CJ_PASSWORD=your_password")
        return

    if not gmail_address or not gmail_app_password:
        print("Error: Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD environment variables")
        print("\nTo get Gmail app password:")
        print("1. Go to https://myaccount.google.com/")
        print("2. Security > 2-Step Verification (enable if not already)")
        print("3. Security > App passwords")
        print("4. Generate a new app password for 'Mail'")
        print("5. Copy the 16-digit password to .env file")
        return

    try:
        # Authenticate and request code
        authenticator = CJWorldAuthenticator(username, password)
        session = authenticator.authenticate()

        # Get authentication code from Gmail
        print("[4/4] Retrieving authentication code from Gmail...")
        auth_code = authenticator.get_auth_code_from_gmail(gmail_address, gmail_app_password)

        # Submit the authentication code to complete login
        authenticator._submit_auth_code(auth_code)

        print("\n" + "="*50)
        print("✓ Login completed successfully!")
        print("="*50)

        # Reserve seat
        success = authenticator.reserve_seat(days_ahead=14, start_time="08:00", end_time="17:00")

        if success:
            print("\n" + "="*50)
            print("✓ Seat reservation completed!")
            print("="*50)
        else:
            print("\n" + "="*50)
            print("Seat reservation skipped or failed.")
            print("="*50)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
