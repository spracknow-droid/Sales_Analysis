# ══════════════════════════════════════════════════════════════════════════════
# models.py  —  차이 분석 핵심 계산 로직 (순수 Python/pandas, Streamlit 의존 없음)
# ══════════════════════════════════════════════════════════════════════════════
import numpy as np
import pandas as pd


# ── 집계 공통 함수 ─────────────────────────────────────────────────────────────

def aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """
    [품목명 × 환종] 기준 분리 집계.

    핵심 설계 원칙:
      - KRW 거래와 USD(외화) 거래를 절대 혼합하지 않음
      - KRW행 : P_krw = 원화단가 가중평균,  P_fx = NaN,  ER = NaN
      - USD행 : P_fx  = 외화단가 가중평균,  P_krw = 원화단가 가중평균,
                ER    = 원화매출합 / 외화금액합  (항등식 Q·P_fx·ER = 원화매출 보장)

    반환 컬럼: 품목명, 환종, Q, P_fx, P_krw, ER, 원화매출, is_krw
    """
    if df.empty:
        return pd.DataFrame(
            columns=["품목명", "환종", "Q", "P_fx", "P_krw", "ER", "원화매출", "is_krw"])

    g = df.copy()
    g["_ccy"] = g["환종"].str.strip().str.upper()

    rows = []
    for (item, ccy), grp in g.groupby(["품목명", "_ccy"]):
        is_krw = (ccy == "KRW")
        Q      = grp["수량"].sum()
        rev    = grp["원화금액"].sum()
        if Q == 0:
            continue

        P_krw = (grp["원화단가"] * grp["수량"]).sum() / Q

        if is_krw:
            P_fx = np.nan
            ER   = np.nan
        else:
            P_fx = (grp["외화단가"] * grp["수량"]).sum() / Q
            fx_amt_sum = grp["외화금액"].sum()
            if fx_amt_sum == 0:
                fx_amt_sum = Q * P_fx
            ER = rev / fx_amt_sum if fx_amt_sum != 0 else np.nan

        rows.append({
            "품목명": item, "환종": ccy,
            "Q": Q, "P_fx": P_fx, "P_krw": P_krw,
            "ER": ER, "원화매출": rev, "is_krw": is_krw,
        })

    return pd.DataFrame(rows)


def _merge_base_curr(base_df: pd.DataFrame, curr_df: pd.DataFrame) -> pd.DataFrame:
    """
    기준/실적 집계 후 [품목명 × 환종] outer merge.
    신규(Q0=0) / 단종(Q1=0) 케이스도 자동 포함.
    """
    b = aggregate(base_df).rename(columns={
        "Q": "Q0", "P_fx": "P0_fx", "P_krw": "P0_krw",
        "ER": "ER0", "원화매출": "매출0", "is_krw": "is_krw0",
    })
    c = aggregate(curr_df).rename(columns={
        "Q": "Q1", "P_fx": "P1_fx", "P_krw": "P1_krw",
        "ER": "ER1", "원화매출": "매출1", "is_krw": "is_krw1",
    })
    m = pd.merge(b, c, on=["품목명", "환종"], how="outer")

    num_cols  = ["Q0","P0_fx","P0_krw","ER0","매출0","Q1","P1_fx","P1_krw","ER1","매출1"]
    bool_cols = ["is_krw0", "is_krw1"]
    m[num_cols]  = m[num_cols].fillna(0)
    m[bool_cols] = m[bool_cols].fillna(False)
    m["is_krw"]  = m["is_krw0"] | m["is_krw1"]
    return m


def _summarize_by_item(m: pd.DataFrame) -> pd.DataFrame:
    """환종별 raw 계산 결과를 품목명 단위로 합산."""
    agg_cols = ["매출0","매출1","총차이","수량차이","단가차이","환율차이"]
    grp_sum  = m.groupby("품목명")[agg_cols].sum().reset_index()
    grp_krw  = m.groupby("품목명")["is_krw"].all().reset_index()
    grp_q    = m.groupby("품목명")[["Q0","Q1"]].sum().reset_index()
    result   = pd.merge(grp_sum, grp_krw, on="품목명")
    result   = pd.merge(result,  grp_q,   on="품목명")
    for c in ["P0_fx","P0_krw","ER0","P1_fx","P1_krw","ER1"]:
        result[c] = np.nan
    return result


