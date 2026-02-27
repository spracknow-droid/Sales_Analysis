# ══════════════════════════════════════════════════════════════════════════════
# ui_sidebar.py  —  사이드바 렌더링
#   반환값: (df_all, df_base, df_curr, base_label, curr_label,
#            analysis_model, show_detail, period_mode)
# ══════════════════════════════════════════════════════════════════════════════
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)


import streamlit as st
from data_loader import load_excel, groups_to_json_bytes, json_bytes_to_groups
from config import MONTH_KR


def render_sidebar():
    """
    사이드바 전체를 렌더링하고 메인 화면에서 필요한 상태값을 dict로 반환.

    반환 키:
      df_all, df_base, df_curr,
      base_label, curr_label, period_mode,
      analysis_model, show_detail
    """
    df_all = None

    with st.sidebar:
        st.markdown("## 📂 파일 업로드")
        uploaded = st.file_uploader("ERP 매출실적 (.xlsx / .xls)", type=["xlsx", "xls"])
        st.markdown("---")

        if uploaded:
            df_all = load_excel(uploaded.read(), uploaded.name)

        if df_all is not None:
            # ── 실적 연월 ────────────────────────────────────────────────────
            st.markdown("### 📅 실적 연월")
            avail_years = sorted(df_all["연도"].unique())
            curr_year   = st.selectbox("실적 연도", avail_years, index=len(avail_years)-1)
            avail_m     = sorted(df_all[df_all["연도"] == curr_year]["월"].unique())
            curr_month  = st.selectbox("실적 월", avail_m,
                                       format_func=lambda x: MONTH_KR[x],
                                       index=len(avail_m)-1)

            # ── 비교 기간 ────────────────────────────────────────────────────
            st.markdown("### 🔀 비교 기간")
            period_mode = st.radio("기준 기간 설정",
                                   ["전년 동월 대비 (YoY)", "전월 대비 (MoM)"], index=0)
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
                unsafe_allow_html=True,
            )

            # ── 분석 모델 선택 ───────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### 🧮 분석 모델 선택")
            if "analysis_model" not in st.session_state:
                st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"

            is_A_active = "모델 A" in st.session_state.analysis_model
            _render_model_cards(is_A_active)
            analysis_model = st.session_state.analysis_model

            # ── 품목 그룹 설정 ───────────────────────────────────────────────
            st.markdown("---")
            _render_group_settings(df_all)

            # ── 표시 설정 ────────────────────────────────────────────────────
            st.markdown("---")
            st.markdown("### ⚙️ 표시 설정")
            show_detail = st.checkbox("수량·단가·환율 상세 컬럼 표시", value=False)
            st.caption("ℹ️ ①수량차이 + ②단가차이 + ③환율차이 = 총차이")
            st.caption("🆕 신규 품목은 당해 매출 전액을 수량차이로 귀속 (단가·환율차이=0)")

            df_base = df_all[(df_all["연도"] == base_year) & (df_all["월"] == base_month)].copy()
            df_curr = df_all[(df_all["연도"] == curr_year) & (df_all["월"] == curr_month)].copy()

        else:
            base_label = curr_label = period_mode = ""
            df_base = df_curr = None
            show_detail = False
            if "analysis_model" not in st.session_state:
                st.session_state.analysis_model = "모델 A — 원인별 임팩트 분석"
            analysis_model = st.session_state.analysis_model

    return dict(
        df_all=df_all, df_base=df_base, df_curr=df_curr,
        base_label=base_label, curr_label=curr_label, period_mode=period_mode,
        analysis_model=analysis_model, show_detail=show_detail,
    )


# ── 내부 헬퍼: 모델 카드 ──────────────────────────────────────────────────────

def _render_model_cards(is_A_active: bool):
    # 모델 A
    if is_A_active:
        card_s  = "background:#1e3a6e;border:2px solid #1e3a6e;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#ffffff;"
        desc_s  = "font-size:0.76rem;color:#c8dcff;margin-top:5px;line-height:1.6;"
        tag_s   = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#ffffff;color:#1e3a6e;"
        btn_lbl = "✔ 선택됨 (모델 A)"
    else:
        card_s  = "background:#dde8ff;border:2px solid #2d5faa;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#0d2050;"
        desc_s  = "font-size:0.76rem;color:#1a2d50;margin-top:5px;line-height:1.6;"
        tag_s   = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#1e3a6e;color:#ffffff;"
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

    # 모델 B
    if not is_A_active:
        card_s  = "background:#7a3300;border:2px solid #7a3300;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#ffffff;"
        desc_s  = "font-size:0.76rem;color:#ffd8b0;margin-top:5px;line-height:1.6;"
        tag_s   = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#ffffff;color:#7a3300;"
        btn_lbl = "✔ 선택됨 (모델 B)"
    else:
        card_s  = "background:#ffe0c0;border:2px solid #c9641a;border-radius:10px;padding:13px 15px;margin-bottom:4px;"
        title_s = "font-size:0.9rem;font-weight:800;color:#5a1800;"
        desc_s  = "font-size:0.76rem;color:#4a1800;margin-top:5px;line-height:1.6;"
        tag_s   = "display:inline-block;font-size:0.69rem;font-weight:700;border-radius:4px;padding:2px 8px;margin-top:7px;background:#7a3300;color:#ffffff;"
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


