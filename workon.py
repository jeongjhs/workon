"""
CJ World Login and Authentication Script

This script logs into CJ World and obtains an authenticated session.
Returns a requests.Session object with SSO authentication completed for reserve.cjenm.com.
"""

import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

load_dotenv()


class CJWorldAuthenticator:
    """CJ World Authentication Class"""

    def __init__(self, username: str, password: str):
        """
        Args:
            username: CJ World user ID
            password: CJ World password
        """
        self.session = requests.Session()
        self.username = username
        self.password = password

        # CJ World URLs
        self.login_url = "https://cj.cj.net/PT/login.aspx?sLang=KOR"
        self.main_url = "https://cj.cj.net/PT/PortalBuilder/main_frame.aspx"
        self.sso_page_url = "https://cj.cj.net/NPT/PortalBuilder/Framework/contents_system.aspx?SYSTEM_ID=SY7c88ddea-815f-42d6-90c6-064663262c6a&CONTENTS_ID=EPCT1639&CONTROL_MODE=FULL"
        self.sso_url = "https://reserve.cjenm.com/sso.fo"

    def authenticate(self) -> requests.Session:
        """
        Performs CJ World login and SSO authentication.

        Returns:
            Authenticated requests.Session object

        Raises:
            Exception: On login failure
        """
        print("[1/5] Accessing login page...")
        self._init_session()

        print("[2/5] Logging into CJ World...")
        self._login()

        print("[3/5] Accessing main page...")
        self._access_main_page()

        print("[4/5] Getting SSO token...")
        cjworld_id = self._get_sso_token()

        print("[5/5] Authenticating to reserve.cjenm.com...")
        self._sso_authenticate(cjworld_id)

        print("Authentication completed!")
        return self.session

    def _init_session(self):
        """Initialize session by accessing login page"""
        self.session.get(self.login_url)

    def _login(self):
        """Login to CJ World"""
        login_data = {
            'txtID': self.username,
            'txtPWD': self.password,
        }
        login_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': self.login_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = self.session.post(
            self.login_url,
            data=login_data,
            headers=login_headers,
            allow_redirects=False
        )

        # Check login failure (additional validation can be added if needed)
        if response.status_code not in [200, 302]:
            raise Exception(f"Login failed: HTTP {response.status_code}")

    def _access_main_page(self):
        """Access main page"""
        self.session.get(self.main_url)

    def _get_sso_token(self) -> str:
        """Extract cjworld_id token from SSO page"""
        response = self.session.get(self.sso_page_url)
        soup = BeautifulSoup(response.text, 'html.parser')

        form = soup.find('form', {'action': self.sso_url})
        if not form:
            raise Exception("Cannot find SSO form")

        cjworld_id_input = form.find('input', {'name': 'cjworld_id'})
        if not cjworld_id_input:
            raise Exception("Cannot find cjworld_id")

        cjworld_id = cjworld_id_input.get('value')
        if not cjworld_id:
            raise Exception("cjworld_id value is empty")

        return cjworld_id

    def _sso_authenticate(self, cjworld_id: str):
        """Authenticate to reserve.cjenm.com via SSO"""
        sso_data = {
            'cjworld_id': cjworld_id
        }
        self.session.post(self.sso_url, data=sso_data)

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
        from datetime import datetime, timedelta
        import json
        import holidays

        # Calculate reservation date
        reserve_date = datetime.now() + timedelta(days=days_ahead)
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

        # If date is even, try 004-001 first; if odd, try 004-002 first
        if day % 2 == 0:
            primary_seat = "004-001"
            secondary_seat = "004-002"
        else:
            primary_seat = "004-002"
            secondary_seat = "004-001"

        print(f"Primary seat: {primary_seat}")
        print(f"Secondary seat: {secondary_seat} (if primary fails)")

        # Access base office page
        print("\n[1/3] Accessing base office page...")
        base_office_url = "https://cj.cj.net/conf/autonomousseat/user/baseoffice.aspx"
        self.session.get(base_office_url)

        # First attempt
        print(f"\n[2/3] Attempting to reserve seat {primary_seat}...")
        success = self._try_reserve(date_str, primary_seat, start_time, end_time)

        if success:
            print(f"Successfully reserved seat {primary_seat}!")
            return True

        # Second attempt
        print(f"\n[3/3] Attempting to reserve seat {secondary_seat}...")
        success = self._try_reserve(date_str, secondary_seat, start_time, end_time)

        if success:
            print(f"Successfully reserved seat {secondary_seat}!")
            return True
        else:
            print(f"Failed to reserve both seats")
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

    if not username or not password:
        print("Error: Please set CJ_USERNAME and CJ_PASSWORD environment variables")
        print("\n.env file example:")
        print("CJ_USERNAME=your_username")
        print("CJ_PASSWORD=your_password")
        return

    try:
        # Authenticate
        authenticator = CJWorldAuthenticator(username, password)
        session = authenticator.authenticate()

        # Reserve seat
        success = authenticator.reserve_seat(days_ahead=14, start_time="08:00", end_time="17:00")

        if success:
            print("\n" + "="*50)
            print("Seat reservation completed!")
            print("="*50)
        else:
            print("\n" + "="*50)
            print("Seat reservation failed.")
            print("="*50)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
