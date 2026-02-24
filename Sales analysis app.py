import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ── 페이지 설정 ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="매출 차이 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 스타일 ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-title { font-size: 1.8rem; font-weight: 700; color: #1f3864; margin-bottom: 0.2rem; }
    .sub-title  { font-size: 0.95rem; color: #555; margin-bottom: 1.5rem; }
    .metric-card {
        background: #f0f4ff; border-radius: 10px; padding: 16px 20px;
        border-left: 5px solid #4472c4; margin-bottom: 10px;
    }
    .metric-label { font-size: 0.8rem; color: #555; margin-bottom: 2px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #1f3864; }
    .positive { color: #1a7a4a; }
    .negative { color: #c0392b; }
    div[data-testid="stDataFrame"] { width: 100% !important; }
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #1f3864;
        border-bottom: 2px solid #4472c4; padding-bottom: 4px; margin: 1.2rem 0 0.8rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── 컬럼 매핑 (0-based index) ────────────────────────────────────────────────
# D=3, I=8, V=21, W=22, AB=27, AD=29, AE=30, AF=31, AI=34, AJ=35, AN=39, AO=40, BC=54
COL_IDX = {
    "매출일":    3,
    "매출처명":  8,
    "품목코드":  21,
    "품목명":    22,
    "단위":      27,
    "수량":      29,
    "환종":      30,
    "환율":      31,
    "외화단가":  34,
    "외화금액":  35,
    "원화단가":  39,
    "원화금액":  40,
    "품목계정":  54,
}

# ── 공통 함수 ────────────────────────────────────────────────────────────────
def load_excel(file):
    """엑셀 파일을 읽어 표준 컬럼명으로 반환"""
    try:
        df_raw = pd.read_excel(file, header=0, dtype=str)
        result = {}
        for name, idx in COL_IDX.items():
            if idx < len(df_raw.columns):
                result[name] = df_raw.iloc[:, idx]
            else:
                result[name] = pd.Series([None] * len(df_raw))
        df = pd.DataFrame(result)

        # 타입 변환
        df["매출일"]   = pd.to_datetime(df["매출일"], errors="coerce")
        for c in ["수량", "환율", "외화단가", "외화금액", "원화단가", "원화금액"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df = df.dropna(subset=["매출일"])
        df["연월"] = df["매출일"].dt.to_period("M")
        df["연도"] = df["매출일"].dt.year
        df["월"]   = df["매출일"].dt.month
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None


def variance_analysis(base: pd.DataFrame, curr: pd.DataFrame, group_cols: list) -> pd.DataFrame:
    """
    차이 분석 (Price / Quantity / FX Variance)
    P = 외화단가, Q = 수량, ER = 환율
    원화매출(KRW)은 ER=1 고정, P=원화단가 로 처리
    """
    def agg(df):
        g = df.copy()
        # KRW의 경우 환율을 1로 고정
        g["환율_adj"] = g.apply(lambda r: 1.0 if r["환종"] == "KRW" else r["환율"], axis=1)
        g["단가_adj"] = g.apply(lambda r: r["원화단가"] if r["환종"] == "KRW" else r["외화단가"], axis=1)
        return g.groupby(group_cols).agg(
            Q    = ("수량",    "sum"),
            P    = ("단가_adj", lambda x: (x * g.loc[x.index, "수량"]).sum() / x.size if x.size else 0),
            ER   = ("환율_adj", "mean"),
            원화매출 = ("원화금액", "sum"),
        ).reset_index()

    b = agg(base).rename(columns={"Q": "Q0", "P": "P0", "ER": "ER0", "원화매출": "매출0"})
    c = agg(curr).rename(columns={"Q": "Q1", "P": "P1", "ER": "ER1", "원화매출": "매출1"})

    m = pd.merge(b, c, on=group_cols, how="outer").fillna(0)

    m["단가차이"]  = (m["P1"]  - m["P0"])  * m["Q1"]  * m["ER0"]
    m["수량차이"]  = (m["Q1"]  - m["Q0"])  * m["P0"]  * m["ER0"]
    m["환율차이"]  = (m["ER1"] - m["ER0"]) * m["P1"]  * m["Q1"]
    m["총차이"]    = m["매출1"] - m["매출0"]
    m["검증"]      = m["단가차이"] + m["수량차이"] + m["환율차이"]  # ≈ 총차이

    return m


def fmt(val, unit="원"):
    """숫자 포맷"""
    if pd.isna(val):
        return "-"
    if unit == "원":
        return f"{val:,.0f}"
    return f"{val:,.1f}"


def color_val(val):
    if val > 0:
        return "positive"
    elif val < 0:
        return "negative"
    return ""


def styled_df(df: pd.DataFrame, money_cols: list):
    """금액 컬럼에 색상 및 포맷 적용"""
    def color_neg(v):
        try:
            return "color: #c0392b" if float(v) < 0 else "color: #1a7a4a" if float(v) > 0 else ""
        except:
            return ""

    fmt_dict = {c: "{:,.0f}" for c in money_cols if c in df.columns}
    styler = df.style.format(fmt_dict, na_rep="-")
    for c in money_cols:
        if c in df.columns:
            styler = styler.applymap(color_neg, subset=[c])
    return styler


# ── 사이드바 ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 파일 업로드")
    st.markdown("ERP에서 내려받은 매출실적 엑셀 파일을 업로드하세요.")

    st.markdown("### 📌 기준 기간 (비교 대상)")
    file_base = st.file_uploader("기준 매출파일 (전년·전월)", type=["xlsx", "xls"], key="base")

    st.markdown("### 📌 실적 기간 (분석 대상)")
    file_curr = st.file_uploader("실적 매출파일 (당기)", type=["xlsx", "xls"], key="curr")

    st.markdown("---")
    st.markdown("### ⚙️ 분석 설정")
    group_by = st.multiselect(
        "그룹핑 기준",
        ["매출처명", "품목코드", "품목명", "품목계정", "환종"],
        default=["매출처명", "품목명"],
    )
    show_krw_only = st.checkbox("원화 환산 기준으로만 표시", value=True)

    st.markdown("---")
    st.caption("ℹ️ 단가차이 + 수량차이 + 환율차이 = 총차이 (검증)")


# ── 메인 영역 ────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📊 매출 차이 분석 (Variance Analysis)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">단가차이 · 수량차이 · 환율차이 분해 분석</div>', unsafe_allow_html=True)

if not file_base or not file_curr:
    st.info("👈 왼쪽 사이드바에서 **기준 매출파일**과 **실적 매출파일**을 모두 업로드하세요.")

    with st.expander("📋 엑셀 파일 컬럼 구성 안내"):
        col_info = pd.DataFrame({
            "열": ["D", "I", "V", "W", "AB", "AD", "AE", "AF", "AI", "AJ", "AN", "AO", "BC"],
            "내용": ["매출일(YYYY-MM-DD)", "매출처명", "품목코드", "품목명", "단위",
                     "수량", "환종(KRW/USD)", "환율", "(외화)판매단가", "(외화)판매금액",
                     "(장부단가)원화환산판매단가", "(장부금액)원화환산판매금액",
                     "품목계정(제품/상품/원재료/부재료/제조-수선비)"],
        })
        st.dataframe(col_info, use_container_width=True, hide_index=True)
    st.stop()

# ── 데이터 로딩 ───────────────────────────────────────────────────────────────
with st.spinner("파일 분석 중..."):
    df_base = load_excel(file_base)
    df_curr = load_excel(file_curr)

if df_base is None or df_curr is None:
    st.stop()

if not group_by:
    st.warning("그룹핑 기준을 1개 이상 선택해주세요.")
    st.stop()

# ── 기간 정보 ────────────────────────────────────────────────────────────────
base_period = f"{df_base['매출일'].min().strftime('%Y-%m-%d')} ~ {df_base['매출일'].max().strftime('%Y-%m-%d')}"
curr_period = f"{df_curr['매출일'].min().strftime('%Y-%m-%d')} ~ {df_curr['매출일'].max().strftime('%Y-%m-%d')}"

col1, col2 = st.columns(2)
col1.info(f"📅 **기준 기간**: {base_period}  (행수: {len(df_base):,})")
col2.success(f"📅 **실적 기간**: {curr_period}  (행수: {len(df_curr):,})")

# ── 차이 분석 실행 ────────────────────────────────────────────────────────────
va = variance_analysis(df_base, df_curr, group_by)

# ── KPI 요약 ──────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📈 종합 요약</div>', unsafe_allow_html=True)

total_base = va["매출0"].sum()
total_curr = va["매출1"].sum()
total_diff = va["총차이"].sum()
price_var  = va["단가차이"].sum()
qty_var    = va["수량차이"].sum()
fx_var     = va["환율차이"].sum()

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)

def kpi(col, label, value, unit="원"):
    sign = "+" if value > 0 else ""
    css  = "positive" if value > 0 else "negative" if value < 0 else ""
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css}">{sign}{value:,.0f} {unit}</div>
    </div>""", unsafe_allow_html=True)

k1.markdown(f'<div class="metric-card"><div class="metric-label">기준 매출 (원화)</div><div class="metric-value">{total_base:,.0f} 원</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="metric-card"><div class="metric-label">실적 매출 (원화)</div><div class="metric-value">{total_curr:,.0f} 원</div></div>', unsafe_allow_html=True)
kpi(k3, "총 차이", total_diff)
kpi(k4, "① 단가 차이 (Price Variance)", price_var)
kpi(k5, "② 수량 차이 (Quantity Variance)", qty_var)
kpi(k6, "③ 환율 차이 (FX Variance)", fx_var)

# ── 상세 분석 테이블 ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 상세 차이 분석 테이블</div>', unsafe_allow_html=True)

display_cols = group_by + ["매출0", "매출1", "총차이", "단가차이", "수량차이", "환율차이"]
if not show_krw_only:
    display_cols += ["Q0", "Q1", "P0", "P1", "ER0", "ER1"]

va_disp = va[display_cols].copy()
va_disp = va_disp.sort_values("총차이")

rename_map = {
    "매출0":   f"기준매출(원)",
    "매출1":   f"실적매출(원)",
    "총차이":  "총차이(원)",
    "단가차이": "①단가차이(원)",
    "수량차이": "②수량차이(원)",
    "환율차이": "③환율차이(원)",
    "Q0": "기준수량", "Q1": "실적수량",
    "P0": "기준단가", "P1": "실적단가",
    "ER0": "기준환율", "ER1": "실적환율",
}
va_disp = va_disp.rename(columns=rename_map)

money_cols = ["기준매출(원)", "실적매출(원)", "총차이(원)", "①단가차이(원)", "②수량차이(원)", "③환율차이(원)",
              "기준수량", "실적수량", "기준단가", "실적단가", "기준환율", "실적환율"]

st.dataframe(
    styled_df(va_disp, money_cols),
    use_container_width=True,
    height=450,
)

# ── 차이 구성 시각화 ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 차이 구성 요소 분석 (상위/하위 20개)</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go

    # Waterfall chart: 전체 합산
    fig_wf = go.Figure(go.Waterfall(
        name="차이 분해",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["기준 매출", "①단가 차이", "②수량 차이", "③환율 차이", "실적 매출"],
        y=[total_base, price_var, qty_var, fx_var, 0],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#1a7a4a"}},
        decreasing={"marker": {"color": "#c0392b"}},
        totals={"marker": {"color": "#4472c4"}},
        text=[f"{v:,.0f}" for v in [total_base, price_var, qty_var, fx_var, total_curr]],
        textposition="outside",
    ))
    fig_wf.update_layout(
        title="매출 차이 Waterfall Chart (원화 기준)",
        height=400,
        margin=dict(t=50, b=20),
        yaxis_title="원(₩)",
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Bar: 그룹별 총차이 상위/하위
    va_sorted = va.set_index(group_by[0] if len(group_by) == 1 else va[group_by].apply(lambda r: " | ".join(r.astype(str)), axis=1))
    va_sorted = va[["총차이"]].copy()
    va_sorted.index = va[group_by].apply(lambda r: " | ".join(r.astype(str)), axis=1)
    va_sorted = va_sorted["총차이"].sort_values()

    top_n = 20
    plot_data = pd.concat([va_sorted.head(top_n // 2), va_sorted.tail(top_n // 2)])

    fig_bar = go.Figure(go.Bar(
        x=plot_data.values,
        y=plot_data.index,
        orientation="h",
        marker_color=["#c0392b" if v < 0 else "#1a7a4a" for v in plot_data.values],
        text=[f"{v:,.0f}" for v in plot_data.values],
        textposition="outside",
    ))
    fig_bar.update_layout(
        title=f"그룹별 총 매출 차이 (상위/하위 {top_n//2}개)",
        height=max(400, len(plot_data) * 28),
        margin=dict(l=200, r=80, t=50, b=20),
        xaxis_title="원(₩)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

except ImportError:
    st.info("plotly가 설치되지 않아 차트를 표시할 수 없습니다. `pip install plotly`를 실행하세요.")

# ── 엑셀 다운로드 ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">⬇️ 결과 다운로드</div>', unsafe_allow_html=True)

@st.cache_data
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="차이분석")
    return buf.getvalue()

excel_bytes = to_excel_bytes(va_disp.reset_index(drop=True))
st.download_button(
    label="📥 차이분석 결과 엑셀 다운로드",
    data=excel_bytes,
    file_name="매출차이분석.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 원본 데이터 탭 ────────────────────────────────────────────────────────────
with st.expander("🗂️ 원본 데이터 확인"):
    tab1, tab2 = st.tabs(["기준 데이터", "실적 데이터"])
    with tab1:
        st.dataframe(df_base, use_container_width=True, height=300)
    with tab2:
        st.dataframe(df_curr, use_container_width=True, height=300)
