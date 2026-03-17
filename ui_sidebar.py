# ══════════════════════════════════════════════════════════════════════════════
# ui_sidebar.py  —  사이드바 렌더링 (그룹 설정은 메인 화면으로 이동)
# ══════════════════════════════════════════════════════════════════════════════
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

import streamlit as st
import pandas as pd
from io import BytesIO
from data_loader import load_excel
from config import MONTH_KR



def _parse_group_excel(data: bytes) -> dict:
    """그룹 설정 엑셀(품목명, 커스텀 그룹명) → {품목명: 그룹명} dict."""
    try:
        df = pd.read_excel(BytesIO(data), dtype=str).fillna("")
        if "품목명" not in df.columns or "커스텀 그룹명" not in df.columns:
            return {}
        return {
            str(row["품목명"]).strip(): str(row["커스텀 그룹명"]).strip()
            for _, row in df.iterrows()
            if str(row["품목명"]).strip() and str(row["커스텀 그룹명"]).strip()
        }
    except Exception:
        return {}


def render_sidebar():
    df_all = None

    with st.sidebar:
        st.markdown("## 📂 파일 업로드")
        uploaded = st.file_uploader("ERP 매출실적 (.xlsx / .xls)", type=["xlsx", "xls"])

        st.markdown("---")
        st.markdown("### 📋 품목 그룹 설정 불러오기")
        grp_uploaded = st.file_uploader(
            "그룹 설정 엑셀 업로드 (.xlsx)",
            type=["xlsx"],
            key="sidebar_group_upload",
        )
        if grp_uploaded:
            # file_id로 중복 처리 방지 — rerun 후 무한루프 차단
            fid = getattr(grp_uploaded, "file_id", grp_uploaded.name)
            if st.session_state.get("_last_grp_file_id") != fid:
                mapping = _parse_group_excel(grp_uploaded.read())
                if mapping:
                    st.session_state.item_mapping = mapping
                    st.session_state["_last_grp_file_id"] = fid
                    st.session_state.pop("group_editor_table", None)
                    st.session_state.pop("ms_groups", None)
                    st.session_state.pop("known_custom_groups", None)
                    st.success(f"{len(mapping)}개 품목 그룹 불러오기 완료")
                    st.rerun()
                else:
                    st.session_state["_last_grp_file_id"] = fid
                    st.error("형식 오류 (품목명·커스텀 그룹명 열 필요)")
        st.markdown("---")

        if uploaded:
            df_all = load_excel(uploaded.read(), uploaded.name)

        if df_all is not None:
            st.markdown("### 📅 실적 연월")
            avail_years = sorted(df_all["연도"].unique())
            curr_year   = st.selectbox("실적 연도", avail_years, index=len(avail_years)-1)
            avail_m     = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
            curr_month  = st.selectbox("실적 월", avail_m,
                                       format_func=lambda x: MONTH_KR[x],
                                       index=len(avail_m)-1)

            st.markdown("### 🔀 비교 기간")
            period_mode = st.radio("기준 기간 설정",
                                   ["전년 동월 대비 (YoY)", "전월 대비 (MoM)", "전년 동기 누적 대비 (YTD)"],
                                   index=0)

            is_ytd = (period_mode == "전년 동기 누적 대비 (YTD)")

            if period_mode == "전년 동월 대비 (YoY)":
                base_year, base_month = curr_year - 1, curr_month
            elif period_mode == "전월 대비 (MoM)":
                base_year  = curr_year - 1 if curr_month == 1 else curr_year
                base_month = 12            if curr_month == 1 else curr_month - 1
            else:  # YTD
                base_year, base_month = curr_year - 1, curr_month

            if is_ytd:
                m_range = list(range(1, curr_month + 1))
                base_label = f"{base_year}년 1~{MONTH_KR[curr_month]} 누적"
                curr_label = f"{curr_year}년 1~{MONTH_KR[curr_month]} 누적"
            else:
                base_label = f"{base_year}년 {MONTH_KR[base_month]}"
                curr_label = f"{curr_year}년 {MONTH_KR[curr_month]}"

            st.markdown(
                f'<span class="period-badge badge-base">기준: {base_label}</span>'
                f'<span class="period-badge badge-curr">실적: {curr_label}</span>',
                unsafe_allow_html=True,
            )

            st.markdown("---")
            st.markdown("### 🧮 분석 모델 선택")
            if "analysis_model" not in st.session_state:
                st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
            is_A_active = "모델 A" in st.session_state.analysis_model
            _render_model_cards(is_A_active)
            analysis_model = st.session_state.analysis_model

            st.markdown("---")
            st.markdown("### ⚙️ 표시 설정")
            show_detail = st.checkbox("수량·단가·환율 상세 컬럼 표시", value=False)
            st.caption("ℹ️ ①수량차이 + ②단가차이 + ③환율차이 = 총차이")
            st.caption("🆕 신규 품목은 당해 매출 전액을 수량차이로 귀속 (단가·환율차이=0)")

            if is_ytd:
                df_base = df_all[(df_all["연도"] == base_year) & (df_all["월"].isin(m_range))].copy()
                df_curr = df_all[(df_all["연도"] == curr_year) & (df_all["월"].isin(m_range))].copy()
            else:
                df_base = df_all[(df_all["연도"] == base_year) & (df_all["월"] == base_month)].copy()
                df_curr = df_all[(df_all["연도"] == curr_year) & (df_all["월"] == curr_month)].copy()

        else:
            base_label = curr_label = period_mode = ""
            df_base = df_curr = None
            show_detail = False
            is_ytd = False
            if "analysis_model" not in st.session_state:
                st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
            analysis_model = st.session_state.analysis_model

    return dict(
        df_all=df_all, df_base=df_base, df_curr=df_curr,
        base_label=base_label, curr_label=curr_label, period_mode=period_mode,
        analysis_model=analysis_model, show_detail=show_detail, is_ytd=is_ytd,
    )


