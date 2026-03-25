import path_finder
import pandas as pd
import requests
import io
import time
from datetime import datetime
from API.TickersManager import TickersManager
from DataPipeline.FileManager import FileManager # 💡 파일 매니저 추가

class FSDataManager:
    def __init__(self):
        self.cfg = path_finder.get_cfg()
        
        # 1. 파일 매니저 및 종목 매니저 소환
        self.fm = FileManager()
        tm = TickersManager()
        self.tickers = tm.get(data_type="base") # 기초 필터링된 종목 대상
        
        # 경로설정
        self.snapshot_dir = self.cfg.SNAPSHOT_DIR
        # 💡 로그도 JSON으로 관리하여 FM의 이점을 살립니다.
        self.log_path = self.snapshot_dir / "fs_update_log.json"
        
    def get(self, code, data_type="annual"):
        """
        [외부 호출용] 저장된 재무제표 파일을 읽어 반환합니다. 
        파일이 없으면 실시간으로 스크래핑하여 저장 후 반환합니다.
        
        Args:
            code (str): 종목코드
            type (str): "annual" 또는 "quarterly" (기본값: "annual")
            
        Returns:
            pd.DataFrame: 요청한 재무 데이터프레임 (실패 시 None)
        """
        # 1. 입력값 방어
        if data_type not in ["annual", "quarterly"]:
            print("⚠️ type 파라미터는 'annual' 또는 'quarterly'만 가능합니다.")
            return None
            
        target_path = self.snapshot_dir / f"{code}_{data_type}.parquet"
        
        # 💡 [변경] FM을 통해 데이터 로드 (None이면 파일이 없거나 손상됨)
        df = self.fm.load(target_path)
        
        if df is not None:
            return df
        
        result = self.get_snapshot(code)
        
        if result:
            df_a, df_q = result
            
            # 💡 [핵심] 기왕 긁어온 김에 연간/분기 둘 다 저장해둡니다 (효율 극대화)
            self._save(df_a, code, type="annual")
            self._save(df_q, code, type="quarterly")
            
            # 사용자가 요청한 타입에 맞춰서 반환
            return df_a if type == "annual" else df_q
        else:
            print(f"❌ {code} 재무 데이터 스크래핑 실패 (제공되지 않는 종목일 수 있습니다)")
            return None
            
    def collect_all(self):
        """
        1. 오늘 이미 완료했으면 즉시 종료
        2. 아니면 종목별로 파일 날짜 확인해서 오늘치면 건너뛰고, 옛날치면 새로 받음
        """
        # 💡 [핵심 1] 오늘 전체 작업이 이미 끝났는지 확인
        if self._is_up_to_date():
            print(f"✅ [Snapshot] 오늘자 재무 데이터가 이미 최신입니다. 수집을 종료합니다.")
            return

        total_cnt = len(self.tickers)
        today_str = datetime.now().strftime("%Y-%m-%d")
        print(f"🚀 총 {total_cnt}개 종목의 데이터 수집/업데이트를 시작합니다.")
        
        for i, (idx, row) in enumerate(self.tickers.iterrows(), 1):
            code = row['code']
            name = row['name']
            
            # 연간/분기 경로 두 개를 다 정의
            path_a = self.snapshot_dir / f"{code}_annual.parquet"
            path_q = self.snapshot_dir / f"{code}_quarterly.parquet"
            
            # 💡 [개선] 두 파일이 '모두' 존재하고, '모두' 오늘 날짜인지 확인
            if path_a.exists() and path_q.exists():
                mtime_a = datetime.fromtimestamp(path_a.stat().st_mtime).strftime("%Y-%m-%d")
                mtime_q = datetime.fromtimestamp(path_q.stat().st_mtime).strftime("%Y-%m-%d")
                
                if mtime_a == today_str and mtime_q == today_str:
                    print(f"[{i}/{total_cnt}] {name}({code}) 오늘 수집 완료. 건너뜀.", end="\r")
                    continue
            
            print(f"[{i}/{total_cnt}] {name}({code}) 새 데이터 수집 중...          ", end="\r")
            
            try:
                result = self.get_snapshot(code)
                if result:
                    df_a, df_q = result
                    self._save(df_a, code, type="annual")
                    self._save(df_q, code, type="quarterly")
                
                time.sleep(1.0) # 서버 부하 방지
                
            except Exception as e:
                print(f"\n❌ {name}({code}) 에러 발생: {e}")
                continue
                
        # 💡 [변경] 수집 완료 후 로그 기록도 FM으로!
        self.fm.save({"last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, self.log_path)
        print(f"\n✨ 재무 데이터 업데이트 완료.")
            
    def _is_up_to_date(self):
        """오늘 업데이트 로그 확인"""
        # 💡 [변경] FM으로 JSON 로그 로드
        log = self.fm.load(self.log_path)
        if not log: return False
        return log.get("last_update", "").split(" ")[0] == datetime.now().strftime("%Y-%m-%d")
            
    def _save(self, df, code, data_type="annual"):
        """
        재무제표 데이터프레임과 종목코드를 인자로 받아 파일로 저장합니다.
        
        Args:
            df (pd.DataFrame): 재무제표 데이터프레임
            code (str): 종목코드
            data_type (str): "annual" 또는 "quarterly" (기본값: "annual")
        """
        target_path = self.snapshot_dir / f"{code}_{data_type}.parquet"
        self.fm.save(df, target_path)
        
    def get_snapshot(self, code):
        """
        종목코드를 입력받아서 컴퍼니가이드의 하이라이트 표를 가져와 전처리 합니다.

        Args:
            code (str): 종목코드

        Returns:
            pd.DataFrame: 종목의 간단한 재무정보를 담은 판다스 데이터프레임
        """
        # 컴퍼니가이드 Snapshot URL (삼성전자 예시: 005930)
        url = f"https://comp.fnguide.com/SVO2/ASP/SVD_Main.asp?gicode=A{code}"
        
        # 헤더 설정 (봇 차단 방지용 User-Agent)
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        
        # encoding 설정 (한글 깨짐 방지)
        res.encoding = 'utf-8'
        
        # HTML 내의 모든 테이블 읽기
        tables = pd.read_html(io.StringIO(res.text))
        if len(tables) > 12:
            df_a = tables[11].copy()
            df_q = tables[12].copy()
            
            df_a = self._preprocess(df_a)
            df_q = self._preprocess(df_q)
            
            return df_a, df_q
        else:
            return None # 표가 부족한 종목은 예외 처리 (None 반환)
        
    def _preprocess(self, df):
        """
        수집된 재무제표 데이터프레임의 구조를 정리하고 타입을 변환합니다.
        """

        # 1. 필요 없는 상단 MultiIndex(컬럼 이름이 2줄인 것) 정리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(1) # '2021/12', '2022/12' 부분만 가져옴

        # 2. 첫 번째 열('IFRS(연결)' 등)을 인덱스로 설정하고 행/열 뒤집기 (Transpose)
        df.set_index(df.columns[0], inplace=True)
        df = df.transpose()
        
        # 💡 [추가] 인덱스 이름을 'Date'로 깔끔하게 통일합니다!
        df.index.name = 'Date'
        
        # 3. 데이터 타입 숫자로 변환 (문자열로 된 숫자를 계산 가능하게)
        df = df.apply(pd.to_numeric, errors='coerce')
        # 💡 [수정 2] Parquet 저장을 위해 모든 컬럼명을 문자열(str)로 강제 변환
        df.columns = df.columns.astype(str)
        
        return df

# 실행 테스트
if __name__ == "__main__":
    ssc = FSDataManager()
    
    # df_a, df_q = ssc.get_snapshot("005930")
    # print(df_a)
    # print(df_q)
    
    # ssc.collect_all()
    ssc = FSDataManager()
    df = ssc.get("005930", data_type="annual")
    print(df.tail())