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
    # session_state로 그룹 선택 유지 (모델 변경 시에도 초기화 안 됨)
    if "selected_groups_persistent" not in st.session_state:
        st.session_state.selected_groups_persistent = custom_group_names

    # 유효하지 않은 그룹(삭제된 그룹) 정리
    st.session_state.selected_groups_persistent = [
        g for g in st.session_state.selected_groups_persistent if g in group_names
    ]
    # 새로 생긴 커스텀 그룹은 자동 추가
    for g in custom_group_names:
        if g not in st.session_state.selected_groups_persistent:
            st.session_state.selected_groups_persistent.append(g)

    selected_groups = st.multiselect(
        "그룹 선택 (기본: 커스텀 그룹 전체)",
        options=group_names,
        default=st.session_state.selected_groups_persistent,
        key="ms_groups",
        placeholder="그룹을 선택하세요",
    )
    # 선택 결과를 session_state에 저장 → 모델 변경 후에도 유지
    st.session_state.selected_groups_persistent = selected_groups

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
# 품목별 차이 분석 테이블 — 그룹별 섹션
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">📋 품목별 차이 분석 테이블</div>', unsafe_allow_html=True)

if has_custom and selected_groups:
    # 그룹별 탭으로 표시
    tab_labels = ["전체 합산"] + [gn for gn in selected_groups]
    tabs = st.tabs(tab_labels)

    # 전체 합산 탭
    with tabs[0]:
        va_disp_total, money_cols = build_table(
            va_detail_filtered if show_detail else va_filtered,
            base_label, curr_label, show_detail
        )
        st.dataframe(
            styled_df(va_disp_total, money_cols),
            use_container_width=True,
            height=min(520, max(260, (len(va_disp_total)+1)*36+40)),
        )

    # 그룹별 탭
    for ti, gn in enumerate(selected_groups):
        with tabs[ti + 1]:
            grp_items = [i for i in groups.get(gn, []) if i in selected_items]
            if not grp_items:
                st.info("선택된 품목이 없습니다.")
                continue
            clr = GROUP_COLORS[list(groups.keys()).index(gn) % len(GROUP_COLORS)][0]
            grp_va_t     = va[va["품목명"].isin(grp_items)]
            grp_detail_t = va_detail[va_detail["품목명"].isin(grp_items)]
            g_base = grp_va_t["매출0"].sum()
            g_curr = grp_va_t["매출1"].sum()
            g_diff = grp_va_t["총차이"].sum()
            d_sign = "▲ +" if g_diff >= 0 else "▼ "
            st.markdown(
                f'<div style="background:{clr};border-radius:7px;padding:7px 14px;'
                f'color:white;font-size:0.85rem;font-weight:700;margin-bottom:8px;">'
                f'📦 {gn} &nbsp;│&nbsp; 기준 {g_base:,.0f}원 → 실적 {g_curr:,.0f}원 '
                f'&nbsp;│&nbsp; 총차이 {d_sign}{g_diff:,.0f}원</div>',
                unsafe_allow_html=True,
            )
            grp_tbl, grp_money = build_table(
                grp_detail_t if show_detail else grp_va_t,
                base_label, curr_label, show_detail
            )
            st.dataframe(
                styled_df(grp_tbl, grp_money),
                use_container_width=True,
                height=min(480, max(200, (len(grp_tbl)+1)*36+40)),
            )
else:
    # 커스텀 그룹 없는 경우 기존 단일 테이블
    va_disp_total, money_cols = build_table(
        va_detail_filtered if show_detail else va_filtered,
        base_label, curr_label, show_detail
    )
    st.dataframe(
        styled_df(va_disp_total, money_cols),
        use_container_width=True,
        height=min(520, max(260, (len(va_disp_total)+1)*36+40)),
    )

# ══════════════════════════════════════════════════════════════════════════════
# 그룹별 드릴다운 (컴팩트 expander)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.get("item_mapping") and len(selected_groups) > 0:
    with st.expander("🔍 그룹별 드릴다운 상세 보기", expanded=False):
        for gi, gn in enumerate(selected_groups):
            if gn == "미분류":
                continue
            items = groups.get(gn, [])
            grp_items_valid = [i for i in items if i in all_items and i in selected_items]
            if not grp_items_valid:
                continue

            clr_active = GROUP_COLORS[gi % len(GROUP_COLORS)][0]
            grp_va = va[va["품목명"].isin(grp_items_valid)]
            g_base  = grp_va["매출0"].sum()
            g_curr  = grp_va["매출1"].sum()
            g_diff  = grp_va["총차이"].sum()
            g_qty   = grp_va["수량차이"].sum()
            g_price = grp_va["단가차이"].sum()
            g_fx    = grp_va["환율차이"].sum()
            d_sign  = "▲ +" if g_diff >= 0 else "▼ "

            st.markdown(f"""
            <div style="background:{clr_active};border-radius:8px;padding:8px 14px;
                        display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
              <span style="color:white;font-weight:800;font-size:0.88rem;">📦 {gn} ({len(grp_items_valid)}개)</span>
              <span style="color:white;font-size:0.78rem;">
                기준 {g_base:,.0f} → 실적 {g_curr:,.0f} │
                총차이 <b>{d_sign}{g_diff:,.0f}</b>원
                (① {g_qty:+,.0f} ② {g_price:+,.0f} ③ {g_fx:+,.0f})
              </span>
            </div>""", unsafe_allow_html=True)

            grp_detail = va_detail[va_detail["품목명"].isin(grp_items_valid)].copy()
            grp_tbl, grp_money = build_table(
                grp_detail if show_detail else grp_va,
                base_label, curr_label, show_detail
            )
            st.dataframe(
                styled_df(grp_tbl, grp_money),
                use_container_width=True,
                height=min(350, max(180, (len(grp_tbl)+1)*36+40)),
            )
            st.markdown("---")

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
