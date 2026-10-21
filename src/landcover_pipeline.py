"""
都市公園の Forest / Grass / Water / Other 被覆率算出パイプライン
東京都デジタルツイン実現プロジェクト 3次元点群データ（LAS）を入力とする。

卒業研究「自然保全指定 × 都市公園音環境」用。
2026-10-11  v0.2 / PROVISIONAL（ChatGPT査読を受けた修正版）

v0.1 からの変更（いずれも査読指摘に基づく）
-------------------------------------------
1. 【バグ修正】未観測セル（リターン0）が Other に混入していた。
   unobserved を4クラスと独立のマスクとして保持する。
   影響：多摩平第６公園の Other% 2.35 → 1.55、山王下公園 1.93 → 1.26。
2. 【定義修正】多重反射率 pen をパルスベースに改めた。
   v0.1 は点ベース（全点に対する number_of_returns>1 の点の割合）で、
   多重反射パルスを反射数だけ重複計数していた。
   閾値0.20での判定は両定義で 21.6% のセルが食い違う。
3. 【表示修正】被覆率を A_park 基準と有効観測域基準の両方で返す。
4. survey_date は LAS ヘッダから取得しない（下記 注意 を参照）。

前提
----
- 入力 LAS の座標参照系は JGD2011 / 平面直角座標系第9系（EPSG:6677）。
  LAS ファイルに CRS の VLR は格納されていないため外部から与える。
  適用前に X/Y 実座標が図郭位置と整合することを確認すること。
- 公園ポリゴンも EPSG:6677。
- LAS point format 3（RGB 付き）、classification に 2=地表面 が付与されていること。

注意：計測日は本ファイルから取得できない
----------------------------------------
LAS ヘッダの File Creation Year / Day は **ファイル作成日** であり測量日ではない。
実測でも、物理的に隣接する 2 図郭の creation_date が 2023-01-05 と 2023-06-07 と
5 か月ずれる一方、両図郭の gps_time 分布はほぼ同一であった。
さらに global_encoding の GPS Time Type = 0（GPS Week Time）であるため、
週番号が格納されておらず gps_time から絶対日時を復元できない。
→ survey_date は東京都の公式測量メタデータから取得すること。

未確定のパラメータ（精度検証後に固定すること）
---------------------------------------------
- VEG_EXG_MIN, VEG_PEN_MIN : 植生判定閾値。目視判読との照合で較正が必要。
  実測では Forest の 17.5 ポイント分が ExG 単独（構造的裏づけなし）で判定されており、
  この閾値の較正は結果に直接効く。
- WATER_MIN_AREA_M2        : 無返測域を水面とみなす最小連結面積。パイロットでは
                             検証対象公園に水面がなく **未検証**。
- H_TREE                   : 3.0 m を主分析、2.0 / 5.0 m を感度分析とする想定。
- RES                      : 0.25 m と 0.5 m で Forest% が 2.4 ポイント異なる。
                             0.25 m では地表面リターンのあるセルが 39.7% しかなく、
                             DEM の 6 割が補間値になる。解像度は未確定。
"""

from dataclasses import dataclass, asdict

import laspy
import numpy as np
from affine import Affine
from rasterio import features
from scipy import ndimage

# --- 固定パラメータ -------------------------------------------------------
CRS = "EPSG:6677"
RES = 0.25           # 解析グリッド [m]
BUFFER = 5.0         # 公園ポリゴン外側に確保する余白 [m]
H_TREE = 3.0         # 樹冠とみなす最低樹高 [m]
MIN_COVERAGE = 0.95  # これ未満は NA 扱い

# --- 要較正パラメータ -----------------------------------------------------
VEG_EXG_MIN = 0.02        # 可視域植生指数 ExG の下限
VEG_PEN_MIN = 0.20        # 多重反射率（number_of_returns > 1 の点の割合）の下限
WATER_MIN_AREA_M2 = 4.0   # 無返測域を水面と判定する最小連結面積 [m2]
CHM_MAX_PLAUSIBLE = 45.0  # これを超える CHM は外れ値として除去（都データは外れ値を含むと明記）


PEN_MODE = "pulse"   # "pulse"（推奨・物理的に正しい）または "point"（v0.1互換）


