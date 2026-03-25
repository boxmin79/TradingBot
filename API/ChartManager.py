import path_finder
import pandas as pd
from datetime import datetime, timedelta
import time
from API.API import API
from dotenv import load_dotenv

load_dotenv()

class ChartManager(API):
    def __init__(self):
        # 💡 [보완] 부모 클래스(API)를 초기화해야 self.cfg, self.file_manager 등을 사용할 수 있습니다.
        super().__init__()
        
        # 경로 설정
        self.chart_dir = self.cfg.CHART_DIR

    def get_chart(self, 
                  stk_cd: str = None,
                  inds_cd: str = None,
                  chart_type: str = "day",
                  base_dt: str = None, 
                  tic_scope: str = "1",
                  upd_stkpc_tp: str = "1",
                  cont_yn: str = None,
                  next_key: str = None,
                  end_dt: str = None,
                  save=True):
        """
        종목 또는 업종의 차트 데이터를 가져옵니다. (파일 우선 -> API 수집)

        Args:
            stk_cd (str, optional): 종목코드. Defaults to None.
            inds_cd (str, optional): 업종코드. Defaults to None.
            base_dt (str, optional): 기준일. YYYYMMDD. Defaults to None.
            chart_type (str): "day", "week", "month", "year", "min". Defaults to "day".
            
            tic_scope (str, optional): 틱범위   종목차트는 "1", "3", "5", "10", "15", "30", "45", "60". Defaults to "1".
                                                업종차트는 "1", "3", "5", "10", "30". Defaults to "1".
            upd_stkpc_tp (str, optional): 수정주가 "0" or "1". Defaults to "1".
            cont_yn (str, optional): 연속 조회 여부. Defaults to None.
            next_key (str, optional): 연속 조회 키값. Defaults to None.
            end_dt (str, optional): 종료일. Defaults to None.
            
        """
        code = stk_cd if stk_cd else inds_cd
        if not code:
            print("❌ 종목코드(stk_cd) 또는 업종코드(inds_cd)가 필요합니다.")
            return None

        # 1. 로컬 파일 확인 (캐싱)
        df_local = self._load(code, chart_type)
        if df_local is not None:
            # 실전에서는 파일의 마지막 날짜가 오늘인지 체크하는 로직이 추가되면 좋습니다.
            return df_local

        # 2. API ID 및 응답 키값 매핑
        api_id = self._get_api_id(stk_cd, inds_cd, chart_type)
        res_key = self._get_response_key(stk_cd, inds_cd, chart_type)
        if not api_id or not res_key: return None

        # 3. API 요청 파라미터 준비
        params = self._get_params(api_id)
        if not params: return None
        url, headers, body = params
        
        # 기준일 및 종료일 기본값 설정
        base_dt = base_dt if base_dt else datetime.now().strftime("%Y%m%d")
        if end_dt is None:
            # 기본적으로 1년치 데이터 타겟팅 (필요에 따라 3년으로 변경 가능)
            end_dt = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        combined_df = pd.DataFrame()
        cont_yn = "N"
        next_key = "N"
        
        # 🔄 연속 조회 루프 시작
        while True:
            headers["cont-yn"] = cont_yn
            headers["next-key"] = next_key
            
            # Body 값 세팅 (매 루프마다 갱신 필요 없음, base_dt는 고정)
            if stk_cd:
                body["stk_cd"] = stk_cd
                body["upd_stkpc_tp"] = upd_stkpc_tp
            else:
                body["inds_cd"] = inds_cd
            body["base_dt"] = base_dt
            if chart_type == "min": body["tic_scope"] = tic_scope

            try:
                data, res_headers = self._requests_post(url, headers, body)
                if data:
                    raw_list = data.get(res_key, [])
                    if not raw_list: break

                    # 데이터 전처리 및 누적
                    temp_df = self._preprocess_chart(pd.DataFrame(raw_list), chart_type)
                    combined_df = pd.concat([combined_df, temp_df])

                    # 💡 연속 조회 정보 추출 (응답 헤더)
                    cont_yn = res_headers.get("cont-yn", "N")
                    next_key = res_headers.get("next-key", "N")

                    # 💡 수집 종료 조건 체크 (수집된 데이터의 가장 과거 날짜가 end_dt보다 이전인가?)
                    earliest_date = temp_df.index.min().strftime("%Y%m%d")
                    if earliest_date <= end_dt:
                        print(f"✅ {code} 목표 기간 수집 완료 ({earliest_date} <= {end_dt})")
                        break
                    
                    if cont_yn == "N":
                        break
                        
                    print(f"⏳ {code} 연속 조회 중... (현재 수집: {earliest_date})", end="\r")
                    time.sleep(0.3) # 서버 부하 방지
                else:
                    print(f"❌ API 실패: {res_headers}")
                    print(data)
                    break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                break

        # 3. 최종 정렬, 중복 제거 및 저장
        if not combined_df.empty:
            # 과거에서 최신순으로 정렬 (인덱스가 Date이므로)
            combined_df = combined_df[~combined_df.index.duplicated(keep='first')]
            combined_df.sort_index(inplace=True)
            
            # 지정한 end_dt 이후 데이터만 최종 슬라이싱
            final_df = combined_df.loc[end_dt:]
            if save:
                self._save(final_df, code, chart_type)
            return final_df
            
        return None

    def _get_api_id(self, stk_cd, inds_cd, chart_type):
        """요청 타입에 따른 API ID 매핑"""
        mapping = {
            "stock": {"min": "ka10080", "day": "ka10081", "week": "ka10082", "month": "ka10083", "year": "ka10084"},
            "index": {"min": "ka20005", "day": "ka20006", "week": "ka20007", "month": "ka20008", "year": "ka20019"}
        }
        if stk_cd:
            target = "stock" 
        elif inds_cd:
            target = "index"
        return mapping[target].get(chart_type)

    def _get_response_key(self, stk_cd, inds_cd, chart_type):
        """데이터 샘플 기반 응답 리스트 키값 매핑"""
        if stk_cd:
            return {
                "min": "stk_min_pole_chart_qry",
                "day": "stk_dt_pole_chart_qry",
                "week": "stk_stk_pole_chart_qry",
                "month": "stk_mth_pole_chart_qry",
                "year": "stk_yr_pole_chart_qry"
            }.get(chart_type)
        elif inds_cd:
            return {
                "min": "inds_min_pole_qry",
                "day": "inds_dt_pole_qry",
                "week": "inds_stk_pole_qry",
                "month": "inds_mth_pole_qry",
                "year": "inds_yr_pole_qry"
            }.get(chart_type)
        
    def _preprocess_chart(self, df, chart_type):
        """샘플 데이터 구조에 맞춘 정밀 전처리"""
        if df is None or df.empty: return df
        
        # 1. 컬럼명 표준화
        rename_map = {
            "cntr_tm": "date", "dt": "date",
            "open_pric": "open", "high_pric": "high", 
            "low_pric": "low", "cur_prc": "close",
            "trde_qty": "volume", "acc_trde_qty": "volume",
            "trde_prica": "amount"
        }
        df.rename(columns=rename_map, inplace=True)

        # 2. 숫자형 변환 (부호 제거 및 절댓값 처리)
        # 키움 데이터의 '+78800', '-78800' 등을 숫자로 바꾸기 위해 모든 컬럼 순회
        cols_to_fix = ["open", "high", "low", "close", "volume"]
        for col in cols_to_fix:
            if col in df.columns:
                # 💡 문자열 내의 +, - 기호를 제거하고 숫자로 변환 후 절댓값 취함
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('+', '').str.replace('-', ''), errors='coerce')

        # 3. 날짜 설정
        if 'date' in df.columns:
            # 분봉은 YYYYMMDDHHMMSS, 나머지는 YYYYMMDD
            fmt = "%Y%m%d%H%M%S" if chart_type == "min" else "%Y%m%d"
            df['date'] = pd.to_datetime(df['date'], format=fmt, errors='coerce')
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

        return df[["open", "high", "low", "close", "volume"]]
    
    def _save(self, df, code, chart_type):
        """FileManager를 이용한 차트 저장 (종목/업종 및 차트타입별 폴더 분리)"""
        if df is None or df.empty:
            return

        # 1. 코드 길이에 따라 저장 루트 디렉토리 결정 (종목: 6자리, 업종: 3자리)
        if len(code) > 3:
            root_dir = self.cfg.STOCK_CHART_DIR
        else:
            root_dir = self.cfg.INDEX_CHART_DIR
            
        # 2. 하위 폴더(day, min 등) 경로 설정 및 생성
        # 💡 exist_ok=True를 넣어야 폴더가 이미 있을 때 에러가 나지 않습니다.
        file_dir = root_dir / f"{chart_type}"
        file_dir.mkdir(parents=True, exist_ok=True) 
        
        # 3. 최종 파일 경로 설정 및 저장
        file_path = file_dir / f"{code}.parquet"
        
        # FileManager의 save 메서드가 경로(Path 객체)를 지원하므로 그대로 전달
        self.file_manager.save(df, file_path)

    def _load(self, code, chart_type):
        """저장된 경로 규칙(종목/업종별 폴더)에 맞춰 차트 데이터를 로드합니다."""
        # 1. 코드 길이에 따라 루트 디렉토리 결정 (저장 로직과 동일하게)
        if len(code) > 3:
            root_dir = self.cfg.STOCK_CHART_DIR
        else:
            root_dir = self.cfg.INDEX_CHART_DIR
            
        # 2. 하위 폴더 및 파일 경로 구성
        file_path = root_dir / f"{chart_type}" / f"{code}.parquet"
        
        # 3. 파일 존재 여부 확인 후 로드
        # FileManager.load는 파일이 없으면 내부적으로 None을 반환하도록 설계되어 있습니다.
        df = self.file_manager.load(file_path)
        
        if df is not None:
            # 로드 시에도 인덱스가 날짜 순으로 잘 정렬되어 있는지 보장하면 좋습니다.
            df.sort_index(inplace=True)
            
        return df

if __name__ == "__main__":
    cm = ChartManager()
    
    # 1. 종목 일봉 테스트 (삼성전자 005930)
    # df_stock = cm.get_chart(stk_cd="005930", chart_type="day")
    # print(df_stock.tail())

    # 2. 업종 일봉 테스트 (KOSPI 001)
    df_index = cm.get_chart(inds_cd="001", chart_type="day")
    if df_index is not None:
        print("\n🔍 업종 차트 데이터:")
        print(df_index.tail())