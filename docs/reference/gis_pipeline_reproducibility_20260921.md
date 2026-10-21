# Tokyo Conservation × Acoustic Environment GIS Pipeline
## 2026-09-21 再現手順・処理記録

> Status: **CURRENT V2 / provisional**
>
> 本ファイルは、2026-09-21 にQGIS Python Console上で実施した一連のGIS処理を、後日GitHubへ移しても再現できるように整理したもの。
>
> 対象範囲は、**公式データ取得 → 都市公園母集団作成 → 緑地保全地域との重複抽出 → Protection Ratio算出 → Control V1/V2構築 → 面積一次スクリーニング → 永久保存GeoPackage/QGIS Project作成**まで。
>
> 土地被覆（Forest / Grass / Water）の推定はまだ本パイプラインには含めない。

---

# 1. 研究上の位置付け

現時点の比較対象は、

```text
Treatment
= 東京都の都市公園
  ∩
  緑地保全地域

vs

Control
= 東京都の都市公園
  ∩
  研究上の自然保全指定を受けていない公園
```

とする。

Treatmentは「緑地保全地域そのもの」ではなく、

> **都市公園ポリゴンのうち、緑地保全地域と空間的に重複する公園**

である。

Protection Ratio は、

```text
Protection Ratio
=
Area(Park ∩ 緑地保全地域)
/
Area(Park)
```

とする。

現時点では **Treatment採用閾値は固定していない**。

---

# 2. QGIS実行環境

この処理はQGIS Python Console上で実行する。

重要：

> **複数行PyQGISコードは必ず `exec(""" ... """)` で包む。**

QGIS Python Consoleへそのまま複数行を貼り付けると、インデント等でエラーになることがある。

QGISバージョン確認：

```python
from qgis.core import Qgis
print(Qgis.QGIS_VERSION)
```

GitHub公開時には、実際に使用したQGIS versionをREADME等へ固定して記録する。

使用する主なモジュール：

- QGIS Processing
- `qgis.core`
- Python標準ライブラリ
  - `os`
  - `csv`
  - `math`
  - `shutil`
  - `zipfile`
  - `urllib.request`
  - `hashlib`
  - `collections`

外部pip packageはこの段階では不要。

---

# 3. ワークスペース

基準ディレクトリ：

```text
~/qgis_tokyo_acoustic_research
```

想定構造：

```text
qgis_tokyo_acoustic_research/
├── downloads/
├── data/
│   ├── parks/
│   ├── conservation/
│   ├── natural_parks/
│   └── urban_green/
├── output/
├── qgis/
└── styles/
```

---

# 4. 使用した東京都公式データ

## 4.1 都市公園

```text
https://data.storage.data.metro.tokyo.lg.jp/toshiseibi/01_kouenryokuchi.zip
```

研究母集団に使用するのは次の3レイヤのみ。

```text
都立公園.shp
区市町村立公園(都市公園).shp
国営公園.shp
```

2026-09-21実行時：

```text
都立公園                       83
区市町村立公園(都市公園)     8685
国営公園                        2
--------------------------------
Total                         8770
```

CRS：

```text
EPSG:6677
```

---

## 4.2 東京都条例上の保全地域等

```text
https://data.storage.data.metro.tokyo.lg.jp/toshiseibi/13_jourei.zip
```

主要レイヤ：

```text
東京都保全地域.shp
保存樹林.shp
保存樹林_ポイント.shp
保存樹木・生垣.shp
農の風景育成地区.shp
都民の森.shp
```

`東京都保全地域.shp` の種別：

```text
森林環境保全地域   1
歴史環境保全地域  21
緑地保全地域      46
自然環境保全地域   1
里山保全地域       6
```

---

## 4.3 自然公園

```text
https://data.storage.data.metro.tokyo.lg.jp/toshiseibi/11_sizenkouen.zip
```

使用レイヤ：

```text
国立公園.shp
国定公園.shp
都立自然公園.shp
```

---

## 4.4 都市緑地・都市計画系

```text
https://data.storage.data.metro.tokyo.lg.jp/toshiseibi/12_toshikeikaku_toshiryokuchi.zip
```

確認対象：

```text
都市計画公園・緑地等.shp
特別緑地保全地区.shp
風致地区.shp
首都圏近郊緑地保全区域.shp
市民緑地_ポイント.shp
市民緑地_ポリゴン.shp
緑化地域.shp
緑地協定.shp
地区計画で定めた「地区施設」.shp
再開発促進区を定める地区計画で定めた「主要な公共施設」.shp
```

---

# 5. 再現性上の重要事項：元データの固定

上記URLは「現在の公開ファイル」を指すため、将来データが更新される可能性がある。

したがってGitHubで再現可能性を担保する場合は、

1. 元ZIPのURL
2. ダウンロード日
3. SHA256
4. 使用QGIS version

を必ず記録する。

本パイプラインでは `source_manifest_sha256.csv` を生成する。

大容量・ライセンス上の理由から元データそのものをGitHubへ入れない場合でも、**URL＋SHA256は必ず残す**。

---

# 6. 今日の処理フロー

```text
Official Tokyo ZIPs
        ↓
download / unzip
        ↓
都市公園3レイヤを抽出
        ↓
fix geometries
        ↓
park_source / raw_uid / park_key
        ↓
merge
        ↓
park_key単位でdissolve
        ↓
公園面積計算
        ↓
緑地保全地域を抽出・dissolve
        ↓
Intersection
        ↓
Protection Ratio
        ↓
Treatment候補 30公園
        ↓
Control V1
        ↓
追加の保全制度を監査
        ↓
Control V2 / Excluded Core
        ↓
面積のみの一次スクリーニング
        ↓
永久保存GeoPackage
        ↓
QGIS Project保存
```

---

# 7. 公園単位の識別

安定キー：

```text
park_key
=
park_source
+
区市町村
+
複数区市
+
公園名
```

公園名が空の場合のみ、

```text
park_source + raw_uid
```

で別個の地物として保持する。

2026-09-21監査結果：

```text
Raw park features:                  8770
Unique park keys:                   8770
Multi-feature park groups:             0
Park units after dissolve:          8770
```

したがって、今回の東京都都市公園データでは、

> 1つの公園が複数featureに分割されていたため小面積になっている

という問題は確認されなかった。

---

# 8. Treatment抽出結果

