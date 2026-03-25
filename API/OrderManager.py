import path_finder
from API.API import API

class OrderManager(API):
    def __init__(self):
        super().__init__()
        
    def buy_order(self, 
                  dmst_stex_tp: str="KRX", 
                  stk_cd: str="", 
                  ord_qty:str="", 
                  ord_uv:str="", 
                  trde_tp:str="3", 
                  cond_uv:str=""):
        """
        [kt10000] 주식 매수주문
        :param dmst_stex_tp: 국내거래소구분 (KRX, NXT, SOR)
        :param stk_cd: 종목코드 (12자리)
        :param ord_qty: 주문수량
        :param ord_uv: 주문단가 (시장가 시 "0" 등)
        :param trde_tp: 매매구분 (0:보통, 3:시장가, 5:조건부지정가 등)
        """
        url, headers, body = self._get_params("kt10000")
        
        # 문서에 명시된 파라미터만 Body에 업데이트
        body.update({
            "dmst_stex_tp": dmst_stex_tp,
            "stk_cd": stk_cd,
            "ord_qty": ord_qty,
            "ord_uv": ord_uv,
            "trde_tp": trde_tp,
            "cond_uv": cond_uv
        })

        data, _ = self._requests_post(url, headers, body)
        return data

    def sell_order(self, 
                  dmst_stex_tp: str="KRX", 
                  stk_cd: str="", 
                  ord_qty:str="", 
                  ord_uv:str="", 
                  trde_tp:str="3", 
                  cond_uv:str=""):
        """
        [kt10001] 주식 매도수주문
        :param dmst_stex_tp: 국내거래소구분 (KRX, NXT, SOR)
        :param stk_cd: 종목코드 (12자리)
        :param ord_qty: 주문수량
        :param ord_uv: 주문단가 (시장가 시 "0" 등)
        :param trde_tp: 매매구분 (0:보통, 3:시장가, 5:조건부지정가 등)
        """
        url, headers, body = self._get_params("kt10001")
        if not url: return None

        body.update({
            "dmst_stex_tp": dmst_stex_tp,
            "stk_cd": stk_cd,
            "ord_qty": ord_qty,
            "ord_uv": ord_uv,
            "trde_tp": trde_tp,
            "cond_uv": cond_uv
        })

        data, _ = self.api._requests_post(url, headers, body)
        return data

    def modify_order(self, 
                     dmst_stex_tp:str="KRX", 
                     orig_ord_no:str="",
                     stk_cd:str="",
                     mdfy_qty:str="",
                     mdfy_uv:str="",
                     mdfy_cond_uv:str=""):
        """
        [kt10002] 주식 정정주문
        :param dmst_stex_tp: 국내거래소구분
        :param orig_ord_no: 원주문번호 (7자리)
        :param stk_cd: 종목코드
        :param mdfy_qty: 정정수량
        :param mdfy_uv: 정정단가
        :param mdfy_cond_uv: 정정조건단가
        """
        url, headers, body = self._get_params("kt10002")
        if not url: return None

        body.update({
            "dmst_stex_tp": dmst_stex_tp,
            "orig_ord_no": orig_ord_no,
            "stk_cd": stk_cd,
            "mdfy_qty": mdfy_qty,
            "mdfy_uv": mdfy_uv,
            "mdfy_cond_uv": mdfy_cond_uv
        })

        data, _ = self._requests_post(url, headers, body)
        return data

    def cancel_order(self, 
                     dmst_stex_tp:str="KRX", 
                     orig_ord_no:str="", 
                     stk_cd:str="", 
                     cncl_qty:str="0"):
        """
        [kt10003] 주식 취소주문
        :param dmst_stex_tp: 국내거래소구분
        :param orig_ord_no: 원주문번호
        :param stk_cd: 종목코드
        :param cncl_qty: 취소수량 ("0":전량 취소)
        """
        url, headers, body = self._get_params("kt10003")
        if not url: return None

        body.update({
            "dmst_stex_tp": dmst_stex_tp,
            "orig_ord_no": orig_ord_no,
            "stk_cd": stk_cd,
            "cncl_qty": cncl_qty
        })

        data, _ = self._requests_post(url, headers, body)
        return data

# --- 사용 예시 ---
if __name__ == "__main__":
    om = OrderManager()
    
    