@dataclass
class ParkCover:
    """被覆率。*_pct は A_park（公園ポリゴン面積）を分母とする。

    forest/grass/water/other/unobserved の5つで A_park を網羅し、合計100%になる。
    これは計算上の恒等式であり、分類が正しいことの証拠ではない。
    *_of_observed は有効観測域（リターンのあったセル＋水面判定セル）を分母とする。
    """
    cells: int
    area_m2: float
    forest_pct: float
    grass_pct: float
    water_pct: float
    other_pct: float
    unobserved_pct: float
    forest_of_observed: float
    grass_of_observed: float
    coverage_ratio: float          # (観測セル＋水面セル) / 全セル。DEM補間は含めない
    ground_observed_ratio: float   # 地表面リターンのあるセル / 全セル
    median_points_per_cell: int
    n_outlier_cells: int
    h_tree: float
    res: float
    pen_mode: str


def _load_points(las_paths, bounds, buffer=BUFFER):
    """公園の外接矩形＋余白に入る点のみを複数 LAS から集約する。"""
    mnx, mny, mxx, mxy = bounds
    acc = []
    for path in las_paths:
        las = laspy.read(path)
        m = ((las.x >= mnx - buffer) & (las.x <= mxx + buffer)
             & (las.y >= mny - buffer) & (las.y <= mxy + buffer))
        if not m.any():
            continue
        acc.append(np.column_stack([
            las.x[m], las.y[m], las.z[m], las.classification[m],
            las.red[m], las.green[m], las.blue[m], las.number_of_returns[m],
            las.return_number[m],
        ]))
    if not acc:
        raise ValueError("公園範囲に点群が存在しない（図郭の指定を確認すること）")
    return np.vstack(acc)


def _rasterize(points, bounds, res=RES, buffer=BUFFER):
    """点群を 0.25 m グリッドへ集約し DSM / DEM / CHM / ExG / 多重反射率を返す。"""
    mnx, mny, mxx, mxy = bounds
    x0, y0 = mnx - buffer, mny - buffer
    nx = int(np.ceil((mxx + buffer - x0) / res))
    ny = int(np.ceil((mxy + buffer - y0) / res))
    n = nx * ny

    ix = np.clip(((points[:, 0] - x0) / res).astype(int), 0, nx - 1)
    iy = np.clip(((points[:, 1] - y0) / res).astype(int), 0, ny - 1)
    cell = iy * nx + ix

    # DSM: セル内最高点。DEM: 地表面点（classification==2）の最低点。
    dsm = np.full(n, -9999.0)
    np.maximum.at(dsm, cell, points[:, 2])
    ground = points[:, 3] == 2
    dem = np.full(n, 9999.0)
    np.minimum.at(dem, cell[ground], points[ground, 2])

    count = np.bincount(cell, minlength=n)
    ground_count = np.bincount(cell[ground], minlength=n)

    # 多重反射率 pen
    #   pulse: (return_number==1 かつ number_of_returns>1 の点数) / (return_number==1 の点数)
    #          = 「そのセルを通過したパルスのうち、複数反射を生じた割合」
    #   point: (number_of_returns>1 の点数) / (全点数)  ← v0.1。多重反射を重複計数する
    if PEN_MODE == "pulse":
        first = points[:, 8] == 1
        pen_den = np.bincount(cell[first], minlength=n)
        pen_num = np.bincount(cell[first & (points[:, 7] > 1)], minlength=n)
    else:
        pen_den = count
        pen_num = np.bincount(cell[points[:, 7] > 1], minlength=n)

    dsm = np.where(dsm == -9999.0, np.nan, dsm).reshape(ny, nx)
    dem = np.where(dem == 9999.0, np.nan, dem).reshape(ny, nx)
    count = count.reshape(ny, nx)
    ground_count = ground_count.reshape(ny, nx)
    pen = np.divide(pen_num, pen_den, out=np.zeros(n),
                    where=pen_den > 0).reshape(ny, nx)

    # 地表面点のないセルは最近傍の地盤高で補完する（樹冠下・建物下で頻出）
    idx = ndimage.distance_transform_edt(
        np.isnan(dem), return_distances=False, return_indices=True)
    chm = dsm - dem[tuple(idx)]

    # セル内最高点の RGB から可視域植生指数 ExG を計算
    order = np.lexsort((points[:, 2], cell))
    cs = cell[order]
    last = np.ones(len(cs), bool)
    last[:-1] = cs[1:] != cs[:-1]
    rgb = np.full((n, 3), np.nan)
    rgb[cs[last]] = points[np.ix_(order[last], [4, 5, 6])]
    s = np.nansum(rgb, axis=1)
    s[s == 0] = np.nan
    exg = ((2 * rgb[:, 1] - rgb[:, 0] - rgb[:, 2]) / s).reshape(ny, nx)

    return dict(nx=nx, ny=ny, x0=x0, y0=y0, dsm=dsm, chm=chm,
                exg=exg, pen=pen, count=count, ground_count=ground_count)


