# ══════════════════════════════════════════════════════════════════════════════
# ui_group_selector.py  —  품목/그룹 선택 카드 UI
# ══════════════════════════════════════════════════════════════════════════════
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)


import streamlit as st
import pandas as pd
from config import GROUP_COLORS


def render_group_selector(va: pd.DataFrame) -> tuple[list[str], dict[str, list[str]]]:
    """
    분석 결과 DataFrame(va)을 받아 그룹 카드 UI를 렌더링하고,
    선택된 품목 목록과 그룹 구조를 반환한다.

    반환: (selected_items, groups)
      selected_items : 선택된 그룹에 속한 품목명 리스트
      groups         : {그룹명: [품목명, ...]} (미분류 포함)
    """
    st.markdown('<div class="section-header">📦 분석 대상 선택</div>',
                unsafe_allow_html=True)

    all_items = sorted(va["품목명"].unique())

    # ── 그룹 구조 계산 ──────────────────────────────────────────────────────
    groups_raw  = st.session_state.get("item_groups", {})
    assigned    = {item for items in groups_raw.values() for item in items}
    unassigned  = [i for i in all_items if i not in assigned]

    groups: dict[str, list[str]] = {}
    for gn, items in groups_raw.items():
        valid = [i for i in items if i in all_items]
        if valid:
            groups[gn] = valid
    if unassigned:
        groups["미분류"] = unassigned

    # ── selected_groups 초기화 ──────────────────────────────────────────────
    if "selected_groups" not in st.session_state:
        st.session_state.selected_groups = set(groups.keys())

    for gn in groups:
        if (gn not in st.session_state.selected_groups
                and gn not in st.session_state.get("_deselected_groups", set())):
            st.session_state.selected_groups.add(gn)
    st.session_state.selected_groups = {
        g for g in st.session_state.selected_groups if g in groups
    }

    # ── 전체 선택/해제 ──────────────────────────────────────────────────────
    ga, gb, _ = st.columns([1, 1, 6])
    with ga:
        if st.button("✅ 전체 선택", key="grp_all", use_container_width=True):
            st.session_state.selected_groups = set(groups.keys())
            st.session_state["_deselected_groups"] = set()
            st.rerun()
    with gb:
        if st.button("⬜ 전체 해제", key="grp_none", use_container_width=True):
            st.session_state.selected_groups = set()
            st.session_state["_deselected_groups"] = set(groups.keys())
            st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # ── 그룹 카드 렌더링 ────────────────────────────────────────────────────
    for gi, (gn, items) in enumerate(groups.items()):
        is_active = gn in st.session_state.selected_groups
        clr_active, _, clr_dark = GROUP_COLORS[gi % len(GROUP_COLORS)]

        grp_va    = va[va["품목명"].isin(items)]
        grp_diff  = grp_va["총차이"].sum()
        grp_curr  = grp_va["매출1"].sum()
        diff_sign = "▲ +" if grp_diff >= 0 else "▼ "

        card_bg     = clr_active              if is_active else "#f8fafc"
        card_border = clr_active              if is_active else "#cbd5e1"
        tag_bg      = "rgba(255,255,255,0.22)" if is_active else "#e2e8f0"
        tag_color   = "#ffffff"               if is_active else "#374151"
        title_color = "#ffffff"               if is_active else clr_dark
        kpi_color   = "#e0f2fe"               if is_active else "#475569"
        diff_color  = "#86efac" if is_active else ("#16a34a" if grp_diff >= 0 else "#dc2626")

        item_tags = "  ".join(
            f'<span style="display:inline-block;background:{tag_bg};color:{tag_color};'
            f'border-radius:4px;padding:1px 8px;font-size:0.7rem;margin:1px;">'
            f'{item}</span>'
            for item in items
        )

        left_col, right_col = st.columns([1, 11])
        with left_col:
            if st.button(
                "✔" if is_active else "○",
                key=f"grp_toggle_{gn}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if is_active:
                    st.session_state.selected_groups.discard(gn)
                    st.session_state.setdefault("_deselected_groups", set()).add(gn)
                else:
                    st.session_state.selected_groups.add(gn)
                    st.session_state.get("_deselected_groups", set()).discard(gn)
                st.rerun()

        with right_col:
            st.markdown(f"""
            <div style="background:{card_bg};border:1.5px solid {card_border};
                        border-radius:10px;padding:10px 14px;margin-bottom:2px;">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
                <span style="font-size:0.88rem;font-weight:800;color:{title_color};">
                  📦 {gn}&nbsp;<span style="font-size:0.72rem;font-weight:500;opacity:0.85;">({len(items)}개 품목)</span>
                </span>
                <span style="font-size:0.78rem;color:{kpi_color};text-align:right;">
                  실적 {grp_curr:,.0f}원<br>
                  <span style="color:{diff_color};font-weight:700;">{diff_sign}{grp_diff:,.0f}원</span>
                </span>
              </div>
              <div style="line-height:1.8;">{item_tags}</div>
            </div>""", unsafe_allow_html=True)

    # ── 선택된 품목 계산 ────────────────────────────────────────────────────
    selected_items = [
        item for gn in st.session_state.selected_groups
        for item in groups.get(gn, [])
        if item in all_items
    ]
    if not selected_items:
        st.warning("그룹을 1개 이상 선택하세요.")
        st.stop()

    return selected_items, groups