`緑地保全地域` と都市公園をIntersection。

結果：

```text
緑地保全地域 polygons: 46
Treatment overlap parks: 30
```

Protection Ratio別：

```text
>= 10% : 12
>= 25% : 11
>= 50% : 7
>= 75% : 5
>= 90% : 3
```

Treatment thresholdはまだ固定しない。

上位：

```text
多摩平第６公園       日野市       99.5%
黒川清流公園         日野市       99.4%
多摩平第３緑地       日野市       92.2%
城山手緑地           八王子市     85.4%
とりで公園           多摩市       77.1%
多摩平第１緑地       日野市       67.2%
入間いちょう公園     調布市       57.3%
原ヶ谷戸どんぐり公園 福生市       49.7%
姿見の池緑地         国分寺市     40.1%
矢川緑地             立川市       35.4%
前沢第３緑地         東久留米市   29.0%
城山手しらかし公園   八王子市     20.1%
```

20.1%の次は3.9%まで大きく低下するが、これを理由に現時点でTreatment閾値を固定しない。

---

# 9. Control V1

Control V1は、

> `東京都保全地域.shp` の5カテゴリのどれにも重複しない都市公園

とした。

結果：

```text
Total urban parks:             8770
Treatment overlap:               30
Control V1:                    8719
Other conservation excluded:    21
```

検算：

```text
30 + 8719 + 21 = 8770
```

Control V1は広い暫定poolであり、最終Controlではない。

---

# 10. Designation Audit V2

追加の保全制度をControl contamination防止のため監査した。

## 10.1 今日実行したCURRENT V2のCORE

今日のV2では以下をCORE exclusionとして処理した。

```text
tokyo_conservation
special_green
scenic_district
metro_green
national_park
quasi_national_park
tokyo_natural_park
saved_forest
```

対応：

```text
tokyo_conservation   = 東京都保全地域
special_green        = 特別緑地保全地区
scenic_district      = 風致地区
metro_green          = 首都圏近郊緑地保全区域
national_park        = 国立公園
quasi_national_park  = 国定公園
tokyo_natural_park   = 都立自然公園
saved_forest         = 保存樹林
```

今日の overlap counts：

```text
tokyo_conservation : 51
special_green      : 24
scenic_district    : 251
metro_green        : 21
national_park      : 3
quasi_national_park: 2
tokyo_natural_park : 268
saved_forest       : 15
```

---

## 10.2 FLAGとして監査した制度

```text
citizen_green
green_agreement
greening_district
agricultural_landscape
tokyo_forest
```

今日の実行結果：

```text
citizen_green         : missing optional
green_agreement       : 28
greening_district     : 446
agricultural_landscape: 45
tokyo_forest          : 0
```

### citizen_green の既知バグ

今日のコードは、

```text
市民緑地.shp
```

を探していたが、実際のファイル名は、

```text
市民緑地_ポリゴン.shp
```

である。

したがって今日のCURRENT V2では citizen_green は未監査。

**これは次版で修正する。**

---

## 10.3 CURRENT V2結果

```text
Total parks:          8770
Treatment:              30
Control V2:            8195
Excluded by CORE:       545
```

検算：

```text
30 + 8195 + 545 = 8770
```

Treatmentで他CORE designationにも重複したもの：

```text
とりで公園     | 多摩市 | OTHER CORE = tokyo_natural_park
東寺方橋緑地   | 多摩市 | OTHER CORE = tokyo_natural_park
```

Treatmentについては他CORE designationとの重複があっても自動除外していない。

---

# 11. CURRENT V2の既知の問題

今日のV2は**研究結果ではなく暫定Control定義**。

次版 V2.1 では少なくとも以下を再検討する。

## 11.1 風致地区

今日：

```text
風致地区 = CORE
```

今後の有力案：

```text
風致地区 = FLAG
```

理由：

- 251公園と重複し、除外影響が大きい
- 自然保全だけでなく都市景観・環境形成の性格を持つ
- 自動的に「自然保全Control contamination」とみなすには厳しすぎる可能性がある

---

## 11.2 市民緑地

次版では、

```text
市民緑地_ポリゴン.shp
```

を正しく監査する。

---

## 11.3 微小Intersection / sliver

CURRENT V2では、

```text
ANY spatial intersection
```

でCORE exclusionしている。

そのため、ごく微小な境界sliverでもControlから落ちる可能性がある。

次版では、

```text
Area(Park ∩ Designation) / Area(Park)
```

を他指定についても計算し、overlap ratio分布を監査する。

**閾値は分布確認前に恣意的に設定しない。**

---

# 12. 面積マッチング feasibility audit

Treatment / Controlで公園面積の分布を確認した。

CURRENT V2：

```text
Control V2 n = 8195

min     0.0011 ha
Q1      0.0374 ha
median  0.0931 ha
Q3      0.2390 ha
max     167.2347 ha
```

Treatment：

```text
n       30
min     0.0273 ha
Q1      0.2227 ha
median  0.6407 ha
Q3      3.1920 ha
max     17.4187 ha
```

小規模Treatmentでも面積が近いControlは多数存在した。

例：

```text
矢川緑地 0.0273 ha
V2 0.90–1.10x : 406 controls

前沢第３緑地 0.0309 ha
V2 0.90–1.10x : 416 controls

城山手しらかし公園 0.0467 ha
V2 0.90–1.10x : 436 controls
```

したがって、

> 小さいTreatmentだから比較不能

とは判断しない。

---

# 13. Stage 1: 面積のみの一次スクリーニング

最終matchingでは、

```text
Area
Forest %
Grass %
Water %
```

を使う予定。

ただし土地被覆処理を約8,000公園すべてへ実施する前に、

> **面積だけで一次候補poolを作る**

段階を置く。

この段階では以下を使って候補を落とさない。

```text
自治体
Forest %
Grass %
Water %
道路距離
交通量
鉄道
建物密度
建物高さ
3D遮蔽
```

また、

```text
上位50件
```

のような固定件数cutoffは使わない。

面積caliper内のControlを**全件保存**する。

今日出力した記述的caliper：

```text
0.90x – 1.10x
0.80x – 1.25x
0.667x – 1.50x
```

これらは現時点では最終採用基準ではない。

---

# 14. 土地被覆処理について今日確認したこと

当初、

```text
東京都みどりシェープファイル（平成30年）
```

