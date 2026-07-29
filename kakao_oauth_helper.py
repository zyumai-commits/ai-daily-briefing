"""Run once on your PC to obtain a Kakao refresh token. Never commit or share the output."""
import secrets, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests

REST_API_KEY=input("Kakao REST API key: ").strip()
CLIENT_SECRET=input("Kakao Login Client Secret (Enter if unused): ").strip()
REDIRECT_URI="http://localhost:8765/callback"
state=secrets.token_urlsafe(24); received={}
class Callback(BaseHTTPRequestHandler):
    def do_GET(self):
        query=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if query.get("state",[None])[0] != state: self.send_error(400,"Invalid state"); return
        received["code"]=query.get("code",[None])[0]
        self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers()
        self.wfile.write("<h2>인증 완료</h2><p>터미널로 돌아가 refresh token을 복사하세요.</p>".encode())
    def log_message(self,*args): pass
server=HTTPServer(("127.0.0.1",8765),Callback)
params={"client_id":REST_API_KEY,"redirect_uri":REDIRECT_URI,"response_type":"code","scope":"talk_message","state":state}
url="https://kauth.kakao.com/oauth/authorize?"+urllib.parse.urlencode(params)
print("\n브라우저에서 로그인·동의가 열립니다. 열리지 않으면 이 주소를 브라우저에 붙여넣으세요:\n",url)
webbrowser.open(url); server.socket.settimeout(300); server.handle_request()
if not received.get("code"): raise RuntimeError("No authorization code received.")
data={"grant_type":"authorization_code","client_id":REST_API_KEY,"redirect_uri":REDIRECT_URI,"code":received["code"]}
if CLIENT_SECRET: data["client_secret"]=CLIENT_SECRET
response=requests.post("https://kauth.kakao.com/oauth/token",data=data,timeout=30); response.raise_for_status()
print("\nKAKAO_REFRESH_TOKEN (GitHub Secret에만 저장, 채팅에 붙여넣지 마세요):\n"+response.json()["refresh_token"])
