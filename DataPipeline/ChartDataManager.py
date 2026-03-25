import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta # timedelta 추가
import time
import path_finder
from API.TickersManager import TickersManager
from DataPipeline.FileManager import FileManager # 💡 파일 매니저만 사용

class ChartDataManager:
    def __init__(self):
        self.cfg = path_finder.get_cfg()
        
        # 1. 파일 매니저 소환 (상속 대신 직접 생성)
        self.fm = FileManager()
        
        # 2. 분석 대상 종목 리스트 로드 (우량주 유니버스 기반)
        tm = TickersManager()
        self.tickers = tm.get(data_type="base")
        
        # 경로 설정 및 폴더 생성 보장
        self.chart_dir = self.cfg.CHART_DIR
        
    def collect_all(self, start_date=None, end_date=None):
        """
        [일괄 수집용] 필터링된 모든 종목의 일봉 데이터를 수집합니다.
        - start_date가 None이면 오늘부터 3년 전 데이터를 기본으로 설정합니다.
        """
        # 💡 [핵심] 이제 날짜 계산은 이 한 줄로 끝납니다!
        start_date, end_date = self._prepare_dates(start_date, end_date)
            
        total_cnt = len(self.tickers)
        print(f"🚀 총 {total_cnt}개 종목의 데이터 수집을 시작합니다. ({start_date} ~ {end_date})")

        for i, (idx, row) in enumerate(self.tickers.iterrows(), 1):
            code = row['code']
            name = row['name']
            
            # get() 메서드를 호출하여 있으면 넘어가고 없으면 수집하게 함
            print(f"[{i}/{total_cnt}] {name}({code}) 분석 중...", end="\r")
            self.get(code, start_date, end_date)
            
            # FDR은 웹 스크래핑 방식이라 차단 방지를 위해 아주 미세한 대기
            time.sleep(0.05) 

        print(f"\n✨ 모든 수집 작업이 완료되었습니다. 저장 위치: {self.chart_dir}")

    def get(self, code, start_date=None, end_date=None):
        """[외부 호출용] 저장된 차트 파일을 읽어 반환합니다. 데이터 부족 시 자동 보충합니다."""
        start_date, end_date = self._prepare_dates(start_date, end_date)
        target_path = self.chart_dir / f"{code}.parquet"
        
        # 1. FileManager를 통해 파일 로드 시도
        df = self.fm.load(target_path)
        
        if df is not None:
            try:
                # 파일 내 실제 날짜 범위 확인 (인덱스는 DatetimeIndex)
                actual_start = df.index.min().strftime("%Y-%m-%d")
                actual_end = df.index.max().strftime("%Y-%m-%d")
                
                # 요청 범위가 파일 안에 다 있다면 바로 슬라이싱해서 반환
                if actual_start <= start_date and actual_end >= end_date:
                    return df.loc[start_date:end_date]
                else:
                    print(f"🔄 {code}: 데이터 보충 필요 (실제: {actual_end} / 요청: {end_date})")
            except Exception as e:
                print(f"⚠️ {code} 데이터 검증 실패: {e}")

        # 2. 파일이 없거나 데이터가 부족한 경우 FDR로 수집
        df = self.get_chart_by_fdr(code, start_date, end_date)
        
        if df is not None and not df.empty:
            self._save(df, code)
            return df
        return None

    def get_chart_by_fdr(self, code, start_date=None, end_date=None):
        """
        FDR을 이용해 실제 웹에서 데이터를 가져옵니다. 
        날짜가 없으면 자동으로 최근 3년치를 타겟팅합니다.
        """
        # 1. 날짜 세팅
        start_date, end_date = self._prepare_dates(start_date, end_date)
        
        try:
            # 2. FDR 호출
            df = fdr.DataReader(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 💡 [데이터 클리닝] FDR 데이터의 인덱스 이름이 제각각일 수 있으니 'Date'로 통일
                df.index.name = 'Date'
                return df
            return None
            
        except Exception as e:
            print(f"\n❌ {code} FDR 수집 에러: {e}")
            return None
        
    def _prepare_dates(self, start_date, end_date):
        """날짜가 None일 경우 기본값(오늘, 3년 전)으로 계산하여 반환합니다."""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if start_date is None:
            # 3년(1095일) 전 계산
            three_years_ago = datetime.now() - timedelta(days=365 * 3)
            start_date = three_years_ago.strftime("%Y-%m-%d")
            
        return start_date, end_date
    
    def _save(self, df, code):
        """FileManager를 사용하여 parquet 파일로 깔끔하게 저장합니다."""
        target_path = self.chart_dir / f"{code}.parquet"
        self.fm.save(df, target_path) # 확장자 자동 판별로 parquet 저장

if __name__ == "__main__":
    manager = ChartDataManager()
    # 삼성전자 테스트
    test_df = manager.get("005930", start_date="2024-01-01")
    if test_df is not None:
        print(f"\n🔍 데이터 로드 성공! (건수: {len(test_df)})")
        print(test_df.tail(3))