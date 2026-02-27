import pandas as pd
import streamlit as st
from io import BytesIO
from collections import Counter


def _mapping_to_excel(editor_df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        editor_df.to_excel(writer, index=False, sheet_name="품목그룹")
    return buf.getvalue()


def _excel_to_mapping(data):
    try:
        df = pd.read_excel(BytesIO(data), dtype=str).fillna("")
        if "품목명" not in df.columns or "커스텀 그룹명" not in df.columns:
            return {}
        return {
            row["품목명"]: row["커스텀 그룹명"].strip()
            for _, row in df.iterrows()
            if str(row["품목명"]).strip()
        }
    except Exception:
        return {}


def render_group_editor(df_all):
    st.markdown('<div class="section-header">📂 품목 그룹 설정</div>',
                unsafe_allow_html=True)
    st.caption("커스텀 그룹명 열에 그룹명을 입력하면 같은 이름끼리 묶입니다. 빈칸은 미분류로 처리됩니다.")

    items_df = (
        df_all[["품목계정", "품목명", "품목코드"]]
        .drop_duplicates(subset=["품목명"])
        .sort_values(["품목계정", "품목명"])
        .reset_index(drop=True)
    )

    mapping = st.session_state.get("item_mapping", {})
    items_df["커스텀 그룹명"] = items_df["품목명"].map(mapping).fillna("")

    col_up, col_dl = st.columns(2)
    with col_up:
        uploaded = st.file_uploader(
            "이전 그룹 설정 불러오기 (.xlsx)",
            type=["xlsx"],
            key="upload_group_excel",
        )
        if uploaded:
            loaded = _excel_to_mapping(uploaded.read())
            if loaded:
                st.session_state.item_mapping = loaded
                st.success("불러오기 완료")
                st.rerun()
            else:
                st.error("파일 형식 오류 (품목명, 커스텀 그룹명 열 필요)")

    with col_dl:
        dl_df = items_df.copy()
        dl_df["커스텀 그룹명"] = dl_df["품목명"].map(
            st.session_state.get("item_mapping", {})
        ).fillna("")
        st.download_button(
            label="현재 그룹 설정 다운로드 (.xlsx)",
            data=_mapping_to_excel(dl_df),
            file_name="품목그룹설정.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    edited_df = st.data_editor(
        items_df,
        use_container_width=True,
        hide_index=True,
        height=min(600, max(200, len(items_df) * 36 + 60)),
        column_config={
            "품목계정": st.column_config.TextColumn("품목계정", disabled=True, width="small"),
            "품목코드": st.column_config.TextColumn("품목코드", disabled=True, width="small"),
            "품목명":   st.column_config.TextColumn("품목명",   disabled=True, width="medium"),
            "커스텀 그룹명": st.column_config.TextColumn(
                "커스텀 그룹명",
                help="같은 이름을 입력한 품목끼리 하나의 그룹으로 묶입니다",
                width="medium",
            ),
        },
        key="group_editor_table",
    )

    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button("그룹 설정 저장", type="primary", use_container_width=True):
            new_mapping = {
                str(row["품목명"]): str(row["커스텀 그룹명"]).strip()
                for _, row in edited_df.iterrows()
                if str(row.get("커스텀 그룹명", "")).strip()
            }
            st.session_state.item_mapping = new_mapping
            grp_count = len(set(new_mapping.values()))
            st.success(f"{len(new_mapping)}개 품목 / {grp_count}개 그룹 저장 완료")
            st.rerun()
    with c2:
        if st.button("전체 초기화", use_container_width=True):
            st.session_state.item_mapping = {}
            st.rerun()

    current_mapping = st.session_state.get("item_mapping", {})
    if current_mapping:
        grp_counts = Counter(v for v in current_mapping.values() if v)
        badges = "  ".join(
            f'<span style="display:inline-block;background:#1e40af;color:white;'
            f'border-radius:12px;padding:2px 10px;font-size:0.75rem;margin:2px;">'
            f'{grp} ({cnt})</span>'
            for grp, cnt in sorted(grp_counts.items())
        )
        st.markdown(
            f'<div style="margin-top:6px;line-height:2;">{badges}</div>',
            unsafe_allow_html=True,
        )
