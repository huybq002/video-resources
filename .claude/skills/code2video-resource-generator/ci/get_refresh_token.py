"""ONE-TIME, run on your own computer (not in CI): get the YouTube refresh token that upload_youtube.py needs.
1. Google Cloud Console -> create a project -> enable "YouTube Data API v3" -> OAuth consent screen (add yourself as test user)
   -> Credentials -> Create OAuth client ID -> type "Desktop app". Copy the client id and secret.
2. python get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>   (a browser opens; sign in with the channel's account and allow)
3. Store the printed values as GitHub repository secrets: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Scope requested: youtube.upload only (cannot read or delete anything).
"""
import http.server, sys, threading, urllib.parse, webbrowser
import requests

cid, secret = sys.argv[1], sys.argv[2]; PORT = 8765; redirect = f"http://localhost:{PORT}"; box = {}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query); box["code"] = q.get("code", [None])[0]
        self.send_response(200); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers(); self.wfile.write(b"OK, you can close this tab.")
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("localhost", PORT), H)
url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({"client_id": cid, "redirect_uri": redirect, "response_type": "code",
      "scope": "https://www.googleapis.com/auth/youtube.upload", "access_type": "offline", "prompt": "consent"})
print("Opening browser..."); webbrowser.open(url); t = threading.Thread(target=srv.handle_request); t.start(); t.join(300)
if not box.get("code"): sys.exit("no authorisation code received")
r = requests.post("https://oauth2.googleapis.com/token", data={"code": box["code"], "client_id": cid, "client_secret": secret, "redirect_uri": redirect, "grant_type": "authorization_code"}, timeout=60)
r.raise_for_status(); print("\nYT_CLIENT_ID    =", cid, "\nYT_CLIENT_SECRET=", secret, "\nYT_REFRESH_TOKEN=", r.json()["refresh_token"])
