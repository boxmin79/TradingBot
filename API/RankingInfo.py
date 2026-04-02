import path_finder
from API.API import API

class RankingInfo(API):
    def __init__(self):
        super().__init__()
        
    def get_top_quote_volume(self, 
                             mrkt_tp="101", 
                             sort_tp="1", 
                             trde_qty_tp="0010", 
                             stk_cnd="1", 
                             crd_cnd="0", 
                             stex_tp="3"):
        """
        호가잔량 상위 종목 리스트 요청 (순매수/순매도 잔량 상위 등)
        api_id : "ka10020" (TODO: 실제 api.json에 정의된 ID로 반드시 변경하세요)
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (001:코스피, 101:코스닥)
        :param sort_tp: 정렬구분 (1:순매수잔량순, 2:순매도잔량순, 3:매수비율순, 4:매도비율순)
        :param trde_qty_tp: 거래량구분 (0000:장시작전/0주이상, 0010:1만주이상, 0050:5만주이상, 00100:10만주이상)
        :param stk_cnd: 종목조건 (0:전체조회, 1:관리종목제외, 5:증100제외, 6:증100만, 7:증40만, 8:증30만, 9:증20만)
        :param crd_cnd: 신용조건 (0:전체조회, 1:신용융자A군, 2:B군, 3:C군, 4:D군, 7:E군, 9:신용전체)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10020") 
        if not url: return None
        
        # 제공해주신 API 명세에 맞게 파라미터 6개를 모두 body에 주입
        body.update({
            "mrkt_tp": mrkt_tp,
            "sort_tp": sort_tp,
            "trde_qty_tp": trde_qty_tp,
            "stk_cnd": stk_cnd,
            "crd_cnd": crd_cnd,
            "stex_tp": stex_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_quote_volume_surge(self,
                               mrkt_tp="101",
                               trde_tp="1",
                               sort_tp="1",
                               tm_tp="5",
                               trde_qty_tp="10",
                               stk_cnd="0",
                               stex_tp="3"):
        """
        호가잔량급증요청 (특정 시간 대비 잔량이 급증한 종목 리스트)
        api_id : "ka10021"
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (001:코스피, 101:코스닥)
        :param trde_tp: 매매구분 (1:매수잔량, 2:매도잔량)
        :param sort_tp: 정렬구분 (1:급증량, 2:급증률)
        :param tm_tp: 시간구분 (분 단위 입력, 예: '5')
        :param trde_qty_tp: 거래량구분 (1:천주이상, 5:5천주이상, 10:만주이상, 50:5만주이상, 100:10만주이상)
        :param stk_cnd: 종목조건 (0:전체조회, 1:관리종목제외, 5:증100제외, 6:증100만, 7:증40만, 8:증30만, 9:증20만)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10021")
        if not url: return None

        # API 명세에 따른 파라미터 업데이트
        body.update({
            "mrkt_tp": mrkt_tp,
            "trde_tp": trde_tp,
            "sort_tp": sort_tp,
            "tm_tp": tm_tp,
            "trde_qty_tp": trde_qty_tp,
            "stk_cnd": stk_cnd,
            "stex_tp": stex_tp
        })

        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_residual_ratio_surge(self,
                                 mrkt_tp="101",
                                 rt_tp="1",
                                 tm_tp="5",
                                 trde_qty_tp="10",
                                 stk_cnd="0",
                                 stex_tp="3"):
        """
        잔량율급증요청 (매수/매도 잔량 비율이 급격히 변한 종목 리스트)
        api_id : "ka10022"
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (001:코스피, 101:코스닥)
        :param rt_tp: 비율구분 (1:매수/매도비율, 2:매도/매수비율)
        :param tm_tp: 시간구분 (분 단위 입력, 예: '5')
        :param trde_qty_tp: 거래량구분 (5:5천주이상, 10:만주이상, 50:5만주이상, 100:10만주이상)
        :param stk_cnd: 종목조건 (0:전체조회, 1:관리종목제외, 5:증100제외, 6:증100만, 7:증40만, 8:증30만, 9:증20만)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10022")
        if not url: return None

        body.update({
            "mrkt_tp": mrkt_tp,
            "rt_tp": rt_tp,
            "tm_tp": tm_tp,
            "trde_qty_tp": trde_qty_tp,
            "stk_cnd": stk_cnd,
            "stex_tp": stex_tp
        })

        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_volume_surge(self, 
                         mrkt_tp="000", 
                         sort_tp="1", 
                         tm_tp="1", 
                         trde_qty_tp="10", 
                         tm="", 
                         stk_cnd="0", 
                         pric_tp="0", 
                         stex_tp="3"):
        """
        거래량급증요청 (특정 시간 또는 전일 대비 거래량이 급증/급감한 종목 리스트 요청)
        api_id : "ka10023"
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (000:전체, 001:코스피, 101:코스닥)
        :param sort_tp: 정렬구분 (1:급증량, 2:급증률, 3:급감량, 4:급감률)
        :param tm_tp: 시간구분 (1:분, 2:전일)
        :param trde_qty_tp: 거래량구분 (5:5천주이상, 10:만주이상, 50:5만주이상, 100:10만주이상, 200:20만주이상 등)
        :param tm: 시간 (분 입력, 선택사항)
        :param stk_cnd: 종목조건 (0:전체조회, 1:관리종목제외, 3:우선주제외, 5:증100제외, 14:ETF제외 등)
        :param pric_tp: 가격구분 (0:전체조회, 2:5만원이상, 5:1만원이상, 6:5천원이상, 9:10만원이상 등)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10023") #
        if not url: return None
        
        # 상세 명세의 8개 요소를 바디에 업데이트
        body.update({
            "mrkt_tp": mrkt_tp,
            "sort_tp": sort_tp,
            "tm_tp": tm_tp,
            "trde_qty_tp": trde_qty_tp,
            "tm": tm,
            "stk_cnd": stk_cnd,
            "pric_tp": pric_tp,
            "stex_tp": stex_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_today_top_volume(self, 
                             mrkt_tp="000", 
                             sort_tp="1", 
                             mang_stk_incls="0", 
                             crd_tp="0", 
                             trde_qty_tp="0", 
                             pric_tp="0", 
                             trde_prica_tp="0", 
                             mrkt_open_tp="0", 
                             stex_tp="3"):
        """
        당일거래량상위요청 (당일 거래량, 회전율, 거래대금 기준 상위 종목 리스트 요청)
        api_id : "ka10030"
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (000:전체, 001:코스피, 101:코스닥)
        :param sort_tp: 정렬구분 (1:거래량, 2:거래회전율, 3:거래대금)
        :param mang_stk_incls: 관리종목포함 (0:관리종목 포함, 1:미포함, 3:우선주제외, 14:ETF제외 등)
        :param crd_tp: 신용구분 (0:전체조회, 9:신용융자전체, 1:신용융자A군, 8:신용대주 등)
        :param trde_qty_tp: 거래량구분 (0:전체조회, 5:5천주이상, 10:1만주이상, 1000:백만주이상 등)
        :param pric_tp: 가격구분 (0:전체조회, 1:1천원미만, 5:5천원이상, 8:5만원이상, 9:10만원이상 등)
        :param trde_prica_tp: 거래대금구분 (0:전체조회, 1:1천만원이상, 10:1억원이상, 1000:100억원이상 등)
        :param mrkt_open_tp: 장운영구분 (0:전체조회, 1:장중, 2:장전시간외, 3:장후시간외)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10030")
        if not url: return None
        
        # 상세 명세의 9개 요소를 바디에 업데이트
        body.update({
            "mrkt_tp": mrkt_tp,
            "sort_tp": sort_tp,
            "mang_stk_incls": mang_stk_incls,
            "crd_tp": crd_tp,
            "trde_qty_tp": trde_qty_tp,
            "pric_tp": pric_tp,
            "trde_prica_tp": trde_prica_tp,
            "mrkt_open_tp": mrkt_open_tp,
            "stex_tp": stex_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    
    def get_today_volume_surge(self, 
                               mrkt_tp="000", 
                               mang_stk_incls="0", 
                               stex_tp="3"):
        """
        당일거래량급증요청 (전일 대비 당일 거래량이 급증한 종목 리스트 요청)
        api_id : "ka10032"
        
        [파라미터 명세]
        :param mrkt_tp: 시장구분 (000:전체, 001:코스피, 101:코스닥)
        :param mang_stk_incls: 관리종목포함 (0:관리종목 미포함, 1:관리종목 포함)
        :param stex_tp: 거래소구분 (1:KRX, 2:NXT, 3:통합)
        """
        url, headers, body = self._get_params("ka10032")
        if not url: return None
        
        # 상세 명세의 3개 요소를 바디에 업데이트
        body.update({
            "mrkt_tp": mrkt_tp,
            "mang_stk_incls": mang_stk_incls,
            "stex_tp": stex_tp
        })
        
        data, _ = self._requests_post(url, headers, body)
        return data
    