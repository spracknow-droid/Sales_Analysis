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
    .main-title {
        font-size: 1.8rem; font-weight: 700; color: #1f3864; margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 0.95rem; color: #555; margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #f0f4ff; border-radius: 10px; padding: 16px 20px;
        border-left: 5px solid #4472c4; margin-bottom: 10px;
    }
    .metric-label { font-size: 0.8rem; color: #555; margin-bottom: 2px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #1f3864; }
    .positive { color: #1a7a4a; }
    .negative { color: #c0392b; }
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #1f3864;
        border-bottom: 2px solid #4472c4; padding-bottom: 4px;
        margin: 1.4rem 0 0.8rem 0;
    }
    div[data-testid="stDataFrame"] { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ── 컬럼 매핑 (0-based index) ────────────────────────────────────────────────
# D=3, I=8, V=21, W=22, AB=27, AD=29, AE=30, AF=31, AI=34, AJ=35, AN=39, AO=40, BC=54
COL_IDX = {
    "매출일":   3,
    "매출처명": 8,
    "품목코드": 21,
    "품목명":   22,
    "단위":     27,
    "수량":     29,
    "환종":     30,
    "환율":     31,
    "외화단가": 34,
    "외화금액": 35,
    "원화단가": 39,
    "원화금액": 40,
    "품목계정": 54,
}

# ── 데이터 로딩 ───────────────────────────────────────────────────────────────
@st.cache_data
def load_excel(file_bytes, file_name):
    try:
        df_raw = pd.read_excel(BytesIO(file_bytes), header=0, dtype=str)
        result = {}
        for name, idx in COL_IDX.items():
            if idx < len(df_raw.columns):
                result[name] = df_raw.iloc[:, idx]
            else:
                result[name] = pd.Series([None] * len(df_raw))
        df = pd.DataFrame(result)

        df["매출일"] = pd.to_datetime(df["매출일"], errors="coerce")
        for c in ["수량", "환율", "외화단가", "외화금액", "원화단가", "원화금액"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df = df.dropna(subset=["매출일"])
        df["연도"] = df["매출일"].dt.year.astype(int)
        df["월"]   = df["매출일"].dt.month.astype(int)
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None


# ── 차이 분석 ────────────────────────────────────────────────────────────────
def variance_analysis(base, curr, group_cols):
    def agg(df):
        g = df.copy()
        g["환율_adj"] = g.apply(
            lambda r: 1.0 if str(r["환종"]).strip().upper() == "KRW" else r["환율"], axis=1
        )
        g["단가_adj"] = g.apply(
            lambda r: r["원화단가"] if str(r["환종"]).strip().upper() == "KRW" else r["외화단가"], axis=1
        )
        grp = g.groupby(group_cols)
        Q  = grp["수량"].sum()
        PQ = grp.apply(lambda x: (x["단가_adj"] * x["수량"]).sum())
        P  = (PQ / Q.replace(0, np.nan)).fillna(0)
        ER = grp["환율_adj"].mean()
        rev = grp["원화금액"].sum()
        return pd.DataFrame({"Q": Q, "P": P, "ER": ER, "원화매출": rev}).reset_index()

    b = agg(base).rename(columns={"Q": "Q0", "P": "P0", "ER": "ER0", "원화매출": "매출0"})
    c = agg(curr).rename(columns={"Q": "Q1", "P": "P1", "ER": "ER1", "원화매출": "매출1"})

    m = pd.merge(b, c, on=group_cols, how="outer").fillna(0)
    m["단가차이"] = (m["P1"]  - m["P0"])  * m["Q1"]  * m["ER0"]
    m["수량차이"] = (m["Q1"]  - m["Q0"])  * m["P0"]  * m["ER0"]
    m["환율차이"] = (m["ER1"] - m["ER0"]) * m["P1"]  * m["Q1"]
    m["총차이"]   = m["매출1"] - m["매출0"]
    return m


# ── 스타일 적용 ───────────────────────────────────────────────────────────────
def styled_df(df, money_cols):
    def color_cell(v):
        try:
            fv = float(v)
            if fv < 0:
                return "color: #c0392b; font-weight:600"
            elif fv > 0:
                return "color: #1a7a4a; font-weight:600"
        except Exception:
            pass
        return ""

    fmt_dict = {c: "{:,.0f}" for c in money_cols if c in df.columns}
    styler = df.style.format(fmt_dict, na_rep="-")
    for c in money_cols:
        if c in df.columns:
            styler = styler.applymap(color_cell, subset=[c])
    return styler


# ── KPI 카드 ─────────────────────────────────────────────────────────────────
def kpi_card(col, label, value, neutral=False):
    sign = "+" if value > 0 else ""
    if neutral:
        css = ""
    else:
        css = "positive" if value > 0 else ("negative" if value < 0 else "")
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {css}">{sign}{value:,.0f} 원</div>
    </div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# 사이드바
# ════════════════════════════════════════════════════════════════════════════
MONTH_KR = {
    1:"1월", 2:"2월", 3:"3월", 4:"4월", 5:"5월", 6:"6월",
    7:"7월", 8:"8월", 9:"9월", 10:"10월", 11:"11월", 12:"12월"
}

with st.sidebar:
    st.markdown("## 📂 파일 업로드")
    st.markdown("ERP 매출실적 엑셀 파일 **1개**를 업로드하세요.")
    uploaded = st.file_uploader(
        "매출실적 파일 (.xlsx / .xls)",
        type=["xlsx", "xls"],
    )

    st.markdown("---")

    df_all   = None
    df_base  = None
    df_curr  = None
    group_by = []
    show_detail = False

    if uploaded:
        file_bytes = uploaded.read()
        df_all = load_excel(file_bytes, uploaded.name)

        if df_all is not None:
            years  = sorted(df_all["연도"].unique())
            months = sorted(df_all["월"].unique())

            st.markdown("### 📌 기준 기간 (비교 대상)")
            base_year  = st.selectbox("기준 연도", years, index=0, key="by")
            avail_base = sorted(df_all[df_all["연도"] == base_year]["월"].unique())
            base_month = st.selectbox(
                "기준 월", avail_base,
                format_func=lambda x: MONTH_KR[x],
                index=0, key="bm"
            )

            st.markdown("### 📌 실적 기간 (분석 대상)")
            curr_year  = st.selectbox("실적 연도", years, index=len(years)-1, key="cy")
            avail_curr = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
            curr_month = st.selectbox(
                "실적 월", avail_curr,
                format_func=lambda x: MONTH_KR[x],
                index=len(avail_curr)-1, key="cm"
            )

            st.markdown("---")
            st.markdown("### ⚙️ 분석 설정")
            group_by = st.multiselect(
                "그룹핑 기준",
                ["매출처명", "품목코드", "품목명", "품목계정", "환종"],
                default=["매출처명", "품목명"],
            )
            show_detail = st.checkbox("수량·단가·환율 상세 표시", value=False)
            st.markdown("---")
            st.caption("ℹ️ 단가차이 + 수량차이 + 환율차이 ≈ 총차이")

            df_base = df_all[(df_all["연도"] == base_year) & (df_all["월"] == base_month)].copy()
            df_curr = df_all[(df_all["연도"] == curr_year) & (df_all["월"] == curr_month)].copy()

            base_label = f"{base_year}년 {MONTH_KR[base_month]}"
            curr_label = f"{curr_year}년 {MONTH_KR[curr_month]}"


# ════════════════════════════════════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">📊 매출 차이 분석 (Variance Analysis)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">단가차이 · 수량차이 · 환율차이 분해 분석</div>', unsafe_allow_html=True)

if df_all is None:
    st.info("👈 왼쪽 사이드바에서 **ERP 매출실적 파일**을 업로드하세요.")
    with st.expander("📋 엑셀 파일 컬럼 구성 안내"):
        col_info = pd.DataFrame({
            "열":  ["D", "I", "V", "W", "AB", "AD", "AE", "AF", "AI", "AJ", "AN", "AO", "BC"],
            "내용": [
                "매출일 (YYYY-MM-DD)", "매출처명", "품목코드", "품목명", "단위",
                "수량", "환종 (KRW/USD)", "환율",
                "(외화)판매단가", "(외화)판매금액",
                "(장부단가)원화환산판매단가", "(장부금액)원화환산판매금액",
                "품목계정 (제품/상품/원재료/부재료/제조-수선비)",
            ],
        })
        st.dataframe(col_info, use_container_width=True, hide_index=True)
    st.stop()

if not group_by:
    st.warning("그룹핑 기준을 1개 이상 선택해주세요.")
    st.stop()

# ── 기간 상태 표시 ────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
if df_base.empty:
    c1.warning(f"⚠️ 기준 기간 ({base_label}) 데이터가 없습니다.")
else:
    c1.info(f"📅 **기준 기간**: {base_label}  ({len(df_base):,}건)")

if df_curr.empty:
    c2.warning(f"⚠️ 실적 기간 ({curr_label}) 데이터가 없습니다.")
else:
    c2.success(f"📅 **실적 기간**: {curr_label}  ({len(df_curr):,}건)")

if df_base.empty and df_curr.empty:
    st.error("선택한 두 기간 모두 데이터가 없습니다. 연도/월을 다시 확인하세요.")
    st.stop()

# ── 차이 분석 실행 ────────────────────────────────────────────────────────────
with st.spinner("차이 분석 중..."):
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

kpi_card(k1, f"기준 매출 ({base_label})", total_base, neutral=True)
kpi_card(k2, f"실적 매출 ({curr_label})", total_curr, neutral=True)
kpi_card(k3, "총 차이 (실적 − 기준)", total_diff)
kpi_card(k4, "① 단가 차이 (Price Variance)", price_var)
kpi_card(k5, "② 수량 차이 (Quantity Variance)", qty_var)
kpi_card(k6, "③ 환율 차이 (FX Variance)", fx_var)

# ── 상세 분석 테이블 ──────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 상세 차이 분석 테이블</div>', unsafe_allow_html=True)

display_cols = group_by + ["매출0", "매출1", "총차이", "단가차이", "수량차이", "환율차이"]
if show_detail:
    display_cols += ["Q0", "Q1", "P0", "P1", "ER0", "ER1"]

va_disp = va[display_cols].copy().sort_values("총차이")

rename_map = {
    "매출0":    f"기준매출(원) [{base_label}]",
    "매출1":    f"실적매출(원) [{curr_label}]",
    "총차이":   "총차이(원)",
    "단가차이": "①단가차이(원)",
    "수량차이": "②수량차이(원)",
    "환율차이": "③환율차이(원)",
    "Q0": "기준수량", "Q1": "실적수량",
    "P0": "기준단가", "P1": "실적단가",
    "ER0": "기준환율", "ER1": "실적환율",
}
va_disp = va_disp.rename(columns=rename_map)

money_cols = [
    f"기준매출(원) [{base_label}]", f"실적매출(원) [{curr_label}]",
    "총차이(원)", "①단가차이(원)", "②수량차이(원)", "③환율차이(원)",
    "기준수량", "실적수량", "기준단가", "실적단가", "기준환율", "실적환율",
]

st.dataframe(
    styled_df(va_disp, money_cols),
    use_container_width=True,
    height=460,
)

# ── 시각화 ───────────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 차이 구성 요소 시각화</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go

    # Waterfall
    fig_wf = go.Figure(go.Waterfall(
        name="차이 분해",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[f"기준매출({base_label})", "①단가 차이", "②수량 차이", "③환율 차이", f"실적매출({curr_label})"],
        y=[total_base, price_var, qty_var, fx_var, 0],
        connector={"line": {"color": "#aaa"}},
        increasing={"marker": {"color": "#1a7a4a"}},
        decreasing={"marker": {"color": "#c0392b"}},
        totals={"marker": {"color": "#4472c4"}},
        text=[f"{v:,.0f}" for v in [total_base, price_var, qty_var, fx_var, total_curr]],
        textposition="outside",
    ))
    fig_wf.update_layout(
        title=f"매출 차이 Waterfall (원화 기준) │ {base_label} → {curr_label}",
        height=420,
        margin=dict(t=55, b=30, l=40, r=40),
        yaxis_title="원(₩)",
        font=dict(family="Malgun Gothic, AppleGothic, sans-serif"),
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Bar: 그룹별 총차이
    label_col = va[group_by].apply(lambda r: " | ".join(r.astype(str)), axis=1)
    va_bar = pd.Series(va["총차이"].values, index=label_col).sort_values()

    top_n = 20
    if len(va_bar) > top_n:
        half = top_n // 2
        va_bar = pd.concat([va_bar.head(half), va_bar.tail(half)])

    fig_bar = go.Figure(go.Bar(
        x=va_bar.values,
        y=va_bar.index,
        orientation="h",
        marker_color=["#c0392b" if v < 0 else "#1a7a4a" for v in va_bar.values],
        text=[f"{v:,.0f}" for v in va_bar.values],
        textposition="outside",
    ))
    fig_bar.update_layout(
        title=f"그룹별 총 매출 차이 (상위·하위 {top_n//2}개)",
        height=max(400, len(va_bar) * 30),
        margin=dict(l=220, r=100, t=50, b=20),
        xaxis_title="원(₩)",
        font=dict(family="Malgun Gothic, AppleGothic, sans-serif"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

except ImportError:
    st.info("plotly가 설치되지 않아 차트를 표시할 수 없습니다.")

# ── 엑셀 다운로드 ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">⬇️ 결과 다운로드</div>', unsafe_allow_html=True)

def to_excel_bytes(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="차이분석")
    return buf.getvalue()

excel_bytes = to_excel_bytes(va_disp.reset_index(drop=True))
st.download_button(
    label="📥 차이분석 결과 엑셀 다운로드",
    data=excel_bytes,
    file_name=f"매출차이분석_{base_label}vs{curr_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 원본 데이터 확인 ──────────────────────────────────────────────────────────
with st.expander("🗂️ 원본 데이터 확인"):
    tab1, tab2 = st.tabs([f"기준 데이터 ({base_label})", f"실적 데이터 ({curr_label})"])
    with tab1:
        st.dataframe(df_base.reset_index(drop=True), use_container_width=True, height=300)
    with tab2:
        st.dataframe(df_curr.reset_index(drop=True), use_container_width=True, height=300)
