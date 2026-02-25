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
    font-size: 1.75rem; font-weight: 900; color: #0d1f3c;
    letter-spacing: -0.5px; margin-bottom: 0.15rem;
}
.sub-title {
    font-size: 0.88rem; color: #5a6a85; margin-bottom: 1rem; font-weight: 500;
}

/* ── 섹션 헤더 ── */
.section-header {
    font-size: 1.0rem; font-weight: 800;
    background: linear-gradient(90deg, #1e3a6e 0%, #2d5faa 100%);
    color: white; padding: 8px 16px; border-radius: 6px;
    margin: 1.6rem 0 1rem 0; letter-spacing: 0.3px;
}

/* ── KPI 카드 ── */
.kpi-card {
    border-radius: 10px; padding: 16px 20px;
    margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.kpi-card-neutral {
    background: #ffffff; border: 1px solid #c8d6f0; border-top: 4px solid #2d5faa;
}
.kpi-card-total {
    background: #f0f4ff; border: 1px solid #a8bde8; border-top: 4px solid #1e3a6e;
}
.kpi-card-pos {
    background: #f0faf4; border: 1px solid #8ecba8; border-top: 4px solid #1a7a4a;
}
.kpi-card-neg {
    background: #fdf2f2; border: 1px solid #e8a8a8; border-top: 4px solid #c0392b;
}
.kpi-card-zero {
    background: #f7f8fa; border: 1px solid #d0d5de; border-top: 4px solid #8a95a8;
}
.kpi-label {
    font-size: 0.78rem; font-weight: 700; color: #3a4a65;
    margin-bottom: 3px; letter-spacing: 0.2px;
}
.kpi-formula {
    font-size: 0.67rem; color: #7a8aaa; margin-bottom: 6px;
    font-family: 'Courier New', monospace; background: rgba(0,0,0,0.04);
    padding: 2px 6px; border-radius: 3px; display: inline-block;
}
.kpi-value {
    font-size: 1.35rem; font-weight: 900; letter-spacing: -0.5px; margin-top: 4px;
}
.kpi-val-neutral { color: #1e3a6e; }
.kpi-val-pos     { color: #155d35; }
.kpi-val-neg     { color: #9e1f1f; }
.kpi-val-zero    { color: #6b7a95; }

/* ── 분석 모델 카드 ── */
.model-card-A {
    background: #f0f5ff; border: 2px solid #2d5faa;
    border-radius: 10px; padding: 13px 15px; margin-bottom: 6px;
}
.model-card-B {
    background: #fff6ee; border: 2px solid #c9641a;
    border-radius: 10px; padding: 13px 15px; margin-bottom: 6px;
}
.model-title-A { font-size: 0.88rem; font-weight: 800; color: #1e3a6e; }
.model-title-B { font-size: 0.88rem; font-weight: 800; color: #7a3300; }
.model-desc {
    font-size: 0.76rem; color: #3d4d65; margin-top: 5px;
    line-height: 1.6; font-weight: 500;
}
.model-tag {
    display: inline-block; font-size: 0.69rem; font-weight: 700;
    border-radius: 4px; padding: 2px 8px; margin-top: 7px;
}
.tag-A { background: #2d5faa; color: white; }
.tag-B { background: #c9641a; color: white; }

/* ── 기간 배지 ── */
.period-badge {
    display: inline-block; border-radius: 6px;
    padding: 4px 12px; font-size: 0.8rem; font-weight: 700; margin: 3px 3px;
}
.badge-base { background: #1e3a6e; color: #ffffff; }
.badge-curr { background: #1a7a4a; color: #ffffff; }

/* ── 테이블 ── */
div[data-testid="stDataFrame"] { width: 100% !important; }
div[data-testid="stDataFrame"] table { font-size: 0.83rem !important; }
div[data-testid="stDataFrame"] th {
    background: #1e3a6e !important; color: white !important;
    font-weight: 700 !important; font-size: 0.78rem !important;
}
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
      ① 수량 차이 : (Q1−Q0) × P0_krw
      ② 단가 차이 : (P1_krw−P0_krw) × Q1
      ③ 환율 차이 : 0

    신규 품목 예외 (Q0 = 0):
      → 전년 단가(P0)가 존재하지 않아 단가·환율 차이 계산 불가
      → 당해 매출 전액을 수량 차이(신규 개척 성과)로 귀속
      → 단가 차이 = 0, 환율 차이 = 0
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
        # ── 신규 품목 예외 처리 (Q0 = 0) ──────────────────────────────────────
        # 전년 실적이 없으면 전년 단가(P0)가 존재하지 않아 단가·환율 차이 계산 불가.
        # 당해 매출 전액을 수량 차이(신규 개척 성과)로 귀속하고 나머지는 0으로 처리.
        if row["Q0"] == 0:
            return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})

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
      B. 환율 차이 : 0
      C. 단가 차이 : 총차이 − ①  (=원화단가 변동분)

    신규 품목 예외 (Q0 = 0):
      → 신규 시장 개척 성과로 보아 당해 매출 전액을 수량 증분 성과로 귀속
      → 단가 차이 = 0, 환율 차이 = 0
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
        # ── 신규 품목 예외 처리 (Q0 = 0) ─────────────────────────────────────
        # 전년 실적이 없으면 전년 단가(P0)가 존재하지 않아 단가·환율 차이 계산 불가.
        # 신규 시장 개척 성과로 보아 당해 매출 전액을 수량 증분 성과로 귀속.
        if row["Q0"] == 0:
            return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})

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
    if neutral:
        card_cls = "kpi-card-neutral"
        val_cls  = "kpi-val-neutral"
    elif value > 0:
        card_cls = "kpi-card-pos"
        val_cls  = "kpi-val-pos"
    elif value < 0:
        card_cls = "kpi-card-neg"
        val_cls  = "kpi-val-neg"
    else:
        card_cls = "kpi-card-zero"
        val_cls  = "kpi-val-zero"
    col.markdown(f"""
    <div class="kpi-card {card_cls}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-formula">{formula}</div>
        <div class="kpi-value {val_cls}">{sign}{value:,.0f} 원</div>
    </div>""", unsafe_allow_html=True)


def render_waterfall(total_base, qty_v, price_v, fx_v, total_curr, base_label, curr_label, accent):
    import plotly.graph_objects as go

    # ── 색상 팔레트 ──────────────────────────────────────────────────────────
    CLR_BASE = "#2d5faa"   # 기준매출 - 짙은 파랑
    CLR_CURR = "#1a7a4a"   # 실적매출 - 짙은 녹색
    CLR_UP   = "#27ae60"   # 증가 - 선명한 녹
    CLR_DOWN = "#e74c3c"   # 감소 - 선명한 적
    CLR_CONN = "#bdc3c7"   # 연결선

    def bar_color(v):
        return CLR_UP if v >= 0 else CLR_DOWN

    x_labels = [
        f"<b>기준 매출</b><br><sub>({base_label})</sub>",
        "<b>① 수량 차이</b>",
        "<b>② 단가 차이</b>",
        "<b>③ 환율 차이</b>",
        f"<b>실적 매출</b><br><sub>({curr_label})</sub>",
    ]

    # ── 텍스트 레이블 ─────────────────────────────────────────────────────────
    def fmt_diff(v):
        if v > 0:  return f"▲ +{v:,.0f}"
        if v < 0:  return f"▼ {v:,.0f}"
        return f"{v:,.0f}"

    text_labels = [
        f"{total_base:,.0f}",
        fmt_diff(qty_v),
        fmt_diff(price_v),
        fmt_diff(fx_v),
        f"{total_curr:,.0f}",
    ]

    # ── Waterfall: 색상은 increasing/decreasing/totals 으로만 제어 ───────────
    # 기준매출(absolute)은 increasing으로 분류되므로 CLR_BASE 로 override 불가
    # → 대신 Go.Bar 5개를 직접 쌓아 완전한 색상 제어를 구현
    # running 합산으로 base 계산
    running = [0, total_base, total_base + qty_v, total_base + qty_v + price_v]
    bar_vals = [total_base, qty_v, price_v, fx_v, total_curr]
    bar_bases= [0, running[1], running[2], running[3], 0]
    bar_clrs = [CLR_BASE, bar_color(qty_v), bar_color(price_v), bar_color(fx_v), CLR_CURR]
    line_clrs= ["#1e4080", "#1e8449" if qty_v>=0 else "#b03a2e",
                "#1e8449" if price_v>=0 else "#b03a2e",
                "#1e8449" if fx_v>=0 else "#b03a2e", "#145a32"]

    fig = go.Figure()

    for i, (x, y, base, clr, lclr, txt) in enumerate(
        zip(x_labels, bar_vals, bar_bases, bar_clrs, line_clrs, text_labels)
    ):
        # 실적매출(마지막)은 0부터 시작
        b = 0 if i == 4 else base
        fig.add_trace(go.Bar(
            name        = "",
            x           = [x],
            y           = [y],
            base        = [b],
            marker_color= clr,
            marker_line = dict(color=lclr, width=1.5),
            text        = [txt],
            textposition= "outside",
            textfont    = dict(
                size   = 13,
                color  = "#0d1f3c",
                family = "Malgun Gothic, AppleGothic, sans-serif",
            ),
            showlegend  = False,
            width       = 0.55,
        ))

    # 연결 점선 (기준→①→②→③→실적)
    connector_y = [total_base, total_base + qty_v, total_base + qty_v + price_v,
                   total_base + qty_v + price_v + fx_v]
    for i, cy in enumerate(connector_y):
        fig.add_shape(
            type  = "line",
            x0    = i + 0.28, x1 = i + 0.72,
            y0    = cy, y1 = cy,
            line  = dict(color=CLR_CONN, width=1.5, dash="dot"),
        )

    # 총차이 subtitle 계산
    diff_val   = total_curr - total_base
    diff_sign  = "▲ +" if diff_val >= 0 else "▼ "
    diff_pct   = f"({diff_val / total_base * 100:+.1f}%)" if total_base != 0 else ""
    title_text = (f"매출 차이 분석 Waterfall  |  "
                  f"{base_label} → {curr_label}  |  "
                  f"총차이: {diff_sign}{diff_val:,.0f}원 {diff_pct}")

    fig.update_layout(
        title_text        = title_text,
        title_font_size   = 14,
        title_font_color  = "#0d1f3c",
        title_x           = 0.01,
        barmode           = "stack",
        height            = 500,
        margin            = dict(t=80, b=60, l=60, r=60),
        plot_bgcolor      = "#fafbfd",
        paper_bgcolor     = "#ffffff",
        showlegend        = False,
        font              = dict(family="Malgun Gothic, AppleGothic, sans-serif"),
        xaxis             = dict(
            tickfont      = dict(size=12, color="#0d1f3c"),
            tickangle     = 0,
        ),
        yaxis             = dict(
            title         = "원화 매출 (₩)",
            title_font    = dict(size=12, color="#3a4a65"),
            tickfont      = dict(size=11, color="#3a4a65"),
            gridcolor     = "#e8ecf3",
            gridwidth     = 1,
            zeroline      = True,
            zerolinecolor = "#8a95a8",
            zerolinewidth = 1.5,
        ),
    )
    return fig


def build_table(va_filtered, base_label, curr_label, show_detail):
    display_cols = ["품목명", "is_krw", "Q0", "매출0", "매출1", "총차이", "수량차이", "단가차이", "환율차이"]
    if show_detail:
        extra = [c for c in ["Q0","Q1","P0_fx","P1_fx","P0_krw","P1_krw","ER0","ER1"] if c in va_filtered.columns]
        # Q0는 이미 포함했으므로 중복 방지
        display_cols += [c for c in extra if c not in display_cols]
    va_d = va_filtered[[c for c in display_cols if c in va_filtered.columns]].copy().sort_values("총차이")

    # 신규 품목 표시 (Q0 = 0): 품목명 앞에 🆕 뱃지 추가
    is_new = va_d["Q0"] == 0
    va_d.loc[is_new, "품목명"] = "🆕 " + va_d.loc[is_new, "품목명"]

    # show_detail 아닐 때는 Q0 컬럼 숨김
    if not show_detail:
        va_d = va_d.drop(columns=["Q0"], errors="ignore")

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

        # session_state 초기화
        if "analysis_model" not in st.session_state:
            st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"

        is_A_active = "모델 A" in st.session_state.analysis_model

        # ── 모델 A 카드 ───────────────────────────────────────────────────────
        if is_A_active:
            # 선택됨: 짙은 네이비 배경 → 흰 제목, 밝은 하늘색 본문
            card_a_style  = "background:#1e3a6e; border:2px solid #1e3a6e; border-radius:10px; padding:13px 15px; margin-bottom:4px;"
            title_a_style = "font-size:0.9rem; font-weight:800; color:#ffffff;"
            desc_a_style  = "font-size:0.76rem; color:#c8dcff; margin-top:5px; line-height:1.6;"
            tag_a_style   = "display:inline-block; font-size:0.69rem; font-weight:700; border-radius:4px; padding:2px 8px; margin-top:7px; background:#ffffff; color:#1e3a6e;"
            btn_a_label   = "✔ 선택됨 (모델 A)"
        else:
            # 비선택: 연한 파랑 배경 → 어두운 텍스트
            card_a_style  = "background:#dde8ff; border:2px solid #2d5faa; border-radius:10px; padding:13px 15px; margin-bottom:4px;"
            title_a_style = "font-size:0.9rem; font-weight:800; color:#0d2050;"
            desc_a_style  = "font-size:0.76rem; color:#1a2d50; margin-top:5px; line-height:1.6;"
            tag_a_style   = "display:inline-block; font-size:0.69rem; font-weight:700; border-radius:4px; padding:2px 8px; margin-top:7px; background:#1e3a6e; color:#ffffff;"
            btn_a_label   = "이 모델 선택 →"

        st.markdown(f"""
        <div style="{card_a_style}">
            <div style="{title_a_style}">📐 모델 A — 원인별 임팩트 분석 {'&nbsp;<span style="font-size:0.75rem; background:#27ae60; color:white; border-radius:3px; padding:1px 7px;">선택중</span>' if is_A_active else ''}</div>
            <div style="{desc_a_style}">
                변수 간 간섭을 완전히 제거하여<br>
                각 요인의 <b>절대적 영향력</b>을 측정.<br><br>
                ① 수량차이: (Q1−Q0)×<b>P0_fx</b>×<b>ER0</b><br>
                ② 단가차이: (P1−P0)×<b>Q1</b>×<b>ER0</b><br>
                ③ 환율차이: (ER1−ER0)×<b>Q1</b>×<b>P1_fx</b><br><br>
                <b>✔ 재무·감사·외부보고 표준</b>
            </div>
            <span style="{tag_a_style}">수량↑↓ 모두 전년 외화단가 적용</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button(btn_a_label, key="sel_model_A", use_container_width=True,
                     type="primary" if is_A_active else "secondary"):
            st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
            st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── 모델 B 카드 ───────────────────────────────────────────────────────
        if not is_A_active:
            # 선택됨: 짙은 다크오렌지 배경 → 흰 제목, 밝은 크림 본문
            card_b_style  = "background:#7a3300; border:2px solid #7a3300; border-radius:10px; padding:13px 15px; margin-bottom:4px;"
            title_b_style = "font-size:0.9rem; font-weight:800; color:#ffffff;"
            desc_b_style  = "font-size:0.76rem; color:#ffd8b0; margin-top:5px; line-height:1.6;"
            tag_b_style   = "display:inline-block; font-size:0.69rem; font-weight:700; border-radius:4px; padding:2px 8px; margin-top:7px; background:#ffffff; color:#7a3300;"
            btn_b_label   = "✔ 선택됨 (모델 B)"
        else:
            # 비선택: 연한 오렌지 배경 → 어두운 갈색 텍스트
            card_b_style  = "background:#ffe0c0; border:2px solid #c9641a; border-radius:10px; padding:13px 15px; margin-bottom:4px;"
            title_b_style = "font-size:0.9rem; font-weight:800; color:#5a1800;"
            desc_b_style  = "font-size:0.76rem; color:#4a1800; margin-top:5px; line-height:1.6;"
            tag_b_style   = "display:inline-block; font-size:0.69rem; font-weight:700; border-radius:4px; padding:2px 8px; margin-top:7px; background:#7a3300; color:#ffffff;"
            btn_b_label   = "이 모델 선택 →"

        st.markdown(f"""
        <div style="{card_b_style}">
            <div style="{title_b_style}">📈 모델 B — 활동별 증분 분석 {'&nbsp;<span style="font-size:0.75rem; background:#27ae60; color:white; border-radius:3px; padding:1px 7px;">선택중</span>' if not is_A_active else ''}</div>
            <div style="{desc_b_style}">
                영업 활동의 <b>실질적 비즈니스 가치</b>를 평가.<br>
                상황(Case)에 따라 가중치를 다르게 적용.<br><br>
                ① 수량차이: Q↑→×<b>P1_krw</b> / Q↓→×<b>P0_krw</b><br>
                ② 단가차이: <b>총차이 − ① − ③</b> (잔여값)<br>
                ③ 환율차이: P/Q 방향 <b>4-Case 분기</b><br><br>
                <b>✔ 영업·전략·내부경영 보고</b>
            </div>
            <span style="{tag_b_style}">수량↑ = 현재 원화단가 / 수량↓ = 전년 원화단가</span>
        </div>
        """, unsafe_allow_html=True)
        if st.button(btn_b_label, key="sel_model_B", use_container_width=True,
                     type="primary" if not is_A_active else "secondary"):
            st.session_state.analysis_model = "모델 B — 활동별 증분 분석"
            st.rerun()

        analysis_model = st.session_state.analysis_model

        st.markdown("---")
        st.markdown("### ⚙️ 표시 설정")
        show_detail = st.checkbox("수량·단가·환율 상세 컬럼 표시", value=False)
        st.caption("ℹ️ ①수량차이 + ②단가차이 + ③환율차이 = 총차이")
        st.caption("🆕 전년 실적이 없는 신규 품목은 당해 매출 전액을 수량차이로 귀속 (단가·환율차이 = 0)")

        # 기간 필터
        df_base = df_all[(df_all["연도"]==base_year) & (df_all["월"]==base_month)].copy()
        df_curr = df_all[(df_all["연도"]==curr_year) & (df_all["월"]==curr_month)].copy()
    else:
        base_label = curr_label = ""
        df_base = df_curr = None
        show_detail = False
        if "analysis_model" not in st.session_state:
            st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
        analysis_model = st.session_state.analysis_model


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
    f'<div style="background:#c8d8f8;border-radius:8px;padding:9px 15px;color:#0d1f3c;font-weight:600;">'
    f'<b>기준</b>: {base_label} &nbsp; {"✅ "+str(len(df_base))+"건" if base_ok else "⚠️ 데이터 없음"}'
    f'</div>', unsafe_allow_html=True)
c2.markdown(
    f'<div style="background:#b8e8c8;border-radius:8px;padding:9px 15px;color:#0a2d18;font-weight:600;">'
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
# 총차이는 별도 카드 타입(total)으로 강조
sign_td = "+" if total_diff > 0 else ""
card_td = "kpi-card-pos" if total_diff > 0 else ("kpi-card-neg" if total_diff < 0 else "kpi-card-zero")
val_td  = "kpi-val-pos"  if total_diff > 0 else ("kpi-val-neg"  if total_diff < 0 else "kpi-val-zero")
k3.markdown(f"""
<div class="kpi-card {card_td}" style="border-top-width:5px;">
    <div class="kpi-label">▶ 총 차이 (실적 − 기준)</div>
    <div class="kpi-formula">①수량 + ②단가 + ③환율</div>
    <div class="kpi-value {val_td}" style="font-size:1.5rem;">{sign_td}{total_diff:,.0f} 원</div>
</div>""", unsafe_allow_html=True)

if is_model_A:
    kpi_card(k4, "① 수량 차이", "(Q1−Q0)×P0_fx×ER0", qty_v)
    kpi_card(k5, "② 단가 차이", "(P1−P0)×Q1×ER0", price_v)
    if all_krw_selected:
        k6.markdown('<div class="kpi-card kpi-card-zero"><div class="kpi-label">③ 환율 차이</div><div class="kpi-formula">(ER1−ER0)×Q1×P1_fx</div><div class="kpi-value kpi-val-zero">— KRW 해당없음</div></div>', unsafe_allow_html=True)
    else:
        kpi_card(k6, "③ 환율 차이", "(ER1−ER0)×Q1×P1_fx", fx_v)
else:
    kpi_card(k4, "① 수량 차이 (Volume Incremental)", "Q↑→×P1_krw / Q↓→×P0_krw", qty_v)
    kpi_card(k5, "② 단가 차이 (Negotiation Residual)", "총차이 − ① − ③", price_v)
    if all_krw_selected:
        k6.markdown('<div class="kpi-card kpi-card-zero"><div class="kpi-label">③ 환율 차이 (FX Exposure)</div><div class="kpi-formula">P/Q 방향 4-Case 분기</div><div class="kpi-value kpi-val-zero">— KRW 해당없음</div></div>', unsafe_allow_html=True)
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
        bar_colors = ["#e74c3c" if v < 0 else "#27ae60" for v in va_bar.values]
        bar_text   = [
            f"▼ {v:,.0f}" if v < 0 else (f"▲ +{v:,.0f}" if v > 0 else f"{v:,.0f}")
            for v in va_bar.values
        ]
        fig_bar = go.Figure(go.Bar(
            x             = va_bar.values,
            y             = va_bar.index,
            orientation   = "h",
            marker_color  = bar_colors,
            marker_line   = dict(color=["#b03a2e" if v < 0 else "#1e8449" for v in va_bar.values], width=1),
            text          = bar_text,
            textposition  = "outside",
            textfont      = dict(size=12, color="#0d1f3c",
                                 family="Malgun Gothic, AppleGothic, sans-serif"),
        ))
        fig_bar.update_layout(
            title_text        = "품목별 총 매출 차이",
            title_font_size   = 14,
            title_font_color  = "#0d1f3c",
            title_x           = 0.01,
            height            = max(380, len(va_bar) * 40),
            margin            = dict(l=10, r=140, t=50, b=30),
            plot_bgcolor      = "#fafbfd",
            paper_bgcolor     = "#ffffff",
            font              = dict(family="Malgun Gothic, AppleGothic, sans-serif"),
            xaxis             = dict(
                title         = "원화 매출 차이 (₩)",
                title_font    = dict(size=11, color="#3a4a65"),
                tickfont      = dict(size=11, color="#3a4a65"),
                gridcolor     = "#e8ecf3",
                gridwidth     = 1,
                zeroline      = True,
                zerolinecolor = "#5a6a85",
                zerolinewidth = 2,
            ),
            yaxis             = dict(
                tickfont      = dict(size=12, color="#0d1f3c",
                                     family="Malgun Gothic, AppleGothic"),
                automargin    = True,
            ),
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

# ══════════════════════════════════════════════════════════════════════════════
# 두 모델 상세 비교표
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📖 분석 모델 상세 비교</div>', unsafe_allow_html=True)

# ── 공통 CSS (단순 클래스만) ─────────────────────────────────────────────────
st.markdown("""<style>
.fb-block { border-radius:8px; padding:13px 16px; margin:6px 0; font-family:'Malgun Gothic','AppleGothic',sans-serif; }
/* 밝은 배경 박스 → 어두운 텍스트 */
.fb-block-qty   { background:#ddeeff; border-left:4px solid #1a4a9a; }
.fb-block-price { background:#ffe8d0; border-left:4px solid #9a3d00; }
.fb-block-fx    { background:#d4f0e0; border-left:4px solid #0d5c30; }
/* 제목 — 각 배경에서 잘 보이는 진한 색 */
.fb-title { font-size:0.72rem; font-weight:800; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:7px; }
.fb-title-qty   { color:#0d2d6e; }
.fb-title-price { color:#6b2200; }
.fb-title-fx    { color:#0a3d20; }
/* 수식 박스 — 배경보다 살짝 진하게, 텍스트는 검정 */
.fb-eq  { font-family:'Courier New',monospace; font-size:0.9rem; font-weight:700;
          background:rgba(0,0,0,0.10); color:#0d1f3c; padding:6px 11px; border-radius:4px;
          display:block; margin:6px 0; }
.fb-eq2 { font-family:'Courier New',monospace; font-size:0.78rem; font-weight:600;
          background:rgba(0,0,0,0.08); color:#0d1f3c; padding:4px 9px; border-radius:3px;
          display:block; margin:3px 0; }
/* 설명 텍스트 — 진한 회색 */
.fb-desc { font-size:0.76rem; color:#1a2535; line-height:1.6; margin-top:5px; }
/* 노트 뱃지 — 배경보다 진하게 */
.fb-note { font-size:0.71rem; color:#1a2535; background:rgba(0,0,0,0.10);
           padding:3px 9px; border-radius:3px; display:inline-block; margin-top:6px; font-weight:600; }
/* Case 그리드 */
.case-g { display:grid; grid-template-columns:1fr 1fr; gap:5px; margin-top:7px; }
.case-b { background:white; border:1px solid #7abf90; border-radius:6px; padding:7px 9px; }
.case-lbl { font-size:0.7rem; font-weight:800; color:#0a3d20; margin-bottom:3px; }
.case-eq  { font-family:'Courier New',monospace; font-size:0.71rem;
            background:#c8ecd8; color:#0a3d20; padding:2px 5px; border-radius:3px; display:block; font-weight:600; }
/* 비교 테이블 */
.diff-tbl { width:100%; border-collapse:collapse; font-family:'Malgun Gothic','AppleGothic',sans-serif; font-size:0.8rem; margin-top:6px; }
.diff-tbl th { padding:9px 12px; font-weight:800; text-align:center; }
.diff-tbl td { padding:9px 12px; border:1px solid #d0d8e8; vertical-align:top; line-height:1.55; }
/* td-cat: 연한 파랑 → 진한 네이비 텍스트 */
.diff-tbl .td-cat { background:#dde6ff; color:#0d1f3c; font-weight:800; text-align:center; width:140px; }
/* td-a: 매우 연한 파랑 → 진한 네이비 */
.diff-tbl .td-a   { background:#eef3ff; color:#0d1f3c; }
/* td-b: 매우 연한 오렌지 → 진한 갈색 */
.diff-tbl .td-b   { background:#fff0e0; color:#4a1800; }
/* 칩 뱃지 — 모두 어두운 배경에 흰 글씨 OR 진한 색에 진한 글씨 (충분한 대비) */
.ch { display:inline-block; font-size:0.68rem; font-weight:800; border-radius:20px; padding:2px 9px; margin:1px 2px; }
.ch-b { background:#1e40af; color:#ffffff; }
.ch-o { background:#9a3412; color:#ffffff; }
.ch-g { background:#065f46; color:#ffffff; }
</style>""", unsafe_allow_html=True)

# ── 모델 헤더 배너 ─────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e3a6e,#2d5faa);border-radius:10px;
                padding:14px 18px;color:white;margin-bottom:8px;">
      <div style="font-size:1.0rem;font-weight:900;margin-bottom:3px;color:#ffffff;">📐 모델 A — 원인별 임팩트 분석</div>
      <div style="font-size:0.78rem;color:#c8dcff;">재무·감사·외부보고 표준 | 변수 간 간섭 완전 제거</div>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#7a3300,#c9641a);border-radius:10px;
                padding:14px 18px;color:white;margin-bottom:8px;">
      <div style="font-size:1.0rem;font-weight:900;margin-bottom:3px;color:#ffffff;">📈 모델 B — 활동별 증분 분석</div>
      <div style="font-size:0.78rem;color:#ffd8b0;">영업·전략 보고용 | 실제 비즈니스 가치 평가</div>
    </div>""", unsafe_allow_html=True)

# ── ① 수량 차이 ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    <div class="fb-block fb-block-qty">
      <div class="fb-title fb-title-qty">① 수량 차이 (Quantity Variance)</div>
      <span class="fb-eq">(Q당해 − Q전년) × P전년_외화단가 × ER전년</span>
      <div class="fb-desc">
        💡 <b>수량만 변했다면?</b><br>
        단가와 환율을 전년 그대로 고정하고,<br>
        수량 변화만으로 생긴 매출 증감을 측정.<br>
        판매량이 늘어 생긴 순수 '물량 효과'.
      </div>
      <span class="fb-note">수량↑↓ 무관 — 항상 전년 외화단가 적용</span>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div class="fb-block fb-block-qty">
      <div class="fb-title fb-title-qty">① 수량 차이 (Volume Incremental)</div>
      <div class="fb-desc">💡 <b>새로 판 물건은 현재 가격으로, 잃은 물건은 과거 가격으로</b></div>
      <div style="margin-top:8px;">
        <div style="font-size:0.73rem;font-weight:800;color:#0a4d20;margin-bottom:2px;">▲ 수량 증가 시</div>
        <span class="fb-eq2">(Q당해 − Q전년) × P당해_원화단가</span>
        <div class="fb-desc">새로 확보한 물량 → 현재 가격으로 가치 산정</div>
        <div style="font-size:0.73rem;font-weight:800;color:#8b0000;margin:7px 0 2px 0;">▼ 수량 감소 시</div>
        <span class="fb-eq2">(Q당해 − Q전년) × P전년_원화단가</span>
        <div class="fb-desc">잃어버린 물량 → 과거 가격만큼의 손실</div>
      </div>
    </div>""", unsafe_allow_html=True)

# ── ② 단가 차이 ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    <div class="fb-block fb-block-price">
      <div class="fb-title fb-title-price">② 단가 차이 (Price Variance)</div>
      <span class="fb-eq">(P당해_외화단가 − P전년_외화단가) × Q당해 × ER전년</span>
      <div class="fb-desc">
        💡 <b>단가만 바뀌었다면?</b><br>
        수량은 당해 실적으로 확정, 환율은 전년 고정.<br>
        외화 판매 단가 변동이 만들어낸 순수 '단가 효과'.
      </div>
      <span class="fb-note">환율 전년 고정 → 환율 효과 완전 배제</span>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div class="fb-block fb-block-price">
      <div class="fb-title fb-title-price">② 단가 차이 (Negotiation Residual) — 마지막에 계산</div>
      <span class="fb-eq">총차이 − ①수량차이 − ③환율차이</span>
      <div class="fb-desc">
        💡 <b>수량·환율 효과를 모두 제거하고 남은 것이 단가 협상 결과</b><br>
        수량과 환율이라는 외부 변수를 먼저 확정한 뒤,<br>
        영업팀의 가격 협상력이 만들어낸 순수 기여분을 잔여로 도출.
      </div>
      <span class="fb-note">잔여(Residual) → 설계상 항등식 항상 성립</span>
    </div>""", unsafe_allow_html=True)

# ── ③ 환율 차이 ───────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    <div class="fb-block fb-block-fx">
      <div class="fb-title fb-title-fx">③ 환율 차이 (FX Variance)</div>
      <span class="fb-eq">(ER당해 − ER전년) × Q당해 × P당해_외화단가</span>
      <div class="fb-desc">
        💡 <b>환율만 바뀌었다면?</b><br>
        수량·단가가 당해 실적으로 모두 확정된 상태에서,<br>
        환율 변동만으로 원화 환산액이 얼마나 달라졌는지 측정.
      </div>
      <span class="fb-note">KRW 거래는 환율차이 = 0 (환율 개념 없음)</span>
    </div>""", unsafe_allow_html=True)
with col_b:
    st.markdown("""
    <div class="fb-block fb-block-fx">
      <div class="fb-title fb-title-fx">③ 환율 차이 (FX Exposure) — 먼저 계산</div>
      <div class="fb-desc" style="margin-bottom:6px;">💡 <b>단가↑↓ × 수량↑↓ 조합에 따라 환율 노출 범위가 달라짐</b></div>
      <div class="case-g">
        <div class="case-b">
          <div class="case-lbl">단가↑ &amp; 수량↑</div>
          <span class="case-eq">(ER당해−ER전년) × Q전년 × P당해_fx</span>
        </div>
        <div class="case-b">
          <div class="case-lbl">단가↑ &amp; 수량↓</div>
          <span class="case-eq">(ER당해−ER전년) × Q당해 × P당해_fx</span>
        </div>
        <div class="case-b">
          <div class="case-lbl">단가↓ &amp; 수량↑</div>
          <span class="case-eq">(ER당해−ER전년) × Q전년 × P전년_fx</span>
        </div>
        <div class="case-b">
          <div class="case-lbl">단가↓ &amp; 수량↓</div>
          <span class="case-eq">(ER당해−ER전년) × Q당해 × P전년_fx</span>
        </div>
      </div>
      <span class="fb-note">KRW 거래는 환율차이 = 0</span>
    </div>""", unsafe_allow_html=True)

# ── 핵심 차이점 비교표 ─────────────────────────────────────────────────────────
st.markdown("""
<div style="font-size:0.88rem;font-weight:800;color:#0d1f3c;
            border-bottom:2px solid #e2e8f0;padding-bottom:5px;margin:20px 0 10px 0;">
  🔍 핵심 차이점 비교
</div>
<table class="diff-tbl">
<thead>
  <tr>
    <th class="td-cat" style="background:#0d1f3c;color:white;"> </th>
    <th style="background:#1e3a6e;color:white;">📐 모델 A — 원인별 임팩트</th>
    <th style="background:#7a3300;color:white;">📈 모델 B — 활동별 증분</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td class="td-cat">수량↑ 시<br>단가 기준</td>
    <td class="td-a"><span class="ch ch-b">전년 외화단가</span><br>물량 성과를 <b>과거 가치</b>로 보수적 평가</td>
    <td class="td-b"><span class="ch ch-o">당해 원화단가</span><br>새로 판 물건은 <b>현재 가격</b>으로 입금되는 현실 반영</td>
  </tr>
  <tr>
    <td class="td-cat">수량↓ 시<br>단가 기준</td>
    <td class="td-a"><span class="ch ch-b">전년 외화단가</span><br>동일 기준 유지 — 일관성 보장</td>
    <td class="td-b"><span class="ch ch-b">전년 원화단가</span><br>잃어버린 물량 = 과거 가격만큼의 손실</td>
  </tr>
  <tr>
    <td class="td-cat">단가차이<br>계산 방식</td>
    <td class="td-a"><span class="ch ch-g">직접 계산</span><br>공식으로 직접 산출 → 변수 독립</td>
    <td class="td-b"><span class="ch ch-o">잔여값 Residual</span><br>총차이에서 수량·환율을 뺀 나머지</td>
  </tr>
  <tr>
    <td class="td-cat">환율차이<br>계산 방식</td>
    <td class="td-a"><span class="ch ch-g">단일 공식</span><br>Q당해 × P당해_fx 고정 → 단순·명확</td>
    <td class="td-b"><span class="ch ch-o">4-Case 분기</span><br>단가·수량 방향 조합에 따라 가중치 상이</td>
  </tr>
  <tr>
    <td class="td-cat">①+②+③<br>= 총차이</td>
    <td class="td-a"><span class="ch ch-g">✅ 수학적 항등</span><br>공식 구조상 항상 성립</td>
    <td class="td-b"><span class="ch ch-g">✅ 설계상 보장</span><br>단가차이를 잔여로 정의하므로 항상 성립</td>
  </tr>
  <tr>
    <td class="td-cat">주요 장점</td>
    <td class="td-a">
      <span class="ch ch-b">재현 가능</span>
      <span class="ch ch-b">변수 독립</span>
      <span class="ch ch-b">감사 방어 용이</span>
    </td>
    <td class="td-b">
      <span class="ch ch-o">영업 현실 반영</span>
      <span class="ch ch-o">성과 인센티브 연계</span>
      <span class="ch ch-o">경영진 직관 부합</span>
    </td>
  </tr>
  <tr>
    <td class="td-cat">주의사항</td>
    <td class="td-a">수량 증가 성과를 전년 가격으로 평가 →<br><b>영업 기여 과소평가</b> 가능성</td>
    <td class="td-b">단가차이가 잔여값이라<br>복잡한 상황에서 <b>해석 주의</b> 필요</td>
  </tr>
  <tr>
    <td class="td-cat">적합한<br>보고 용도</td>
    <td class="td-a">
      <span class="ch ch-b">재무제표</span>
      <span class="ch ch-b">외부감사</span>
      <span class="ch ch-b">예산대비실적</span>
      <span class="ch ch-b">원가분석</span>
    </td>
    <td class="td-b">
      <span class="ch ch-o">영업성과평가</span>
      <span class="ch ch-o">전략보고</span>
      <span class="ch ch-o">단가협상결과</span>
      <span class="ch ch-o">내부경영보고</span>
    </td>
  </tr>
</tbody>
</table>
""", unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)