# ── 내부 헬퍼: 그룹 설정 UI ───────────────────────────────────────────────────

def _render_group_settings(df_all):
    st.markdown("### 📂 품목 그룹 설정")

    if "item_groups" not in st.session_state:
        st.session_state.item_groups = {}

    all_items = sorted(df_all["품목명"].unique().tolist())

    # 저장/불러오기
    with st.expander("💾 설정 저장 / 불러오기", expanded=False):
        st.caption("Streamlit Cloud는 새로고침 시 초기화됩니다. PC에 저장 후 불러오세요.")
        if st.session_state.item_groups:
            st.download_button(
                "⬇️ 현재 그룹 설정 다운로드 (.json)",
                data=groups_to_json_bytes(st.session_state.item_groups),
                file_name="groups_config.json", mime="application/json",
                use_container_width=True,
            )
        else:
            st.info("저장할 그룹이 없습니다.")
        st.markdown("---")
        uploaded_cfg = st.file_uploader("⬆️ 그룹 설정 불러오기 (.json)",
                                        type=["json"], key="upload_groups_cfg")
        if uploaded_cfg is not None:
            loaded = json_bytes_to_groups(uploaded_cfg.read())
            if loaded:
                if st.button("이 설정으로 덮어쓰기", use_container_width=True, type="primary"):
                    st.session_state.item_groups = loaded
                    st.success(f"✅ {len(loaded)}개 그룹 불러오기 완료")
                    st.rerun()
            else:
                st.error("파일 형식이 올바르지 않습니다.")

    # 새 그룹 추가
    with st.expander("➕ 새 그룹 추가", expanded=False):
        new_name = st.text_input("그룹 이름", key="new_grp_name", placeholder="예: 주력 제품")
        assigned = {i for items in st.session_state.item_groups.values() for i in items}
        new_items = st.multiselect("포함할 품목 선택",
                                   options=[i for i in all_items if i not in assigned],
                                   key="new_grp_items", placeholder="품목을 선택하세요")
        if st.button("그룹 추가", key="btn_add_group", use_container_width=True, type="primary"):
            name = new_name.strip()
            if not name:                              st.error("그룹 이름을 입력하세요.")
            elif name in st.session_state.item_groups: st.error(f"'{name}' 그룹이 이미 존재합니다.")
            elif not new_items:                       st.error("품목을 1개 이상 선택하세요.")
            else:
                st.session_state.item_groups[name] = new_items
                st.rerun()

    # 기존 그룹 수정/삭제
    if st.session_state.item_groups:
        for grp_name, grp_items in list(st.session_state.item_groups.items()):
            with st.expander(f"📦 {grp_name}  ({len(grp_items)}개)", expanded=False):
                st.caption("포함 품목: " + ", ".join(grp_items))
                except_this = {i for gn, its in st.session_state.item_groups.items()
                               if gn != grp_name for i in its}
                edited = st.multiselect("품목 수정",
                                        options=[i for i in all_items if i not in except_this],
                                        default=grp_items, key=f"edit_{grp_name}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("저장", key=f"save_{grp_name}", use_container_width=True):
                        if not edited: st.error("품목 1개 이상 필요")
                        else:
                            st.session_state.item_groups[grp_name] = edited
                            st.rerun()
                with c2:
                    if st.button("🗑 삭제", key=f"del_{grp_name}", use_container_width=True):
                        del st.session_state.item_groups[grp_name]
                        st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        st.download_button(
            "💾 현재 설정 저장하기",
            data=groups_to_json_bytes(st.session_state.item_groups),
            file_name="groups_config.json", mime="application/json",
            use_container_width=True, key="dl_groups_bottom",
        )
    else:
        st.caption("그룹이 없습니다. 위에서 추가하세요.")