を使って、

```text
Forest %
Grass %
Water %
```

を求めるコードを試した。

しかしローカルにH30データが存在しなかったため、

```text
RuntimeError:
H30 Midori shapefile not found.
Stopped to avoid invalid land-cover matching.
```

で安全停止した。

この失敗処理は**canonical pipelineには含めない**。

また、2026年公開の `樹林地.shp` は公園・緑地開園区域との重複を対象外とするため、本研究の「公園内部Forest%」にはそのまま使用しない。

今後は別途、

- 東京都R5/H30みどりGIS
- 東京都デジタルツイン 20 cm ortho
- LiDAR / DSM / DEM

等を検討する。

---

# 15. 今日の永久保存成果物

最終的にQGIS上の一時レイヤをGeoPackageへ保存した。

基準：

```text
~/qgis_tokyo_acoustic_research/output/
tokyo_acoustic_research_permanent_layers.gpkg
```

対象レイヤ：

```text
Treatment_緑地保全地域
Control_V2_CoreDesignationsExcluded
Excluded_CoreConservation
```

QGIS Project：

```text
~/qgis_tokyo_acoustic_research/qgis/
tokyo_acoustic_research.qgz
```

---

# 16. One-shot canonical reproduction script

以下は、今日バラバラに実行した処理を整理した**canonical reproduction script**。

注意：

- 今日のCURRENT V2を再現するため、`風致地区` はCOREのまま。
- `citizen_green` は今日の結果互換のためV2分類には入れない。
- 次版V2.1を作る際は、このスクリプトを上書きせず別versionとして保存する。
- 公開元ZIPが更新された場合、件数が変化する可能性がある。

QGIS Python Consoleで実行する。

