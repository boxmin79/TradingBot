import path_finder
import asyncio
import json
import websockets
from API.API import API  

class RealtimeAPI(API):
    def __init__(self):
        super().__init__()
        self.ws = None
        self.is_running = False

    async def connect(self):
        """웹소켓 서버 연결 및 로그인 절차 수행"""
        url, _, _ = self._get_params("ws_base")
        
        try:
            # 1. 서버 연결 (websockets 16.0 기준 headers 인자 사용)
            self.ws = await websockets.connect(url)
            self.is_running = True
            print(f"🌐 [Websocket] 연결 성공: {url}")

            # 2. 로그인 패킷 전송 (예제 로직 반영)
            await self._send_login_packet()
            
            # 3. 메시지 수신 루프 시작
            await self._listen()
            
        except Exception as e:
            print(f"❌ [Websocket] 연결 오류: {e}")
            self.is_running = False
            
    async def _send_login_packet(self):
        """[LOGIN] 상위 클래스의 토큰을 사용하여 로그인 수행"""
        token = self.get_token() # API 클래스의 토큰 관리 기능 활용
        login_msg = {
            "trnm": "LOGIN",
            "token": token
        }
        await self.ws.send(json.dumps(login_msg))
        print("🔑 [Websocket] 로그인 패킷 전송 완료")
        
    async def subscribe(self, tr_id, stock_codes):
        """[REG] 실시간 데이터 구독 요청"""
        _, _, body = self._get_params("ws_base")
        
        body["data"] = [{
            "item": stock_codes,
            "type": [tr_id]
        }]
        
        await self.ws.send(json.dumps(body))
        print(f"🔔 [Websocket] 구독 요청: {tr_id} -> {stock_codes}")

    async def _listen(self):
        """수신 및 PING-PONG 처리 루프"""
        while self.is_running:
            try:
                message = await self.ws.recv()
                res = json.loads(message)
                trnm = res.get("trnm")

                # 💡 예제 핵심: PING 수신 시 그대로 송신 (연결 유지)
                if trnm == "PING":
                    await self.ws.send(json.dumps(res))
                
                # 로그인 결과 확인
                elif trnm == "LOGIN":
                    if res.get("return_code") != 0:
                        print(f"❌ 로그인 실패: {res.get('return_msg')}")
                        await self.close()
                    else:
                        print("✅ 로그인 성공")

                # 실시간 시세 데이터 처리
                else:
                    self.on_message(res)

            except websockets.ConnectionClosed:
                print("🛑 서버와 연결이 종료되었습니다.")
                break
            
    def on_message(self, data):
        """수신된 데이터를 분석하여 필요한 정보만 추출합니다."""
        trnm = data.get("trnm")

        # 1. 구독 확인 응답 처리
        if trnm == "REG":
            print("📢 [Websocket] 종목 구독이 정상적으로 시작되었습니다.")
            return

        # 2. 실시간 데이터(Body) 파싱
        # 실시간 데이터는 보통 'body' 키 안에 정보가 담겨 옵니다.
        body = data.get("body")
        if body:
            stk_cd = body.get("stk_cd")    # 종목코드 (005930 등)
            price = body.get("stk_prc")     # 현재가
            vol = body.get("cnt_vol")       # 누적거래량
            time = body.get("trde_tm")      # 체결시간
            
            print(f"📈 [{stk_cd}] 시간: {time} | 현재가: {price} | 거래량: {vol}")
            
            # TODO: 여기서 self.file_manager를 사용하여 데이터를 캐싱하거나 
            # Pandas DataFrame에 추가하는 로직을 넣을 수 있습니다.

    async def close(self):
        self.is_running = False
        if self.ws:
            await self.ws.close()
            
# --- 실행 테스트 ---
if __name__ == "__main__":
    async def main():
        rt_api = RealtimeAPI()
        
        # 1. 서버 연결과 동시에 수신 루프 실행 (태스크 생성)
        ws_task = asyncio.create_task(rt_api.connect())
        
        # 연결될 때까지 잠시 대기
        await asyncio.sleep(2)
        
        if rt_api.is_running:
            # 2. 삼성전자(005930), SK하이닉스(000660) 체결(0B) 구독
            await rt_api.subscribe("0B", ["005930", "000660"])
            
            # 3. 30초간 데이터 수신 유지 후 종료
            await asyncio.sleep(30)
            await rt_api.close()
        
        await ws_task

    asyncio.run(main())