# ── 모델 A: 원인별 임팩트 분석 ────────────────────────────────────────────────

def model_A(base_df: pd.DataFrame, curr_df: pd.DataFrame):
    """
    원인별 임팩트 분석 — 재무/감사용 표준 모델

    KRW:  ①(Q1−Q0)×P0_krw  ②(P1_krw−P0_krw)×Q1  ③0
    USD:  ①(Q1−Q0)×P0_fx×ER0  ②(P1_fx−P0_fx)×Q1×ER0  ③(ER1−ER0)×Q1×P1_fx
          항등식: ①+②+③ = 매출1 − 매출0  (항상 성립)

    신규(Q0=0) → 매출1 전액 → ①,  단종(Q1=0) → 매출0 전액 → ①(-)

    반환: (품목명 단위 요약 DataFrame, 환종별 raw DataFrame)
    """
    m = _merge_base_curr(base_df, curr_df)

    def calc_row(row):
        if row["Q0"] == 0:
            return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})
        if row["Q1"] == 0:
            return pd.Series({"수량차이": -row["매출0"], "단가차이": 0.0, "환율차이": 0.0})

        if row["is_krw"]:
            qty   = (row["Q1"]     - row["Q0"])     * row["P0_krw"]
            price = (row["P1_krw"] - row["P0_krw"]) * row["Q1"]
            fx    = 0.0
        else:
            qty   = (row["Q1"]    - row["Q0"])    * row["P0_fx"] * row["ER0"]
            price = (row["P1_fx"] - row["P0_fx"]) * row["Q1"]   * row["ER0"]
            fx    = (row["ER1"]   - row["ER0"])   * row["Q1"]   * row["P1_fx"]

        total = row["매출1"] - row["매출0"]
        if abs(qty + price + fx - total) > 1:
            price += total - (qty + price + fx)   # 부동소수점 잔차 흡수

        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})

    v = m.apply(calc_row, axis=1)
    m["수량차이"], m["단가차이"], m["환율차이"] = v["수량차이"], v["단가차이"], v["환율차이"]
    m["총차이"] = m["매출1"] - m["매출0"]

    return _summarize_by_item(m), m.copy()


# ── 모델 B: 활동별 증분 분석 ──────────────────────────────────────────────────

def model_B(base_df: pd.DataFrame, curr_df: pd.DataFrame):
    """
    활동별 증분 분석 — 영업/전략 보고용 모델

    ① 수량차이: Q↑→(Q1−Q0)×P1_krw  /  Q↓→(Q1−Q0)×P0_krw
    ③ 환율차이: P/Q 방향 4-Case 분기  (KRW=0)
    ② 단가차이: 총차이 − ① − ③  (Residual)

    반환: (품목명 단위 요약 DataFrame, 환종별 raw DataFrame)
    """
    m = _merge_base_curr(base_df, curr_df)

    def calc_row(row):
        if row["Q0"] == 0:
            return pd.Series({"수량차이": row["매출1"], "단가차이": 0.0, "환율차이": 0.0})
        if row["Q1"] == 0:
            return pd.Series({"수량차이": -row["매출0"], "단가차이": 0.0, "환율차이": 0.0})

        q_up  = row["Q1"] >= row["Q0"]
        qty   = (row["Q1"] - row["Q0"]) * (row["P1_krw"] if q_up else row["P0_krw"])
        total = row["매출1"] - row["매출0"]

        if row["is_krw"]:
            fx    = 0.0
            price = total - qty
        else:
            dER  = row["ER1"] - row["ER0"]
            p_up = row["P1_fx"] >= row["P0_fx"]
            if   p_up and     q_up:  fx = dER * row["Q0"] * row["P1_fx"]
            elif p_up and not q_up:  fx = dER * row["Q1"] * row["P1_fx"]
            elif not p_up and q_up:  fx = dER * row["Q0"] * row["P0_fx"]
            else:                    fx = dER * row["Q1"] * row["P0_fx"]
            price = total - qty - fx

        return pd.Series({"수량차이": qty, "단가차이": price, "환율차이": fx})

    v = m.apply(calc_row, axis=1)
    m["수량차이"], m["단가차이"], m["환율차이"] = v["수량차이"], v["단가차이"], v["환율차이"]
    m["총차이"] = m["매출1"] - m["매출0"]

    return _summarize_by_item(m), m.copy()
