# データ辞書

本リポジトリの CSV / GeoPackage の列定義。すべての座標系は **EPSG:6677（JGD2011 平面直角座標系第9系）**、緯度経度は WGS84。

`PROVISIONAL` が付く列は暫定値、`SOURCE_ATTR` が付く列は原典属性の転記で未検証であることを示します。


## `data/final/final_pair_summary.csv`

7 行 × 14 列

| 列名 | 型 | 説明 |
|---|---|---|
| `pair_id` | str | ペア識別子 P01–P07 |
| `T_park` | str | Treatment 公園名 |
| `C_park` | str | Control 公園名 |
| `area_ratio` | float64 | Control面積 ÷ Treatment面積 |
| `d_forest_pt` | float64 | Control樹冠率 − Treatment樹冠率（ポイント） |
| `d_grass_pt_PROVISIONAL` | float64 | 低層植生率の差（ポイント・暫定） |
| `d_other_pt` | float64 | その他被覆率の差（ポイント） |
| `water_mismatch` | str | 水域の有無がペア内で食い違うか（Yes/No、1%閾値） |
| `pair_separation_km` | float64 | 代表点間の直線距離 km |
| `min_park_area_m2` | float64 | ペア内の小さいほうの公園面積 m² |
| `T_overlap_m2` | float64 | Treatment の指定区域重複面積 m² |
| `T_PR_pct` | float64 | Treatment の Protection Ratio % |
| `min_coverage_ratio` | float64 | ペア内の低いほうの被覆率 |
| `caliper_strict_10pt` | str | 厳格caliper（面積比0.80–1.25 かつ |Δ樹冠|≤10pt）の合否 |

## `data/final/final_park_list.csv`

14 行 × 36 列

| 列名 | 型 | 説明 |
|---|---|---|
| `pair_id` | str | ペア識別子 P01–P07 |
| `role` | str | Treatment / Control |
| `park` | str | 公園名（正式名称） |
| `partner_park` | str | ペア相手の公園名 |
| `muni` | str | 所在自治体 |
| `park_key` | str | 既存GISの公園識別子 `<source>|<自治体>|-|<公園名>` |
| `address_SOURCE_ATTR_representative_lot` | str | 原典『位置』属性（代表地番）。公園の所在地ではなく**未検証** |
| `opened` | str | 開園年月日（原典属性） |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `protection_ratio_pct` | float64 | 公園面積に占める緑地保全地域の割合 %（Treatmentのみ） |
| `conservation_area` | str | 重複する緑地保全地域の名称 |
| `overlap_m2` | float64 | 緑地保全地域との重複面積 m² |
| `overlap_rep_lat` | float64 | 重複部分の代表点 緯度（WGS84） |
| `overlap_rep_lon` | float64 | 重複部分の代表点 経度（WGS84） |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct_PROVISIONAL` | float64 | 低層植生被覆率 %（**暫定**。芝生と舗装の判別は未検証） |
| `water_pct_landuse_PROVISIONAL` | float64 | 水域率 %（土地利用現況調査コード700由来。**暫定**） |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `unobserved_pct` | float64 | レーザ反射が得られなかったセルの割合 % |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `n_tiles` | int64 | 使用した1/500図郭の枚数 |
| `rep_lat` | float64 | ポリゴン内保証点の緯度（WGS84）。**現地同定はこれを使う** |
| `rep_lon` | float64 | 同 経度（WGS84） |
| `rep_x_6677` | float64 | 同 X 座標（EPSG:6677, m） |
| `rep_y_6677` | float64 | 同 Y 座標（EPSG:6677, m） |
| `centroid_inside_polygon` | bool | 重心がポリゴン内か。False の公園では重心法が使えない |
| `bbox_ew_m` | int64 | 外接矩形の東西幅 m |
| `bbox_ns_m` | int64 | 外接矩形の南北幅 m |
| `n_parts` | int64 | ポリゴンの構成パーツ数 |
| `largest_part_pct` | float64 | 最大パーツが全体面積に占める割合 % |
| `part_separation_m` | float64 | パーツ間の最大距離 m |
| `map_url` | str | 地図URL |
| `mapillary_url` | str | Mapillary URL |
| `site_access_status` | str | 立入可否（記入欄・既定値は未確認） |
| `visit_date` | float64 | 訪問日（記入欄） |
| `recording_point_fixed` | str | 録音地点の確定状況（記入欄） |

## `data/landcover/landcover_control10_20261012.csv`

114 行 × 19 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park_key` | str | 既存GISの公園識別子 `<source>|<自治体>|-|<公園名>` |
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `role` | str | Treatment / Control |
| `park_area_m2` | float64 | — |
| `protection_ratio` | float64 | — |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct` | float64 | — |
| `water_pct_landuse` | float64 | — |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `unobserved_pct` | float64 | レーザ反射が得られなかったセルの割合 % |
| `building_pct` | float64 | — |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `dem_missing_pct` | float64 | — |
| `outlier_pct` | float64 | — |
| `median_pts_per_cell` | int64 | — |
| `n_tiles` | int64 | 使用した1/500図郭の枚数 |
| `cells` | int64 | — |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |

## `data/landcover/landcover_pilot_resolution_sensitivity_20261011.csv`

3 行 × 8 列

| 列名 | 型 | 説明 |
|---|---|---|
| `res_m` | float64 | — |
| `cells` | int64 | — |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct` | float64 | — |
| `water_pct` | float64 | — |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |

