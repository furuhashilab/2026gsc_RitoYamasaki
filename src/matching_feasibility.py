"""Matched-pair 成立性の予備診断（PROVISIONAL）

暫定的な土地被覆値を用いて、各 Treatment に比較可能な Control が存在するかを診断する。
最終ペアを固定するものではない。
"""
import numpy as np
import pandas as pd

COV_MIN = 0.93          # PROVISIONAL。分布の自然な切れ目に基づく（§report）
SCENARIOS = {
    "S1_area_forest_grass_water": ["log_area", "forest_pct", "grass_pct"],
    "S2_area_forest_water":       ["log_area", "forest_pct"],
    "S3_area_forest":             ["log_area", "forest_pct"],
}
WATER_CONSTRAINT = {"S1_area_forest_grass_water": True, "S2_area_forest_water": True,
                    "S3_area_forest": False}


def prep(df, cov_min=COV_MIN):
    d = df.copy()
    d["log_area"] = np.log10(d.park_area_m2)
    d["has_water"] = (d.water_pct_landuse >= 1.0).astype(int)
    d["usable"] = d.coverage_ratio >= cov_min
    return d


def match(treat, ctrl, cols, water_constraint, replace=False):
    """貪欲マッチング。候補の少ない Treatment から順に割り当てる（復元なし）。"""
    pool = pd.concat([treat[cols], ctrl[cols]])
    mu, sd = pool.mean(), pool.std(ddof=0).replace(0, 1.0)
    T = ((treat[cols] - mu) / sd).values
    C = ((ctrl[cols] - mu) / sd).values
    D = np.sqrt(((T[:, None, :] - C[None, :, :]) ** 2).sum(axis=2))
    if water_constraint:
        bad = treat.has_water.values[:, None] != ctrl.has_water.values[None, :]
        D = np.where(bad, np.inf, D)
    order = np.argsort(np.isfinite(D).sum(axis=1))      # 候補が少ない Treatment を優先
    used, out = set(), []
    for i in order:
        cand = [(D[i, j], j) for j in range(len(ctrl)) if np.isfinite(D[i, j])
                and (replace or j not in used)]
        if not cand:
            out.append(dict(t_idx=i, c_idx=None, dist=np.nan)); continue
        dist, j = min(cand)
        if not replace:
            used.add(j)
        out.append(dict(t_idx=i, c_idx=j, dist=dist))
    return pd.DataFrame(out).sort_values("t_idx").reset_index(drop=True), D


def rank_table(treat, ctrl, cols, water_constraint, topn=5):
    pool = pd.concat([treat[cols], ctrl[cols]])
    mu, sd = pool.mean(), pool.std(ddof=0).replace(0, 1.0)
    T = ((treat[cols] - mu) / sd).values
    C = ((ctrl[cols] - mu) / sd).values
    D = np.sqrt(((T[:, None, :] - C[None, :, :]) ** 2).sum(axis=2))
    if water_constraint:
        bad = treat.has_water.values[:, None] != ctrl.has_water.values[None, :]
        D = np.where(bad, np.inf, D)
    rows = []
    for i in range(len(treat)):
        order = np.argsort(D[i])
        for r, j in enumerate(order[:topn], 1):
            if not np.isfinite(D[i, j]):
                break
            rows.append(dict(
                treatment=treat.park.iloc[i], t_muni=treat.muni.iloc[i],
                protection_ratio=treat.protection_ratio.iloc[i],
                t_area=treat.park_area_m2.iloc[i], t_forest=treat.forest_pct.iloc[i],
                t_grass=treat.grass_pct.iloc[i], t_water=treat.has_water.iloc[i],
                rank=r, control=ctrl.park.iloc[j], c_muni=ctrl.muni.iloc[j],
                c_area=ctrl.park_area_m2.iloc[j], c_forest=ctrl.forest_pct.iloc[j],
                c_grass=ctrl.grass_pct.iloc[j], c_water=ctrl.has_water.iloc[j],
                dist=round(float(D[i, j]), 4),
                area_ratio=round(float(ctrl.park_area_m2.iloc[j] / treat.park_area_m2.iloc[i]), 3),
                d_forest=round(float(ctrl.forest_pct.iloc[j] - treat.forest_pct.iloc[i]), 2),
                d_grass=round(float(ctrl.grass_pct.iloc[j] - treat.grass_pct.iloc[i]), 2)))
    return pd.DataFrame(rows)
