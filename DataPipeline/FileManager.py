import pandas as pd
import json
from pathlib import Path
import path_finder

class FileManager:
    def __init__(self):
        self.cfg = path_finder.get_cfg()

    def save(self, data, path, file_type=None):
        """
        데이터를 지정된 경로에 저장합니다.
        data: 저장할 객체 (DataFrame 또는 Dict)
        path: Path 객체 또는 문자열
        file_type: 'parquet', 'csv', 'json' (None일 경우 확장자로 자동 판별)
        """
        path = Path(path)
        if file_type is None:
            file_type = path.suffix.replace('.', '').lower()

        # 디렉토리가 없으면 생성 (안전장치)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if file_type == 'parquet':
                if isinstance(data, pd.DataFrame):
                    data.to_parquet(path, engine='pyarrow', index=True)
                else:
                    raise ValueError("Parquet 저장에는 DataFrame이 필요합니다.")
            
            elif file_type == 'csv':
                if isinstance(data, pd.DataFrame):
                    data.to_csv(path, index=False, encoding='utf-8-sig')
                else:
                    raise ValueError("CSV 저장에는 DataFrame이 필요합니다.")
            
            elif file_type == 'json':
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            
            # print(f"💾 파일 저장 완료: {path.name}")
            return True
        except Exception as e:
            print(f"❌ 파일 저장 실패 ({path}): {e}")
            return False

    def load(self, path, file_type=None):
        """
        지정된 경로의 파일을 읽어옵니다.
        """
        path = Path(path)
        if not path.exists():
            return None

        if file_type is None:
            file_type = path.suffix.replace('.', '').lower()

        try:
            if file_type == 'parquet':
                return pd.read_parquet(path)
            
            elif file_type == 'csv':
                # 💡 저장할 때 utf-8-sig를 썼으므로 읽을 때도 맞춰줍니다.
                # 한국어 환경에서 가장 범용적인 설정입니다.
                return pd.read_csv(path, encoding='utf-8-sig')
            
            elif file_type == 'json':
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                
        except UnicodeDecodeError:
            # 만약 다른 곳에서 만든 cp949(EUC-KR) 파일일 경우를 대비한 2차 방어
            try:
                return pd.read_csv(path, encoding='cp949')
            except Exception as e:
                print(f"❌ CSV 인코딩 에러 ({path}): {e}")
                return None
                        
        except Exception as e:
            print(f"❌ 파일 로드 실패 ({path}): {e}")
            return None