## `data/landcover/landcover_pilot_results_20261011.csv`

2 行 × 9 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `role` | str | Treatment / Control |
| `area_m2` | int64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `Forest_pct` | float64 | — |
| `Grass_pct` | float64 | — |
| `Water_pct` | float64 | — |
| `Other_pct` | float64 | — |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |

## `data/landcover/landcover_pilot_v3_20261011.csv`

4 行 × 10 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park` | str | 公園名（正式名称） |
| `role` | str | Treatment / Control |
| `pen_mode` | str | — |
| `F` | float64 | — |
| `G` | float64 | — |
| `W` | float64 | — |
| `O` | float64 | — |
| `unobserved` | float64 | — |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `ground_obs` | float64 | — |

## `data/landcover/landcover_treatment_20261012.csv`

12 行 × 19 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park_key` | str | 既存GISの公園識別子 `<source>|<自治体>|-|<公園名>` |
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `role` | str | Treatment / Control |
| `park_area_m2` | float64 | — |
| `protection_ratio` | float64 | — |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct` | float64 | — |
| `water_pct_landuse` | float64 | — |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `unobserved_pct` | float64 | レーザ反射が得られなかったセルの割合 % |
| `building_pct` | float64 | — |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `dem_missing_pct` | float64 | — |
| `outlier_pct` | float64 | — |
| `median_pts_per_cell` | int64 | — |
| `n_tiles` | int64 | 使用した1/500図郭の枚数 |
| `cells` | int64 | — |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |

## `data/landcover/landuse_control_composition_20261011.csv`

3767 行 × 9 列

| 列名 | 型 | 説明 |
|---|---|---|
| `pid` | int64 | — |
| `公園・運動場等%` | float64 | — |
| `森林%` | float64 | — |
| `原野%` | float64 | — |
| `採草放牧地%` | float64 | — |
| `水面%` | float64 | — |
| `被覆合計%` | float64 | — |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `sizebin` | str | — |

## `data/landcover/landuse_treatment_composition_20261011.csv`

30 行 × 27 列

| 列名 | 型 | 説明 |
|---|---|---|
| `公園名` | str | — |
| `park_area_m2` | float64 | — |
| `官公庁` | float64 | — |
| `教育文化` | float64 | — |
| `厚生医療` | float64 | — |
| `供給処理` | float64 | — |
| `事務所` | float64 | — |
| `専用商業` | float64 | — |
| `住商併用` | float64 | — |
| `スポーツ興行` | float64 | — |
| `独立住宅` | float64 | — |
| `集合住宅` | float64 | — |
| `専用工場` | float64 | — |
| `倉庫運輸` | float64 | — |
| `屋外利用地・仮設` | float64 | — |
| `その他` | float64 | — |
| `公園・運動場等` | float64 | — |
| `未利用地等` | float64 | — |
| `道路` | float64 | — |
| `鉄道・港湾等` | float64 | — |
| `田` | float64 | — |
| `畑` | float64 | — |
| `樹園地` | float64 | — |
| `水面・河川・水路` | float64 | — |
| `原野` | float64 | — |
| `森林` | float64 | — |
| `被覆合計%` | float64 | — |

## `data/landcover/park_data_availability_audit.csv`

126 行 × 20 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park_key` | str | 既存GISの公園識別子 `<source>|<自治体>|-|<公園名>` |
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `role` | str | Treatment / Control |
| `protection_ratio` | float64 | — |
| `park_area_m2` | float64 | — |
| `n_tiles` | int64 | 使用した1/500図郭の枚数 |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `unobserved_pct` | float64 | レーザ反射が得られなかったセルの割合 % |
| `dem_missing_pct` | float64 | — |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct` | float64 | — |
| `water_pct_landuse` | float64 | — |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `building_pct` | float64 | — |
| `median_pts_per_cell` | int64 | — |
| `water_source` | str | — |
| `survey_date_status` | str | — |
| `flag_coverage` | str | — |
| `landcover_computable` | str | — |

## `data/literature/literature_evidence_table.csv`

36 行 × 18 列

| 列名 | 型 | 説明 |
|---|---|---|
| `ID` | str | — |
| `領域` | str | — |
| `著者` | str | — |
| `著者数` | float64 | — |
| `年` | int64 | — |
| `タイトル` | str | — |
| `掲載誌` | str | — |
| `DOI_URL` | str | — |
| `査読` | str | — |
| `被引用数_Crossref` | float64 | — |
| `研究タイプ` | str | — |
| `対象地域_規模` | str | — |
| `アウトカム種別` | str | — |
| `比較設計` | str | — |
| `統制_マッチング変数` | str | — |
| `本研究への含意` | str | — |
| `確認水準` | str | — |
| `評価深度` | str | — |

## `data/matching/matched_pair_candidate_ranking.csv`

391 行 × 20 列

| 列名 | 型 | 説明 |
|---|---|---|
| `treatment` | str | — |
| `t_muni` | str | — |
| `protection_ratio` | float64 | — |
| `t_area` | float64 | — |
| `t_forest` | float64 | — |
| `t_grass` | float64 | — |
| `t_water` | int64 | — |
| `rank` | int64 | — |
| `control` | str | — |
| `c_muni` | str | — |
| `c_area` | float64 | — |
| `c_forest` | float64 | — |
| `c_grass` | float64 | — |
| `c_water` | int64 | — |
| `dist` | float64 | — |
| `area_ratio` | float64 | Control面積 ÷ Treatment面積 |
| `d_forest` | float64 | — |
| `d_grass` | float64 | — |
| `scenario` | str | — |
| `pr_threshold` | int64 | — |

## `data/matching/matched_pairs_S1_PR10_20261012.csv`

11 行 × 17 列

| 列名 | 型 | 説明 |
|---|---|---|
| `treatment` | str | — |
| `t_muni` | str | — |
| `PR` | float64 | — |
| `t_area` | float64 | — |
| `t_forest` | float64 | — |
| `t_grass` | float64 | — |
| `t_water` | int64 | — |
| `control` | str | — |
| `c_muni` | str | — |
| `c_area` | float64 | — |
| `c_forest` | float64 | — |
| `c_grass` | float64 | — |
| `c_water` | int64 | — |
| `area_ratio` | float64 | Control面積 ÷ Treatment面積 |
| `d_forest` | float64 | — |
| `d_grass` | float64 | — |
| `dist` | float64 | — |

## `data/matching/matched_pairs_S3_PR10_20261012.csv`

11 行 × 17 列

| 列名 | 型 | 説明 |
|---|---|---|
| `treatment` | str | — |
| `t_muni` | str | — |
| `PR` | float64 | — |
| `t_area` | float64 | — |
| `t_forest` | float64 | — |
| `t_grass` | float64 | — |
| `t_water` | int64 | — |
| `control` | str | — |
| `c_muni` | str | — |
| `c_area` | float64 | — |
| `c_forest` | float64 | — |
| `c_grass` | float64 | — |
| `c_water` | int64 | — |
| `area_ratio` | float64 | Control面積 ÷ Treatment面積 |
| `d_forest` | float64 | — |
| `d_grass` | float64 | — |
| `dist` | float64 | — |

## `data/matching/matching_sensitivity_summary.csv`

9 行 × 7 列

| 列名 | 型 | 説明 |
|---|---|---|
| `pr` | int64 | — |
| `scenario` | str | — |
| `n_treat` | int64 | — |
| `assigned` | int64 | — |
| `good_15pt` | int64 | — |
| `strict_10pt` | int64 | — |
| `dist_med` | float64 | — |

## `data/matching/park_pair_shortlist.csv`

8 行 × 72 列

| 列名 | 型 | 説明 |
|---|---|---|
| `pair_id` | str | ペア識別子 P01–P07 |
| `match_rank_by_dist` | int64 | — |
| `match_distance` | float64 | — |
| `caliper_good_15pt` | str | — |
| `caliper_strict_10pt` | str | 厳格caliper（面積比0.80–1.25 かつ |Δ樹冠|≤10pt）の合否 |
| `T_park` | str | Treatment 公園名 |
| `T_muni` | str | — |
| `T_park_key` | str | — |
| `T_address_SOURCE_ATTR_representative_lot` | str | — |
| `T_opened` | str | — |
| `T_source` | str | — |
| `T_area_m2` | float64 | — |
| `T_PR_pct` | float64 | Treatment の Protection Ratio % |
| `T_conservation_area` | str | — |
| `T_overlap_m2` | float64 | Treatment の指定区域重複面積 m² |
| `T_overlap_lat` | float64 | — |
| `T_overlap_lon` | float64 | — |
| `T_forest_pct` | float64 | — |
| `T_grass_pct_PROVISIONAL` | float64 | — |
| `T_water_pct_landuse_PROVISIONAL` | float64 | — |
| `T_other_pct` | float64 | — |
| `T_unobserved_pct` | float64 | — |
| `T_coverage_ratio` | float64 | — |
| `T_n_tiles` | int64 | — |
| `T_rep_lat` | float64 | — |
| `T_rep_lon` | float64 | — |
| `T_rep_x_6677` | float64 | — |
| `T_rep_y_6677` | float64 | — |
| `T_centroid_inside_polygon` | bool | — |
| `T_bbox_m` | str | — |
| `C_park` | str | Control 公園名 |
| `C_muni` | str | — |
| `C_park_key` | str | — |
| `C_address_SOURCE_ATTR_representative_lot` | str | — |
| `C_opened` | str | — |
| `C_source` | str | — |
| `C_area_m2` | float64 | — |
| `C_forest_pct` | float64 | — |
| `C_grass_pct_PROVISIONAL` | float64 | — |
| `C_water_pct_landuse_PROVISIONAL` | float64 | — |
| `C_other_pct` | float64 | — |
| `C_unobserved_pct` | float64 | — |
| `C_coverage_ratio` | float64 | — |
| `C_n_tiles` | int64 | — |
| `C_rep_lat` | float64 | — |
| `C_rep_lon` | float64 | — |
| `C_rep_x_6677` | float64 | — |
| `C_rep_y_6677` | float64 | — |
| `C_centroid_inside_polygon` | bool | — |
| `C_bbox_m` | str | — |
| `area_ratio` | float64 | Control面積 ÷ Treatment面積 |
| `d_forest_pt` | float64 | Control樹冠率 − Treatment樹冠率（ポイント） |
| `d_grass_pt_PROVISIONAL` | float64 | 低層植生率の差（ポイント・暫定） |
| `water_mismatch` | str | 水域の有無がペア内で食い違うか（Yes/No、1%閾値） |
| `map_url_T` | str | — |
| `map_url_C` | str | — |
| `mapillary_url_T` | str | — |
| `mapillary_url_C` | str | — |
| `site_access_status` | str | 立入可否（記入欄・既定値は未確認） |
| `pair_separation_km` | float64 | 代表点間の直線距離 km |
| `T_overlap_share_pct` | float64 | — |
| `min_park_area_m2` | float64 | ペア内の小さいほうの公園面積 m² |
| `passes_size_floor_2000` | bool | — |
| `T_n_parts` | int64 | — |
| `C_n_parts` | int64 | — |
| `address_caveat` | str | — |
| `T_largest_part_pct` | float64 | — |
| `T_part_separation_m` | float64 | — |
| `C_largest_part_pct` | float64 | — |
| `C_part_separation_m` | float64 | — |
| `fragmentation_flag` | str | — |
| `recommended_alternative_control` | str | — |

## `data/matching/treatment_candidate_inventory.csv`

12 行 × 46 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `park_key` | str | 既存GISの公園識別子 `<source>|<自治体>|-|<公園名>` |
| `address_SOURCE_ATTR_representative_lot` | str | 原典『位置』属性（代表地番）。公園の所在地ではなく**未検証** |
| `opened` | str | 開園年月日（原典属性） |
| `park_source` | str | — |
| `area_m2` | float64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `PR_pct` | float64 | — |
| `in_PR10` | bool | — |
| `in_PR25` | bool | — |
| `in_PR50` | bool | — |
| `conservation_area` | str | 重複する緑地保全地域の名称 |
| `overlap_m2` | float64 | 緑地保全地域との重複面積 m² |
| `overlap_share_of_park_pct` | float64 | — |
| `overlap_lat` | float64 | — |
| `overlap_lon` | float64 | — |
| `forest_pct` | float64 | 樹冠被覆率 %（CHM ≥3 m かつ建物フットプリント外） |
| `grass_pct_PROVISIONAL` | float64 | 低層植生被覆率 %（**暫定**。芝生と舗装の判別は未検証） |
| `water_pct_landuse_PROVISIONAL` | float64 | 水域率 %（土地利用現況調査コード700由来。**暫定**） |
| `other_pct` | float64 | 上記以外の被覆率 % |
| `unobserved_pct` | float64 | レーザ反射が得られなかったセルの割合 % |
| `coverage_ratio` | float64 | 公園面積のうちLiDARで観測できた割合（0–1） |
| `landcover_usable_cov093` | bool | — |
| `n_tiles` | int64 | 使用した1/500図郭の枚数 |
| `median_pts_per_cell` | int64 | — |
| `match_status_greedy` | str | — |
| `match_reason` | str | — |
| `best_control_greedy` | str | — |
| `match_distance_greedy` | float64 | — |
| `best_control_optimal` | str | — |
| `n_acceptable_alternatives` | int64 | — |
| `acceptable_alternatives` | str | — |
| `rep_lat` | float64 | ポリゴン内保証点の緯度（WGS84）。**現地同定はこれを使う** |
| `rep_lon` | float64 | 同 経度（WGS84） |
| `rep_x_6677` | float64 | 同 X 座標（EPSG:6677, m） |
| `rep_y_6677` | float64 | 同 Y 座標（EPSG:6677, m） |
| `centroid_inside_polygon` | bool | 重心がポリゴン内か。False の公園では重心法が使えない |
| `bbox_m` | str | — |
| `boundary_qc_needed` | bool | — |
| `site_access_status` | str | 立入可否（記入欄・既定値は未確認） |
| `map_url` | str | 地図URL |
| `mapillary_url` | str | Mapillary URL |
| `n_parts` | int64 | ポリゴンの構成パーツ数 |
| `address_caveat` | str | — |
| `largest_part_pct` | float64 | 最大パーツが全体面積に占める割合 % |
| `part_separation_m` | float64 | パーツ間の最大距離 m |

## `data/qc/dem_holdout_block_20261011.csv`

6 行 × 8 列

| 列名 | 型 | 説明 |
|---|---|---|
| `res_m` | float64 | — |
| `block_m` | float64 | — |
| `held_cells` | int64 | — |
| `MAE_m` | float64 | — |
| `RMSE_m` | float64 | — |
| `p95_m` | float64 | — |
| `MAE_under` | float64 | — |
| `RMSE_under` | float64 | — |

## `data/qc/dem_holdout_validation_20261011.csv`

3 行 × 11 列

| 列名 | 型 | 説明 |
|---|---|---|
| `res_m` | float64 | — |
| `held_cells` | int64 | — |
| `MAE_m` | float64 | — |
| `RMSE_m` | float64 | — |
| `p95_m` | float64 | — |
| `under_n` | int64 | — |
| `MAE_under` | float64 | — |
| `RMSE_under` | float64 | — |
| `open_n` | int64 | — |
| `MAE_open` | float64 | — |
| `RMSE_open` | float64 | — |

## `data/qc/pipeline_verification_summary_20261011.csv`

13 行 × 3 列

| 列名 | 型 | 説明 |
|---|---|---|
| `item` | str | — |
| `description` | str | — |
| `value` | str | — |

## `data/qc/source_comparison_summary_20261011.csv`

12 行 × 3 列

| 列名 | 型 | 説明 |
|---|---|---|
| `項目` | str | — |
| `実測値` | str | — |
| `判定` | str | — |

## `data/qc/source_manifest_las_20261011.csv`

2 行 × 6 列

| 列名 | 型 | 説明 |
|---|---|---|
| `mesh_no` | str | — |
| `region` | str | — |
| `url` | str | — |
| `sha256` | str | — |
| `size_bytes` | int64 | — |
| `downloaded_utc` | str | — |

## `data/qc/source_manifest_sha256_20261011.csv`

4 行 × 5 列

| 列名 | 型 | 説明 |
|---|---|---|
| `filename` | str | — |
| `url` | str | — |
| `sha256` | str | — |
| `size_bytes` | int64 | — |
| `mtime_utc` | str | — |

## `data/qc/treatment_area_protection_qc_20261011.csv`

30 行 × 15 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park_name` | str | — |
| `municipality` | str | — |
| `block` | str | — |
| `park_source` | str | — |
| `park_category` | str | — |
| `area_attr_m2` | float64 | — |
| `area_geom_m2` | float64 | — |
| `ratio_geom_over_attr` | float64 | — |
| `green_overlap_m2` | float64 | — |
| `protection_ratio_geom_pct` | float64 | — |
| `protection_ratio_attr_pct` | float64 | — |
| `n_control_caliper020_all` | int64 | — |
| `n_control_caliper020_tama` | int64 | — |
| `n_control_k30_tama_maxlogdist` | float64 | — |
| `area_qc_flag` | str | — |

