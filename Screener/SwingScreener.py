import pandas as pd

class SwingScreener:
    """
    입력받은 데이터를 바탕으로 전략 적합성 여부(True/False)만 판단하는 분석 전문 클래스입니다.
    """

    @staticmethod
    def is_fundamental_ok(df_a):
        """
        [재무 분석 스크리너] 
        - 입력: 연간 재무제표 데이터프레임 (FSDataManager.get()의 결과물)
        - 반환: True (우량주 기준 충족) / False (미달)
        """
        if df_a is None or df_a.empty:
            return False
            
        try:
            # 가장 최근 실적(마지막 행) 추출
            latest = df_a.iloc[-1]
            
            # 조건: 영업이익 흑자 AND ROE 10% 이상
            op_profit = latest.get('영업이익', 0)
            roe = latest.get('ROE', 0)
            
            return (op_profit > 0) and (roe >= 10.0)
        except Exception:
            return False

    @staticmethod
    def is_technical_ok(df_c):
        """
        [차트 분석 스크리너]
        - 입력: 일봉 차트 데이터프레임 (ChartDataManager.get()의 결과물)
        - 반환: True (눌림목 타점 충족) / False (미달)
        """
        # 분석을 위해 최소 60거래일 이상의 데이터가 필요함
        if df_c is None or len(df_c) < 60:
            return False
            
        try:
            # 원본 데이터 보호를 위해 복사본 사용
            df = df_c.copy()
            
            # 지표 계산
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            df['VMA20'] = df['Volume'].rolling(window=20).mean()
            
            curr = df.iloc[-1] # 오늘 데이터
            
            # 1. 정배열 조건 (20일선 > 60일선)
            is_uptrend = curr['MA20'] > curr['MA60']
            
            # 2. 눌림목 조건 (종가가 20일선 기준 ±2% 이내 밀착)
            diff_ratio = abs(curr['Close'] - curr['MA20']) / curr['MA20']
            is_on_ma20 = diff_ratio <= 0.02
            
            # 3. 거래량 조건 (오늘 거래량이 20일 평균의 70% 미만으로 마름)
            is_vol_dried = curr['Volume'] < (curr['VMA20'] * 0.7)
            
            return is_uptrend and is_on_ma20 and is_vol_dried
        except Exception:
            return False