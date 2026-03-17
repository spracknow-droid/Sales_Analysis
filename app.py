# ══════════════════════════════════════════════════════════════════════════════
# app.py  —  Streamlit 진입점 (오케스트레이션만 담당)
# ══════════════════════════════════════════════════════════════════════════════
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO

from config import GROUP_COLORS
from models import model_A, model_B
from ui_components import styled_df, kpi_card, render_waterfall, build_table
from ui_sidebar import render_sidebar
from ui_group_editor import render_group_editor
from ui_model_guide import render_model_guide
# app.py  —  Streamlit 진입점 (오케스트레이션만 담당)
#
# 실행: streamlit run app.py
#
# 의존 모듈:
#   config.py            상수 (COL_IDX, MONTH_KR, GROUP_COLORS)
#   data_loader.py       load_excel, groups_to_json_bytes, json_bytes_to_groups
#   models.py            aggregate, model_A, model_B
#   ui_components.py     styled_df, kpi_card, render_waterfall, build_table
#   ui_sidebar.py        render_sidebar → 사이드바 전체
#   ui_group_selector.py render_group_selector → 그룹 카드 UI
#   ui_model_guide.py    render_model_guide → 하단 모델 비교표
# ══════════════════════════════════════════════════════════════════════════════



# ── 페이지 설정 ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="매출 차이 분석",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 글로벌 CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Malgun Gothic', 'AppleGothic', 'Noto Sans KR', sans-serif;
}
.main-title {
    font-size: 1.75rem; font-weight: 900; color: #1a6fd4;
    letter-spacing: -0.5px; margin-bottom: 0.15rem;
}
.section-header {
    font-size: 1.0rem; font-weight: 800;
    background: linear-gradient(90deg, #2563eb 0%, #60a5fa 100%);
    color: white; padding: 8px 16px; border-radius: 6px;
    margin: 1.6rem 0 1rem 0; letter-spacing: 0.3px;
}
.kpi-card { border-radius:10px; padding:16px 20px; margin-bottom:8px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
.kpi-card-neutral { background:#ffffff; border:1px solid #c8d6f0; border-top:4px solid #2d5faa; }
.kpi-card-pos  { background:#f0faf4; border:1px solid #8ecba8; border-top:4px solid #1a7a4a; }
.kpi-card-neg  { background:#fdf2f2; border:1px solid #e8a8a8; border-top:4px solid #c0392b; }
.kpi-card-zero { background:#f7f8fa; border:1px solid #d0d5de; border-top:4px solid #8a95a8; }
.kpi-label   { font-size:0.78rem; font-weight:700; color:#3a4a65; margin-bottom:3px; letter-spacing:0.2px; }
.kpi-formula { font-size:0.67rem; color:#7a8aaa; margin-bottom:6px; font-family:'Courier New',monospace;
               background:rgba(0,0,0,0.04); padding:2px 6px; border-radius:3px; display:inline-block; }
.kpi-value   { font-size:1.35rem; font-weight:900; letter-spacing:-0.5px; margin-top:4px; }
.kpi-val-neutral { color:#1e3a6e; }
.kpi-val-pos     { color:#155d35; }
.kpi-val-neg     { color:#9e1f1f; }
.kpi-val-zero    { color:#6b7a95; }
.period-badge { display:inline-block; border-radius:6px; padding:4px 12px; font-size:0.8rem; font-weight:700; margin:3px; }
.badge-base { background:#1e3a6e; color:#ffffff; }
.badge-curr { background:#1a7a4a; color:#ffffff; }
div[data-testid="stDataFrame"] { width:100% !important; }
div[data-testid="stDataFrame"] table { font-size:0.83rem !important; }
div[data-testid="stDataFrame"] th {
    background:#1e3a6e !important; color:white !important;
    font-weight:700 !important; font-size:0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════════════════════
ctx = render_sidebar()   # → dict with df_all, df_base, df_curr, labels, model, show_detail

df_all         = ctx["df_all"]
df_base        = ctx["df_base"]
df_curr        = ctx["df_curr"]
base_label     = ctx["base_label"]
curr_label     = ctx["curr_label"]
period_mode    = ctx["period_mode"]
analysis_model = ctx["analysis_model"]
show_detail    = ctx["show_detail"]
is_ytd         = ctx.get("is_ytd", False)

# ══════════════════════════════════════════════════════════════════════════════
# 타이틀
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="main-title">📊 매출 차이 분석 (Variance Analysis)</div>',
            unsafe_allow_html=True)

if df_all is None:
    st.info("👈 왼쪽 사이드바에서 **ERP 매출실적 파일**을 업로드하세요.")
    with st.expander("📋 엑셀 파일 컬럼 구성 안내"):
        col_info = pd.DataFrame({
            "열":  ["D","I","V","W","AB","AD","AE","AF","AI","AJ","AN","AO","BC"],
            "내용": ["매출일(YYYY-MM-DD)","매출처명","품목코드","품목명","단위",
                     "수량","환종(KRW/USD)","환율","(외화)판매단가","(외화)판매금액",
                     "(장부단가)원화환산판매단가","(장부금액)원화환산판매금액",
                     "품목계정(제품/상품/원재료/부재료/제조-수선비)"],
        })
        st.dataframe(col_info, use_container_width=True, hide_index=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# 품목 그룹 설정 (편집 테이블) — 접기/펼치기
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📂 품목 그룹 설정  (클릭하여 펼치기 / 접기)", expanded=False):
    render_group_editor(df_all)

# ── 선택된 모델 배너 ──────────────────────────────────────────────────────────
is_model_A   = "모델 A" in analysis_model
accent_color = "#4472c4" if is_model_A else "#e6812a"
badge_bg     = "#eef4ff" if is_model_A else "#fff8ee"

if is_model_A:
    st.markdown(f"""
    <div style="background:{badge_bg};border-left:5px solid {accent_color};border-radius:8px;padding:10px 16px;margin-bottom:8px;">
      <b style="color:{accent_color}">📐 모델 A — 원인별 임팩트 분석</b>&nbsp;&nbsp;
      <span style="font-size:0.82rem;color:#555;">재무·감사용 표준 │ 변수 간 간섭 완전 제거</span><br/>
      <span style="font-size:0.75rem;color:#888;margin-top:4px;display:block;">
        ① (Q1−Q0)×<b>P0_fx</b>×<b>ER0</b> │ ② (P1−P0)×<b>Q1</b>×<b>ER0</b> │ ③ (ER1−ER0)×<b>Q1</b>×<b>P1_fx</b>
      </span>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="background:{badge_bg};border-left:5px solid {accent_color};border-radius:8px;padding:10px 16px;margin-bottom:8px;">
      <b style="color:{accent_color}">📈 모델 B — 활동별 증분 분석</b>&nbsp;&nbsp;
      <span style="font-size:0.82rem;color:#555;">영업·전략 보고용 │ 상황별 Case 분기</span><br/>
      <span style="font-size:0.75rem;color:#888;margin-top:4px;display:block;">
        ① Q↑:(Q1−Q0)×<b>P1_krw</b> / Q↓:(Q1−Q0)×<b>P0_krw</b> │ ② 총차이−①−③ │ ③ P/Q 4-Case
      </span>
    </div>""", unsafe_allow_html=True)

# ── 기간 유효성 ───────────────────────────────────────────────────────────────
st.markdown("<br/>", unsafe_allow_html=True)
if df_base.empty and df_curr.empty:
    st.error("두 기간 모두 데이터가 없습니다.")
    st.stop()

# ── 차이 분석 실행 ────────────────────────────────────────────────────────────
with st.spinner("분석 중..."):
    va, va_detail = model_A(df_base, df_curr) if is_model_A else model_B(df_base, df_curr)

# ══════════════════════════════════════════════════════════════════════════════
# 분석 대상 선택 — 커스텀 그룹 기준
# ══════════════════════════════════════════════════════════════════════════════
all_items    = sorted(va["품목명"].unique())
item_mapping = st.session_state.get("item_mapping", {})

# item_mapping → groups 구성 (커스텀 그룹 우선, 미분류 후순위)
custom_groups: dict = {}
for item in all_items:
    grp = item_mapping.get(item, "").strip()
    if grp:
        custom_groups.setdefault(grp, []).append(item)

unassigned = [i for i in all_items if not item_mapping.get(i, "").strip()]

# 전체 groups (커스텀 + 미분류)
groups: dict = dict(custom_groups)
if unassigned:
    groups["미분류"] = unassigned

has_custom = len(custom_groups) > 0
custom_group_names = list(custom_groups.keys())
group_names = list(groups.keys())

st.markdown('<div class="section-header">📦 분석 대상 선택</div>', unsafe_allow_html=True)

if has_custom:
    # ── 커스텀 그룹이 있는 경우 ──────────────────────────────────────────────
    # key 직접 초기화 방식 — default 파라미터 없이 session_state만 사용
    # (default + key 동시 사용 시 리런마다 default로 리셋되는 Streamlit 버그 회피)

    # 처음 접근 시에만 초기화
    if "ms_groups" not in st.session_state:
        st.session_state["ms_groups"] = list(custom_group_names)

    # 삭제된 그룹 정리
    st.session_state["ms_groups"] = [
        g for g in st.session_state["ms_groups"] if g in group_names
    ]

    # 진짜 새로 생긴 그룹만 자동 추가 (기존에 없던 것만)
    if "known_custom_groups" not in st.session_state:
        st.session_state["known_custom_groups"] = set()
    truly_new = [g for g in custom_group_names
                 if g not in st.session_state["known_custom_groups"]]
    for g in truly_new:
        if g not in st.session_state["ms_groups"]:
            st.session_state["ms_groups"].append(g)
    st.session_state["known_custom_groups"] = set(custom_group_names)

    # default 없이 key만 — session_state 값이 그대로 유지됨
    selected_groups = st.multiselect(
        "그룹 선택 (기본: 커스텀 그룹 전체)",
        options=group_names,
        key="ms_groups",
        placeholder="그룹을 선택하세요",
    )

    # 선택된 그룹의 품목 전체 = 분석 대상
    selected_items = [
        item for gn in selected_groups for item in groups.get(gn, [])
    ]
else:
    # ── 커스텀 그룹 없는 경우: 품목 직접 선택 ───────────────────────────────
    st.caption("💡 품목 그룹 설정을 완료하면 그룹 단위로 선택할 수 있습니다.")
    selected_items = st.multiselect(
        "품목 선택 (기본: 전체)",
        options=all_items,
        default=all_items,
        key="ms_items",
        placeholder="품목을 선택하세요",
    )
    selected_groups = []

if not selected_items:
    st.warning("그룹 또는 품목을 1개 이상 선택하세요.")
    st.stop()

va_filtered        = va[va["품목명"].isin(selected_items)].copy()
va_detail_filtered = va_detail[va_detail["품목명"].isin(selected_items)].copy()

# ══════════════════════════════════════════════════════════════════════════════
# KPI 요약
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📈 종합 요약</div>', unsafe_allow_html=True)

total_base = va_filtered["매출0"].sum()
total_curr = va_filtered["매출1"].sum()
total_diff = va_filtered["총차이"].sum()
qty_v      = va_filtered["수량차이"].sum()
price_v    = va_filtered["단가차이"].sum()
fx_v       = va_filtered["환율차이"].sum()
all_krw    = va_filtered["is_krw"].all() if "is_krw" in va_filtered.columns else False

k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)

kpi_card(k1, f"기준 매출 ({base_label})", "원화 실적 합계", total_base, neutral=True)
kpi_card(k2, f"실적 매출 ({curr_label})", "원화 실적 합계", total_curr, neutral=True)
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
    if all_krw:
        k6.markdown('<div class="kpi-card kpi-card-zero"><div class="kpi-label">③ 환율 차이</div><div class="kpi-formula">(ER1−ER0)×Q1×P1_fx</div><div class="kpi-value kpi-val-zero">— KRW 해당없음</div></div>', unsafe_allow_html=True)
    else:
        kpi_card(k6, "③ 환율 차이", "(ER1−ER0)×Q1×P1_fx", fx_v)
else:
    kpi_card(k4, "① 수량 차이 (Volume Incremental)", "Q↑→×P1_krw / Q↓→×P0_krw", qty_v)
    kpi_card(k5, "② 단가 차이 (Negotiation Residual)", "총차이 − ① − ③", price_v)
    if all_krw:
        k6.markdown('<div class="kpi-card kpi-card-zero"><div class="kpi-label">③ 환율 차이 (FX Exposure)</div><div class="kpi-formula">P/Q 방향 4-Case 분기</div><div class="kpi-value kpi-val-zero">— KRW 해당없음</div></div>', unsafe_allow_html=True)
    else:
        kpi_card(k6, "③ 환율 차이 (FX Exposure)", "P/Q 방향 4-Case 분기", fx_v)

# ══════════════════════════════════════════════════════════════════════════════
# 커스텀 그룹별 차이 분석  (기본 분석 화면)
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 커스텀 그룹별 차이 분석</div>', unsafe_allow_html=True)


# ── 세부 품목 표 렌더 헬퍼 (합계 행 분리, 행 너비 통일) ─────────────────────────
def _show_split_table(df_with_total: "pd.DataFrame", money_cols: list):
    """
    build_table()이 반환하는 DataFrame(마지막 행=합계)을
    - 데이터 표 (정렬 가능)
    - 합계 표 (고정, height=56px)
    두 개로 나눠 렌더링. use_container_width=True로 너비 통일.
    """
    ROW_H = 36   # px per row (Streamlit 기본값)
    HDR_H = 40   # header height

    # 마지막 행이 합계인지 확인 후 분리
    total_mask = df_with_total.apply(
        lambda r: any("합 계" in str(v) for v in r.values), axis=1
    )
    data_df  = df_with_total[~total_mask].reset_index(drop=True)
    total_df = df_with_total[total_mask].reset_index(drop=True)

    # 데이터 표
    data_h = min(520, max(HDR_H + ROW_H, len(data_df) * ROW_H + HDR_H))
    st.dataframe(
        styled_df(data_df, money_cols),
        use_container_width=True,
        hide_index=True,
        height=data_h,
    )

    # 합계 표 (헤더 없음 효과: height = 딱 1행)
    if not total_df.empty:
        # 합계 행 스타일: 볼드 + 차이 컬럼 색상
        def _total_style(df):
            def color(v):
                try:
                    fv = float(v)
                    if fv < 0: return "color:#c0392b;font-weight:700"
                    if fv > 0: return "color:#1a7a4a;font-weight:700"
                except: pass
                return "font-weight:700"
            fmt = {c: "{:,.0f}" for c in money_cols if c in df.columns}
            styler = df.style.format(fmt, na_rep="-")
            for c in df.columns:
                styler = styler.applymap(color if c in money_cols else (lambda v: "font-weight:700"), subset=[c])
            return styler

        st.dataframe(
            _total_style(total_df),
            use_container_width=True,
            hide_index=True,
            height=HDR_H + ROW_H,   # 헤더 + 1행 = 76px
        )

# ── 그룹별 표 + 드롭다운 헬퍼 ───────────────────────────────────────────────
def _render_group_section(grp_list, grp_map, color_map, va_src, va_detail_src, sel_key):
    """
    ① 상단: 드롭다운 selectbox (어느 그룹 세부 품목을 볼지 선택)
    ② 중단: 그룹별 요약 표 (행=그룹, 열=기준매출/실적매출/총차이/①②③)
    ③ 하단: 선택된 그룹의 품목별 상세 테이블
    """
    if not grp_list:
        st.info("표시할 그룹이 없습니다.")
        return

    # ① 드롭다운 (상단 배치)
    dropdown_opts = ["전체 합산"] + grp_list
    selected_drp = st.selectbox(
        "세부 품목 드릴다운",
        options=dropdown_opts,
        index=0,
        key=sel_key,
    )

    # ② 그룹별 요약 표 데이터 구성 (합계는 마지막 행)
    all_items_in = [i for gn in grp_list for i in grp_map.get(gn, [])]
    tot = va_src[va_src["품목명"].isin(all_items_in)]
    bl = base_label; cl = curr_label

    data_rows = []
    for gn in grp_list:
        items = grp_map.get(gn, [])
        if not items:
            continue
        g_va = va_src[va_src["품목명"].isin(items)]
        data_rows.append({
            "그룹": f"📦 {gn}  ({len(items)}개 품목)",
            f"기준매출 [{bl}]": g_va["매출0"].sum(),
            f"실적매출 [{cl}]": g_va["매출1"].sum(),
            "총차이(원)":  g_va["총차이"].sum(),
            "①수량차이":  g_va["수량차이"].sum(),
            "②단가차이":  g_va["단가차이"].sum(),
            "③환율차이":  g_va["환율차이"].sum(),
            "_is_total": False,
        })

    total_row = {
        "그룹": "【합 계】",
        f"기준매출 [{bl}]": tot["매출0"].sum(),
        f"실적매출 [{cl}]": tot["매출1"].sum(),
        "총차이(원)":  tot["총차이"].sum(),
        "①수량차이":  tot["수량차이"].sum(),
        "②단가차이":  tot["단가차이"].sum(),
        "③환율차이":  tot["환율차이"].sum(),
        "_is_total": True,
    }

    # 정렬 state: 컬럼 클릭 시 데이터 행만 정렬, 합계 행은 항상 마지막
    sort_key = f"{sel_key}_sort"
    sort_col = st.session_state.get(sort_key, None)
    sort_asc = st.session_state.get(f"{sort_key}_asc", True)

    tbl_df_data = pd.DataFrame(data_rows)
    money_c = [c for c in tbl_df_data.columns if c not in ("그룹", "_is_total")]

    if sort_col and sort_col in tbl_df_data.columns:
        tbl_df_data = tbl_df_data.sort_values(sort_col, ascending=sort_asc)

    # 데이터 행만 포함한 표 (정렬 가능)
    tbl_df = tbl_df_data.drop(columns=["_is_total"])

    def _style_data(df):
        def color(v):
            try:
                fv = float(v)
                if fv < 0: return "color:#c0392b;font-weight:600"
                if fv > 0: return "color:#1a7a4a;font-weight:600"
            except: pass
            return ""
        diff_cols = ["총차이(원)", "①수량차이", "②단가차이", "③환율차이"]
        fmt = {c: "{:,.0f}" for c in money_c}
        styler = df.style.format(fmt, na_rep="-")
        for c in diff_cols:
            if c in df.columns:
                styler = styler.applymap(color, subset=[c])
        return styler

    st.dataframe(
        _style_data(tbl_df),
        use_container_width=True,
        hide_index=True,
        height=min(460, max(80, len(tbl_df)*36+40)),
    )

    # 합계 행 — 별도 고정 테이블 (정렬 영향 없음)
    total_df = pd.DataFrame([{
        k: v for k, v in total_row.items() if k != "_is_total"
    }])

    def _style_total(df):
        def color(v):
            try:
                fv = float(v)
                if fv < 0: return "color:#c0392b;font-weight:700"
                if fv > 0: return "color:#1a7a4a;font-weight:700"
            except: pass
            return "font-weight:700"
        diff_cols = ["총차이(원)", "①수량차이", "②단가차이", "③환율차이"]
        fmt = {c: "{:,.0f}" for c in money_c}
        styler = df.style.format(fmt, na_rep="-")
        for c in df.columns:
            styler = styler.applymap(
                (lambda v: color(v)) if c in diff_cols else (lambda v: "font-weight:700"),
                subset=[c]
            )
        return styler

    st.dataframe(
        _style_total(total_df),
        use_container_width=True,
        hide_index=True,
        height=70,
    )

    # ③ 선택된 그룹의 품목별 상세
    if selected_drp == "전체 합산":
        drp_items = all_items_in
        clr2 = "#1e293b"
        title = f"전체 합산 — 품목별 상세 ({len(drp_items)}개)"
    else:
        drp_items = grp_map.get(selected_drp, [])
        clr2 = color_map.get(selected_drp, "#1e40af")
        title = f"📦 {selected_drp} — 세부 품목 ({len(drp_items)}개)"

    if drp_items:
        st.markdown(
            f'<div style="background:{clr2};border-radius:7px;padding:6px 14px;'
            f'color:white;font-size:0.82rem;font-weight:700;margin:8px 0 6px 0;">'
            f'{title}</div>',
            unsafe_allow_html=True)
        drp_va = va_src[va_src["품목명"].isin(drp_items)]
        drp_vd = va_detail_src[va_detail_src["품목명"].isin(drp_items)]
        dtbl, dmc = build_table(
            drp_vd if show_detail else drp_va,
            base_label, curr_label, show_detail)
        _show_split_table(dtbl, dmc)


# ── va_disp_total 항상 정의 (다운로드용) ─────────────────────────────────────
va_disp_total, money_cols = build_table(
    va_detail_filtered if show_detail else va_filtered,
    base_label, curr_label, show_detail)

if has_custom and selected_groups:
    grp_colors = {
        gn: GROUP_COLORS[i % len(GROUP_COLORS)][0]
        for i, gn in enumerate(list(groups.keys()))
        if gn != "미분류"
    }
    sel_grp_map = {gn: [i for i in groups.get(gn, []) if i in selected_items]
                   for gn in selected_groups}
    _render_group_section(selected_groups, sel_grp_map, grp_colors,
                          va_filtered, va_detail_filtered, "drp_main")
else:
    _show_split_table(va_disp_total, money_cols)

# ══════════════════════════════════════════════════════════════════════════════
# 품목계정 분류별 차이 분석 (제품 / 상품 / 기타)
# — 각 탭 안에서 커스텀 그룹 단위로 표시, 세부 품목은 드롭다운
# ══════════════════════════════════════════════════════════════════════════════
if "품목계정_분류" in df_all.columns:
    st.markdown('<div class="section-header">🗂️ 품목계정별 차이 분석</div>', unsafe_allow_html=True)
    st.caption("제품 / 상품 / 기타(원재료·부재료·제조-수선비) 기준 집계 — 각 탭은 커스텀 그룹 단위로 표시")

    acct_map = (
        df_all[["품목명", "품목계정_분류"]]
        .drop_duplicates(subset=["품목명"])
        .set_index("품목명")["품목계정_분류"].to_dict()
    )
    ACCT_CATS   = ["제품", "상품", "기타"]
    ACCT_COLORS = {"제품": "#1e40af", "상품": "#065f46", "기타": "#7c3aed"}

    # ── KPI 카드 (제품/상품/기타 합산) ────────────────────────────────────────
    acct_cols = st.columns(3)
    for ci, cat in enumerate(ACCT_CATS):
        cat_items = [i for i in selected_items if acct_map.get(i,"기타") == cat]
        sub  = va_filtered[va_filtered["품목명"].isin(cat_items)]
        c_b  = sub["매출0"].sum(); c_c = sub["매출1"].sum()
        c_d  = sub["총차이"].sum()
        c_q  = sub["수량차이"].sum(); c_p = sub["단가차이"].sum(); c_f = sub["환율차이"].sum()
        clr  = ACCT_COLORS[cat]
        d_s  = "▲ +" if c_d >= 0 else "▼ "
        d_cl = "#16a34a" if c_d >= 0 else "#dc2626"
        acct_cols[ci].markdown(f"""
        <div style="background:white;border:1px solid #e2e8f0;border-top:4px solid {clr};
                    border-radius:10px;padding:14px 16px;">
          <div style="font-size:0.82rem;font-weight:800;color:{clr};margin-bottom:8px;">{cat}</div>
          <div style="font-size:0.72rem;color:#64748b;">기준 매출</div>
          <div style="font-size:0.98rem;font-weight:700;color:#1e293b;margin-bottom:5px;">{c_b:,.0f}원</div>
          <div style="font-size:0.72rem;color:#64748b;">실적 매출</div>
          <div style="font-size:0.98rem;font-weight:700;color:#1e293b;margin-bottom:5px;">{c_c:,.0f}원</div>
          <div style="font-size:0.72rem;color:#64748b;">총 차이</div>
          <div style="font-size:1.08rem;font-weight:900;color:{d_cl};">{d_s}{c_d:,.0f}원</div>
          <div style="font-size:0.68rem;color:#94a3b8;margin-top:4px;">
            ① {c_q:+,.0f} ② {c_p:+,.0f} ③ {c_f:+,.0f}
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── 탭별 커스텀 그룹 테이블 ────────────────────────────────────────────────
    acct_tab_list = st.tabs(["전체"] + ACCT_CATS)

    for ti, cat_label in enumerate(["전체"] + ACCT_CATS):
        with acct_tab_list[ti]:
            if cat_label == "전체":
                tab_items = selected_items
            else:
                tab_items = [i for i in selected_items if acct_map.get(i,"기타") == cat_label]

            if not tab_items:
                st.info(f"{cat_label} 분류의 데이터가 없습니다.")
                continue

            if has_custom and selected_groups:
                # 커스텀 그룹 단위로 표시
                # 해당 탭 품목이 속한 그룹만 추려서 표시
                tab_grp_map = {}
                for gn in selected_groups:
                    grp_tab_items = [i for i in groups.get(gn,[]) if i in tab_items]
                    if grp_tab_items:
                        tab_grp_map[gn] = grp_tab_items
                tab_grp_list = list(tab_grp_map.keys())

                grp_colors_acct = {
                    gn: GROUP_COLORS[i % len(GROUP_COLORS)][0]
                    for i, gn in enumerate(list(groups.keys()))
                    if gn != "미분류"
                }
                tab_va  = va_filtered[va_filtered["품목명"].isin(tab_items)]
                tab_vd  = va_detail_filtered[va_detail_filtered["품목명"].isin(tab_items)]
                _render_group_section(tab_grp_list, tab_grp_map, grp_colors_acct,
                                     tab_va, tab_vd, f"drp_acct_{cat_label}")
            else:
                # 커스텀 그룹 없으면 품목명 단위 테이블
                sub_va = va_filtered[va_filtered["품목명"].isin(tab_items)].copy()
                sub_vd = va_detail_filtered[va_detail_filtered["품목명"].isin(tab_items)].copy()
                tbl, mc = build_table(sub_vd if show_detail else sub_va,
                                      base_label, curr_label, show_detail)
                _show_split_table(tbl, mc)


# ══════════════════════════════════════════════════════════════════════════════
# 시각화
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📊 차이 구성 요소 시각화</div>', unsafe_allow_html=True)

try:
    import plotly.graph_objects as go

    tab_wf, tab_bar = st.tabs(["🌊 Waterfall (전체 합산)", "📊 품목별 총차이"])

    with tab_wf:
        fig_wf = render_waterfall(total_base, qty_v, price_v, fx_v,
                                  total_curr, base_label, curr_label, accent_color)
        st.plotly_chart(fig_wf, use_container_width=True)

        with st.expander("🔢 Waterfall 계산 근거 데이터", expanded=False):
            sign = lambda v: f"+{v:,.0f}" if v >= 0 else f"{v:,.0f}"
            pct  = lambda v, base: f"({v/base*100:+.1f}%)" if base != 0 else ""

            calc_rows = [
                {"구분": "기준 매출",   "금액 (원)": f"{total_base:,.0f}",
                 "설명": f"{base_label} 원화매출 합계", "비고": ""},
                {"구분": "① 수량 차이", "금액 (원)": sign(qty_v),
                 "설명": "수량 변동에 의한 매출 증감",
                 "비고": "기준단가×수량변화" if is_model_A else "실적/기준단가×수량변화"},
                {"구분": "② 단가 차이", "금액 (원)": sign(price_v),
                 "설명": "단가 변동에 의한 매출 증감",
                 "비고": "(P실적−P기준)×Q실적×ER기준" if is_model_A else "총차이−①−③"},
                {"구분": "③ 환율 차이", "금액 (원)": sign(fx_v),
                 "설명": "환율 변동에 의한 매출 증감",
                 "비고": "(ER실적−ER기준)×Q실적×P실적_fx" if is_model_A else "4-Case 분기"},
                {"구분": "실적 매출",   "금액 (원)": f"{total_curr:,.0f}",
                 "설명": f"{curr_label} 원화매출 합계", "비고": ""},
                {"구분": "▶ 총 차이",   "금액 (원)": sign(total_diff),
                 "설명": f"실적−기준 {pct(total_diff, total_base)}",
                 "비고": "①+②+③ = 총차이 검증"},
            ]
            calc_df = pd.DataFrame(calc_rows)
            check   = abs((qty_v + price_v + fx_v) - total_diff) < 1
            st.markdown(
                f'<div style="background:{"#d4edda" if check else "#f8d7da"};border-radius:6px;'
                f'padding:7px 14px;font-size:0.8rem;font-weight:700;'
                f'color:{"#155724" if check else "#721c24"};margin-bottom:8px;">'
                f'{"✅ 항등식 검증 통과: ①+②+③ = 총차이 (" + sign(qty_v+price_v+fx_v) + "원)" if check else "⚠️ 항등식 오차 발생"}'
                f'</div>', unsafe_allow_html=True)
            st.dataframe(calc_df, use_container_width=True, hide_index=True)

            # 품목×환종 상세
            st.markdown("**품목별 구성요소 상세 (환종 분리)**")
            st.caption("KRW행: 원화단가만 표시 / USD행: 외화단가·환율 표시")
            dr = va_detail_filtered.copy()
            dr["검증"] = dr.apply(
                lambda r: "✅" if abs(
                    round(r["수량차이"]+r["단가차이"]+r["환율차이"]) - round(r["총차이"])
                ) < 1 else f"⚠️ {round(r['수량차이']+r['단가차이']+r['환율차이'])-round(r['총차이']):+,.0f}",
                axis=1
            )
            krw_mask = dr["is_krw"] == True
            for col_name in ["P0_fx","P1_fx","ER0","ER1"]:
                if col_name in dr.columns:
                    dr.loc[krw_mask, col_name] = np.nan

            col_map = [("품목명","품목명"),("환종","환종"),("매출1","실적매출(원)"),
                       ("Q1","실적수량"),("P1_krw","실적단가(원화)"),("P1_fx","실적단가(외화)"),
                       ("ER1","실적환율"),("매출0","기준매출(원)"),("Q0","기준수량"),
                       ("P0_krw","기준단가(원화)"),("P0_fx","기준단가(외화)"),("ER0","기준환율"),
                       ("총차이","총차이(원)"),("수량차이","①수량차이(원)"),
                       ("단가차이","②단가차이(원)"),("환율차이","③환율차이(원)"),("검증","검증")]
            seen, sel_src, sel_dst = set(), [], []
            for src, dst in col_map:
                if src in dr.columns and src not in seen:
                    seen.add(src); sel_src.append(src); sel_dst.append(dst)
            detail_df = dr[sel_src].rename(columns=dict(zip(sel_src, sel_dst)))

            str_cols   = {"품목명","환종","검증"}
            num_cols_d = [c for c in detail_df.columns
                          if c not in str_cols and pd.api.types.is_numeric_dtype(detail_df[c])]
            sidx = len(detail_df)
            detail_df.loc[sidx, "품목명"] = "【합 계】"
            detail_df.loc[sidx, "환종"]   = ""
            detail_df.loc[sidx, "검증"]   = ""
            sum_target = [c for c in num_cols_d if not any(kw in c for kw in ["단가","환율"])]
            for c in sum_target:
                detail_df.loc[sidx, c] = detail_df[c].iloc[:sidx].sum()

            fmt = {c: ("{:,.2f}" if any(kw in c for kw in ["단가","환율"]) else "{:,.0f}")
                   for c in num_cols_d}

            def row_style(row):
                if row.get("품목명","") == "【합 계】":
                    return ["font-weight:700"] * len(row)
                return [""] * len(row)

            st.dataframe(
                detail_df.style.format(fmt, na_rep="-").apply(row_style, axis=1),
                use_container_width=True, hide_index=True,
            )

    with tab_bar:
        va_bar     = va_filtered.set_index("품목명")["총차이"].sort_values()
        bar_colors = ["#e74c3c" if v < 0 else "#27ae60" for v in va_bar.values]
        bar_text   = [f"▼ {v:,.0f}" if v < 0 else (f"▲ +{v:,.0f}" if v > 0 else f"{v:,.0f}")
                      for v in va_bar.values]
        fig_bar = go.Figure(go.Bar(
            x=va_bar.values, y=va_bar.index, orientation="h",
            marker_color=bar_colors,
            marker_line=dict(color=["#b03a2e" if v<0 else "#1e8449" for v in va_bar.values], width=1),
            text=bar_text, textposition="outside",
            textfont=dict(size=12, color="#0d1f3c", family="Malgun Gothic, AppleGothic, sans-serif"),
        ))
        fig_bar.update_layout(
            title_text="품목별 총 매출 차이", title_font_size=14, title_x=0.01,
            height=max(380, len(va_bar)*40),
            margin=dict(l=10, r=140, t=50, b=30),
            plot_bgcolor="#fafbfd", paper_bgcolor="#ffffff",
            font=dict(family="Malgun Gothic, AppleGothic, sans-serif"),
            xaxis=dict(title="원화 매출 차이 (₩)", gridcolor="#e8ecf3",
                       zeroline=True, zerolinecolor="#5a6a85", zerolinewidth=2),
            yaxis=dict(tickfont=dict(size=12, color="#0d1f3c"), automargin=True),
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
model_label       = "A_원인별임팩트" if is_model_A else "B_활동별증분"
excel_bytes       = to_excel_bytes(va_disp_total.reset_index(drop=True))
st.download_button(
    label="📥 분석 결과 엑셀 다운로드",
    data=excel_bytes,
    file_name=f"매출차이분석_{model_label}_{period_mode_label}_{base_label}vs{curr_label}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

with st.expander("🗂️ 원본 데이터 확인 (선택 품목 기준)"):
    raw_base = df_base[df_base["품목명"].isin(selected_items)].reset_index(drop=True)
    raw_curr = df_curr[df_curr["품목명"].isin(selected_items)].reset_index(drop=True)
    t1, t2 = st.tabs([f"기준 ({base_label}) · {len(raw_base):,}건",
                       f"실적 ({curr_label}) · {len(raw_curr):,}건"])
    with t1:
        if not raw_base.empty:
            st.dataframe(raw_base, use_container_width=True, height=280)
        else:
            st.info("선택된 품목의 기준 기간 데이터가 없습니다.")
    with t2:
        if not raw_curr.empty:
            st.dataframe(raw_curr, use_container_width=True, height=280)
        else:
            st.info("선택된 품목의 실적 기간 데이터가 없습니다.")

# ══════════════════════════════════════════════════════════════════════════════
# 모델 상세 비교표
# ══════════════════════════════════════════════════════════════════════════════
render_model_guide()