## `data/qc/treatment_tile_index_20261011.csv`

30 行 × 7 列

| 列名 | 型 | 説明 |
|---|---|---|
| `park` | str | 公園名（正式名称） |
| `muni` | str | 所在自治体 |
| `pr` | float64 | — |
| `area_m2` | int64 | 公園ポリゴンの平面面積 m²（EPSG:6677） |
| `mesh_centroid` | str | — |
| `n_mesh` | int64 | — |
| `meshes` | str | — |

## GeoPackage

### `data/final/final_park_list.gpkg`（EPSG:6677）

| レイヤ | ジオメトリ | 内容 |
|---|---|---|
| `final_pair_parks` | MultiPolygon | 最終候補14公園のポリゴン（pair_id, pair_role, 公園名, 区市町村, 位置, 開園年月日, park_key, park_area_m2, counterpart） |
| `treatment_conservation_overlap` | MultiPolygon | Treatment 7公園と緑地保全地域の重複部分（conservation_area, overlap_m2） |
| `recording_point_candidates` | Point | 全14公園のポリゴン内保証点（録音地点選定の出発点） |

### `data/gis/park_pairs_fieldwork.gpkg`（EPSG:6677）

暫定8ペア16公園版。`final_park_list.gpkg` の前段で、P08（矢川緑地–北田南公園）と差し替え前の平松緑地を含みます。

### `data/gis/tile_grid_tama.gpkg`（EPSG:6677）

| レイヤ | ジオメトリ | 内容 |
|---|---|---|
| `mesh500` | Polygon | 多摩地域の 1/500 図郭 6,452枚。東西400 m × 南北300 m を原点から算術的に再構成したもの（ウェブ配信のベクタタイルは図郭境界で切り取られるため、そのまま空間結合すると取りこぼす） |

## 欠損値の扱い

- 空欄・`NaN` は「未観測」「該当なし」「未記入」のいずれかで、**0 を意味しません**
- `coverage_ratio` が 0.93 未満の公園は土地被覆を使用不可として扱います
- `protection_ratio_pct`, `conservation_area`, `overlap_m2`, `overlap_rep_lat/lon` は Control 行では空欄（該当なし）
