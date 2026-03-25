import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
import path_finder

class FdrTickersManager:
    def __init__(self):
        self.cfg = path_finder.get_cfg()
        
        # 경로 설정 (TickersManager와 동일하게 설정)
        self.raw_file = r"./Collector/tickers.csv"
        

    def collect_from_fdr(self):
        """
        FDR을 통해 KRX 전체 종목을 가져와서 키움 포맷과 유사하게 저장합니다.
        """
        print("🚀 [FDR] 한국거래소 종목 리스트 수집 시작...")
        
        # 1. KRX 전체 상장 종목 리스트 가져오기 (KOSPI, KOSDAQ, KONEX 포함)
        df_krx = fdr.StockListing('KRX')
        
        # 2. 키움 API 컬럼명과 유사하게 매칭 (호환성 유지)
        # FDR 컬럼: Code, Name, Market, ListingDate 등
        df = df_krx.rename(columns={
            'Code': 'code',
            'Name': 'name',
            'Market': 'marketName',
            
        })

        # 3. 원본 저장
        df.to_csv(self.raw_file, index=False, encoding="utf-8-sig")
        print(f"✅ 원본 수집 완료 ({len(df)}개) -> {self.raw_file}")

        # # 4. 정밀 필터링 실행
        # self.filter_tickers(df)

    # def filter_tickers(self, df):
    #     """
    #     기존 TickersManager와 동일한 필터링 로직 적용
    #     """
    #     print("🔍 [FDR] 정밀 필터링 및 업력(2년) 체크 시작...")
    #     current_date = datetime.now()

    #     # --- 필터 1: KRX 코드 규칙 (외국기업 '9', ETN '5') ---
    #     df = df[~df['code'].str.startswith(('9', '5'))]

    #     # --- 필터 2: 보통주 외 제외 (끝자리 '0' 필수) ---
    #     df = df[df['code'].str.endswith('0')]

    #     # --- 필터 3: 종목명 키워드 제외 (ETF, 스팩, 리츠 등) ---
    #     # FDR 데이터에는 'Stocks'라는 구분이 있지만, 키워드로 한 번 더 거르는 것이 안전합니다.
    #     name_exclude = ["ETF", "ETN", "스팩", "리츠", "인프라", "KODEX", "TIGER", "KBSTAR", "신영스팩"]
    #     df = df[~df['name'].str.contains('|'.join(name_exclude), na=False, case=False)]

    #     # --- 필터 4: 상장일 필터 (업력 2년 - 730일) ---
    #     # FDR의 regDay는 이미 datetime 객체인 경우가 많지만, 안전하게 한 번 더 변환
    #     df['regDay'] = pd.to_datetime(df['regDay'], errors='coerce')
    #     df = df.dropna(subset=['regDay'])
        

    #     # --- 필터 5: 시장 제외 (KONEX 등 제외하고 KOSPI, KOSDAQ만 남기기) ---
    #     df = df[df['marketName'].isin(['KOSPI', 'KOSDAQ'])]

    #     # 결과 저장
    #     self.filtered_tickers_df = df.drop(columns=['days_since_listing'])
    #     self.filtered_tickers_df.to_csv(self.filtered_file, index=False, encoding="utf-8-sig")
        
    #     print(f"🎯 필터링 완료: {len(df)}개 종목 최종 확정")
    #     print(f"💾 필터링 결과 저장 완료 -> {self.filtered_file}")

if __name__ == "__main__":
    manager = FdrTickersManager()
    manager.collect_from_fdr()