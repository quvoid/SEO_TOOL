"""
generate_ga4_gsc_token.py

BEFORE RUNNING:
  GCP Console -> APIs & Services -> Credentials -> your OAuth 2.0 Client ID
  Add  http://localhost:8765  to "Authorised redirect URIs" -> SAVE
  Wait 30 seconds, then run this script.
"""

import http.server
import threading
import webbrowser
import urllib.parse
import os
import sys

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")

import config

CLIENT_ID     = config.USER_OAUTH_CLIENT_ID or ""
CLIENT_SECRET = config.USER_OAUTH_CLIENT_SECRET or ""
PORT          = 8765
REDIRECT_URI  = f"http://localhost:{PORT}"

if not CLIENT_ID or not CLIENT_SECRET:
    print("Error: USER_OAUTH_CLIENT_ID and USER_OAUTH_CLIENT_SECRET must be configured in secrets.toml before running this script.")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

# Local callback server
auth_code = None

class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#f0fdf4">
        <h2 style="color:#16a34a">Authorisation successful!</h2>
        <p>You can close this tab and return to the terminal.</p>
        </body></html>""")

    def log_message(self, *args):
        pass

server = http.server.HTTPServer(("localhost", PORT), _Handler)
thread = threading.Thread(target=server.handle_request)
thread.daemon = True
thread.start()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from google_auth_oauthlib.flow import Flow

flow = Flow.from_client_config(
    {
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI,
)

auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")

print("\n" + "=" * 65)
print("Opening browser - sign in with analytics.schbang@gmail.com")
print("(the account with GA4 + Search Console access)")
print("")
print("If browser does not open, paste this URL manually:")
print(auth_url)
print("=" * 65 + "\n")
webbrowser.open(auth_url)

print("Waiting for Google to redirect back (up to 120 seconds)...")
thread.join(timeout=120)

if not auth_code:
    print("")
    print("TIMED OUT - Most likely cause:")
    print("  http://localhost:8765 is NOT yet in your OAuth client's")
    print("  Authorised redirect URIs in GCP Console.")
    print("")
    print("Fix:")
    print("  1. Go to https://console.cloud.google.com/apis/credentials")
    print("  2. Click your OAuth 2.0 Client ID")
    print("  3. Add http://localhost:8765 under Authorised redirect URIs")
    print("  4. Click SAVE, wait 30 seconds, then run this script again.")
    raise SystemExit(1)

flow.fetch_token(code=auth_code)
creds = flow.credentials

print("")
print("=" * 65)
print("SUCCESS! Add this block to .streamlit/secrets.toml:")
print("")
print("[user_oauth]")
print(f'client_id     = "{CLIENT_ID}"')
print(f'client_secret = "{CLIENT_SECRET}"')
print(f'refresh_token = "{creds.refresh_token}"')
print("=" * 65)
print("")
print("Then restart the Streamlit app - GA4 + GSC will work with")
print("your analytics.schbang@gmail.com account.")
