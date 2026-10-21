"""図郭ストリーミングで公園群の土地被覆を算出する実行スクリプト。

使い方:  python run_landcover.py <set>   (set = treatment | control10 | control30)
"""
import json
import os
import sys
import time

import geopandas as gpd
import laspy
import numpy as np
import pandas as pd
import rasterio
from rasterio import features

sys.path.append(os.getcwd())
from tile_stream_landcover import RES, ParkAccum, cleanup, fetch_tile

GPKG = "proj/qgis_tokyo_acoustic_research/output/tokyo_acoustic_research_permanent_layers.gpkg"
LU = "dl/r04/R04土地利用現況_ウ多摩全域.shp"
BLD = "dl/r04b/R04建物現況_ウ多摩全域.shp"
LOCAL_LAS = {"09LC2948": "dl/las/t2948/09LC2948.las", "09LC2938": "dl/las/t2938/09LC2938.las"}
LOCAL_DEM = {"09LC2948": "dl/grd25/09LC2948.tif", "09LC2938": "dl/grd25/09LC2938.tif"}


def build_targets(which):
    tg = gpd.read_file(GPKG, layer="Treatment_緑地保全地域")
    cg = gpd.read_file(GPKG, layer="Control_V2_CoreDesignationsExcluded")
    cg = cg[~cg["区市町村"].fillna("").str.endswith("区")].reset_index(drop=True)
    t12 = tg[tg.green_pct >= 10].reset_index(drop=True)
    if which == "treatment":
        g = t12.copy()
        g["role"] = "Treatment"
        return g
    lt = np.log10(t12.park_area_m2.values)
    lc = np.log10(cg.park_area_m2.values)
    d = np.abs(lc[None, :] - lt[:, None])
    k = 10 if which == "control10" else 30
    idx = np.unique(np.argsort(d, axis=1)[:, :k])
    g = cg.iloc[idx].reset_index(drop=True)
    g["role"] = "Control"
    g["green_pct"] = 0.0
    return g


def main(which):
    tiles = json.load(open("tiles_needed.json"))
    parks = build_targets(which)
    pmap = json.load(open(f"parkmap_{which}.json"))  # park index -> [mesh,...]
    needed = sorted({m for v in pmap.values() for m in v})
    print(f"[{which}] parks={len(parks)} tiles={len(needed)}", flush=True)

    acc = {int(i): ParkAccum(int(i), parks.geometry.iloc[int(i)]) for i in pmap if pmap[i]}
    bbox = tuple(parks.total_bounds)
    bld = gpd.read_file(BLD, bbox=bbox)
    lu = gpd.read_file(LU, bbox=bbox)
    water = lu[lu.LU_1 == 700]
    print(f"  buildings={len(bld)} water_polys={len(water)}", flush=True)

    t0 = time.time()
    for n, mesh in enumerate(needed, 1):
        users = [int(i) for i, v in pmap.items() if mesh in v and int(i) in acc]
        las_path = LOCAL_LAS.get(mesh)
        dem_path = LOCAL_DEM.get(mesh)
        d1 = d2 = None
        if las_path is None:
            d1 = fetch_tile(mesh, "lp")
            if d1:
                f = [x for x in os.listdir(d1) if x.lower().endswith(".las")]
                las_path = os.path.join(d1, f[0]) if f else None
        if dem_path is None:
            d2 = fetch_tile(mesh, "grd25")
            if d2:
                f = [x for x in os.listdir(d2) if x.lower().endswith(".tif")]
                dem_path = os.path.join(d2, f[0]) if f else None
        if las_path and os.path.exists(las_path):
            las = laspy.read(las_path)
            X, Y = np.asarray(las.x), np.asarray(las.y)
            for i in users:
                a = acc[i]
                m = ((X >= a.x0) & (X <= a.x0 + a.nx * RES)
                     & (Y >= a.y0) & (Y <= a.y0 + a.ny * RES))
                if m.any():
                    a.add_points(X[m], Y[m], np.asarray(las.z)[m],
                                 np.asarray(las.red)[m], np.asarray(las.green)[m],
                                 np.asarray(las.blue)[m],
                                 np.asarray(las.number_of_returns)[m],
                                 np.asarray(las.return_number)[m])
            del las, X, Y
        if dem_path and os.path.exists(dem_path):
            with rasterio.open(dem_path) as src:
                for i in users:
                    acc[i].add_dem(src)
        cleanup(d1, d2)
        if n % 10 == 0 or n == len(needed):
            print(f"  tile {n}/{len(needed)} {mesh} elapsed={time.time()-t0:.0f}s", flush=True)

    rows = []
    for i, a in acc.items():
        sub = bld[bld.intersects(a.poly)]
        bm = (features.rasterize([(g, 1) for g in sub.geometry], out_shape=(a.ny, a.nx),
                                 transform=a.transform, dtype="uint8").astype(bool)
              if len(sub) else np.zeros((a.ny, a.nx), bool))
        wsub = water[water.intersects(a.poly)]
        warea = float(wsub.intersection(a.poly).area.sum()) if len(wsub) else 0.0
        r = a.finalize(bm, warea)
        p = parks.iloc[i]
        r.update(park_key=p["park_key"], park=p["公園名"], muni=p["区市町村"], role=p["role"],
                 park_area_m2=round(float(p["park_area_m2"]), 1),
                 protection_ratio=round(float(p["green_pct"]), 2), n_tiles=len(pmap[str(i)]))
        rows.append(r)
    df = pd.DataFrame(rows)
    cols = ["park_key", "park", "muni", "role", "park_area_m2", "protection_ratio", "forest_pct",
            "grass_pct", "water_pct_landuse", "other_pct", "unobserved_pct", "building_pct",
            "coverage_ratio", "dem_missing_pct", "outlier_pct", "median_pts_per_cell", "n_tiles",
            "cells", "area_m2"]
    df[cols].to_csv(f"landcover_{which}_20261012.csv", index=False, encoding="utf-8-sig")
    print(df[["park", "forest_pct", "grass_pct", "water_pct_landuse", "coverage_ratio"]].to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1])
