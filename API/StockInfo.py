import path_finder
from API.API import API

class StockInfo(API):
    def __init__(self):
        super().__init__()
        
    def get_base_info(self, stk_cd):
        """
        주식기본정보요청
        api_id : "ka10001"
        :param stk_cd: 종목코드 (예: "005930")
        """
        url, headers, body = self._get_params("ka10001")
        if not url: return None
        
        # 문서 기준 필수 파라미터 업데이트
        body.update({
            "stk_cd": stk_cd
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_stock_list(self, mrkt_tp="0"):
        """
        종목정보 리스트
        api_id : "ka10099"
        :param mrkt_tp: 시장구분 (0: 코스피, 10: 코스닥, 30: K-OTC, 50: 코넥스 등)
        """
        url, headers, body = self._get_params("ka10099")
        if not url: return None
        
        # 문서 기준 필수 파라미터 업데이트
        body.update({
            "mrkt_tp": mrkt_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_up_code_list(self, mrkt_tp="0"):
        """
        업종코드 리스트
        api_id : "ka10101"
        :param mrkt_tp: 시장구분 (0: 코스피, 1: 코스닥, 2: KOSPI200, 4: KOSDAQ150 등)
        """
        url, headers, body = self._get_params("ka10101")
        if not url: return None
        
        # 문서 기준 필수 파라미터 업데이트
        body.update({
            "mrkt_tp": mrkt_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data