```python
exec("""
import os
import csv
import math
import shutil
import zipfile
import hashlib
import urllib.request
from collections import Counter, defaultdict

import processing

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsVectorFileWriter,
    QgsCoordinateTransformContext
)

from qgis.PyQt.QtCore import QVariant


# ============================================================
# 0. SETTINGS
# ============================================================

BASE_DIR = os.path.expanduser(
    "~/qgis_tokyo_acoustic_research"
)

DOWNLOAD_DIR = os.path.join(
    BASE_DIR,
    "downloads"
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

PARK_DIR = os.path.join(
    DATA_DIR,
    "parks"
)

CONSERVATION_DIR = os.path.join(
    DATA_DIR,
    "conservation"
)

NATURAL_PARK_DIR = os.path.join(
    DATA_DIR,
    "natural_parks"
)

URBAN_GREEN_DIR = os.path.join(
    DATA_DIR,
    "urban_green"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "output"
)

QGIS_DIR = os.path.join(
    BASE_DIR,
    "qgis"
)

for d in [
    BASE_DIR,
    DOWNLOAD_DIR,
    DATA_DIR,
    PARK_DIR,
    CONSERVATION_DIR,
    NATURAL_PARK_DIR,
    URBAN_GREEN_DIR,
    OUTPUT_DIR,
    QGIS_DIR
]:
    os.makedirs(
        d,
        exist_ok=True
    )

TARGET_CRS = "EPSG:6677"

URLS = {
    "01_kouenryokuchi.zip":
        "https://data.storage.data.metro.tokyo.lg.jp/"
        "toshiseibi/01_kouenryokuchi.zip",

    "13_jourei.zip":
        "https://data.storage.data.metro.tokyo.lg.jp/"
        "toshiseibi/13_jourei.zip",

    "11_sizenkouen.zip":
        "https://data.storage.data.metro.tokyo.lg.jp/"
        "toshiseibi/11_sizenkouen.zip",

    "12_toshikeikaku_toshiryokuchi.zip":
        "https://data.storage.data.metro.tokyo.lg.jp/"
        "toshiseibi/12_toshikeikaku_toshiryokuchi.zip"
}

EXTRACT_TARGETS = {
    "01_kouenryokuchi.zip":
        PARK_DIR,

    "13_jourei.zip":
        CONSERVATION_DIR,

    "11_sizenkouen.zip":
        NATURAL_PARK_DIR,

    "12_toshikeikaku_toshiryokuchi.zip":
        URBAN_GREEN_DIR
}


# ============================================================
# 1. DOWNLOAD
# ============================================================

def download_file(
    url,
    destination
):

    if os.path.exists(
        destination
    ):

        print(
            "[SKIP download]",
            os.path.basename(
                destination
            )
        )

        return


    print(
        "[DOWNLOAD]",
        os.path.basename(
            destination
        )
    )


    req = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 "
                "QGIS Academic Research"
        }
    )


    with urllib.request.urlopen(
        req,
        timeout=180
    ) as response:

        with open(
            destination,
            "wb"
        ) as fp:

            shutil.copyfileobj(
                response,
                fp
            )


for filename, url in URLS.items():

    download_file(
        url,
        os.path.join(
            DOWNLOAD_DIR,
            filename
        )
    )


# ============================================================
# 2. SHA256 MANIFEST
# ============================================================

manifest_path = os.path.join(
    OUTPUT_DIR,
    "source_manifest_sha256.csv"
)


with open(
    manifest_path,
    "w",
    newline="",
    encoding="utf-8-sig"
) as fp:

    writer = csv.writer(
        fp
    )

    writer.writerow(
        [
            "filename",
            "url",
            "sha256"
        ]
    )


    for filename, url in URLS.items():

        path = os.path.join(
            DOWNLOAD_DIR,
            filename
        )

        h = hashlib.sha256()

        with open(
            path,
            "rb"
        ) as src:

            while True:

                chunk = src.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                h.update(
                    chunk
                )

        writer.writerow(
            [
                filename,
                url,
                h.hexdigest()
            ]
        )


# ============================================================
# 3. EXTRACT
# ============================================================

def extract_zip(
    zip_path,
    destination
):

    marker = os.path.join(
        destination,
        ".extracted"
    )


    if os.path.exists(
        marker
    ):

        print(
            "[SKIP extract]",
            os.path.basename(
                zip_path
            )
        )

        return


    with zipfile.ZipFile(
        zip_path,
        "r"
    ) as zf:

        zf.extractall(
            destination
        )


    with open(
        marker,
        "w",
        encoding="utf-8"
    ) as fp:

        fp.write(
            "done"
        )


for filename, destination in (
    EXTRACT_TARGETS.items()
):

    extract_zip(
        os.path.join(
            DOWNLOAD_DIR,
            filename
        ),
        destination
    )


# ============================================================
# 4. FILE HELPERS
# ============================================================

def find_file(
    root_dir,
    target_name
):

    for root, dirs, files in os.walk(
        root_dir
    ):

        if target_name in files:

            return os.path.join(
                root,
                target_name
            )

    return None


def load_fixed_projected(
    path,
    layer_name
):

    if path is None:

        return None


    layer = QgsVectorLayer(
        path,
        layer_name,
        "ogr"
    )


    if not layer.isValid():

        raise RuntimeError(
            "Invalid layer: "
            + str(path)
        )


    fixed = processing.run(
        "native:fixgeometries",
        {
            "INPUT":
                layer,

            "METHOD":
                1,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    projected = processing.run(
        "native:reprojectlayer",
        {
            "INPUT":
                fixed,

            "TARGET_CRS":
                TARGET_CRS,

            "CONVERT_CURVED_GEOMETRIES":
                False,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    return projected


# ============================================================
# 5. PREPARE URBAN PARK POPULATION
# ============================================================

park_specs = [
    (
        "NATIONAL",
        "国営公園.shp"
    ),
    (
        "TOKYO",
        "都立公園.shp"
    ),
    (
        "MUNICIPAL",
        "区市町村立公園(都市公園).shp"
    )
]


prepared = []

raw_feature_counts = Counter()


for source_code, filename in park_specs:

    path = find_file(
        PARK_DIR,
        filename
    )


    if path is None:

        raise RuntimeError(
            "Missing park layer: "
            + filename
        )


    layer = load_fixed_projected(
        path,
        source_code
    )


    with_source = processing.run(
        "native:fieldcalculator",
        {
            "INPUT":
                layer,

            "FIELD_NAME":
                "park_source",

            "FIELD_TYPE":
                2,

            "FIELD_LENGTH":
                20,

            "FIELD_PRECISION":
                0,

            "FORMULA":
                "'{}'".format(
                    source_code
                ),

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    with_raw_uid = processing.run(
        "native:fieldcalculator",
        {
            "INPUT":
                with_source,

            "FIELD_NAME":
                "raw_uid",

            "FIELD_TYPE":
                2,

            "FIELD_LENGTH":
                60,

            "FIELD_PRECISION":
                0,

            "FORMULA":
                "'{}_' || "
                "to_string($id)".format(
                    source_code
                ),

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    key_expression = (
        "CASE "
        "WHEN length("
        "trim(coalesce("
        "\\"公園名\\", ''))) > 0 "
        "THEN "
        "\\"park_source\\" || '|' || "
        "trim(coalesce("
        "\\"区市町村\\", '')) || '|' || "
        "trim(coalesce("
        "\\"複数区市\\", '')) || '|' || "
        "trim(\\"公園名\\") "
        "ELSE "
        "\\"park_source\\" || "
        "'|UNNAMED|' || "
        "\\"raw_uid\\" "
        "END"
    )


    with_key = processing.run(
        "native:fieldcalculator",
        {
            "INPUT":
                with_raw_uid,

            "FIELD_NAME":
                "park_key",

            "FIELD_TYPE":
                2,

            "FIELD_LENGTH":
                255,

            "FIELD_PRECISION":
                0,

            "FORMULA":
                key_expression,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    prepared.append(
        with_key
    )


parks_raw = processing.run(
    "native:mergevectorlayers",
    {
        "LAYERS":
            prepared,

        "CRS":
            TARGET_CRS,

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


for f in parks_raw.getFeatures():

    raw_feature_counts[
        str(
            f["park_key"]
        )
    ] += 1


print(
    "Raw park features:",
    parks_raw.featureCount()
)

print(
    "Unique park keys:",
    len(
        raw_feature_counts
    )
)


# ============================================================
# 6. PARK-UNIT DISSOLVE
# ============================================================

parks = processing.run(
    "native:dissolve",
    {
        "INPUT":
            parks_raw,

        "FIELD":
            [
                "park_key",
                "park_source",
                "公園名",
                "区市町村",
                "複数区市"
            ],

        "SEPARATE_DISJOINT":
            False,

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


parks = processing.run(
    "native:fixgeometries",
    {
        "INPUT":
            parks,

        "METHOD":
            1,

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


provider = parks.dataProvider()

provider.addAttributes(
    [
        QgsField(
            "raw_n",
            QVariant.Int
        )
    ]
)

parks.updateFields()

idx_raw_n = (
    parks.fields()
    .indexFromName(
        "raw_n"
    )
)


parks.startEditing()

for f in parks.getFeatures():

    f[idx_raw_n] = int(
        raw_feature_counts.get(
            str(
                f["park_key"]
            ),
            0
        )
    )

    parks.updateFeature(
        f
    )

parks.commitChanges()


parks = processing.run(
    "native:fieldcalculator",
    {
        "INPUT":
            parks,

        "FIELD_NAME":
            "park_area_m2",

        "FIELD_TYPE":
            0,

        "FIELD_LENGTH":
            20,

        "FIELD_PRECISION":
            3,

        "FORMULA":
            "$area",

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


print(
    "Park units:",
    parks.featureCount()
)


# ============================================================
# 7. TOKYO CONSERVATION / TREATMENT
# ============================================================

tokyo_cons_path = find_file(
    CONSERVATION_DIR,
    "東京都保全地域.shp"
)


tokyo_cons = load_fixed_projected(
    tokyo_cons_path,
    "東京都保全地域"
)


green = processing.run(
    "native:extractbyexpression",
    {
        "INPUT":
            tokyo_cons,

        "EXPRESSION":
            "\\"種別\\" = "
            "'緑地保全地域'",

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


green_union = processing.run(
    "native:dissolve",
    {
        "INPUT":
            green,

        "FIELD":
            [],

        "SEPARATE_DISJOINT":
            False,

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


green_intersection = (
    processing.run(
        "native:intersection",
        {
            "INPUT":
                parks,

            "OVERLAY":
                green_union,

            "INPUT_FIELDS":
                [
                    "park_key"
                ],

            "OVERLAY_FIELDS":
                [],

            "OVERLAY_FIELDS_PREFIX":
                "",

            "GRID_SIZE":
                None,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]
)


green_area_by_key = defaultdict(
    float
)


for f in green_intersection.getFeatures():

    green_area_by_key[
        str(
            f["park_key"]
        )
    ] += (
        f.geometry().area()
    )


# all Tokyo conservation
tokyo_cons_union = (
    processing.run(
        "native:dissolve",
        {
            "INPUT":
                tokyo_cons,

            "FIELD":
                [],

            "SEPARATE_DISJOINT":
                False,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]
)


tokyo_cons_intersection = (
    processing.run(
        "native:intersection",
        {
            "INPUT":
                parks,

            "OVERLAY":
                tokyo_cons_union,

            "INPUT_FIELDS":
                [
                    "park_key"
                ],

            "OVERLAY_FIELDS":
                [],

            "OVERLAY_FIELDS_PREFIX":
                "",

            "GRID_SIZE":
                None,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]
)


tokyo_cons_keys = {
    str(
        f["park_key"]
    )
    for f
    in tokyo_cons_intersection.getFeatures()
}


# protection fields
provider = parks.dataProvider()

provider.addAttributes(
    [
        QgsField(
            "green_m2",
            QVariant.Double,
            len=20,
            prec=3
        ),

        QgsField(
            "green_ratio",
            QVariant.Double,
            len=12,
            prec=8
        ),

        QgsField(
            "green_pct",
            QVariant.Double,
            len=12,
            prec=5
        )
    ]
)

parks.updateFields()

idx_green_m2 = (
    parks.fields()
    .indexFromName(
        "green_m2"
    )
)

idx_green_ratio = (
    parks.fields()
    .indexFromName(
        "green_ratio"
    )
)

idx_green_pct = (
    parks.fields()
    .indexFromName(
        "green_pct"
    )
)


parks.startEditing()

for f in parks.getFeatures():

    key = str(
        f["park_key"]
    )

    park_area = float(
        f["park_area_m2"]
        or 0
    )

    green_area = float(
        green_area_by_key.get(
            key,
            0.0
        )
    )

    ratio = (
        green_area
        /
        park_area
        if park_area > 0
        else 0.0
    )

    ratio = max(
        0.0,
        min(
            1.0,
            ratio
        )
    )

    f[idx_green_m2] = (
        green_area
    )

    f[idx_green_ratio] = (
        ratio
    )

    f[idx_green_pct] = (
        ratio
        *
        100.0
    )

    parks.updateFeature(
        f
    )

parks.commitChanges()


treatment_keys = set(
    green_area_by_key.keys()
)


# ============================================================
# 8. DESIGNATION AUDIT V2
# CURRENT V2 AS EXECUTED ON 2026-09-21
# ============================================================

designation_specs = [
    # name, directory, filename, role

    (
        "tokyo_conservation",
        CONSERVATION_DIR,
        "東京都保全地域.shp",
        "CORE"
    ),

    (
        "special_green",
        URBAN_GREEN_DIR,
        "特別緑地保全地区.shp",
        "CORE"
    ),

    (
        "scenic_district",
        URBAN_GREEN_DIR,
        "風致地区.shp",
        "CORE"
    ),

    (
        "metro_green",
        URBAN_GREEN_DIR,
        "首都圏近郊緑地保全区域.shp",
        "CORE"
    ),

    (
        "national_park",
        NATURAL_PARK_DIR,
        "国立公園.shp",
        "CORE"
    ),

    (
        "quasi_national_park",
        NATURAL_PARK_DIR,
        "国定公園.shp",
        "CORE"
    ),

    (
        "tokyo_natural_park",
        NATURAL_PARK_DIR,
        "都立自然公園.shp",
        "CORE"
    ),

    (
        "saved_forest",
        CONSERVATION_DIR,
        "保存樹林.shp",
        "CORE"
    ),

    # CURRENT V2 citizen_green bug retained
    # for today's result compatibility.
    (
        "citizen_green",
        URBAN_GREEN_DIR,
        "市民緑地.shp",
        "FLAG"
    ),

    (
        "green_agreement",
        URBAN_GREEN_DIR,
        "緑地協定.shp",
        "FLAG"
    ),

    (
        "greening_district",
        URBAN_GREEN_DIR,
        "緑化地域.shp",
        "FLAG"
    ),

    (
        "agricultural_landscape",
        CONSERVATION_DIR,
        "農の風景育成地区.shp",
        "FLAG"
    ),

    (
        "tokyo_forest",
        CONSERVATION_DIR,
        "都民の森.shp",
        "FLAG"
    )
]


designation_keys = {}

designation_role = {}

designation_status = {}


for (
    name,
    root_dir,
    filename,
    role
) in designation_specs:

    designation_role[
        name
    ] = role

    path = find_file(
        root_dir,
        filename
    )


    if path is None:

        designation_keys[
            name
        ] = set()

        designation_status[
            name
        ] = "MISSING_OPTIONAL"

        print(
            "[MISSING]",
            name,
            filename
        )

        continue


    layer = load_fixed_projected(
        path,
        name
    )


    dissolved = processing.run(
        "native:dissolve",
        {
            "INPUT":
                layer,

            "FIELD":
                [],

            "SEPARATE_DISJOINT":
                False,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    inter = processing.run(
        "native:intersection",
        {
            "INPUT":
                parks,

            "OVERLAY":
                dissolved,

            "INPUT_FIELDS":
                [
                    "park_key"
                ],

            "OVERLAY_FIELDS":
                [],

            "OVERLAY_FIELDS_PREFIX":
                "",

            "GRID_SIZE":
                None,

            "OUTPUT":
                "memory:"
        }
    )["OUTPUT"]


    keys = {
        str(
            f["park_key"]
        )
        for f
        in inter.getFeatures()
    }


    designation_keys[
        name
    ] = keys

    designation_status[
        name
    ] = "OK"


# ============================================================
# 9. CLASSIFY CURRENT V2
# ============================================================

core_names = [
    name
    for name, role
    in designation_role.items()
    if role == "CORE"
]

flag_names = [
    name
    for name, role
    in designation_role.items()
    if role == "FLAG"
]


core_union = set()

for name in core_names:

    core_union |= (
        designation_keys.get(
            name,
            set()
        )
    )


provider = parks.dataProvider()

provider.addAttributes(
    [
        QgsField(
            "study_class",
            QVariant.String,
            len=40
        ),

        QgsField(
            "core_hits",
            QVariant.String,
            len=255
        ),

        QgsField(
            "flag_hits",
            QVariant.String,
            len=255
        )
    ]
)

parks.updateFields()

idx_class = (
    parks.fields()
    .indexFromName(
        "study_class"
    )
)

idx_core = (
    parks.fields()
    .indexFromName(
        "core_hits"
    )
)

idx_flag = (
    parks.fields()
    .indexFromName(
        "flag_hits"
    )
)


parks.startEditing()

for f in parks.getFeatures():

    key = str(
        f["park_key"]
    )


    core_hits = [
        name
        for name in core_names
        if key in (
            designation_keys.get(
                name,
                set()
            )
        )
    ]


    flag_hits = [
        name
        for name in flag_names
        if key in (
            designation_keys.get(
                name,
                set()
            )
        )
    ]


    if key in treatment_keys:

        study_class = (
            "TREATMENT"
        )

    elif core_hits:

        study_class = (
            "EXCLUDED_CORE"
        )

    else:

        study_class = (
            "CONTROL_V2"
        )


    f[idx_class] = (
        study_class
    )

    f[idx_core] = (
        ",".join(
            core_hits
        )
    )

    f[idx_flag] = (
        ",".join(
            flag_hits
        )
    )


    parks.updateFeature(
        f
    )

parks.commitChanges()


treatment = processing.run(
    "native:extractbyexpression",
    {
        "INPUT":
            parks,

        "EXPRESSION":
            "\\"study_class\\" = "
            "'TREATMENT'",

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


control_v2 = processing.run(
    "native:extractbyexpression",
    {
        "INPUT":
            parks,

        "EXPRESSION":
            "\\"study_class\\" = "
            "'CONTROL_V2'",

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


excluded_core = processing.run(
    "native:extractbyexpression",
    {
        "INPUT":
            parks,

        "EXPRESSION":
            "\\"study_class\\" = "
            "'EXCLUDED_CORE'",

        "OUTPUT":
            "memory:"
    }
)["OUTPUT"]


treatment.setName(
    "Treatment_緑地保全地域"
)

control_v2.setName(
    "Control_V2_CoreDesignationsExcluded"
)

excluded_core.setName(
    "Excluded_CoreConservation"
)


# ============================================================
# 10. WRITE AUDIT CSV
# ============================================================

designation_csv = os.path.join(
    OUTPUT_DIR,
    "designation_overlap_audit_v2.csv"
)


with open(
    designation_csv,
    "w",
    newline="",
    encoding="utf-8-sig"
) as fp:

    writer = csv.writer(
        fp
    )

    writer.writerow(
        [
            "designation",
            "role",
            "status",
            "parks_overlap"
        ]
    )


    for name, role in (
        designation_role.items()
    ):

        writer.writerow(
            [
                name,
                role,
                designation_status[
                    name
                ],
                len(
                    designation_keys[
                        name
                    ]
                )
            ]
        )


treatment_other_csv = os.path.join(
    OUTPUT_DIR,
    "treatment_other_designation_audit.csv"
)


with open(
    treatment_other_csv,
    "w",
    newline="",
    encoding="utf-8-sig"
) as fp:

    writer = csv.writer(
        fp
    )

    writer.writerow(
        [
            "park_key",
            "park_name",
            "municipality",
            "green_ratio",
            "other_core_designations"
        ]
    )


    for f in treatment.getFeatures():

        key = str(
            f["park_key"]
        )


        other_core = [
            name
            for name in core_names
            if (
                name
                !=
                "tokyo_conservation"
                and
                key in designation_keys[
                    name
                ]
            )
        ]


        writer.writerow(
            [
                key,
                str(
                    f["公園名"]
                    or ""
                ),
                str(
                    f["区市町村"]
                    or ""
                ),
                float(
                    f["green_ratio"]
                    or 0
                ),
                ",".join(
                    other_core
                )
            ]
        )


# ============================================================
# 11. SAVE INTERMEDIATE GPKG
# ============================================================

audit_v2_gpkg = os.path.join(
    OUTPUT_DIR,
    "tokyo_treatment_control_audit_v2.gpkg"
)


if os.path.exists(
    audit_v2_gpkg
):

    os.remove(
        audit_v2_gpkg
    )


def write_layer_to_gpkg(
    layer,
    path,
    layer_name,
    first=False
):

    options = (
        QgsVectorFileWriter
        .SaveVectorOptions()
    )

    options.driverName = (
        "GPKG"
    )

    options.layerName = (
        layer_name
    )

    options.fileEncoding = (
        "UTF-8"
    )


    if first:

        options.actionOnExistingFile = (
            QgsVectorFileWriter
            .CreateOrOverwriteFile
        )

    else:

        options.actionOnExistingFile = (
            QgsVectorFileWriter
            .CreateOrOverwriteLayer
        )


    return (
        QgsVectorFileWriter
        .writeAsVectorFormatV3(
            layer,
            path,
            QgsCoordinateTransformContext(),
            options
        )
    )


write_layer_to_gpkg(
    treatment,
    audit_v2_gpkg,
    "treatment",
    first=True
)

write_layer_to_gpkg(
    control_v2,
    audit_v2_gpkg,
    "control_v2"
)

write_layer_to_gpkg(
    excluded_core,
    audit_v2_gpkg,
    "excluded_core"
)


# ============================================================
# 12. STAGE 1 AREA-ONLY SCREENING
# ============================================================

CALIPERS = {
    "10pct":
        (
            0.90,
            1.10
        ),

    "25pct":
        (
            0.80,
            1.25
        ),

    "50pct":
        (
            2.0 / 3.0,
            1.50
        )
}


all_pairs_csv = os.path.join(
    OUTPUT_DIR,
    "stage1_area_all_pairs_v1.csv"
)

c10_csv = os.path.join(
    OUTPUT_DIR,
    "stage1_area_candidates_10pct_v1.csv"
)

c25_csv = os.path.join(
    OUTPUT_DIR,
    "stage1_area_candidates_25pct_v1.csv"
)

c50_csv = os.path.join(
    OUTPUT_DIR,
    "stage1_area_candidates_50pct_v1.csv"
)

summary_csv = os.path.join(
    OUTPUT_DIR,
    "stage1_area_screening_summary_v1.csv"
)


PAIR_FIELDS = [
    "treatment_key",
    "treatment_name",
    "treatment_municipality",
    "treatment_area_m2",
    "treatment_area_ha",
    "protection_ratio",
    "control_key",
    "control_name",
    "control_municipality",
    "control_area_m2",
    "control_area_ha",
    "area_ratio",
    "area_difference_m2",
    "area_difference_pct",
    "log_area_distance",
    "same_municipality",
    "within_10pct",
    "within_25pct",
    "within_50pct"
]


def record_from_feature(
    f
):

    area = float(
        f["park_area_m2"]
        or 0
    )

    return {
        "park_key":
            str(
                f["park_key"]
            ),

        "park_name":
            str(
                f["公園名"]
                or ""
            ),

        "municipality":
            str(
                f["区市町村"]
                or ""
            ),

        "area_m2":
            area,

        "area_ha":
            area / 10000.0,

        "green_ratio":
            float(
                f["green_ratio"]
                or 0
            )
    }


t_records = [
    record_from_feature(
        f
    )
    for f
    in treatment.getFeatures()
]


c_records = [
    record_from_feature(
        f
    )
    for f
    in control_v2.getFeatures()
]


fps = {
    "all":
        open(
            all_pairs_csv,
            "w",
            newline="",
            encoding="utf-8-sig"
        ),

    "10":
        open(
            c10_csv,
            "w",
            newline="",
            encoding="utf-8-sig"
        ),

    "25":
        open(
            c25_csv,
            "w",
            newline="",
            encoding="utf-8-sig"
        ),

    "50":
        open(
            c50_csv,
            "w",
            newline="",
            encoding="utf-8-sig"
        )
}


writers = {
    key:
        csv.DictWriter(
            fp,
            fieldnames=PAIR_FIELDS
        )
    for key, fp
    in fps.items()
}


for writer in writers.values():

    writer.writeheader()


summary_rows = []


for t in t_records:

    count10 = 0
    count25 = 0
    count50 = 0


    rows = []


    for c in c_records:

        ratio = (
            c["area_m2"]
            /
            t["area_m2"]
        )


        diff_m2 = abs(
            c["area_m2"]
            -
            t["area_m2"]
        )


        diff_pct = (
            diff_m2
            /
            t["area_m2"]
            *
            100.0
        )


        log_distance = abs(
            math.log(
                ratio
            )
        )


        in10 = (
            0.90
            <= ratio
            <= 1.10
        )

        in25 = (
            0.80
            <= ratio
            <= 1.25
        )

        in50 = (
            (2.0 / 3.0)
            <= ratio
            <= 1.50
        )


        row = {
            "treatment_key":
                t["park_key"],

            "treatment_name":
                t["park_name"],

            "treatment_municipality":
                t["municipality"],

            "treatment_area_m2":
                t["area_m2"],

            "treatment_area_ha":
                t["area_ha"],

            "protection_ratio":
                t["green_ratio"],

            "control_key":
                c["park_key"],

            "control_name":
                c["park_name"],

            "control_municipality":
                c["municipality"],

            "control_area_m2":
                c["area_m2"],

            "control_area_ha":
                c["area_ha"],

            "area_ratio":
                ratio,

            "area_difference_m2":
                diff_m2,

            "area_difference_pct":
                diff_pct,

            "log_area_distance":
                log_distance,

            "same_municipality":
                int(
                    t["municipality"]
                    ==
                    c["municipality"]
                ),

            "within_10pct":
                int(
                    in10
                ),

            "within_25pct":
                int(
                    in25
                ),

            "within_50pct":
                int(
                    in50
                )
        }


        rows.append(
            row
        )


    rows.sort(
        key=lambda x:
            x["log_area_distance"]
    )


    for row in rows:

        writers[
            "all"
        ].writerow(
            row
        )


        if row[
            "within_10pct"
        ]:

            writers[
                "10"
            ].writerow(
                row
            )

            count10 += 1


        if row[
            "within_25pct"
        ]:

            writers[
                "25"
            ].writerow(
                row
            )

            count25 += 1


        if row[
            "within_50pct"
        ]:

            writers[
                "50"
            ].writerow(
                row
            )

            count50 += 1


    summary_rows.append(
        {
            "treatment_key":
                t["park_key"],

            "treatment_name":
                t["park_name"],

            "municipality":
                t["municipality"],

            "area_ha":
                t["area_ha"],

            "protection_ratio":
                t["green_ratio"],

            "controls_within_10pct":
                count10,

            "controls_within_25pct":
                count25,

            "controls_within_50pct":
                count50
        }
    )


for fp in fps.values():

    fp.close()


with open(
    summary_csv,
    "w",
    newline="",
    encoding="utf-8-sig"
) as fp:

    fields = [
        "treatment_key",
        "treatment_name",
        "municipality",
        "area_ha",
        "protection_ratio",
        "controls_within_10pct",
        "controls_within_25pct",
        "controls_within_50pct"
    ]

    writer = csv.DictWriter(
        fp,
        fieldnames=fields
    )

    writer.writeheader()

    writer.writerows(
        summary_rows
    )


# ============================================================
# 13. FINAL PERMANENT GPKG
# ============================================================

permanent_gpkg = os.path.join(
    OUTPUT_DIR,
    "tokyo_acoustic_research_permanent_layers.gpkg"
)


if os.path.exists(
    permanent_gpkg
):

    os.remove(
        permanent_gpkg
    )


write_layer_to_gpkg(
    treatment,
    permanent_gpkg,
    "Treatment_緑地保全地域",
    first=True
)

write_layer_to_gpkg(
    control_v2,
    permanent_gpkg,
    "Control_V2_CoreDesignationsExcluded"
)

write_layer_to_gpkg(
    excluded_core,
    permanent_gpkg,
    "Excluded_CoreConservation"
)


# ============================================================
# 14. RELOAD PERMANENT LAYERS + SAVE PROJECT
# ============================================================

QgsProject.instance().removeAllMapLayers()


for layer_name in [
    "Excluded_CoreConservation",
    "Control_V2_CoreDesignationsExcluded",
    "Treatment_緑地保全地域"
]:

    uri = (
        permanent_gpkg
        +
        "|layername="
        +
        layer_name
    )


    layer = QgsVectorLayer(
        uri,
        layer_name,
        "ogr"
    )


    if not layer.isValid():

        raise RuntimeError(
            "Failed to reload "
            + layer_name
        )


    QgsProject.instance().addMapLayer(
        layer
    )


project_path = os.path.join(
    QGIS_DIR,
    "tokyo_acoustic_research.qgz"
)


QgsProject.instance().write(
    project_path
)


# ============================================================
# 15. VALIDATION REPORT
# ============================================================

print()
print("=" * 80)
print("FINAL VALIDATION")
print("=" * 80)

print(
    "Total park units:",
    parks.featureCount()
)

print(
    "Treatment:",
    treatment.featureCount()
)

print(
    "Control V2:",
    control_v2.featureCount()
)

print(
    "Excluded Core:",
    excluded_core.featureCount()
)

print(
    "Check:",
    treatment.featureCount()
    +
    control_v2.featureCount()
    +
    excluded_core.featureCount()
)

print()
print(
    "Permanent GPKG:",
    permanent_gpkg
)

print(
    "QGIS project:",
    project_path
)

print(
    "Source manifest:",
    manifest_path
)

print()
print("=" * 80)
print("PIPELINE COMPLETED")
print("=" * 80)
""")
```

