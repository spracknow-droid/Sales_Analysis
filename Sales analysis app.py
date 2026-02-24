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
html, body, [class*="css"] { font-family: 'Malgun Gothic', 'AppleGothic', sans-serif; }

.main-title { font-size: 1.7rem; font-weight: 800; color: #1f3864; margin-bottom: 0.1rem; }
.sub-title  { font-size: 0.88rem; color: #777; margin-bottom: 0.8rem; }

.section-header {
    font-size: 1.05rem; font-weight: 700; color: #1f3864;
    border-bottom: 2px solid #4472c4; padding-bottom: 5px;
    margin: 1.5rem 0 0.8rem 0;
}

/* KPI 카드 */
.kpi-card {
    background: #f5f7ff; border-radius: 10px;
    padding: 14px 18px; border-left: 5px solid #4472c4;
    margin-bottom: 8px;
}
.kpi-label { font-size: 0.72rem; color: #555; margin-bottom: 3px; line-height:1.3; }
.kpi-formula { font-size: 0.65rem; color: #999; margin-bottom: 4px; font-style: italic; }
.kpi-value { font-size: 1.2rem; font-weight: 800; color: #1f3864; }
.kpi-pos   { color: #1a7a4a; }
.kpi-neg   { color: #c0392b; }

/* 분석 모델 카드 */
.model-card {
    border-radius: 10px; padding: 14px 16px; margin-bottom: 6px;
    border: 2px solid transparent; cursor: pointer;
}
.model-card-A { background: #eef4ff; border-color: #4472c4; }
.model-card-B { background: #fff8ee; border-color: #e6812a; }
.model-title-A { font-size: 0.85rem; font-weight: 700; color: #1f3864; }
.model-title-B { font-size: 0.85rem; font-weight: 700; color: #8b4c0a; }
.model-desc  { font-size: 0.75rem; color: #555; margin-top: 4px; line-height: 1.5; }
.model-tag   { display:inline-block; font-size:0.68rem; font-weight:700;
               border-radius:4px; padding:2px 7px; margin-top:6px; }
.tag-A { background:#4472c4; color:white; }
.tag-B { background:#e6812a; color:white; }

/* 기간 배지 */
.period-badge {
    display: inline-block; border-radius: 6px;
    padding: 3px 10px; font-size: 0.78rem; font-weight: 600; margin: 2px 2px;
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
# 데이터 로딩
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


# ══════════════════════════════════════════════════════════════════════════════
# 집계 공통 함수
# ══════════════════════════════════════════════════════════════════════════════
def aggregate(df):
    """
    품목명 기준 집계.
    반환 컬럼:
      Q       : 총 수량
      P_fx    : 가중평균 외화단가  (KRW 품목은 원화단가, 단 is_krw=True 로 표시)
      P_krw   : 가중평균 원화단가
      ER      : 평균 환율          (KRW 품목은 NaN → 환율차이 계산 제외 표시용)
      원화매출 : 원화 매출 합계
      is_krw  : 품목 전체가 KRW 거래인지 여부 (True이면 환율차이 = 0)
    """
    if df.empty:
        return pd.DataFrame(columns=["품목명","Q","P_fx","P_krw","ER","원화매출","is_krw"])

    g = df.copy()
    g["_is_krw"] = g["환종"].str.strip().str.upper() == "KRW"
    # 외화단가: KRW 거래는 원화단가를 외화단가로 간주 (환율=1이므로 동일)
    g["P_fx_adj"]  = np.where(g["_is_krw"], g["원화단가"], g["외화단가"])
    g["P_krw_adj"] = g["원화단가"]
    # 환율: KRW 거래는 NaN (집계 후 환율차이 계산에서 0 처리)
    g["ER_adj"] = np.where(g["_is_krw"], np.nan, g["환율"])

    grp   = g.groupby("품목명")
    Q     = grp["수량"].sum()
    PfxQ  = grp.apply(lambda x: (x["P_fx_adj"]  * x["수량"]).sum())
    PkwQ  = grp.apply(lambda x: (x["P_krw_adj"] * x["수량"]).sum())
    P_fx  = (PfxQ / Q.replace(0, np.nan)).fillna(0)
    P_krw = (PkwQ / Q.replace(0, np.nan)).fillna(0)
    # 환율 평균: KRW 전용 품목이면 NaN 유지 (mean은 NaN 무시 → 외화 포함 시 외화환율만 평균)
    ER    = grp["ER_adj"].mean()   # 품목이 KRW 전용이면 NaN
    rev   = grp["원화금액"].sum()
    # 품목 내 모든 행이 KRW인지 여부
    is_krw_flag = grp["_is_krw"].all()

    result = pd.DataFrame({
        "Q": Q, "P_fx": P_fx, "P_krw": P_krw,
        "ER": ER, "원화매출": rev, "is_krw": is_krw_flag
    }).reset_index()
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 분석 모델 A: 원인별 임팩트 분석 (Cause-based Impact)
# ══════════════════════════════════════════════════════════════════════════════
def model_A(base_df, curr_df):
    """
    원인별 임팩트 분석 — 재무/감사용 표준 모델

    외화(USD 등) 품목:
      ① 수량 차이 : (Q1−Q0) × P0_fx × ER0
      ② 단가 차이 : (P1_fx−P0_fx) × Q1 × ER0
      ③ 환율 차이 : (ER1−ER0) × Q1 × P1_fx

    KRW 품목 (환율차이 = 0):
      ① 수량 차이 : (Q1−Q0) × P0_krw          ← ER=1 이므로 ×1 생략
      ② 단가 차이 : (P1_krw−P0_krw) × Q1      ← ER=1 이므로 ×1 생략
      ③ 환율 차이 : 0                           ← 환율 개념 없음
    """
    b = aggregate(base_df).rename(columns={
        "Q":"Q0","P_fx":"P0_fx","P_krw":"P0_krw",
        "ER":"ER0","원화매출":"매출0","is_krw":"is_krw0"
    })
    c = aggregate(curr_df).rename(columns={
        "Q":"Q1","P_fx":"P1_fx","P_krw":"P1_krw",
        "ER":"ER1","원화매출":"매출1","is_krw":"is_krw1"
    })
    m = pd.merge(b, c, on="품목명", how="outer")

    # 숫자 컬럼만 fillna(0), bool 컬럼은 별도 처리
    num_cols  = ["Q0","P0_fx","P0_krw","ER0","매출0","Q1","P1_fx","P1_krw","ER1","매출1"]
    bool_cols = ["is_krw0","is_krw1"]
    m[num_cols]  = m[num_cols].fillna(0)
    m[bool_cols] = m[bool_cols].fillna(False)

    # 기준·실적 중 하나라도 KRW이면 해당 품목은 KRW 처리
    m["is_krw"] = m["is_krw0"] | m["is_krw1"]

    def calc_row(row):
        if row["is_krw"]:
            # KRW: 환율 개념 없음 → 원화단가·원화매출 기준, 환율차이=0
            qty   = (row["Q1"]     - row["Q0"])     * row["P0_krw"]
            price = (row["P1_krw"] - row["P0_krw"]) * row["Q1"]
            fx    = 0.0
        else:
            # 외화
            qty   = (row["Q1"]    - row["Q0"])    * row["P0_fx"] * row["ER0"]
            price = (row["P1_fx"] - row["P0_fx"]) * row["Q1"]   * row["ER0"]
            fx    = (row["ER1"]   - row["ER0"])   * row["Q1"]   * row["P1_fx"]
        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})

    variances     = m.apply(calc_row, axis=1)
    m["수량차이"] = variances["수량차이"]
    m["단가차이"] = variances["단가차이"]
    m["환율차이"] = variances["환율차이"]
    m["총차이"]   = m["매출1"] - m["매출0"]
    return m


# ══════════════════════════════════════════════════════════════════════════════
# 분석 모델 B: 활동별 증분 분석 (Activity-based Incremental)
# ══════════════════════════════════════════════════════════════════════════════
def model_B(base_df, curr_df):
    """
    활동별 증분 분석 — 영업/전략 보고용 모델

    외화(USD 등) 품목:
      A. 수량 차이 : Q↑→(Q1−Q0)×P1_krw / Q↓→(Q1−Q0)×P0_krw
      B. 환율 차이 : P/Q 방향 4-Case 분기
      C. 단가 차이 : 총차이 − ① − ③  (Residual)

    KRW 품목 (환율차이 = 0):
      A. 수량 차이 : Q↑→(Q1−Q0)×P1_krw / Q↓→(Q1−Q0)×P0_krw  (동일)
      B. 환율 차이 : 0                                          ← 환율 개념 없음
      C. 단가 차이 : 총차이 − ①  (=원화단가 변동분)
    """
    b = aggregate(base_df).rename(columns={
        "Q":"Q0","P_fx":"P0_fx","P_krw":"P0_krw",
        "ER":"ER0","원화매출":"매출0","is_krw":"is_krw0"
    })
    c = aggregate(curr_df).rename(columns={
        "Q":"Q1","P_fx":"P1_fx","P_krw":"P1_krw",
        "ER":"ER1","원화매출":"매출1","is_krw":"is_krw1"
    })
    m = pd.merge(b, c, on="품목명", how="outer")

    num_cols  = ["Q0","P0_fx","P0_krw","ER0","매출0","Q1","P1_fx","P1_krw","ER1","매출1"]
    bool_cols = ["is_krw0","is_krw1"]
    m[num_cols]  = m[num_cols].fillna(0)
    m[bool_cols] = m[bool_cols].fillna(False)
    m["is_krw"]  = m["is_krw0"] | m["is_krw1"]

    def calc_row(row):
        q_up   = row["Q1"]    >= row["Q0"]
        p_up   = row["P1_fx"] >= row["P0_fx"]
        dER    = row["ER1"]   -  row["ER0"]

        # A. 수량 차이 (KRW·외화 공통: 원화단가 기준)
        qty = ((row["Q1"] - row["Q0"]) * row["P1_krw"] if q_up
               else (row["Q1"] - row["Q0"]) * row["P0_krw"])

        if row["is_krw"]:
            # KRW: 환율차이 = 0, 단가차이 = 잔여
            fx    = 0.0
            total = row["매출1"] - row["매출0"]
            price = total - qty
        else:
            # 외화: 4-Case 환율 분기
            if   p_up and     q_up:  fx = dER * row["Q0"] * row["P1_fx"]
            elif p_up and not q_up:  fx = dER * row["Q1"] * row["P1_fx"]
            elif not p_up and q_up:  fx = dER * row["Q0"] * row["P0_fx"]
            else:                    fx = dER * row["Q1"] * row["P0_fx"]
            total = row["매출1"] - row["매출0"]
            price = total - qty - fx

        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})

    variances     = m.apply(calc_row, axis=1)
    m["수량차이"] = variances["수량차이"]
    m["단가차이"] = variances["단가차이"]
    m["환율차이"] = variances["환율차이"]
    m["총차이"]   = m["매출1"] - m["매출0"]
    return m


# ══════════════════════════════════════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════════════════════════════════════
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


def kpi_card(col, label, formula, value, neutral=False):
    sign = "+" if value > 0 else ""
    css  = "" if neutral else ("kpi-pos" if value > 0 else ("kpi-neg" if value < 0 else ""))
    col.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-formula">{formula}</div>
        <div class="kpi-value {css}">{sign}{value:,.0f} 원</div>
    </div>""", unsafe_allow_html=True)


def render_waterfall(total_base, qty_v, price_v, fx_v, total_curr, base_label, curr_label, accent):
    import plotly.graph_objects as go
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[f"기준\n({base_label})", "①수량차이", "②단가차이", "③환율차이", f"실적\n({curr_label})"],
        y=[total_base, qty_v, price_v, fx_v, 0],
        connector={"line": {"color": "#ccc"}},
        increasing={"marker": {"color": "#1a7a4a"}},
        decreasing={"marker": {"color": "#c0392b"}},
        totals={"marker": {"color": accent}},
        text=[f"{v:,.0f}" for v in [total_base, qty_v, price_v, fx_v, total_curr]],
        textposition="outside",
    ))
    fig.update_layout(
        height=400, margin=dict(t=30, b=20, l=30, r=30),
        yaxis_title="원(₩)",
        font=dict(family="Malgun Gothic, AppleGothic, sans-serif", size=12),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_table(va_filtered, base_label, curr_label, show_detail):
    display_cols = ["품목명", "is_krw", "매출0", "매출1", "총차이", "수량차이", "단가차이", "환율차이"]
    if show_detail:
        extra = [c for c in ["Q0","Q1","P0_fx","P1_fx","P0_krw","P1_krw","ER0","ER1"] if c in va_filtered.columns]
        display_cols += extra
    va_d = va_filtered[[c for c in display_cols if c in va_filtered.columns]].copy().sort_values("총차이")

    # KRW 품목의 환율차이를 NaN으로 → 테이블에서 "-" 표시
    va_d.loc[va_d["is_krw"] == True, "환율차이"] = np.nan

    # is_krw 컬럼 제거 (표시 불필요)
    va_d = va_d.drop(columns=["is_krw"], errors="ignore")

    rename_map = {
        "매출0":    f"기준매출(원) [{base_label}]",
        "매출1":    f"실적매출(원) [{curr_label}]",
        "총차이":   "총차이(원)",
        "수량차이": "①수량차이(원)",
        "단가차이": "②단가차이(원)",
        "환율차이": "③환율차이(원)",
        "Q0":"기준수량","Q1":"실적수량",
        "P0_fx":"기준외화단가","P1_fx":"실적외화단가",
        "P0_krw":"기준원화단가","P1_krw":"실적원화단가",
        "ER0":"기준환율","ER1":"실적환율",
    }
    va_d = va_d.rename(columns=rename_map)

    money_cols = [
        f"기준매출(원) [{base_label}]", f"실적매출(원) [{curr_label}]",
        "총차이(원)","①수량차이(원)","②단가차이(원)","③환율차이(원)",
        "기준수량","실적수량","기준외화단가","실적외화단가","기준원화단가","실적원화단가",
    ]

    # 합계 행: 환율차이는 NaN이 섞여 있으므로 skipna=True 로 합산 (KRW 제외한 외화분만 합산)
    total_row = {}
    for col in va_d.columns:
        if col in money_cols:
            total_row[col] = va_d[col].sum(skipna=True)
        elif col == "품목명":
            total_row[col] = "【 합 계 】"
        else:
            total_row[col] = ""

    va_d_total = pd.concat([va_d, pd.DataFrame([total_row])], ignore_index=True)
    return va_d_total, money_cols


# ══════════════════════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════════════════════
df_all = None

with st.sidebar:
    st.markdown("## 📂 파일 업로드")
    uploaded = st.file_uploader("ERP 매출실적 (.xlsx / .xls)", type=["xlsx","xls"])

    st.markdown("---")

    if uploaded:
        file_bytes = uploaded.read()
        df_all = load_excel(file_bytes, uploaded.name)

    if df_all is not None:
        # ── 실적 연월 ─────────────────────────────────────────────────────────
        st.markdown("### 📅 실적 연월")
        avail_years = sorted(df_all["연도"].unique())
        curr_year   = st.selectbox("실적 연도", avail_years, index=len(avail_years)-1)
        avail_m     = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
        curr_month  = st.selectbox("실적 월", avail_m, format_func=lambda x: MONTH_KR[x], index=len(avail_m)-1)

        # ── 비교 모드 ─────────────────────────────────────────────────────────
        st.markdown("### 🔀 비교 기간")
        period_mode = st.radio("기준 기간 설정", ["전년 동월 대비 (YoY)", "전월 대비 (MoM)"], index=0)
        if period_mode == "전년 동월 대비 (YoY)":
            base_year, base_month = curr_year - 1, curr_month
        else:
            base_year  = curr_year - 1 if curr_month == 1 else curr_year
            base_month = 12            if curr_month == 1 else curr_month - 1

        base_label = f"{base_year}년 {MONTH_KR[base_month]}"
        curr_label = f"{curr_year}년 {MONTH_KR[curr_month]}"
        st.markdown(
            f'<span class="period-badge badge-base">기준: {base_label}</span>'
            f'<span class="period-badge badge-curr">실적: {curr_label}</span>',
            unsafe_allow_html=True
        )

        # ── 분석 모델 선택 ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🧮 분석 모델 선택")

        st.markdown("""
        <div class="model-card model-card-A">
            <div class="model-title-A">📐 모델 A — 원인별 임팩트 분석</div>
            <div class="model-desc">
                변수 간 간섭을 완전히 제거하여<br>
                각 요인의 <b>절대적 영향력</b>을 측정.<br>
                ①+②+③ = 총차이 항등식 보장.<br>
                <b style="color:#1f3864">✔ 재무·감사·외부보고 표준</b>
            </div>
            <span class="model-tag tag-A">수량↓ = 전년단가 적용</span>
        </div>
        <div class="model-card model-card-B" style="margin-top:8px;">
            <div class="model-title-B">📈 모델 B — 활동별 증분 분석</div>
            <div class="model-desc">
                영업 활동(단가협상·물량확보)의<br>
                <b>실질적 비즈니스 가치</b>를 평가.<br>
                단가차이 = 잔여(총차이−①−③) 방식.<br>
                <b style="color:#8b4c0a">✔ 영업·전략·내부경영 보고</b>
            </div>
            <span class="model-tag tag-B">수량↑ = 현재단가 적용</span>
        </div>
        """, unsafe_allow_html=True)

        analysis_model = st.radio(
            "모델 선택",
            ["모델 A — 원인별 임팩트 분석", "모델 B — 활동별 증분 분석"],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")

        # 모델별 특징 요약 표
        with st.expander("📊 두 모델 비교표"):
            cmp = pd.DataFrame({
                "항목": ["목적","수량차이 공식","단가차이 공식","환율차이 공식","수량↑ 시 단가 기준","수량↓ 시 단가 기준","단가차이 도출 방식","①+②+③=총차이","주요 용도"],
                "모델 A": [
                    "절대 원인 측정",
                    "(Q1−Q0)×P0_fx×ER0",
                    "(P1−P0)×Q1×ER0",
                    "(ER1−ER0)×Q1×P1_fx",
                    "전년 외화단가",
                    "전년 외화단가",
                    "직접 계산",
                    "✅ 항상 성립",
                    "재무·감사·외부보고",
                ],
                "모델 B": [
                    "실질 가치 평가",
                    "Q↑: (Q1−Q0)×P1_krw",
                    "총차이−수량−환율",
                    "P/Q 방향 4-Case 분기",
                    "당해 원화단가",
                    "전년 원화단가",
                    "잔여(Residual)",
                    "✅ 항상 성립",
                    "영업·전략·내부경영",
                ],
            })
            st.dataframe(cmp, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### ⚙️ 표시 설정")
        show_detail = st.checkbox("수량·단가·환율 상세 컬럼 표시", value=False)
        st.caption("ℹ️ ①수량차이 + ②단가차이 + ③환율차이 = 총차이")

        # 기간 필터
        df_base = df_all[(df_all["연도"]==base_year) & (df_all["월"]==base_month)].copy()
        df_curr = df_all[(df_all["연도"]==curr_year) & (df_all["월"]==curr_month)].copy()
    else:
        base_label = curr_label = ""
        df_base = df_curr = None
        show_detail = False
        analysis_model = "모델 A — 원인별 임팩트 분석"


# ══════════════════════════════════════════════════════════════════════════════
# 메인
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">📊 매출 차이 분석 (Variance Analysis)</div>', unsafe_allow_html=True)

if df_all is None:
    st.info("👈 왼쪽 사이드바에서 **ERP 매출실적 파일**을 업로드하세요.")
    with st.expander("📋 엑셀 파일 컬럼 구성 안내"):
        col_info = pd.DataFrame({
            "열": ["D","I","V","W","AB","AD","AE","AF","AI","AJ","AN","AO","BC"],
            "내용": ["매출일(YYYY-MM-DD)","매출처명","품목코드","품목명","단위",
                     "수량","환종(KRW/USD)","환율","(외화)판매단가","(외화)판매금액",
                     "(장부단가)원화환산판매단가","(장부금액)원화환산판매금액",
                     "품목계정(제품/상품/원재료/부재료/제조-수선비)"],
        })
        st.dataframe(col_info, use_container_width=True, hide_index=True)
    st.stop()

# ── 선택된 모델 배너 ──────────────────────────────────────────────────────────
is_model_A = "모델 A" in analysis_model
accent_color = "#4472c4" if is_model_A else "#e6812a"
model_badge_style = f"background:{'#eef4ff' if is_model_A else '#fff8ee'}; border-left:5px solid {accent_color}; border-radius:8px; padding:10px 16px; margin-bottom:8px;"

if is_model_A:
    st.markdown(f"""
    <div style="{model_badge_style}">
        <b style="color:{accent_color}">📐 모델 A — 원인별 임팩트 분석</b>&nbsp;&nbsp;
        <span style="font-size:0.82rem; color:#555;">재무·감사용 표준 모델 │ 변수 간 간섭 완전 제거 │ 각 요인의 절대적 영향력 측정</span><br/>
        <span style="font-size:0.75rem; color:#888; margin-top:4px; display:block;">
        ① 수량차이 = (Q1−Q0)×<b>P0_fx</b>×<b>ER0</b> &nbsp;|&nbsp;
        ② 단가차이 = (P1−P0)×<b>Q1</b>×<b>ER0</b> &nbsp;|&nbsp;
        ③ 환율차이 = (ER1−ER0)×<b>Q1</b>×<b>P1_fx</b>
        </span>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="{model_badge_style}">
        <b style="color:{accent_color}">📈 모델 B — 활동별 증분 분석</b>&nbsp;&nbsp;
        <span style="font-size:0.82rem; color:#555;">영업·전략 보고용 모델 │ 실질적 비즈니스 가치 평가 │ 상황별 Case 분기 적용</span><br/>
        <span style="font-size:0.75rem; color:#888; margin-top:4px; display:block;">
        ① 수량차이 = Q↑:(Q1−Q0)×<b>P1_krw</b> / Q↓:(Q1−Q0)×<b>P0_krw</b> &nbsp;|&nbsp;
        ② 단가차이 = 총차이−①−③ &nbsp;|&nbsp;
        ③ 환율차이 = P/Q방향 4-Case 분기
        </span>
    </div>""", unsafe_allow_html=True)

# ── 기간 유효성 ───────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
base_ok = not df_base.empty
curr_ok = not df_curr.empty
c1.markdown(
    f'<div style="background:#e8f0fe;border-radius:8px;padding:9px 15px;">'
    f'<b>기준</b>: {base_label} &nbsp; {"✅ "+str(len(df_base))+"건" if base_ok else "⚠️ 데이터 없음"}'
    f'</div>', unsafe_allow_html=True)
c2.markdown(
    f'<div style="background:#e6f4ea;border-radius:8px;padding:9px 15px;">'
    f'<b>실적</b>: {curr_label} &nbsp; {"✅ "+str(len(df_curr))+"건" if curr_ok else "⚠️ 데이터 없음"}'
    f'</div>', unsafe_allow_html=True)
st.markdown("<br/>", unsafe_allow_html=True)

if not base_ok and not curr_ok:
    st.error("두 기간 모두 데이터가 없습니다.")
    st.stop()

# ── 차이 분석 실행 ────────────────────────────────────────────────────────────
with st.spinner("분석 중..."):
    va = model_A(df_base, df_curr) if is_model_A else model_B(df_base, df_curr)

# ══════════════════════════════════════════════════════════════════════════════
# 품목 선택 버튼
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📦 품목 선택</div>', unsafe_allow_html=True)

all_items = sorted(va["품목명"].unique())

if "selected_items" not in st.session_state:
    st.session_state.selected_items = set(all_items)

# 아이템 목록이 바뀌면 초기화
if not st.session_state.selected_items.issubset(set(all_items)):
    st.session_state.selected_items = set(all_items)

ctrl1, ctrl2, _ = st.columns([1, 1, 8])
with ctrl1:
    if st.button("✅ 전체 선택", use_container_width=True):
        st.session_state.selected_items = set(all_items)
        st.rerun()
with ctrl2:
    if st.button("⬜ 전체 해제", use_container_width=True):
        st.session_state.selected_items = set()
        st.rerun()

cols_per_row = 5
for row_items in [all_items[i:i+cols_per_row] for i in range(0, len(all_items), cols_per_row)]:
    btn_cols = st.columns(cols_per_row)
    for col, item in zip(btn_cols, row_items):
        is_active = item in st.session_state.selected_items
        with col:
            if st.button(
                f"{'✔ ' if is_active else ''}{item}",
                key=f"btn_{item}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
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

va_filtered = va[va["품목명"].isin(selected_items)].copy()

# ══════════════════════════════════════════════════════════════════════════════
# KPI 요약
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 종합 요약</div>', unsafe_allow_html=True)

total_base = va_filtered["매출0"].sum()
total_curr = va_filtered["매출1"].sum()
total_diff = va_filtered["총차이"].sum()
qty_v      = va_filtered["수량차이"].sum()
price_v    = va_filtered["단가차이"].sum()
# 환율차이: KRW 품목은 0이므로 skipna 없이 sum → 외화 품목만 합산됨
fx_v       = va_filtered["환율차이"].sum()

# KRW 전용 선택 여부 (환율차이 KPI 표시 조절용)
all_krw_selected = va_filtered["is_krw"].all() if "is_krw" in va_filtered.columns else False

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)

kpi_card(k1, f"기준 매출 ({base_label})", "원화 실적 합계", total_base, neutral=True)
kpi_card(k2, f"실적 매출 ({curr_label})", "원화 실적 합계", total_curr, neutral=True)
kpi_card(k3, "총 차이 (실적 − 기준)", "①+②+③ 합계", total_diff)

if is_model_A:
    kpi_card(k4, "① 수량 차이", "(Q1−Q0)×P0_fx×ER0", qty_v)
    kpi_card(k5, "② 단가 차이", "(P1−P0)×Q1×ER0", price_v)
    if all_krw_selected:
        k6.markdown('<div class="kpi-card"><div class="kpi-label">③ 환율 차이</div><div class="kpi-formula">(ER1−ER0)×Q1×P1_fx</div><div class="kpi-value" style="color:#aaa;">— KRW 해당없음</div></div>', unsafe_allow_html=True)
    else:
        kpi_card(k6, "③ 환율 차이", "(ER1−ER0)×Q1×P1_fx", fx_v)
else:
    kpi_card(k4, "① 수량 차이 (Volume Incremental)", "Q↑→×P1_krw / Q↓→×P0_krw", qty_v)
    kpi_card(k5, "② 단가 차이 (Negotiation Residual)", "총차이 − ① − ③", price_v)
    if all_krw_selected:
        k6.markdown('<div class="kpi-card"><div class="kpi-label">③ 환율 차이 (FX Exposure)</div><div class="kpi-formula">P/Q 방향 4-Case 분기</div><div class="kpi-value" style="color:#aaa;">— KRW 해당없음</div></div>', unsafe_allow_html=True)
    else:
        kpi_card(k6, "③ 환율 차이 (FX Exposure)", "P/Q 방향 4-Case 분기", fx_v)

# ══════════════════════════════════════════════════════════════════════════════
# 상세 테이블
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 품목별 차이 분석 테이블</div>', unsafe_allow_html=True)

va_disp_total, money_cols = build_table(va_filtered, base_label, curr_label, show_detail)

st.dataframe(
    styled_df(va_disp_total, money_cols),
    use_container_width=True,
    height=min(520, max(260, (len(va_disp_total)+1)*36+40)),
)

# ══════════════════════════════════════════════════════════════════════════════
# 시각화
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 차이 구성 요소 시각화</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go

    tab_wf, tab_bar = st.tabs(["🌊 Waterfall (전체 합산)", "📊 품목별 총차이"])

    with tab_wf:
        fig_wf = render_waterfall(total_base, qty_v, price_v, fx_v, total_curr, base_label, curr_label, accent_color)
        st.plotly_chart(fig_wf, use_container_width=True)

    with tab_bar:
        va_bar = va_filtered.set_index("품목명")["총차이"].sort_values()
        fig_bar = go.Figure(go.Bar(
            x=va_bar.values, y=va_bar.index, orientation="h",
            marker_color=["#c0392b" if v < 0 else "#1a7a4a" for v in va_bar.values],
            text=[f"{v:,.0f}" for v in va_bar.values],
            textposition="outside",
        ))
        fig_bar.update_layout(
            height=max(350, len(va_bar)*32),
            margin=dict(l=180, r=120, t=20, b=20),
            xaxis_title="원(₩)", plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Malgun Gothic, AppleGothic, sans-serif", size=12),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

except ImportError:
    st.info("plotly가 설치되지 않아 차트를 표시할 수 없습니다.")

# ══════════════════════════════════════════════════════════════════════════════
# 다운로드
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">⬇️ 결과 다운로드</div>', unsafe_allow_html=True)

def to_excel_bytes(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="차이분석")
    return buf.getvalue()

period_mode_label = "YoY" if "전년" in period_mode else "MoM"
model_label = "A_원인별임팩트" if is_model_A else "B_활동별증분"
excel_bytes = to_excel_bytes(va_disp_total.reset_index(drop=True))
st.download_button(
    label="📥 분석 결과 엑셀 다운로드",
    data=excel_bytes,
    file_name=f"매출차이분석_{model_label}_{period_mode_label}_{base_label}vs{curr_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ── 원본 데이터 ───────────────────────────────────────────────────────────────
with st.expander("🗂️ 원본 데이터 확인 (선택 품목 기준)"):
    # 현재 선택된 품목으로만 필터
    raw_base = df_base[df_base["품목명"].isin(selected_items)].reset_index(drop=True)
    raw_curr = df_curr[df_curr["품목명"].isin(selected_items)].reset_index(drop=True)

    t1, t2 = st.tabs([
        f"기준 ({base_label}) · {len(raw_base):,}건",
        f"실적 ({curr_label}) · {len(raw_curr):,}건",
    ])
    with t1:
        if raw_base.empty:
            st.info("선택된 품목의 기준 기간 데이터가 없습니다.")
        else:
            st.dataframe(raw_base, use_container_width=True, height=280)
    with t2:
        if raw_curr.empty:
            st.info("선택된 품목의 실적 기간 데이터가 없습니다.")
        else:
            st.dataframe(raw_curr, use_container_width=True, height=280)