def _render_model_cards(is_A_active: bool):
    if is_A_active:
        card_s = "background:#1e3a6e;border:2px solid #1e3a6e;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#ffffff;"
        desc_s = "font-size:0.76rem;color:#c8dcff;margin-top:5px;line-height:1.6;"
        tag_s = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#ffffff;color:#1e3a6e;"
        btn_lbl = "✔ 선택됨 (모델 A)"
    else:
        card_s = "background:#dde8ff;border:2px solid #2d5faa;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#0d2050;"
        desc_s = "font-size:0.76rem;color:#1a2d50;margin-top:5px;line-height:1.6;"
        tag_s = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#1e3a6e;color:#ffffff;"
        btn_lbl = "이 모델 선택 →"

    badge_a = '&nbsp;<span style="font-size:0.75rem;background:#27ae60;color:white;border-radius:3px;padding:1px 7px;">선택중</span>' if is_A_active else ''
    st.markdown(f"""
    <div style="{card_s}">
      <div style="{title_s}">📐 모델 A — 원인별 임팩트 분석{badge_a}</div>
      <div style="{desc_s}">
        변수 간 간섭을 완전히 제거하여<br>각 요인의 <b>절대적 영향력</b>을 측정.<br><br>
        ① 수량차이: (Q1−Q0)×<b>P0_fx</b>×<b>ER0</b><br>
        ② 단가차이: (P1−P0)×<b>Q1</b>×<b>ER0</b><br>
        ③ 환율차이: (ER1−ER0)×<b>Q1</b>×<b>P1_fx</b><br><br>
        <b>✔ 재무·감사·외부보고 표준</b>
      </div>
      <span style="{tag_s}">수량↑↓ 모두 전년 외화단가 적용</span>
    </div>""", unsafe_allow_html=True)
    if st.button(btn_lbl, key="sel_model_A", use_container_width=True,
                 type="primary" if is_A_active else "secondary"):
        st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
        st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if not is_A_active:
        card_s = "background:#7a3300;border:2px solid #7a3300;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#ffffff;"
        desc_s = "font-size:0.76rem;color:#ffd8b0;margin-top:5px;line-height:1.6;"
        tag_s = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#ffffff;color:#7a3300;"
        btn_lbl = "✔ 선택됨 (모델 B)"
    else:
        card_s = "background:#ffe0c0;border:2px solid #c9641a;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#5a1800;"
        desc_s = "font-size:0.76rem;color:#4a1800;margin-top:5px;line-height:1.6;"
        tag_s = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#7a3300;color:#ffffff;"
        btn_lbl = "이 모델 선택 →"

    badge_b = '&nbsp;<span style="font-size:0.75rem;background:#27ae60;color:white;border-radius:3px;padding:1px 7px;">선택중</span>' if not is_A_active else ''
    st.markdown(f"""
    <div style="{card_s}">
      <div style="{title_s}">📈 모델 B — 활동별 증분 분석{badge_b}</div>
      <div style="{desc_s}">
        영업 활동의 <b>실질적 비즈니스 가치</b>를 평가.<br>
        상황(Case)에 따라 가중치를 다르게 적용.<br><br>
        ① 수량차이: Q↑→×<b>P1_krw</b> / Q↓→×<b>P0_krw</b><br>
        ② 단가차이: <b>총차이 − ① − ③</b> (잔여값)<br>
        ③ 환율차이: P/Q 방향 <b>4-Case 분기</b><br><br>
        <b>✔ 영업·전략·내부경영 보고</b>
      </div>
      <span style="{tag_s}">수량↑=현재 원화단가 / 수량↓=전년 원화단가</span>
    </div>""", unsafe_allow_html=True)
    if st.button(btn_lbl, key="sel_model_B", use_container_width=True,
                 type="primary" if not is_A_active else "secondary"):
        st.session_state.analysis_model = "모델 B — 활동별 증분 분석"
        st.rerun()