---

# 17. 今日の再現確認値

2026-09-21のCURRENT V2では、少なくとも以下を満たすこと。

```text
Total park units = 8770
Treatment        = 30
Control V2       = 8195
Excluded Core    = 545

30 + 8195 + 545 = 8770
```

Treatment Protection Ratio：

```text
>=10%  12
>=25%  11
>=50%   7
>=75%   5
>=90%   3
```

上記と大きく異なる場合は、

- 東京都公開データ更新
- source ZIP差異
- ファイル名変更
- QGIS Processing version差
- geometry repair結果差
- designation definition変更

を確認する。

---

# 18. 今日生成した主な成果物

## Treatment audit

```text
output/tokyo_protected_park_audit_v2.gpkg
output/tokyo_protected_park_candidates_v2.csv
output/park_feature_group_audit.csv
```

## Control V1

```text
output/tokyo_treatment_control_audit_v1.gpkg
output/treatment_candidates_v1.csv
output/control_candidates_v1.csv
```

## Designation Audit V2

```text
output/tokyo_treatment_control_audit_v2.gpkg
output/designation_overlap_audit_v2.csv
output/treatment_other_designation_audit.csv
```

## Area matching diagnostics

今日の探索的監査では以下も生成した。

```text
output/area_matching_feasibility_summary.csv
output/area_matching_nearest_controls.csv
```

