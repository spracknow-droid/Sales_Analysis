# ══════════════════════════════════════════════════════════════════════════════
# ui_model_guide.py  —  하단 분석 모델 상세 비교표
# ══════════════════════════════════════════════════════════════════════════════
import streamlit as st


def render_model_guide():
    """두 모델(A/B) 수식·설명·비교표를 렌더링한다."""
    st.markdown('<div class="section-header">📖 분석 모델 상세 비교</div>',
                unsafe_allow_html=True)

    st.markdown("""<style>
.fb-block { border-radius:8px; padding:13px 16px; margin:6px 0; font-family:'Malgun Gothic','AppleGothic',sans-serif; }
.fb-block-qty   { background:#ddeeff; border-left:4px solid #1a4a9a; }
.fb-block-price { background:#ffe8d0; border-left:4px solid #9a3d00; }
.fb-block-fx    { background:#d4f0e0; border-left:4px solid #0d5c30; }
.fb-title { font-size:0.72rem; font-weight:800; letter-spacing:0.5px; text-transform:uppercase; margin-bottom:7px; }
.fb-title-qty   { color:#0d2d6e; }
.fb-title-price { color:#6b2200; }
.fb-title-fx    { color:#0a3d20; }
.fb-eq  { font-family:'Courier New',monospace; font-size:0.9rem; font-weight:700;
          background:rgba(0,0,0,0.10); color:#0d1f3c; padding:6px 11px; border-radius:4px;
          display:block; margin:6px 0; }
.fb-eq2 { font-family:'Courier New',monospace; font-size:0.78rem; font-weight:600;
          background:rgba(0,0,0,0.08); color:#0d1f3c; padding:4px 9px; border-radius:3px;
          display:block; margin:3px 0; }
.fb-desc { font-size:0.76rem; color:#1a2535; line-height:1.6; margin-top:5px; }
.fb-note { font-size:0.71rem; color:#1a2535; background:rgba(0,0,0,0.10);
           padding:3px 9px; border-radius:3px; display:inline-block; margin-top:6px; font-weight:600; }
.case-g { display:grid; grid-template-columns:1fr 1fr; gap:5px; margin-top:7px; }
.case-b { background:white; border:1px solid #7abf90; border-radius:6px; padding:7px 9px; }
.case-lbl { font-size:0.7rem; font-weight:800; color:#0a3d20; margin-bottom:3px; }
.case-eq  { font-family:'Courier New',monospace; font-size:0.71rem;
            background:#c8ecd8; color:#0a3d20; padding:2px 5px; border-radius:3px; display:block; font-weight:600; }
.diff-tbl { width:100%; border-collapse:collapse; font-family:'Malgun Gothic','AppleGothic',sans-serif; font-size:0.8rem; margin-top:6px; }
.diff-tbl th { padding:9px 12px; font-weight:800; text-align:center; }
.diff-tbl td { padding:9px 12px; border:1px solid #d0d8e8; vertical-align:top; line-height:1.55; }
.diff-tbl .td-cat { background:#dde6ff; color:#0d1f3c; font-weight:800; text-align:center; width:140px; }
.diff-tbl .td-a   { background:#eef3ff; color:#0d1f3c; }
.diff-tbl .td-b   { background:#fff0e0; color:#4a1800; }
.ch { display:inline-block; font-size:0.68rem; font-weight:800; border-radius:20px; padding:2px 9px; margin:1px 2px; }
.ch-b { background:#1e40af; color:#ffffff; }
.ch-o { background:#9a3412; color:#ffffff; }
.ch-g { background:#065f46; color:#ffffff; }
</style>""", unsafe_allow_html=True)

    # 헤더 배너
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1e3a6e,#2d5faa);border-radius:10px;
                    padding:14px 18px;color:white;margin-bottom:8px;">
          <div style="font-size:1.0rem;font-weight:900;margin-bottom:3px;">📐 모델 A — 원인별 임팩트 분석</div>
          <div style="font-size:0.78rem;color:#c8dcff;">재무·감사·외부보고 표준 | 변수 간 간섭 완전 제거</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#7a3300,#c9641a);border-radius:10px;
                    padding:14px 18px;color:white;margin-bottom:8px;">
          <div style="font-size:1.0rem;font-weight:900;margin-bottom:3px;">📈 모델 B — 활동별 증분 분석</div>
          <div style="font-size:0.78rem;color:#ffd8b0;">영업·전략 보고용 | 실제 비즈니스 가치 평가</div>
        </div>""", unsafe_allow_html=True)

    # ① 수량 차이
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="fb-block fb-block-qty">
          <div class="fb-title fb-title-qty">① 수량 차이 (Quantity Variance)</div>
          <span class="fb-eq">(Q실적 − Q기준) × P기준_외화단가 × ER기준</span>
          <div class="fb-desc">💡 <b>수량만 변했다면?</b><br>단가·환율을 기준 고정, 수량 변화만으로 생긴 순수 물량 효과.</div>
          <span class="fb-note">수량↑↓ 무관 — 항상 기준 외화단가 적용</span>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="fb-block fb-block-qty">
          <div class="fb-title fb-title-qty">① 수량 차이 (Volume Incremental)</div>
          <div class="fb-desc">💡 <b>새로 판 물건은 실적 가격으로, 잃은 물건은 기준 가격으로</b></div>
          <div style="margin-top:8px;">
            <div style="font-size:0.73rem;font-weight:800;color:#0a4d20;margin-bottom:2px;">▲ 수량 증가 시</div>
            <span class="fb-eq2">(Q실적 − Q기준) × P실적_원화단가</span>
            <div style="font-size:0.73rem;font-weight:800;color:#8b0000;margin:7px 0 2px 0;">▼ 수량 감소 시</div>
            <span class="fb-eq2">(Q실적 − Q기준) × P기준_원화단가</span>
          </div>
        </div>""", unsafe_allow_html=True)

    # ② 단가 차이
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="fb-block fb-block-price">
          <div class="fb-title fb-title-price">② 단가 차이 (Price Variance)</div>
          <span class="fb-eq">(P실적_외화단가 − P기준_외화단가) × Q실적 × ER기준</span>
          <div class="fb-desc">💡 <b>단가만 바뀌었다면?</b><br>수량은 실적 확정, 환율은 기준 고정. 외화 단가 변동의 순수 효과.</div>
          <span class="fb-note">환율 기준 고정 → 환율 효과 완전 배제</span>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="fb-block fb-block-price">
          <div class="fb-title fb-title-price">② 단가 차이 (Negotiation Residual)</div>
          <span class="fb-eq">총차이 − ①수량차이 − ③환율차이</span>
          <div class="fb-desc">💡 <b>수량·환율 효과를 모두 제거하고 남은 것이 단가 협상 결과</b><br>영업팀 가격 협상력의 순수 기여분.</div>
          <span class="fb-note">잔여(Residual) → 설계상 항등식 항상 성립</span>
        </div>""", unsafe_allow_html=True)

    # ③ 환율 차이
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        <div class="fb-block fb-block-fx">
          <div class="fb-title fb-title-fx">③ 환율 차이 (FX Variance)</div>
          <span class="fb-eq">(ER실적 − ER기준) × Q실적 × P실적_외화단가</span>
          <div class="fb-desc">💡 <b>환율만 바뀌었다면?</b><br>수량·단가 실적 확정 후 환율 변동만으로 원화 환산액 변화 측정.</div>
          <span class="fb-note">KRW 거래는 환율차이 = 0</span>
        </div>""", unsafe_allow_html=True)
    with col_b:
        st.markdown("""
        <div class="fb-block fb-block-fx">
          <div class="fb-title fb-title-fx">③ 환율 차이 (FX Exposure) — 4-Case 분기</div>
          <div class="fb-desc" style="margin-bottom:6px;">💡 단가↑↓ × 수량↑↓ 조합에 따라 환율 노출 범위가 달라짐</div>
          <div class="case-g">
            <div class="case-b"><div class="case-lbl">단가↑ &amp; 수량↑</div>
              <span class="case-eq">(ER실적−ER기준) × Q기준 × P실적_fx</span></div>
            <div class="case-b"><div class="case-lbl">단가↑ &amp; 수량↓</div>
              <span class="case-eq">(ER실적−ER기준) × Q실적 × P실적_fx</span></div>
            <div class="case-b"><div class="case-lbl">단가↓ &amp; 수량↑</div>
              <span class="case-eq">(ER실적−ER기준) × Q기준 × P기준_fx</span></div>
            <div class="case-b"><div class="case-lbl">단가↓ &amp; 수량↓</div>
              <span class="case-eq">(ER실적−ER기준) × Q실적 × P기준_fx</span></div>
          </div>
          <span class="fb-note">KRW 거래는 환율차이 = 0</span>
        </div>""", unsafe_allow_html=True)

    # 비교표
    st.markdown("""
<div style="font-size:0.92rem;font-weight:800;color:#1a6fd4;
            border-bottom:2px solid #93c5fd;padding-bottom:5px;margin:20px 0 10px 0;">
  🔍 핵심 차이점 비교
</div>
<table class="diff-tbl">
<thead>
  <tr>
    <th class="td-cat" style="background:#1e40af;color:white;"> </th>
    <th style="background:#1e40af;color:white;">📐 모델 A — 원인별 임팩트</th>
    <th style="background:#9a3412;color:white;">📈 모델 B — 활동별 증분</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td class="td-cat">수량↑ 시 단가 기준</td>
    <td class="td-a"><span class="ch ch-b">기준 외화단가</span><br>물량 성과를 보수적으로 평가</td>
    <td class="td-b"><span class="ch ch-o">실적 원화단가</span><br>새로 판 물건은 실적 가격으로 반영</td>
  </tr>
  <tr>
    <td class="td-cat">단가차이 계산</td>
    <td class="td-a"><span class="ch ch-g">직접 계산</span> 변수 독립</td>
    <td class="td-b"><span class="ch ch-o">잔여값 Residual</span> 총차이−①−③</td>
  </tr>
  <tr>
    <td class="td-cat">환율차이 계산</td>
    <td class="td-a"><span class="ch ch-g">단일 공식</span> 단순·명확</td>
    <td class="td-b"><span class="ch ch-o">4-Case 분기</span> 상황별 가중치</td>
  </tr>
  <tr>
    <td class="td-cat">①+②+③=총차이</td>
    <td class="td-a"><span class="ch ch-g">✅ 수학적 항등</span></td>
    <td class="td-b"><span class="ch ch-g">✅ 설계상 보장</span></td>
  </tr>
  <tr>
    <td class="td-cat">적합한 보고</td>
    <td class="td-a"><span class="ch ch-b">재무제표</span> <span class="ch ch-b">외부감사</span> <span class="ch ch-b">원가분석</span></td>
    <td class="td-b"><span class="ch ch-o">영업성과</span> <span class="ch ch-o">전략보고</span> <span class="ch ch-o">단가협상</span></td>
  </tr>
</tbody>
</table>""", unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)
