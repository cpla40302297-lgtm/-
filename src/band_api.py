"""
네이버 밴드 Open API 연동 모듈
Band Open API: https://developers.band.us/develop/guide/api
"""
import requests
import json
import os
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time


class BandAPIError(Exception):
    """Band API 에러"""
    pass


class BandAPI:
    """네이버 밴드 Open API 클라이언트"""
    
    BASE_URL = "https://openapi.band.us"
    AUTH_URL = "https://auth.band.us/oauth2/authorize"
    TOKEN_URL = "https://auth.band.us/oauth2/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:9988/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self._auth_code = None
        self._auth_event = threading.Event()
    
    # ─── OAuth2 인증 ───────────────────────────────────────────
    def get_auth_url(self) -> str:
        """OAuth2 인증 URL 생성"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def _start_callback_server(self):
        """OAuth2 콜백 서버 실행 (임시)"""
        api_instance = self
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                if "code" in params:
                    api_instance._auth_code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = """
                    <html><body style='font-family:sans-serif;text-align:center;margin-top:80px;background:#f0f8ff;'>
                    <h2 style='color:#03c75a;'>✅ 인증 성공!</h2>
                    <p>이 창을 닫고 프로그램으로 돌아가세요.</p>
                    </body></html>
                    """
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Authentication failed")
                
                api_instance._auth_event.set()
            
            def log_message(self, format, *args):
                pass  # 로그 억제
        
        server = HTTPServer(("localhost", 9988), CallbackHandler)
        server.timeout = 1
        
        # 타임아웃 60초
        start_time = time.time()
        while not self._auth_event.is_set():
            server.handle_request()
            if time.time() - start_time > 120:
                break
        server.server_close()
    
    def authenticate_with_browser(self, callback=None) -> bool:
        """브라우저를 통한 OAuth2 인증 (자동 콜백 처리)"""
        self._auth_code = None
        self._auth_event.clear()
        
        # 콜백 서버 스레드 시작
        server_thread = threading.Thread(target=self._start_callback_server, daemon=True)
        server_thread.start()
        
        time.sleep(0.3)
        
        # 브라우저 열기
        auth_url = self.get_auth_url()
        webbrowser.open(auth_url)
        
        if callback:
            callback("브라우저에서 밴드 로그인 후 인증해 주세요...")
        
        # 인증 대기 (최대 120초)
        self._auth_event.wait(timeout=120)
        
        if self._auth_code:
            return self.exchange_code_for_token(self._auth_code)
        return False
    
    def exchange_code_for_token(self, code: str) -> bool:
        """인증 코드를 액세스 토큰으로 교환"""
        try:
            params = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
            }
            resp = requests.get(self.TOKEN_URL, params=params, timeout=10)
            data = resp.json()
            
            if "access_token" in data:
                self.access_token = data["access_token"]
                return True
            else:
                raise BandAPIError(f"토큰 발급 실패: {data}")
        except Exception as e:
            raise BandAPIError(f"토큰 교환 오류: {str(e)}")
    
    def set_access_token(self, token: str):
        """액세스 토큰 직접 설정"""
        self.access_token = token
    
    def _get(self, endpoint: str, params: dict = None) -> dict:
        """GET 요청"""
        if not self.access_token:
            raise BandAPIError("액세스 토큰이 없습니다. 먼저 인증하세요.")
        
        url = f"{self.BASE_URL}{endpoint}"
        p = {"access_token": self.access_token}
        if params:
            p.update(params)
        
        try:
            resp = requests.get(url, params=p, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("result_code") != 1:
                raise BandAPIError(f"API 오류 (code={data.get('result_code')}): {data}")
            return data
        except requests.RequestException as e:
            raise BandAPIError(f"네트워크 오류: {str(e)}")
    
    def _post(self, endpoint: str, data: dict = None, files=None) -> dict:
        """POST 요청"""
        if not self.access_token:
            raise BandAPIError("액세스 토큰이 없습니다. 먼저 인증하세요.")
        
        url = f"{self.BASE_URL}{endpoint}"
        payload = {"access_token": self.access_token}
        if data:
            payload.update(data)
        
        try:
            if files:
                resp = requests.post(url, data=payload, files=files, timeout=30)
            else:
                resp = requests.post(url, data=payload, timeout=15)
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("result_code") != 1:
                raise BandAPIError(f"API 오류 (code={result.get('result_code')}): {result}")
            return result
        except requests.RequestException as e:
            raise BandAPIError(f"네트워크 오류: {str(e)}")
    
    # ─── 사용자 정보 ───────────────────────────────────────────
    def get_profile(self) -> dict:
        """사용자 프로필 조회"""
        data = self._get("/v2/profile")
        return data.get("result_data", {})
    
    # ─── 밴드 목록 ────────────────────────────────────────────
    def get_bands(self) -> list:
        """가입한 밴드 목록 조회"""
        data = self._get("/v2.1/bands")
        return data.get("result_data", {}).get("bands", [])
    
    # ─── 게시물 작성 ──────────────────────────────────────────
    def write_post(self, band_key: str, content: str, do_push: bool = True, photo_keys: list = None) -> dict:
        """밴드에 게시물 작성"""
        payload = {
            "band_key": band_key,
            "content": content,
            "do_push": "true" if do_push else "false",
        }
        if photo_keys:
            # 이미지가 있을 경우 photo_keys 추가
            payload["photo_keys"] = json.dumps(photo_keys)
        
        data = self._post("/v2.2/band/post/create", payload)
        return data.get("result_data", {})
    
    # ─── 이미지 업로드 ────────────────────────────────────────
    def upload_photo(self, band_key: str, image_path: str) -> str:
        """이미지 업로드 후 photo_key 반환"""
        if not os.path.exists(image_path):
            raise BandAPIError(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        
        with open(image_path, "rb") as f:
            files = {"photo": (os.path.basename(image_path), f, "image/jpeg")}
            data = self._post(
                "/v2/band/photo/upload",
                {"band_key": band_key},
                files=files
            )
        return data.get("result_data", {}).get("photo_key", "")
    
    def is_authenticated(self) -> bool:
        """인증 여부 확인"""
        return bool(self.access_token)
    
    def verify_token(self) -> bool:
        """토큰 유효성 검증"""
        try:
            self.get_profile()
            return True
        except BandAPIError:
            return False