def _classify(grid, h_tree=H_TREE):
    """W → F → G → O の順に相互排他に判定し、未観測を独立マスクとして返す。

    未観測（リターン0）のセルを Other に丸めてはならない。v0.1 はこれを
    Other に混入させていた（多摩平第６公園で 0.80 ポイント分）。

    植生判定は多重反射率（構造）と ExG（分光）の論理和とする。冬季取得の
    データでは落葉樹の ExG が下がるため分光指標のみに依存しない。ただし
    実測では Forest の 17.5 ポイント分が ExG 単独で判定されており、
    この論理和は偽陽性を取り込みうる。閾値は未較正。
    """
    chm, exg, pen, count = grid["chm"], grid["exg"], grid["pen"], grid["count"]

    observed = count > 0
    outlier = observed & (chm > CHM_MAX_PLAUSIBLE)
    valid = observed & ~outlier

    # 無返測域のうち一定面積以上まとまったものを水面候補とする（未検証）
    no_return = ~observed
    lab, nlab = ndimage.label(no_return)
    min_cells = int(round(WATER_MIN_AREA_M2 / (RES * RES)))
    sizes = ndimage.sum(no_return, lab, range(1, nlab + 1))
    water = no_return & np.isin(lab, np.nonzero(sizes >= min_cells)[0] + 1)
    unobserved = no_return & ~water

    is_spec = np.nan_to_num(exg, nan=-1) > VEG_EXG_MIN
    is_veg = (pen >= VEG_PEN_MIN) | is_spec
    forest = valid & (chm >= h_tree) & is_veg
    grass = valid & ~forest & (chm < h_tree) & is_spec
    other = valid & ~forest & ~grass
    return forest, grass, water, other, unobserved, outlier


def compute_park_cover(polygon, las_paths, h_tree=H_TREE, res=RES):
    """公園ポリゴン1件について被覆率を算出する。

    polygon  : shapely geometry（EPSG:6677）
    las_paths: 公園に重なる 1/500 図郭の LAS パス（複数可）
    """
    points = _load_points(las_paths, polygon.bounds)
    grid = _rasterize(points, polygon.bounds, res=res)
    forest, grass, water, other, unobserved, outlier = _classify(grid, h_tree=h_tree)

    transform = Affine(res, 0, grid["x0"], 0, res, grid["y0"])
    mask = features.rasterize(
        [(polygon, 1)], out_shape=(grid["ny"], grid["nx"]),
        transform=transform, dtype="uint8").astype(bool)
    total = int(mask.sum())
    observed_total = int(((grid["count"] > 0) | water)[mask].sum())

    def pct(a, denom=total):
        return round(100 * float((a & mask).sum()) / denom, 2)

    return ParkCover(
        cells=total,
        area_m2=round(total * res * res, 1),
        forest_pct=pct(forest),
        grass_pct=pct(grass),
        water_pct=pct(water),
        other_pct=pct(other),
        unobserved_pct=pct(unobserved),
        forest_of_observed=pct(forest, observed_total),
        grass_of_observed=pct(grass, observed_total),
        coverage_ratio=round(observed_total / total, 4),
        ground_observed_ratio=round(float((grid["ground_count"] > 0)[mask].sum()) / total, 4),
        median_points_per_cell=int(np.median(grid["count"][mask])),
        n_outlier_cells=int((outlier & mask).sum()),
        h_tree=h_tree,
        res=res,
        pen_mode=PEN_MODE,
    )


def tile_url(mesh_no, product="lp", region="tama"):
    """1/500 図郭番号から東京都点群データのダウンロード URL を組み立てる。

    図郭番号と URL の対応は、G空間情報センターが配信するベクタタイル
    （.../Vectortile/{region}/{product}/{z}/{x}/{y}.pbf）の属性 MESH_NO / URL
    から取得したもの。2026-10-11 時点で確認。
    """
    year = {"tama": "2023", "23ku": "2024"}[region]
    return (f"https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/"
            f"{year}/dig/{product}/{mesh_no}.zip")


if __name__ == "__main__":
    import sys

    import geopandas as gpd

    gpkg, layer, name = sys.argv[1], sys.argv[2], sys.argv[3]
    las = sys.argv[4:]
    gdf = gpd.read_file(gpkg, layer=layer)
    poly = gdf.loc[gdf["公園名"] == name].geometry.iloc[0]
    for h in (2.0, 3.0, 5.0):
        print(asdict(compute_park_cover(poly, las, h_tree=h)))
