# ══════════════════════════════════════════════════════════════════════════════
# data_loader.py  —  데이터 로딩 및 그룹 설정 직렬화
# ══════════════════════════════════════════════════════════════════════════════
import json
import pandas as pd
import streamlit as st
from io import BytesIO
from config import COL_IDX


@st.cache_data
def load_excel(file_bytes: bytes, file_name: str) -> pd.DataFrame | None:
    """
    ERP 엑셀 파일을 읽어 정제된 DataFrame 반환.
    컬럼 인덱스는 config.COL_IDX 기준.
    실패 시 st.error 표시 후 None 반환.
    """
    try:
        df_raw = pd.read_excel(BytesIO(file_bytes), header=0, dtype=str)
        result = {}
        for name, idx in COL_IDX.items():
            result[name] = (
                df_raw.iloc[:, idx]
                if idx < len(df_raw.columns)
                else pd.Series([None] * len(df_raw))
            )
        df = pd.DataFrame(result)
        df["매출일"] = pd.to_datetime(df["매출일"], errors="coerce")
        for c in ["수량", "환율", "외화단가", "외화금액", "원화단가", "원화금액"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df = df.dropna(subset=["매출일"])
        df["연도"]   = df["매출일"].dt.year.astype(int)
        df["월"]     = df["매출일"].dt.month.astype(int)
        df["품목명"] = df["품목명"].fillna("(미분류)").str.strip()
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None


# ── 그룹 설정 직렬화 (Streamlit Cloud 대응: 다운로드/업로드 방식) ─────────────

def groups_to_json_bytes(groups: dict) -> bytes:
    """그룹 dict → JSON bytes (다운로드용)."""
    return json.dumps(groups, ensure_ascii=False, indent=2).encode("utf-8")


def json_bytes_to_groups(data: bytes) -> dict:
    """JSON bytes → 그룹 dict (업로드 후 파싱용). 형식 오류 시 빈 dict 반환."""
    try:
        parsed = json.loads(data.decode("utf-8"))
        if isinstance(parsed, dict):
            return {k: v for k, v in parsed.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}