これは「面積だけでmatching可能性があるか」を診断したもので、
最終pair selectionではない。

## Stage 1 area-only screening

```text
output/stage1_area_all_pairs_v1.csv
output/stage1_area_candidates_10pct_v1.csv
output/stage1_area_candidates_25pct_v1.csv
output/stage1_area_candidates_50pct_v1.csv
output/stage1_area_screening_summary_v1.csv
```

## Permanent layers

```text
output/tokyo_acoustic_research_permanent_layers.gpkg
```

## QGIS project

```text
qgis/tokyo_acoustic_research.qgz
```

## Reproducibility manifest

```text
output/source_manifest_sha256.csv
```

---

# 19. GitHubへ移す際の推奨構成

```text
tokyo-conservation-acoustic/
├── README.md
├── docs/
│   ├── research_design.md
│   ├── matching_screening_policy.md
│   └── gis_pipeline_20260921.md
│
├── scripts/
│   ├── 01_download_sources.py
│   ├── 02_build_park_population.py
│   ├── 03_protection_ratio.py
│   ├── 04_control_designation_audit_v2.py
│   ├── 05_area_screening.py
│   └── 06_export_permanent_layers.py
│
├── config/
│   └── source_urls.yml
│
├── output/
│   └── README.md
│
└── .gitignore
```

