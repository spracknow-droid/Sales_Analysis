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
/* ── 기본 폰트 ── */
html, body, [class*="css"] {
    font-family: 'Malgun Gothic', 'AppleGothic', 'Noto Sans KR', sans-serif;
}

/* ── 타이틀 ── */
.main-title {
    font-size: 1.75rem; font-weight: 900; color: #1a6fd4;
    letter-spacing: -0.5px; margin-bottom: 0.15rem;
}

/* ── 섹션 헤더 ── */
.section-header {
    font-size: 1.0rem; font-weight: 800;
    background: linear-gradient(90deg, #2563eb 0%, #60a5fa 100%);
    color: white; padding: 8px 16px; border-radius: 6px;
    margin: 1.6rem 0 1rem 0; letter-spacing: 0.3px;
}

/* ── KPI 카드 ── */
.kpi-card {
    border-radius: 10px; padding: 16px 20px;
    margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.kpi-card-neutral { background: #ffffff; border: 1px solid #c8d6f0; border-top: 4px solid #2d5faa; }
.kpi-card-pos { background: #f0faf4; border: 1px solid #8ecba8; border-top: 4px solid #1a7a4a; }
.kpi-card-neg { background: #fdf2f2; border: 1px solid #e8a8a8; border-top: 4px solid #c0392b; }
.kpi-card-zero { background: #f7f8fa; border: 1px solid #d0d5de; border-top: 4px solid #8a95a8; }
.kpi-label { font-size: 0.78rem; font-weight: 700; color: #3a4a65; margin-bottom: 3px; }
.kpi-formula { font-size: 0.67rem; color: #7a8aaa; background: rgba(0,0,0,0.04); padding: 2px 6px; border-radius: 3px; display: inline-block; }
.kpi-value { font-size: 1.35rem; font-weight: 900; margin-top: 4px; }
.kpi-val-neutral { color: #1e3a6e; }
.kpi-val-pos { color: #155d35; }
.kpi-val-neg { color: #9e1f1f; }

/* ── 분석 모델 카드 ── */
.model-card-A { background: #f0f5ff; border: 2px solid #2d5faa; border-radius: 10px; padding: 13px 15px; }

/* ── 테이블 ── */
div[data-testid="stDataFrame"] { width: 100% !important; }
div[data-testid="stDataFrame"] th { background: #1e3a6e !important; color: white !important; font-size: 0.78rem !important; }

/* ── 커스텀 그룹 헤더 ── */
.group-header-z { color: #1a6fd4; font-weight: 900; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 상수 및 데이터 로딩
# ══════════════════════════════════════════════════════════════════════════════
COL_IDX = {
    "매출일": 3, "매출처명": 8, "품목코드": 21, "품목명": 22, "단위": 27,
    "수량": 29, "환종": 30, "환율": 31, "외화단가": 34, "외화금액": 35,
    "원화단가": 39, "원화금액": 40, "품목계정": 54,
}
MONTH_KR = {i: f"{i}월" for i in range(1, 13)}

@st.cache_data
def load_excel(file_bytes, file_name):
    try:
        df_raw = pd.read_excel(BytesIO(file_bytes), header=0, dtype=str)
        result = {name: df_raw.iloc[:, idx] if idx < len(df_raw.columns) else pd.Series([None]*len(df_raw)) for name, idx in COL_IDX.items()}
        df = pd.DataFrame(result)
        df["매출일"] = pd.to_datetime(df["매출일"], errors="coerce")
        for c in ["수량", "환율", "외화단가", "외화금액", "원화단가", "원화금액"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df = df.dropna(subset=["매출일"])
        df["연도"], df["월"] = df["매출일"].dt.year, df["매출일"].dt.month
        df["품목명"] = df["품목명"].fillna("(미분류)").str.strip()
        return df
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
# 집계 및 분석 엔진 (Model A & B)
# ══════════════════════════════════════════════════════════════════════════════
def aggregate(df):
    if df.empty: return pd.DataFrame(columns=["품목명","환종","Q","P_fx","P_krw","ER","원화매출","is_krw"])
    g = df.copy()
    g["_ccy"] = g["환종"].str.strip().str.upper()
    rows = []
    for (item, ccy), grp in g.groupby(["품목명", "_ccy"]):
        is_krw = (ccy == "KRW")
        Q, rev = grp["수량"].sum(), grp["원화금액"].sum()
        if Q == 0: continue
        P_krw = (grp["원화단가"] * grp["수량"]).sum() / Q
        if is_krw: P_fx, ER = np.nan, np.nan
        else:
            P_fx = (grp["외화단가"] * grp["수량"]).sum() / Q
            fx_amt_sum = grp["외화금액"].sum() or (Q * P_fx)
            ER = rev / fx_amt_sum if fx_amt_sum != 0 else np.nan
        rows.append({"품목명":item, "환종":ccy, "Q":Q, "P_fx":P_fx, "P_krw":P_krw, "ER":ER, "원화매출":rev, "is_krw":is_krw})
    return pd.DataFrame(rows)

def _merge_base_curr(base_df, curr_df):
    b = aggregate(base_df).rename(columns={"Q":"Q0","P_fx":"P0_fx","P_krw":"P0_krw","ER":"ER0","원화매출":"매출0","is_krw":"is_krw0"})
    c = aggregate(curr_df).rename(columns={"Q":"Q1","P_fx":"P1_fx","P_krw":"P1_krw","ER":"ER1","원화매출":"매출1","is_krw":"is_krw1"})
    m = pd.merge(b, c, on=["품목명","환종"], how="outer")
    cols = ["Q0","P0_fx","P0_krw","ER0","매출0","Q1","P1_fx","P1_krw","ER1","매출1"]
    m[cols] = m[cols].fillna(0)
    m["is_krw"] = m["is_krw0"] | m["is_krw1"]
    return m

def model_A(base_df, curr_df):
    m = _merge_base_curr(base_df, curr_df)
    def calc_row(row):
        if row["Q0"] == 0: return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})
        if row["Q1"] == 0: return pd.Series({"수량차이": -row["매출0"], "단가차이": 0.0, "환율차이": 0.0})
        if row["is_krw"]:
            qty, price, fx = (row["Q1"]-row["Q0"])*row["P0_krw"], (row["P1_krw"]-row["P0_krw"])*row["Q1"], 0.0
        else:
            qty = (row["Q1"]-row["Q0"])*row["P0_fx"]*row["ER0"]
            price = (row["P1_fx"]-row["P0_fx"])*row["Q1"]*row["ER0"]
            fx = (row["ER1"]-row["ER0"])*row["Q1"]*row["P1_fx"]
        total, computed = row["매출1"] - row["매출0"], qty + price + fx
        if abs(computed - total) > 1: price += (total - computed)
        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})
    v = m.apply(calc_row, axis=1)
    m[["수량차이", "단가차이", "환율차이"]] = v
    m["총차이"] = m["매출1"] - m["매출0"]
    grp_sum = m.groupby("품목명")[["매출0","매출1","총차이","수량차이","단가차이","환율차이"]].sum().reset_index()
    grp_krw = m.groupby("품목명")["is_krw"].all().reset_index()
    grp_q = m.groupby("품목명")[["Q0","Q1"]].sum().reset_index()
    res = pd.merge(pd.merge(grp_sum, grp_krw, on="품목명"), grp_q, on="품목명")
    return res, m

def model_B(base_df, curr_df):
    m = _merge_base_curr(base_df, curr_df)
    def calc_row(row):
        if row["Q0"] == 0: return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})
        if row["Q1"] == 0: return pd.Series({"수량차이": -row["매출0"], "단가차이": 0.0, "환율차이": 0.0})
        q_up = row["Q1"] >= row["Q0"]
        qty = (row["Q1"] - row["Q0"]) * (row["P1_krw"] if q_up else row["P0_krw"])
        total = row["매출1"] - row["매출0"]
        if row["is_krw"]: fx, price = 0.0, total - qty
        else:
            dER, p_up = row["ER1"]-row["ER0"], row["P1_fx"]>=row["P0_fx"]
            if p_up and q_up: fx = dER*row["Q0"]*row["P1_fx"]
            elif p_up and not q_up: fx = dER*row["Q1"]*row["P1_fx"]
            elif not p_up and q_up: fx = dER*row["Q0"]*row["P0_fx"]
            else: fx = dER*row["Q1"]*row["P0_fx"]
            price = total - qty - fx
        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})
    v = m.apply(calc_row, axis=1)
    m[["수량차이", "단가차이", "환율차이"]] = v
    m["총차이"] = m["매출1"] - m["매출0"]
    grp_sum = m.groupby("품목명")[["매출0","매출1","총차이","수량차이","단가차이","환율차이"]].sum().reset_index()
    grp_krw = m.groupby("품목명")["is_krw"].all().reset_index()
    grp_q = m.groupby("품목명")[["Q0","Q1"]].sum().reset_index()
    res = pd.merge(pd.merge(grp_sum, grp_krw, on="품목명"), grp_q, on="품목명")
    return res, m

# ══════════════════════════════════════════════════════════════════════════════
# 공통 유틸리티
# ══════════════════════════════════════════════════════════════════════════════
def styled_df(df, money_cols):
    def color_cell(v):
        try:
            fv = float(v)
            if fv < 0: return "color:#c0392b; font-weight:600"
            elif fv > 0: return "color:#1a7a4a; font-weight:600"
        except: pass
        return ""
    styler = df.style.format({c: "{:,.0f}" for c in money_cols if c in df.columns}, na_rep="-")
    for c in money_cols:
        if c in df.columns: styler = styler.applymap(color_cell, subset=[c])
    return styler

def kpi_card(col, label, formula, value, neutral=False):
    sign = "+" if value > 0 else ""
    cls = "kpi-card-neutral" if neutral else ("kpi-card-pos" if value > 0 else ("kpi-card-neg" if value < 0 else "kpi-card-zero"))
    val_cls = "kpi-val-neutral" if neutral else ("kpi-val-pos" if value > 0 else ("kpi-val-neg" if value < 0 else "kpi-val-zero"))
    col.markdown(f'<div class="kpi-card {cls}"><div class="kpi-label">{label}</div><div class="kpi-formula">{formula}</div><div class="kpi-value {val_cls}">{sign}{value:,.0f} 원</div></div>', unsafe_allow_html=True)

def render_waterfall(total_base, qty_v, price_v, fx_v, total_curr, base_label, curr_label, accent):
    import plotly.graph_objects as go
    x_labels = [f"기준 매출<br>({base_label})", "① 수량 차이", "② 단가 차이", "③ 환율 차이", f"실적 매출<br>({curr_label})"]
    fig = go.Figure(go.Waterfall(
        orientation = "v",
        measure = ["absolute", "relative", "relative", "relative", "total"],
        x = x_labels,
        textposition = "outside",
        text = [f"{total_base:,.0f}", f"{qty_v:+,.0f}", f"{price_v:+,.0f}", f"{fx_v:+,.0f}", f"{total_curr:,.0f}"],
        y = [total_base, qty_v, price_v, fx_v, total_curr],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
        increasing = {"marker":{"color":"#27ae60"}},
        decreasing = {"marker":{"color":"#e74c3c"}},
        totals = {"marker":{"color":"#2d5faa"}}
    ))
    fig.update_layout(title="매출 차이 분석 Waterfall", height=500, plot_bgcolor="#fafbfd")
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# 메인 로직 및 사이드바
# ══════════════════════════════════════════════════════════════════════════════
df_all = None
with st.sidebar:
    st.markdown("## 📂 파일 업로드")
    uploaded = st.file_uploader("ERP 매출실적 (.xlsx / .xls)", type=["xlsx","xls"])
    if uploaded:
        df_all = load_excel(uploaded.read(), uploaded.name)
    if df_all is not None:
        st.markdown("### 📅 실적 연월")
        avail_years = sorted(df_all["연도"].unique())
        curr_year = st.selectbox("실적 연도", avail_years, index=len(avail_years)-1)
        avail_m = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
        curr_month = st.selectbox("실적 월", avail_m, format_func=lambda x: MONTH_KR[x], index=len(avail_m)-1)
        period_mode = st.radio("기준 기간 설정", ["전년 동월 대비 (YoY)", "전월 대비 (MoM)"])
        base_year, base_month = (curr_year-1, curr_month) if period_mode == "전년 동월 대비 (YoY)" else ((curr_year-1 if curr_month==1 else curr_year), (12 if curr_month==1 else curr_month-1))
        base_label, curr_label = f"{base_year}년 {base_month}월", f"{curr_year}년 {curr_month}월"
        
        st.session_state.analysis_model = st.radio("분석 모델", ["모델 A — 원인별 임팩트", "모델 B — 활동별 증분"])
        show_detail = st.checkbox("상세 컬럼 표시", value=False)
        df_base = df_all[(df_all["연도"]==base_year) & (df_all["월"]==base_month)].copy()
        df_curr = df_all[(df_all["연도"]==curr_year) & (df_all["월"]==curr_month)].copy()

st.markdown('<div class="main-title">📊 매출 차이 분석 (Variance Analysis)</div>', unsafe_allow_html=True)

if df_all is None:
    st.info("👈 왼쪽 사이드바에서 파일을 업로드하세요.")
    st.stop()

is_model_A = "모델 A" in st.session_state.analysis_model
va, va_detail = model_A(df_base, df_curr) if is_model_A else model_B(df_base, df_curr)

# ══════════════════════════════════════════════════════════════════════════════
# [핵심 수정] 커스텀 그룹핑 및 품목 선택 섹션
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📦 품목 및 관리 그룹 선택</div>', unsafe_allow_html=True)

# 1. 철동님의 커스텀 그룹 정의 (필요에 따라 수정)
CUSTOM_MAP = {
    "품목 A": "핵심 관리 그룹 (Z)",
    "품목 B": "핵심 관리 그룹 (Z)",
    "품목 C": "핵심 관리 그룹 (Z)",
    "전략 상품 1": "전략 품목군",
}

# 2. 그룹핑 데이터 구조화
all_items = sorted(va["품목명"].unique())
group_to_items = {}
for item in all_items:
    group = CUSTOM_MAP.get(item, "기타 일반 품목")
    group_to_items.setdefault(group, []).append(item)

# Z그룹을 최상단으로 정렬
sorted_groups = sorted(group_to_items.keys(), key=lambda x: (x != "핵심 관리 그룹 (Z)", x))

if "selected_items" not in st.session_state:
    st.session_state.selected_items = set(all_items)

# 전체 컨트롤 버튼
c1, c2, _ = st.columns([1.2, 1.2, 7.6])
if c1.button("✅ 모든 품목 선택"): st.session_state.selected_items = set(all_items); st.rerun()
if c2.button("⬜ 모든 품목 해제"): st.session_state.selected_items = set(); st.rerun()

# 그룹별 Expander UI
for group in sorted_groups:
    items = group_to_items[group]
    sel_in_group = [i for i in items if i in st.session_state.selected_items]
    is_z = "Z" in group
    header = f"{'⭐ ' if is_z else ''}{group} ({len(sel_in_group)}/{len(items)})"
    
    with st.expander(header, expanded=is_z):
        gc1, gc2, _ = st.columns([1, 1, 8])
        if gc1.button("그룹 선택", key=f"all_{group}"):
            for i in items: st.session_state.selected_items.add(i)
            st.rerun()
        if gc2.button("그룹 해제", key=f"none_{group}"):
            for i in items: st.session_state.selected_items.discard(i)
            st.rerun()
            
        cols = st.columns(5)
        for idx, item in enumerate(items):
            active = item in st.session_state.selected_items
            if cols[idx % 5].button(f"{'✔ ' if active else ''}{item}", key=f"btn_{item}", use_container_width=True, type="primary" if active else "secondary"):
                if active: st.session_state.selected_items.discard(item)
                else: st.session_state.selected_items.add(item)
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 결과 표시 섹션 (KPI, 차트, 테이블)
# ══════════════════════════════════════════════════════════════════════════════
selected_items = list(st.session_state.selected_items)
if not selected_items:
    st.warning("품목을 선택하세요."); st.stop()

va_f = va[va["품목명"].isin(selected_items)]
total_base, total_curr, total_diff = va_f["매출0"].sum(), va_f["매출1"].sum(), va_f["총차이"].sum()
qty_v, price_v, fx_v = va_f["수량차이"].sum(), va_f["단가차이"].sum(), va_f["환율차이"].sum()

st.markdown('<div class="section-header">📈 종합 요약</div>', unsafe_allow_html=True)
k1, k2, k3 = st.columns(3)
kpi_card(k1, f"기준 매출 ({base_label})", "원화 합계", total_base, True)
kpi_card(k2, f"실적 매출 ({curr_label})", "원화 합계", total_curr, True)
kpi_card(k3, "▶ 총 차이 (실적-기준)", "①+②+③", total_diff)

k4, k5, k6 = st.columns(3)
kpi_card(k4, "① 수량 차이", "Volume", qty_v)
kpi_card(k5, "② 단가 차이", "Price", price_v)
kpi_card(k6, "③ 환율 차이", "FX", fx_v)

st.markdown('<div class="section-header">📋 상세 분석 테이블</div>', unsafe_allow_html=True)
money_cols = ["매출0", "매출1", "총차이", "수량차이", "단가차이", "환율차이"]
st.dataframe(styled_df(va_f, money_cols), use_container_width=True)

st.markdown('<div class="section-header">📊 시각화</div>', unsafe_allow_html=True)
st.plotly_chart(render_waterfall(total_base, qty_v, price_v, fx_v, total_curr, base_label, curr_label, "#2d5faa"), use_container_width=True)
