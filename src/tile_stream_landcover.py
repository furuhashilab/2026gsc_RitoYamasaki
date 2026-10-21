"""
図郭ストリーミング方式の土地被覆算出（v0.3 / PROVISIONAL）

1図郭ずつ LAS と公式DEM(grd25) を取得 → 当該図郭に重なる全公園の集計を更新 → 即削除。
ディスク占有のピークを1図郭分（約500MB）に抑える。

v0.2 からの変更（研究者指示 K1–K3 に基づく PROVISIONAL 採用）
 - DEM: 自前補間をやめ公式 grd25 を使用（K2）
 - Forest: CHM >= H_TREE かつ 建物現況ポリゴン外（K1）。分光閾値を樹冠判定に使わない
 - Water : 土地利用現況調査 コード700（K3）。LiDAR無返測域による判定は行わない
 - Grass : CHM < H_TREE かつ ExG > 閾値（舗装・裸地と区別するため分光情報を保持）
           ※ Forest から分光を外しても Grass には必要。NEEDS_VALIDATION
"""
import os
import shutil
import subprocess
import zipfile

import numpy as np
import rasterio
from affine import Affine
from rasterio import features

H_TREE = 3.0
RES = 0.25
BUF = 5.0
EXG_MIN = 0.02
CHM_MAX = 45.0
BASE = "https://gic-tokyo.s3.ap-northeast-1.amazonaws.com/2023/dig"
TMP = "dl/_stream"


class ParkAccum:
    """公園1件分の集計バッファ。図郭をまたいで加算・更新する。"""

    def __init__(self, pid, poly):
        self.pid = pid
        self.poly = poly
        mnx, mny, mxx, mxy = poly.bounds
        self.x0, self.y0 = mnx - BUF, mny - BUF
        self.nx = int(np.ceil((mxx + BUF - self.x0) / RES))
        self.ny = int(np.ceil((mxy + BUF - self.y0) / RES))
        s = (self.ny, self.nx)
        self.dsm = np.full(s, -9e9)
        self.rgb = np.zeros(s + (3,))
        self.dem = np.full(s, np.nan)
        self.cnt = np.zeros(s, np.int32)
        self.pulse = np.zeros(s, np.int32)
        self.multi = np.zeros(s, np.int32)
        self.transform = Affine(RES, 0, self.x0, 0, RES, self.y0)
        self.mask = features.rasterize(
            [(poly, 1)], out_shape=s, transform=self.transform, dtype="uint8").astype(bool)

    def cells(self, x, y):
        ix = ((x - self.x0) / RES).astype(np.int64)
        iy = ((y - self.y0) / RES).astype(np.int64)
        ok = (ix >= 0) & (iy >= 0) & (ix < self.nx) & (iy < self.ny)
        return ix, iy, ok

    def add_points(self, x, y, z, red, green, blue, nret, rnum):
        ix, iy, ok = self.cells(x, y)
        if not ok.any():
            return
        ix, iy = ix[ok], iy[ok]
        z, nret, rnum = z[ok], nret[ok], rnum[ok]
        red, green, blue = red[ok], green[ok], blue[ok]
        flat = iy * self.nx + ix
        self.cnt += np.bincount(flat, minlength=self.nx * self.ny).reshape(self.ny, self.nx)
        first = rnum == 1
        self.pulse += np.bincount(flat[first], minlength=self.nx * self.ny).reshape(self.ny, self.nx)
        self.multi += np.bincount(flat[first & (nret > 1)],
                                  minlength=self.nx * self.ny).reshape(self.ny, self.nx)
        # セル内最高点とその RGB
        order = np.lexsort((z, flat))
        fs = flat[order]
        last = np.ones(len(fs), bool)
        last[:-1] = fs[1:] != fs[:-1]
        cell_id = fs[last]
        pick = order[last]
        cur = self.dsm.ravel()[cell_id]
        upd = z[pick] > cur
        sel = cell_id[upd]
        self.dsm.ravel()[sel] = z[pick][upd]
        self.rgb.reshape(-1, 3)[sel, 0] = red[pick][upd]
        self.rgb.reshape(-1, 3)[sel, 1] = green[pick][upd]
        self.rgb.reshape(-1, 3)[sel, 2] = blue[pick][upd]

    def add_dem(self, src):
        """公式DEM(grd25) から未取得セルを埋める。"""
        need = np.isnan(self.dem)
        if not need.any():
            return
        yy, xx = np.nonzero(need)
        gx = self.x0 + (xx + 0.5) * RES
        gy = self.y0 + (yy + 0.5) * RES
        vals = np.array(list(src.sample(np.column_stack([gx, gy]))), dtype=float).ravel()
        nod = src.nodata
        if nod is not None:
            vals[vals == nod] = np.nan
        vals[vals > 1e30] = np.nan
        self.dem[yy, xx] = vals

    def finalize(self, building_mask, water_area_m2):
        chm = self.dsm.copy()
        chm[chm == -9e9] = np.nan
        chm = chm - self.dem
        observed = self.cnt > 0
        outlier = observed & (chm > CHM_MAX)
        valid = observed & ~outlier
        unobs = ~observed
        s = self.rgb.sum(axis=2)
        with np.errstate(invalid="ignore", divide="ignore"):
            exg = (2 * self.rgb[:, :, 1] - self.rgb[:, :, 0] - self.rgb[:, :, 2]) / np.where(s == 0, np.nan, s)
        is_spec = np.nan_to_num(exg, nan=-1) > EXG_MIN
        forest = valid & (chm >= H_TREE) & ~building_mask
        grass = valid & ~forest & (chm < H_TREE) & is_spec & ~building_mask
        other = valid & ~forest & ~grass
        tot = int(self.mask.sum())
        area = tot * RES * RES
        w_pct = min(100.0, 100.0 * water_area_m2 / area) if area > 0 else np.nan

        def pc(a):
            return round(100.0 * float((a & self.mask).sum()) / tot, 2)

        return dict(
            cells=tot, area_m2=round(area, 1),
            forest_pct=pc(forest), grass_pct=pc(grass), other_pct=pc(other),
            unobserved_pct=pc(unobs), outlier_pct=pc(outlier),
            water_pct_landuse=round(w_pct, 2),
            building_pct=pc(building_mask & observed),
            coverage_ratio=round(float((observed & self.mask).sum()) / tot, 4),
            dem_missing_pct=pc(np.isnan(self.dem)),
            median_pts_per_cell=int(np.median(self.cnt[self.mask])),
        )


def fetch_tile(mesh, product):
    os.makedirs(TMP, exist_ok=True)
    zp = os.path.join(TMP, f"{mesh}_{product}.zip")
    url = f"{BASE}/{product}/{mesh}.zip"
    r = subprocess.run(["curl", "-sL", "-m", "1800", "-o", zp, "-w", "%{http_code}", url],
                       capture_output=True, text=True)
    if r.stdout.strip() != "200" or not os.path.exists(zp):
        return None
    out = os.path.join(TMP, f"{mesh}_{product}")
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        z.extractall(out)
    os.remove(zp)
    return out


def cleanup(*paths):
    for p in paths:
        if p and os.path.exists(p):
            shutil.rmtree(p, ignore_errors=True)
