import path_finder
import os
from datetime import datetime, timedelta
import time
from DataPipeline.FileManager import FileManager # 추가
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class API():
    def __init__(self):
        
        self.cfg = path_finder.get_cfg()
        self.file_manager = FileManager()
        
        self.host = os.getenv("KIWOOM_MOCK_DOMAIN") if os.getenv("MOCK") else os.getenv("KIWOOM_DOMAIN")
        self.wws = os.getenv("KIWOOM_MOCK_WSS") if os.getenv("MOCK") else os.getenv("KIWOOM_WSS")
        
        self.app_key = os.getenv("KIWOOM_API_KEY")
        self.secret_key = os.getenv("KIWOOM_SECRET_KEY")
        
        self.params = self._load_api_params()
        
        self.token = None
        self.expires_at = None
        
        # self.error_code = None
        
        # .env 체크
        if not self.app_key or not self.secret_key :
            print("\n[설정 오류] .env 파일에서 KIWOOM_API_KEY와 KIWOOM_SECRET_KEY를 확인해주세요.")
            
        # self.chart_manager = ChartManager()
        # self.account_manager = AccountManager()
        
        # self.order_manager = OrderManager()
        # self.realtime_manager = RealtimeManager()
        
        self._load_token() # 토큰파일 로드
        
        # self._load_error_code() # 에러코드 파일 로드
        
    # def _load_error_code(self):
    #     """에러코드 파일을 로드합니다."""
    #     path = self.cfg.ERROR_CODE_PATH
    #     data = self.file_manager.load(path)
        
    #     if data:
    #         try:
    #             self.error_code = data
    #         except Exception as e:
    #             print(f"⚠️ [Error] 에러코드 데이터 파싱 오류: {e}")
        
    def _requests_post(self, url, headers, body, max_retries=3):
        """
        공통 POST 요청 처리 모듈 (재시도 및 에러 처리 포함)
        """
        for attempt in range(max_retries):
            try:
                res = requests.post(url, headers=headers, json=body, timeout=15)
                
                # 1. HTTP 429 (Too Many Requests) 처리
                if res.status_code == 429:
                    wait_time = (attempt + 1) * 2  # 시도 횟수가 늘어날수록 대기 시간 증가
                    print(f"🛑 [HTTP 429] 요청 과부하! {wait_time}초 대기 후 재시도합니다... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue  # 루프의 처음으로 돌아가 재요청
                
                # 2. 통신 성공 (200 OK)
                if res.status_code == 200:
                    data = res.json()
                    r_code = str(data.get("return_code", "-1"))
                    
                    # 2-A. 키움 앱 레벨 요청 제한 (Code 5) 처리
                    if r_code == "5":
                        wait_time = (attempt + 1) * 2
                        print(f"🛑 [Code 5] 키움 서버 한도 초과! {wait_time}초 대기 후 재시도... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    
                    # 2-B. 최종 성공 시 (Body와 Headers를 함께 반환)
                    if r_code == "0":
                        # 💡 핵심: 응답 바디(data)와 응답 헤더(res.headers)를 튜플로 반환합니다.
                        return data, res.headers
                    
                    print(f"⚠️ [App Error {r_code}] {data.get('return_msg')}")
                    return None, None
                
                # 3. 기타 HTTP 에러 (401, 404, 500 등)
                else:
                    print(f"❌ [HTTP Error {res.status_code}] {res.text}")
                    return None, None

            except requests.exceptions.RequestException as e:
                # 네트워크 끊김 등 물리적 통신 오류
                print(f"❌ [Network Error] {e}")
                time.sleep(1)
                
        return None, None  # 모든 재시도 실패 시
            
    def _get_params(self, id: str):
        """API 설정 정보를 가져오고 URL/Header/Body를 구성합니다."""
        api_info = self.params.get(id)
        if not api_info:
            print(f"❌ [오류] params.json에 '{id}' 키가 없습니다.")
            return None

        # 💡 1. URL 결정 (웹소켓 여부에 따른 분기)
        endpoint = api_info.get("endpoint", "")
        # 웹소켓 연결의 기준이 되는 'ws_base'인 경우에만 wws 주소를 사용합니다.
        if id == "ws_base":
            base_url = self.wws
        else:
            base_url = self.host
        
        url = base_url + endpoint
        
        # 💡 2. 템플릿 복사 (원본 변조 방지)
        headers = api_info.get("headers", {}).copy()
        body = api_info.get("body", {}).copy()
        
        # 3. 인증 정보 주입
        if "authorization" in headers:
            token = self.get_token()
            headers["authorization"] = f"Bearer {token}"
        
        if body is not None:
            body["appkey"] = self.app_key
            body["secretkey"] = self.secret_key
        
        return url, headers, body
           
    def _load_api_params(self):
        """FileManager를 사용하여 api.json을 읽어옵니다."""
        path = self.cfg.API_PATH
        data = self.file_manager.load(path) # 💡 json.load 대신 FM 사용
        
        if data is None:
            print(f"❌ [오류] {path} 파일을 찾을 수 없거나 형식이 잘못되었습니다.")
        return data
    
    def _load_token(self):
        """FileManager를 사용하여 저장된 토큰을 읽어옵니다."""
        # 💡 [변경] 직접 파일을 열지 않고 FM의 load 기능을 사용합니다.
        path = self.cfg.TOKEN_PATH
        data = self.file_manager.load(path)
        
        if data:
            try:
                # 토큰값과 만료시간 세팅
                self.token = data.get("token")
                exp_str = data.get("expires_at")
                
                if exp_str:
                    # isoformat 문자열을 datetime 객체로 복원
                    self.expires_at = datetime.fromisoformat(exp_str)
                # 토큰 검사, 만료되었으면 재발급
                if not self.is_valid():
                    self.issue_token()                    
                        
            except Exception as e:
                print(f"⚠️ [Token] 토큰 데이터 파싱 오류: {e}")

    def is_valid(self):
        """토큰이 존재하고, 만료 시간이 지나지 않았는지 확인합니다."""
        if not self.token or not self.expires_at:
            return False
        return datetime.now() < self.expires_at

    def get_token(self):
        """외부에서 토큰을 요청할 때 사용합니다. 알아서 유효성을 판단합니다."""
        if self.is_valid():
            return self.token
        else:
            print("🔄 [Token] 토큰이 없거나 만료되었습니다. 재발급을 시도합니다...")
            # 재발급, 
            self.issue_token()
        
    def issue_token(self):
        """[au10001] 서버와 통신하여 토큰을 발급받습니다."""
        url, headers, body = self._get_params("au10001")
        data, _ = self._requests_post(url, headers, body)
        # 💡 [필수] 데이터가 None인지 확인 (발급 실패 시 에러 방지)
        if data:
            self._save_token(data["token"], data["expires_dt"])
        else:
            print("❌ [Token] 토큰 발급에 실패하여 저장할 수 없습니다.")
        
    def _save_token(self, token, expires_dt_str):
        """발급받은 토큰을 FileManager를 통해 저장합니다."""
        self.token = token
        
        # 만료 시간 계산 (안전하게 5분 차감)
        dt_obj = datetime.strptime(expires_dt_str, "%Y%m%d%H%M%S")
        self.expires_at = dt_obj - timedelta(seconds=300)
        
        # 💡 [변경] FM의 save 기능을 사용합니다. (디렉토리 생성까지 자동 처리)
        token_data = {
            "token": self.token,
            "expires_at": self.expires_at.isoformat()
        }
        path = self.cfg.TOKEN_PATH
        self.file_manager.save(token_data, path)
            
        print(f"🔑 [Token] 새 토큰 저장 완료 (만료: {self.expires_at.strftime('%Y-%m-%d %H:%M:%S')})")

    def revoke_token(self):
        """[au10002] 서버 및 로컬에서 토큰을 폐기합니다."""
        if not self.token:
            print("⚠️ [Token] 폐기할 토큰이 없습니다.")
            return
            
        url, headers, body = self._get_params("au10002")
        data, _ = self._requests_post(url, headers, body)
        
        if data:
            if data["return_code"] == "0":
                print("✅ [Token] 서버에서 토큰 폐기 완료")
        
if __name__ == '__main__':
    api = API()
    url, headers, body = api._get_params("au10001")
    
    print(f"url : {url}")
    print(f"headers : {headers}")
    print(f"body : {body}")
    