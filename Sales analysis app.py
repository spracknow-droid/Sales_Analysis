import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="매출 차이 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# 스타일
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* 전체 폰트 */
html, body, [class*="css"] { font-family: 'Malgun Gothic', 'AppleGothic', sans-serif; }

/* 타이틀 */
.main-title { font-size: 1.7rem; font-weight: 800; color: #1f3864; margin-bottom: 0.1rem; }
.sub-title  { font-size: 0.9rem; color: #777; margin-bottom: 1.2rem; }

/* 섹션 헤더 */
.section-header {
    font-size: 1.05rem; font-weight: 700; color: #1f3864;
    border-bottom: 2px solid #4472c4; padding-bottom: 5px;
    margin: 1.5rem 0 0.8rem 0;
}

/* KPI 카드 */
.kpi-row { display: flex; gap: 12px; margin-bottom: 12px; }
.kpi-card {
    flex: 1; background: #f5f7ff; border-radius: 10px;
    padding: 14px 18px; border-left: 5px solid #4472c4;
}
.kpi-label { font-size: 0.75rem; color: #666; margin-bottom: 3px; }
.kpi-value { font-size: 1.25rem; font-weight: 800; color: #1f3864; }
.kpi-pos   { color: #1a7a4a; }
.kpi-neg   { color: #c0392b; }

/* 품목 버튼 그리드 */
.item-grid {
    display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 16px 0;
}
.item-btn {
    padding: 6px 14px; border-radius: 20px; font-size: 0.82rem;
    font-weight: 600; cursor: pointer; border: 2px solid #4472c4;
    background: white; color: #4472c4; transition: all 0.15s;
    white-space: nowrap;
}
.item-btn:hover  { background: #dce6ff; }
.item-btn.active { background: #4472c4; color: white; }

/* 분석 모드 탭 */
.mode-tabs { display: flex; gap: 0; margin-bottom: 16px; }
.mode-tab {
    flex: 1; text-align: center; padding: 9px 0; font-size: 0.88rem;
    font-weight: 700; cursor: pointer; border: 2px solid #4472c4;
    background: white; color: #4472c4;
}
.mode-tab:first-child { border-radius: 8px 0 0 8px; }
.mode-tab:last-child  { border-radius: 0 8px 8px 0; border-left: none; }
.mode-tab.active { background: #4472c4; color: white; }

/* 기간 배지 */
.period-badge {
    display: inline-block; border-radius: 6px;
    padding: 4px 12px; font-size: 0.8rem; font-weight: 600; margin: 2px 4px;
}
.badge-base { background: #e8f0fe; color: #1a56c4; }
.badge-curr { background: #e6f4ea; color: #1a7a4a; }

div[data-testid="stDataFrame"] { width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 상수
# ══════════════════════════════════════════════════════════════════════════════
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

MONTH_KR = {i: f"{i}월" for i in range(1, 13)}

# ══════════════════════════════════════════════════════════════════════════════
# 함수 정의
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load_excel(file_bytes, file_name):
    try:
        df_raw = pd.read_excel(BytesIO(file_bytes), header=0, dtype=str)
        result = {}
        for name, idx in COL_IDX.items():
            result[name] = df_raw.iloc[:, idx] if idx < len(df_raw.columns) else pd.Series([None] * len(df_raw))
        df = pd.DataFrame(result)

        df["매출일"] = pd.to_datetime(df["매출일"], errors="coerce")
        for c in ["수량", "환율", "외화단가", "외화금액", "원화단가", "원화금액"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        df = df.dropna(subset=["매출일"])
        df["연도"] = df["매출일"].dt.year.astype(int)
        df["월"]   = df["매출일"].dt.month.astype(int)
        df["품목명"] = df["품목명"].fillna("(미분류)").str.strip()
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None


def variance_analysis(base, curr):
    """품목명 기준 차이 분석"""
    group_cols = ["품목명"]

    def agg(df):
        if df.empty:
            return pd.DataFrame(columns=["품목명", "Q", "P", "ER", "원화매출"])
        g = df.copy()
        g["환율_adj"] = g.apply(
            lambda r: 1.0 if str(r["환종"]).strip().upper() == "KRW" else float(r["환율"]), axis=1
        )
        g["단가_adj"] = g.apply(
            lambda r: float(r["원화단가"]) if str(r["환종"]).strip().upper() == "KRW" else float(r["외화단가"]), axis=1
        )
        grp = g.groupby(group_cols)
        Q   = grp["수량"].sum()
        PQ  = grp.apply(lambda x: (x["단가_adj"] * x["수량"]).sum())
        P   = (PQ / Q.replace(0, np.nan)).fillna(0)
        ER  = grp["환율_adj"].mean()
        rev = grp["원화금액"].sum()
        return pd.DataFrame({"Q": Q, "P": P, "ER": ER, "원화매출": rev}).reset_index()

    b = agg(base).rename(columns={"Q": "Q0", "P": "P0", "ER": "ER0", "원화매출": "매출0"})
    c = agg(curr).rename(columns={"Q": "Q1", "P": "P1", "ER": "ER1", "원화매출": "매출1"})

    m = pd.merge(b, c, on="품목명", how="outer").fillna(0)
    m["단가차이"] = (m["P1"]  - m["P0"])  * m["Q1"]  * m["ER0"]
    m["수량차이"] = (m["Q1"]  - m["Q0"])  * m["P0"]  * m["ER0"]
    m["환율차이"] = (m["ER1"] - m["ER0"]) * m["P1"]  * m["Q1"]
    m["총차이"]   = m["매출1"] - m["매출0"]
    return m


def styled_df(df, money_cols):
    def color_cell(v):
        try:
            fv = float(v)
            if fv < 0:   return "color:#c0392b; font-weight:600"
            elif fv > 0: return "color:#1a7a4a; font-weight:600"
        except Exception:
            pass
        return ""

    fmt_dict = {c: "{:,.0f}" for c in money_cols if c in df.columns}
    styler = df.style.format(fmt_dict, na_rep="-")
    for c in money_cols:
        if c in df.columns:
            styler = styler.applymap(color_cell, subset=[c])
    return styler


def kpi_card(col, label, value, neutral=False):
    sign = "+" if value > 0 else ""
    css  = "" if neutral else ("kpi-pos" if value > 0 else ("kpi-neg" if value < 0 else ""))
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {css}">{sign}{value:,.0f} 원</div>
    </div>""", unsafe_allow_html=True)


def render_waterfall(total_base, price_var, qty_var, fx_var, total_curr, base_label, curr_label):
    import plotly.graph_objects as go
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[f"기준\n({base_label})", "①단가\n차이", "②수량\n차이", "③환율\n차이", f"실적\n({curr_label})"],
        y=[total_base, price_var, qty_var, fx_var, 0],
        connector={"line": {"color": "#ccc"}},
        increasing={"marker": {"color": "#1a7a4a"}},
        decreasing={"marker": {"color": "#c0392b"}},
        totals={"marker": {"color": "#4472c4"}},
        text=[f"{v:,.0f}" for v in [total_base, price_var, qty_var, fx_var, total_curr]],
        textposition="outside",
    ))
    fig.update_layout(
        height=380, margin=dict(t=30, b=20, l=30, r=30),
        yaxis_title="원(₩)",
        font=dict(family="Malgun Gothic, AppleGothic, sans-serif", size=12),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════════════════════
df_all = None

with st.sidebar:
    st.markdown("## 📂 파일 업로드")
    uploaded = st.file_uploader("ERP 매출실적 (.xlsx / .xls)", type=["xlsx", "xls"])

    st.markdown("---")

    if uploaded:
        file_bytes = uploaded.read()
        df_all = load_excel(file_bytes, uploaded.name)

    if df_all is not None:
        # ── 실적 연월 선택 (단일) ────────────────────────────────────────────
        st.markdown("### 📅 실적 연월 선택")
        avail_years  = sorted(df_all["연도"].unique())
        avail_months = sorted(df_all["월"].unique())

        curr_year  = st.selectbox("실적 연도", avail_years, index=len(avail_years)-1)
        avail_m    = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
        curr_month = st.selectbox("실적 월", avail_m, format_func=lambda x: MONTH_KR[x], index=len(avail_m)-1)

        # ── 분석 모드 선택 ───────────────────────────────────────────────────
        st.markdown("### 🔀 분석 모드")
        mode = st.radio(
            "기준 기간",
            ["전년 동월 대비 (YoY)", "전월 대비 (MoM)"],
            index=0,
        )

        # 기준 기간 자동 계산
        if mode == "전년 동월 대비 (YoY)":
            base_year  = curr_year - 1
            base_month = curr_month
        else:  # MoM
            if curr_month == 1:
                base_year  = curr_year - 1
                base_month = 12
            else:
                base_year  = curr_year
                base_month = curr_month - 1

        base_label = f"{base_year}년 {MONTH_KR[base_month]}"
        curr_label = f"{curr_year}년 {MONTH_KR[curr_month]}"

        st.markdown(
            f'<div style="margin-top:6px; font-size:0.82rem;">'
            f'<span class="period-badge badge-base">기준: {base_label}</span><br/>'
            f'<span class="period-badge badge-curr">실적: {curr_label}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown("### ⚙️ 표시 설정")
        show_detail = st.checkbox("수량·단가·환율 상세 컬럼 표시", value=False)
        st.caption("ℹ️ 단가차이 + 수량차이 + 환율차이 ≈ 총차이")

        # 기간 데이터 필터
        df_base = df_all[(df_all["연도"] == base_year)  & (df_all["월"] == base_month)].copy()
        df_curr = df_all[(df_all["연도"] == curr_year)  & (df_all["월"] == curr_month)].copy()

    else:
        base_label = curr_label = ""
        df_base = df_curr = None
        show_detail = False


# ══════════════════════════════════════════════════════════════════════════════
# 메인 화면
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">📊 매출 차이 분석</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">품목별 단가차이 · 수량차이 · 환율차이 분해 분석</div>', unsafe_allow_html=True)

# 파일 미업로드
if df_all is None:
    st.info("👈 왼쪽 사이드바에서 **ERP 매출실적 파일**을 업로드하세요.")
    with st.expander("📋 엑셀 파일 컬럼 구성 안내"):
        col_info = pd.DataFrame({
            "열":  ["D","I","V","W","AB","AD","AE","AF","AI","AJ","AN","AO","BC"],
            "내용": [
                "매출일(YYYY-MM-DD)","매출처명","품목코드","품목명","단위",
                "수량","환종(KRW/USD)","환율",
                "(외화)판매단가","(외화)판매금액",
                "(장부단가)원화환산판매단가","(장부금액)원화환산판매금액",
                "품목계정(제품/상품/원재료/부재료/제조-수선비)",
            ],
        })
        st.dataframe(col_info, use_container_width=True, hide_index=True)
    st.stop()

# ── 기간 유효성 확인 ──────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
base_ok = not df_base.empty
curr_ok = not df_curr.empty

c1.markdown(
    f'<div style="background:#e8f0fe;border-radius:8px;padding:10px 16px;">'
    f'<b>기준 기간</b>: {base_label}&nbsp;&nbsp;'
    f'{"✅ " + str(len(df_base)) + "건" if base_ok else "⚠️ 데이터 없음"}'
    f'</div>', unsafe_allow_html=True
)
c2.markdown(
    f'<div style="background:#e6f4ea;border-radius:8px;padding:10px 16px;">'
    f'<b>실적 기간</b>: {curr_label}&nbsp;&nbsp;'
    f'{"✅ " + str(len(df_curr)) + "건" if curr_ok else "⚠️ 데이터 없음"}'
    f'</div>', unsafe_allow_html=True
)
st.markdown("<br/>", unsafe_allow_html=True)

if not base_ok and not curr_ok:
    st.error("두 기간 모두 데이터가 없습니다. 실적 연월 또는 파일을 확인하세요.")
    st.stop()

# ── 차이 분석 ────────────────────────────────────────────────────────────────
with st.spinner("분석 중..."):
    va = variance_analysis(df_base, df_curr)

# ══════════════════════════════════════════════════════════════════════════════
# 품목 선택 버튼 그리드
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📦 품목 선택</div>', unsafe_allow_html=True)

all_items = sorted(va["품목명"].unique())

# session_state 초기화
if "selected_items" not in st.session_state:
    st.session_state.selected_items = set(all_items)

# 전체선택 / 전체해제 버튼
ctrl1, ctrl2, ctrl3 = st.columns([1, 1, 8])
with ctrl1:
    if st.button("✅ 전체 선택", use_container_width=True):
        st.session_state.selected_items = set(all_items)
with ctrl2:
    if st.button("⬜ 전체 해제", use_container_width=True):
        st.session_state.selected_items = set()

# 품목 토글 버튼 (5열 그리드)
cols_per_row = 5
rows = [all_items[i:i+cols_per_row] for i in range(0, len(all_items), cols_per_row)]

for row_items in rows:
    btn_cols = st.columns(cols_per_row)
    for col, item in zip(btn_cols, row_items):
        is_active = item in st.session_state.selected_items
        btn_style = (
            "background:#4472c4; color:white; border:2px solid #4472c4;"
            if is_active
            else "background:white; color:#4472c4; border:2px solid #4472c4;"
        )
        with col:
            label = f"{'✔ ' if is_active else ''}{item}"
            if st.button(
                label,
                key=f"btn_{item}",
                use_container_width=True,
            ):
                if item in st.session_state.selected_items:
                    st.session_state.selected_items.discard(item)
                else:
                    st.session_state.selected_items.add(item)
                st.rerun()

selected_items = list(st.session_state.selected_items)

if not selected_items:
    st.warning("품목을 1개 이상 선택하세요.")
    st.stop()

# 선택된 품목으로 필터
va_filtered = va[va["품목명"].isin(selected_items)].copy()

# ══════════════════════════════════════════════════════════════════════════════
# KPI 요약
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 종합 요약</div>', unsafe_allow_html=True)

total_base = va_filtered["매출0"].sum()
total_curr = va_filtered["매출1"].sum()
total_diff = va_filtered["총차이"].sum()
price_var  = va_filtered["단가차이"].sum()
qty_var    = va_filtered["수량차이"].sum()
fx_var     = va_filtered["환율차이"].sum()

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)

kpi_card(k1, f"기준 매출 ({base_label})", total_base, neutral=True)
kpi_card(k2, f"실적 매출 ({curr_label})", total_curr, neutral=True)
kpi_card(k3, "총 차이 (실적 − 기준)", total_diff)
kpi_card(k4, "① 단가 차이", price_var)
kpi_card(k5, "② 수량 차이", qty_var)
kpi_card(k6, "③ 환율 차이", fx_var)

# ══════════════════════════════════════════════════════════════════════════════
# 상세 분석 테이블
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 품목별 차이 분석 테이블</div>', unsafe_allow_html=True)

display_cols = ["품목명", "매출0", "매출1", "총차이", "단가차이", "수량차이", "환율차이"]
if show_detail:
    display_cols += ["Q0", "Q1", "P0", "P1", "ER0", "ER1"]

va_disp = va_filtered[display_cols].copy().sort_values("총차이")

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
    "기준수량", "실적수량", "기준단가", "실적단가",
]

# 합계 행 추가
total_row = {}
for col in va_disp.columns:
    if col in money_cols:
        total_row[col] = va_disp[col].sum()
    elif col == "품목명":
        total_row[col] = "【 합   계 】"
    else:
        total_row[col] = ""

va_disp_with_total = pd.concat(
    [va_disp, pd.DataFrame([total_row])], ignore_index=True
)

st.dataframe(
    styled_df(va_disp_with_total, money_cols),
    use_container_width=True,
    height=min(500, max(250, (len(va_disp_with_total) + 1) * 36 + 40)),
)

# ══════════════════════════════════════════════════════════════════════════════
# 시각화
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 차이 구성 요소 시각화</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go
    import plotly.express as px

    tab_wf, tab_bar = st.tabs(["🌊 Waterfall (전체 합산)", "📊 품목별 총차이"])

    with tab_wf:
        fig_wf = render_waterfall(total_base, price_var, qty_var, fx_var, total_curr, base_label, curr_label)
        st.plotly_chart(fig_wf, use_container_width=True)

    with tab_bar:
        va_bar = va_filtered.set_index("품목명")["총차이"].sort_values()
        fig_bar = go.Figure(go.Bar(
            x=va_bar.values,
            y=va_bar.index,
            orientation="h",
            marker_color=["#c0392b" if v < 0 else "#1a7a4a" for v in va_bar.values],
            text=[f"{v:,.0f}" for v in va_bar.values],
            textposition="outside",
        ))
        fig_bar.update_layout(
            height=max(350, len(va_bar) * 32),
            margin=dict(l=180, r=120, t=20, b=20),
            xaxis_title="원(₩)",
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Malgun Gothic, AppleGothic, sans-serif", size=12),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

except ImportError:
    st.info("plotly가 설치되지 않아 차트를 표시할 수 없습니다. `pip install plotly`")

# ══════════════════════════════════════════════════════════════════════════════
# 다운로드
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⬇️ 결과 다운로드</div>', unsafe_allow_html=True)

def to_excel_bytes(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="차이분석")
    return buf.getvalue()

mode_label = "YoY" if "전년" in mode else "MoM"
excel_bytes = to_excel_bytes(va_disp_with_total.reset_index(drop=True))
st.download_button(
    label="📥 분석 결과 엑셀 다운로드",
    data=excel_bytes,
    file_name=f"매출차이분석_{mode_label}_{base_label}vs{curr_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 원본 데이터 확인 ──────────────────────────────────────────────────────────
with st.expander("🗂️ 원본 데이터 확인 (필터링 전)"):
    t1, t2 = st.tabs([f"기준 데이터 ({base_label})", f"실적 데이터 ({curr_label})"])
    with t1:
        st.dataframe(df_base.reset_index(drop=True), use_container_width=True, height=280)
    with t2:
        st.dataframe(df_curr.reset_index(drop=True), use_container_width=True, height=280)
