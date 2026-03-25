import path_finder
import pandas as pd
import time
from datetime import datetime
from API.API import API
from API.ChartManager import ChartManager
from Screener.SwingScreener import SwingScreener # 💡 분석 엔진 불러오기

class TickersManager(API):
    def __init__(self):
        # 1. 부모(API) 초기화: self.cfg, self.file_manager(FileManager)가 자동으로 세팅됨
        super().__init__()
        
        self.cm = ChartManager()
                
        # 1. 모든 경로를 한곳에서 관리 (나중에 추가하기 매우 쉬움)
        self.paths = {
            "raw": self.cfg.TICKERS_DIR / "raw_tickers.csv",
            "base": self.cfg.TICKERS_DIR / "base_tickers.csv",
            "fundamental": self.cfg.TICKERS_DIR / "fundamental_tickers.csv",
            "technical": self.cfg.TICKERS_DIR / "technical_tickers.csv" # 💡 Step 3용
        }
        self.log_path = self.cfg.TICKERS_DIR / "tickers_log.json"
        
        # 메모리 캐시 (필요시 사용)
        self.cache = {k: None for k in self.paths.keys()}

    def _get_up_code_list(self):
        """[ka10101] 업종 코드 리스트를 가져옵니다."""
        all_upcodes = []
        
        for mrkt_tp, mrkt_name in [("0", "코스피"), ("1", "코스닥")]:
            # 💡 수정: _get_params가 이미 URL, 토큰 주입된 Headers, AppKey가 포함된 Body를 반환함
            params = self._get_params("ka10101")
            if not params: continue
            
            url, headers, body = params
            body["mrkt_tp"] = mrkt_tp
            
            # 💡 수정: 직접 requests를 쓰지 않고 부모의 _requests_post 사용 (재시도 및 에러 처리 통합)
            data, _ = self._requests_post(url, headers, body)
            
            if data:
                up_list = data.get("list", [])
                all_upcodes.extend(up_list)
        
        return pd.DataFrame(all_upcodes) if all_upcodes else None

    def collect(self):
        """[Step 1] 모든 종목 원본 데이터를 수집합니다."""
        # 1. 업종 코드 수집
        print("\n📊 [Tickers] 업종 코드(지수) 데이터 로드 중...")
        up_code_data = self._get_up_code_list()
        
        # 2. 종목 리스트 수집 시작
        print("\n🚀 [Tickers] 키움증권 서버에서 실시간 종목 수집 시작...")
        all_tickers = []
        
        for mrkt_tp, mrkt_name in [("0", "코스피"), ("10", "코스닥")]:
            print(f"⏳ {mrkt_name} 요청 중...", end="\r")
            
            params = self._get_params("ka10099")
            if not params: continue
            
            url, headers, body = params
            body["mrkt_tp"] = mrkt_tp
            
            # 💡 수정: 부모의 _requests_post 활용
            data, _ = self._requests_post(url, headers, body)
            
            if data:
                tickers = data.get("list", [])
                all_tickers.extend(tickers)
        
        if not all_tickers:
            print("❌ 종목 수집에 실패했습니다.")
            return None

        df = pd.DataFrame(all_tickers)

        # 3. 업종명 매핑 로직 (기존과 동일)
        if up_code_data is not None:
            print("🔗 업종명(upName)과 업종코드(upCode) 매칭 중...")
            up_map = up_code_data.set_index('name')['code'].to_dict()
            df['upCode'] = df['upName'].map(up_map).fillna('')

        # 4. 최종 저장
        formatted_df = self._format_datatype(df)
        self._save(formatted_df, data_type="raw")
        
        print(f"\n✅ 수집 완료: 총 {len(formatted_df)}개 종목 확보")
        return formatted_df

    def filter_1_base(self, df):
        """[Step 1] 기초 필터링: ETF, 우선주, 관리종목, 업력 체크"""
        if df is None or df.empty: return None
        
        print("🔍 [Filter 1] 기초 필터링 시작 (ETF, 우선주, 부실주 제외)...")
        df = df.copy()
        current_date = datetime.now()

        # 1) 종목코드 및 우선주 필터링
        df = df[df['code'].str.isnumeric() & 
                df['code'].str.endswith('0') & 
                ~df['code'].str.startswith(('9', '5', '7'))]

        # 2) 시장 분류 제외
        exclude_markets = ['ETF', 'ETN', '리츠']
        df = df[~df['marketName'].isin(exclude_markets)]

        # 3) 상태 필터링
        bad_keywords = ["거래정지", "관리", "정리", "유의", "환기", "불성실", "투자경고", "투자위험"]
        df['combined_info'] = df['state'].fillna('') + df['auditInfo'].fillna('')
        df = df[~df['combined_info'].str.contains('|'.join(bad_keywords), na=False)]

        # 4) 업력 필터 (2년 이상)
        df['regDay'] = pd.to_datetime(df['regDay'], format='%Y%m%d', errors='coerce')
        df = df.dropna(subset=['regDay'])
        df = df[(current_date - df['regDay']).dt.days >= 730]
        df = df.drop(columns=['combined_info'])

        if not df.empty:
            self._save(df, data_type="base")
            print(f"✅ 기초 필터링 완료: 총 {len(df)}개 종목 통과")
        else:
            print("❌ 기초 필터를 통과한 종목이 없습니다.")
            
        return df

    def filter_2_fundamental(self, df):
        """[Step 2] 재무 필터링: 스냅샷 파일을 읽어 SwingScreener로 분석"""
        if df is None or df.empty: return None
        
        print(f"🔍 [Filter 2] 재무 분석 시작 (대상: {len(df)} 종목)...")
        passed_list = []
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            code = str(row['code']).zfill(6)
            name = row['name']
            
            # 1. 파일매니저를 통해 snapshot 폴더의 연간 재무제표 로드
            snapshot_path = self.cfg.SNAPSHOT_DIR / f"{code}_annual.parquet"
            fs_data = self.file_manager.load(snapshot_path)
            
            # 2. 스크리너에게 분석 요청
            print(f"[{i}/{len(df)}] {name}({code}) 재무 검사 중...", end="\r")
            if SwingScreener.is_fundamental_ok(fs_data):
                passed_list.append(row)
        
        if passed_list:
            df_passed = pd.DataFrame(passed_list)
            # 3. 결과 저장 (fundamental_universe.csv)
            self._save(df_passed, data_type="fundamental")
            print(f"\n✅ 재무 필터링 완료: {len(df_passed)}개 종목 통과")
            return df_passed
        
        print("\n❌ 재무 필터를 통과한 종목이 없습니다.")
        return None

    def filter_3_technical(self, df):
        """[Step 3] 차트 필터링: 일봉 차트를 분석하여 기술적 타점(눌림목 등) 체크"""
        if df is None or df.empty: 
            return None
        
        # 💡 메서드 안으로 임포트를 옮깁니다. (로컬 임포트)
        
        print(f"🔍 [Filter 3] 기술적 분석 시작 (대상: {len(df)} 종목)...")
        passed_list = []
        
        for i, (idx, row) in enumerate(df.iterrows(), 1):
            code = str(row['code']).zfill(6)
            name = row['name']
            
            # 1. ChartManager를 통해 일봉 데이터 로드 (파일이 없으면 API 수집까지 자동 수행)
            # 분석에 충분한 데이터(최소 60~120일)를 확보하기 위해 기본값 사용
            df_chart = self.cm.get_chart(stk_cd=code, chart_type="day", save=False)
            
            print(f"[{i}/{len(df)}] {name}({code}) 차트 분석 중...", end="\r")
            
            # 2. SwingScreener의 기술적 분석 엔진 가동 (정배열, 눌림목 등 체크)
            if df_chart is not None and not df_chart.empty:
                if SwingScreener.is_technical_ok(df_chart):
                    passed_list.append(row)
            
            # API 호출 시 과부하 방지를 위한 미세 대기 (필요시)
            time.sleep(1) 

        if passed_list:
            df_final = pd.DataFrame(passed_list)
            # 3. 최종 결과 저장 (technical_tickers.csv)
            self._save(df_final, data_type="technical")
            print(f"\n✨ [최종] 기술적 분석 통과: {len(df_final)}개 종목 발견!")
            return df_final
        
        print("\n❌ 모든 필터를 통과한 최종 종목이 없습니다.")
        return pd.DataFrame()

    # --- [핵심 로직] ---

    def _update_all(self):
        """전체 수집 및 3단계 필터링 프로세스 실행"""
        # 1. 수집
        raw = self.collect() # collect 내부에서 _save("raw") 호출됨
        base = self.filter_1_base(raw)
        fundamental = self.filter_2_fundamental(base)
        technical = self.filter_3_technical(fundamental)
        
        # 메모리 캐시 일괄 갱신
        self.cache["raw"] = raw
        self.cache["base"] = base
        self.cache["fundamental"] = fundamental
        self.cache["technical"] = technical
        
        # 4. 로그 및 메모리 갱신
        self.file_manager.save({"last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, self.log_path)

    def get(self, data_type="fundamental"):
        """
        메모리 캐시를 먼저 확인하고, 없으면 파일에서 로드하여 반환합니다.
        """
        # 1. 오늘자 데이터가 아니면 전체 업데이트 실행
        if not self._is_up_to_date():
            print(f"🔄 [Tickers] 데이터가 최신이 아닙니다. 전체 업데이트를 시작합니다...")
            self._update_all()

        # 1. 메모리 캐시 확인
        df = self.cache.get(data_type)
        if df is not None and not df.empty:
            return df

        # 2. 파일에서 로드
        # print(f"📂 [Tickers] {data_type} 데이터를 파일에서 로드합니다...")
        df = self._load(data_type)
        
        if df is not None and not df.empty:
            self.cache[data_type] = df
            return df
        
        # 3. 파일도 없으면 업데이트 실행 (최후의 수단)
        self._update_all()
        return self.cache.get(data_type, pd.DataFrame())

    def _save(self, df, data_type="raw"):
        """입력받은 data_type에 맞는 경로에 데이터를 저장합니다."""
        if df is None or df.empty:
            return
            
        target_path = self.paths.get(data_type)
        if target_path:
            self.file_manager.save(df, target_path, file_type="csv")
            # 저장과 동시에 메모리 캐시도 갱신하면 좋습니다.
            self.cache[data_type] = df
        else:
            print(f"⚠️ [Save] 정의되지 않은 파일 타입입니다: {data_type}")

    def _load(self, data_type="base"):
        """파일 로드 후 데이터 타입 포맷팅"""
        target_path = self.paths.get(data_type)
        if target_path and target_path.exists():
            data = self.file_manager.load(target_path, file_type="csv")
            return self._format_datatype(data)
        return None

    def _format_datatype(self, df):
        """데이터프레임 컬럼 타입을 표준화합니다."""
        if df is None or df.empty: return df
        df = df.copy()
        if 'code' in df.columns:
            df['code'] = df['code'].astype(str).str.zfill(6)
        if 'upCode' in df.columns:
            df['upCode'] = df['upCode'].astype(str).str.zfill(3)
        if 'regDay' in df.columns:
            # 날짜 형식이 섞여있을 수 있으므로 유연하게 처리
            df['regDay'] = pd.to_datetime(df['regDay'], errors='coerce')
        return df

    def _is_up_to_date(self):
        """오늘 업데이트를 이미 마쳤는지 로그를 확인합니다."""
        log = self.file_manager.load(self.log_path)
        if not log: return False
        return log.get("last_update", "").split(" ")[0] == datetime.now().strftime("%Y-%m-%d")

if __name__ == "__main__":
    tm = TickersManager()
    # 💡 인자 수정: filtered=True 대신 data_type="fundamental"
    universe = tm.get(data_type="fundamental")
    if not universe.empty:
        print(universe[['code', 'name', 'regDay']].head())
    # up_code_list = tm._get_up_code_list()
    # print(up_code_list)
    #