大容量の東京都ZIP、展開済Shapefile、QGIS temporary/cache等は原則Git管理しない。

例：

```gitignore
downloads/
data/
*.zip
*.qgz~
.DS_Store
```

ただし、

```text
source URL
download date
SHA256
expected feature counts
```

は必ずGit管理する。

---

# 20. versioning policy

今日のV2を後から黙って変更しない。

```text
V1
東京都保全地域5カテゴリだけでControl除外

V2
追加保全制度をCORE/FLAG監査
風致地区CORE
市民緑地未取得

V2.1
予定：
- 風致地区 CORE → FLAG 検討
- 市民緑地_ポリゴン修正
- 他指定のoverlap ratio監査
- sliver intersection監査
```

研究結果を再現するため、

> **旧versionのスクリプト・定義・出力を残したまま新versionを作る。**

---

# 21. 次工程

永久保存まで完了した後の次工程は、

```text
Control definition V2.1 audit
        ↓
Stage 1 area screening 再実行
        ↓
土地被覆候補データ確定
        ↓
Forest %
Grass %
Water %
        ↓
Area + Forest + Grass + Water
final matching
        ↓
field acoustic measurement
```

とする。

道路距離・交通量・鉄道・建物密度・建物高さ・3D遮蔽は、
初期matchingには入れず、音環境差の追加説明変数として後段で扱う。

---

# 22. 現時点で固定してはいけないもの

以下はまだ固定しない。

- Treatment Protection Ratio threshold
- 最終area caliper
- matched pair数
- Forest / Grass / Water データソース
- 他指定とのoverlap ratio閾値
- 風致地区の最終CORE/FLAG分類
- 市区町村をhard constraintにするか

今日確認できたのは、

> **面積だけではmatching可能性は破綻していない**

という点まで。

---

# 23. 再現性チェックリスト

GitHubへ上げる前に以下を確認する。

- [ ] QGIS versionを記録
- [ ] source ZIP SHA256を記録
- [ ] 公式source URLを記録
- [ ] CRS = EPSG:6677
- [ ] raw park features = 8770
- [ ] unique park units = 8770
- [ ] Treatment overlap = 30
- [ ] CURRENT V2 Control = 8195
- [ ] CURRENT V2 Excluded Core = 545
- [ ] Treatment + Control + Excluded = 8770
- [ ] Treatment threshold未固定と明記
- [ ] area caliper未固定と明記
- [ ] CURRENT V2が暫定であることを明記
- [ ] V2.1変更を別versionで管理
- [ ] 土地被覆処理をCURRENT pipelineと混同しない

