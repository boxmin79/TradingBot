import path_finder
import pandas as pd
from API.API import API
from dotenv import load_dotenv

load_dotenv()

class AccountManager(API):
    def __init__(self):
        # 부모 클래스(API) 초기화: self.cfg, self.file_manager, self.token 등 세팅
        super().__init__()
        
    def get_account_list(self):
        """[ka00001] 보유한 계좌 번호 리스트를 반환합니다."""
        params = self._get_params("ka00001")
        if not params: return []
        
        url, headers, body = params
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고: 계좌 리스트는 'list' 키에 담겨 옵니다.
        if data:
            return data.get("acctNo", [])
        return []

    def get_deposit(self, qry_tp="2"):
        """
        [kt00001] 예수금 상세 현황을 조회합니다.
        Args:
            qry_tp (str): "2" (일반조회), "3" (추정조회)
        """
        params = self._get_params("kt00001")
        if not params: return {}
        
        url, headers, body = params
        body["qry_tp"] = qry_tp
        
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고 필드: entra(예수금), ord_alow_amt(주문가능금액), d2_entra(D+2예수금), uncla(미수금)
        if data:
            return {
                "예수금": int(data.get("entra", 0)),
                "주문가능금액": int(data.get("ord_alow_amt", 0)),
                "D+2예수금": int(data.get("d2_entra", 0)),
                "미수금": int(data.get("uncla", 0))
            }
        return {}

    def get_holdings(self, qry_tp="1"):
        """
        [kt00018] 계좌 평가 잔고 내역(보유 종목)을 가져옵니다.
        """
        params = self._get_params("kt00018")
        if not params: return pd.DataFrame()
        
        url, headers, body = params
        body.update({"qry_tp": qry_tp, "dmst_stex_tp": "KRX"})
        
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고: 보유 종목 리스트는 'output' 키에 배열로 들어옵니다.
        if data:
            raw_holdings = data.get("output", [])
            return self._preprocess_holdings(raw_holdings)
        return pd.DataFrame()

    def get_unexecuted_orders(self, stk_cd=""):
        """
        [ka10075] 미체결 요청 내역을 조회합니다.
        """
        params = self._get_params("ka10075")
        if not params: return pd.DataFrame()
        
        url, headers, body = params
        body.update({
            "all_stk_tp": "0" if stk_cd else "1", # 0:종목, 1:전체
            "stk_cd": stk_cd,
            "trde_tp": "0",
            "stex_tp": "0"
        })
        
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고: 미체결 리스트 키값은 'oso'입니다.
        if data:
            raw_list = data.get("oso", [])
            df = pd.DataFrame(raw_list)
            rename_map = {
                "ord_no": "order_no", "stk_cd": "code", "stk_nm": "name",
                "ord_qty": "order_qty", "ord_pric": "order_price", 
                "oso_qty": "unexecuted_qty", "io_tp_nm": "side"
            }
            return self._standardize_df(df, rename_map)
        return pd.DataFrame()

    def get_executed_orders(self, stk_cd=""):
        """
        [ka10076] 당일 체결 요청 내역을 조회합니다.
        """
        params = self._get_params("ka10076")
        if not params: return pd.DataFrame()
        
        url, headers, body = params
        body.update({
            "qry_tp": "1" if stk_cd else "0",
            "stk_cd": stk_cd
        })
        
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고: 체결 리스트 키값은 'cntr'입니다.
        if data:
            raw_list = data.get("cntr", [])
            df = pd.DataFrame(raw_list)
            rename_map = {
                "ord_no": "order_no", "stk_nm": "name", "io_tp_nm": "side",
                "ord_pric": "order_price", "ord_qty": "order_qty",
                "cntr_pric": "exec_price", "cntr_qty": "exec_qty"
            }
            return self._standardize_df(df, rename_map)
        return pd.DataFrame()

    def get_trade_diary(self, base_dt="", ottks_tp="2", ch_crd_tp="1"):
        """
        [ka10170] 당일 매매 일지 요청 (수익률 포함)
        """
        params = self._get_params("ka10170")
        if not params: return pd.DataFrame()
        
        url, headers, body = params
        body["base_dt"] = base_dt # 공백 시 오늘
        body["ottks_tp"] = ottks_tp
        body["ch_crd_tp"] = ch_crd_tp   
        
        data, _ = self._requests_post(url, headers, body)
        
        # 문서 참고: 매매일지 리스트 키값은 'tdy_trde_diary'입니다.
        if data:
            # TODO: 총매도금액, 총매숙듬액, 총손익금액, 총수익률
            raw_list = data.get("tdy_trde_diary", [])
            df = pd.DataFrame(raw_list)
            rename_map = {
                "stk_cd": "code", "stk_nm": "name", 
                "buy_avg_pric": "buy_avg", "buy_qty": "buy_qty",
                "sel_avg_pric": "sell_avg", "sell_qty": "sell_qty",
                "pl_amt": "profit_amt", "prft_rt": "return_rate"
            }
            return self._standardize_df(df, rename_map)
        return pd.DataFrame()

    def _preprocess_holdings(self, raw_list):
        """보유 종목 데이터프레임 정제 (kt00018 특화)"""
        df = pd.DataFrame(raw_list)
        if df.empty: return df
        
        rename_map = {
            "stk_cd": "code", "stk_nm": "name", "evltv_prft": "profit_loss",
            "prft_rt": "return_rate", "pur_pric": "buy_price", 
            "cur_prc": "current_price", "rmnd_qty": "quantity"
        }
        return self._standardize_df(df, rename_map)

    def _standardize_df(self, df, rename_map):
        """컬럼명 변경 및 숫자형 변환 공통 모듈"""
        if df.empty: return df
        
        df = df.rename(columns=rename_map)
        
        # 종목코드 A 제거 및 6자리
        if 'code' in df.columns:
            df['code'] = df['code'].str.replace('A', '').str.zfill(6)
            
        # 숫자형 변환 대상 컬럼 자동 감지
        num_cols = ["profit_loss", "return_rate", "buy_price", "current_price", 
                    "quantity", "order_qty", "order_price", "unexecuted_qty",
                    "exec_price", "exec_qty", "buy_avg", "sell_avg", "profit_amt"]
        
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return df[[c for c in rename_map.values() if c in df.columns]]

if __name__ == "__main__":
    am = AccountManager()
    
    # 1. 계좌 확인
    accounts = am.get_account_list()
    print(f"💳 보유 계좌: {accounts}")
    
    if accounts:
        # 2. 예수금 및 보유종목
        print(f"💰 예수금: {am.get_deposit()}")
        print(f"📈 잔고 내역:\n{am.get_holdings().head()}")
        
        # 3. 추가 기능: 미체결 및 매매일지
        print(f"📝 미체결 내역:\n{am.get_unexecuted_orders().head()}")
        print(f"📊 당일 매매 일지:\n{am.get_trade_diary().head()}")