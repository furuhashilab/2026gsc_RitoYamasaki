# フロアプランの「表示方向」が視覚言語ナビゲーションAIの判断に与える影響（仮題）

How does the *display orientation* of a floor plan affect the decisions of an indoor
Vision-and-Language Navigation agent? — A reproduction-first study of FP-Nav (FloorPlan-VLN).

卒業研究（青山学院大学 地球社会共生学部 古橋研究室）のリポジトリ。
古橋研究室の方針「Publish or Die」「オープンナレッジ」に従い、**成功だけでなく失敗・検証過程・未確認事項も記録**する。

> **現在地**: 本研究はまず**原著 FP-Nav の再現**を最優先で進めている段階である。
> 独自研究（地図の表示方向を変える実験）は **未実施の研究計画**であり、新規性はまだ確立していない。
> 本リポジトリは研究成果を誇張しない。確認できたことと、できていないことを分けて書く。

---

## 1. 背景と目的

屋内の視覚言語ナビゲーション（Vision-and-Language Navigation, VLN）では、自然言語の指示に従い、
エージェントが屋内環境を移動する。本研究が対象とする **FP-Nav（FloorPlan-VLN）** は、
エージェント視点のRGB画像に加えて**建物のフロアプラン（間取り図）**を手がかりに次の行動を決める手法である。

本研究の第一の目的は、**原著に可能な限り忠実な再現実験を行い、ローカル環境（Apple Silicon Mac）で
「何が再現できて、何が再現できないか」を明らかにすること**である。その上で、卒業研究として独自の実験を行う。

再現を独立のゴールとして明示するのは、「オープンナレッジ」の方針に沿って、
追試可能な形で環境差・制約・つまずきを公開するためである。

---

## 2. FP-Nav の概要

FP-Nav は次の4種類の情報から次の移動行動を決定する。

1. 建物のフロアプラン（間取り図）
2. エージェント視点のRGB画像
3. 自然言語の移動指示
4. 過去の観測・移動履歴（最大6フレームの画像をサンプル）

内部的には、各ステップで「**左＝エゴRGB（448×448）／右＝軌跡・方位を重ねた間取り図（448×448）**」を
横連結した 896×448 のフレームを時系列に積み、微調整済みの **Qwen2.5-VL-7B**（video入力）へ渡して
行動テキスト（例: `turn left 30 degrees` / `move forward 50` / `stop`）を生成する。
出力テキストは正規表現で行動種別＋数値に分解され、離散行動列へ量子化される。

- 間取り図は毎ステップ JSON から**ライブ描画**される（動画に焼き込まれておらず、差し替え可能）。
- 地図上の自己位置・軌跡は Habitat の **ground-truth pose（オラクル測位）**由来であり、地図は「測位源」ではなく
  「レイアウト事前情報」として働く。
- 間取り図は **Matterport3D（実在建物スキャン）の領域アノテーションから生成した意味的ポリゴン地図**であり、
  公開された正確な建築図面ではない。

コード経路・行番号・入出力仕様の詳細は
[`docs/reproduction/FP_NAV_INFERENCE_SPEC.md`](docs/reproduction/FP_NAV_INFERENCE_SPEC.md) と
[`docs/reproduction/FP_NAV_FEASIBILITY_REPORT.md`](docs/reproduction/FP_NAV_FEASIBILITY_REPORT.md) に記録している。

---

## 3. 先行研究との関係

- FP-Nav 自身が、頂点ジッタ・部屋欠落・スケール不一致・ガウスノイズなど、**地図に幾何ノイズを与えて頑健性を測る実験**を
  すでに実装・報告している。
- 関連研究（FloNa〔AAAI 2025〕ほか）も、**間取り図の不正確さに対する頑健性**を主題化している。

したがって、「**誤った/不正確な地図を与えると性能が落ちる**」という結果は本研究の新規性としては主張しない（既出）。
本研究の独自案（§6）は、地図の内容を誤らせるのではなく、**地図・自己位置・方位・軌跡を整合させたまま「表示方向」だけを変える**点で、
これらの先行研究とは区別される。ただし新規性が確立したわけではなく、先行研究の精読サーベイは継続中である。

---

## 4. 実験環境

| 項目 | 内容 |
|---|---|
| 計算機 | Apple Silicon Mac **M4 / 32GB**（研究室Mac。再現実験の主環境） |
| フレームワーク | PyTorch / **MPS** |
| モデル推論 | **bf16・eager**（flash-attn はCUDA専用のため不使用。詳細は §6 of SPEC） |
| シミュレータ | **Habitat-Sim 0.3.3**（Matterport3D形式シーンの読み込みに使用） |
| SciPy | 主条件 **1.10.1**（方位計算のバージョン依存のため固定。[technical_notes/01](docs/technical_notes/01_scipy_heading_versions.md)） |
| モデル | FP-Nav 公開モデル（微調整済み `qwen2_5_vl`, 16.6GB） |

> 注: 本リポジトリの**ドキュメント整備作業**は別の調査用Mac（16GB）で行っており、
> 再現実験の**一次ログ・成果物は研究室Mac上**にある。本更新時点で、それらのログはこのリポジトリに未取り込み・未再照合である（§5）。

---

## 5. 再現実験の進捗（確認できたこと／未確認のこと）

> 下表の「実施」は**研究者本人の報告**に基づく。再現実験の一次ログは研究室Mac上にあり、
> 本ドキュメント更新環境では実ログを**再照合できていない**。数値は報告された範囲のみを記し、推測で補っていない。

| 段階 | 状態 | 備考 |
|---|---|---|
| 適格性調査（研究対象としての妥当性・評価可能性・実現性・新規性） | **文書化済み** | [`docs/reproduction/`](docs/reproduction/) の4文書。コード経路を `file:line` で確認（2026-11-05, 調査機） |
| シミュレータ検証（Habitat-Sim での RGB観測・行動再生） | 実施（本人報告・実ログ未照合） | R2R の ep85・ep280 で GT 行動を再生し、正解経路の終点一致・開始→ゴールの測地距離一致を確認、と報告 |
| 方位・地図描画の検証 | 実施（本人報告・実ログ未照合） | SciPy 1.10.1 vs 1.13.1 の heading 差を確認。カメラ前方ベクトルと地図矢印を照合、公式 FloorplanNavigator で8エピソードの向きを検証、と報告 |
| モデル入力の再現性確認 | 実施（本人報告・実ログ未照合） | RGB×間取り図の横連結入力を生成し過去Pilotと画像/テンソル比較。画素差は開始位置の小数第3位丸めに起因、ハッシュ不一致は int32 キャストとSHA-256短縮表示の計算方式差、と報告 |
| 閉ループPilot（R2R val-seen ep85） | 実施（本人報告・実ログ未照合） | 下記参照 |
| **完全閉ループ評価（本実行, ep85・ep280）** | **計画・承認済み／結果は未確認** | 本実行の結果ファイルは本更新時点で確認できていない |

### 閉ループPilot（ep85）について — 何を示し、何を示さないか

報告によれば、FP-Nav 公開モデルで ep85 の閉ループPilotを実施し、

- モデル判断 5回／基本移動動作12回（回転6・前進6）／解析失敗0回
- 出力は「左30°回転」を3判断、その後「75cm前進」を2判断
- 行動実行後の観測更新と次の判断が動作することを確認

**これは「モデル判断5回の上限で打ち切ったPilot」であり、完走時の SR・SPL などの性能評価ではない。**
**原著の成功率を再現できたという主張はしない。** これは「地図付き入力でモデルが行動を判断し、観測更新のループが回る」ことの動作確認である。

技術的なつまずきと検証の記録は [`docs/technical_notes/`](docs/technical_notes/)、進捗の全体は
[`docs/research_progress.md`](docs/research_progress.md) にまとめている。

---

## 6. 今後の研究計画（未実施）

### 独自研究案：地図の「表示方向」を変えると判断は変わるか

> **問い（仮説段階）**: フロアプランの情報は正しいまま、**表示方向だけ**を変更したとき、
> 視覚言語ナビゲーションAIの行動判断や性能は変わるのか？

想定する比較条件（3つ）:

1. 公式のフロアプラン表示
2. 進行方向が上になる表示（heading-up）
3. 地図全体を180°回転した表示

重要なのは、地図の内容や位置情報を**誤らせない**こと。**地図全体と自己位置・方位・移動軌跡を整合させたまま**、
表示方向だけを変える。これは「地図の矢印だけを誤った方向へずらす」案や「誤った地図を与える」先行研究とは異なる（§3）。

**この研究案は未実施であり、新規性も確立していない。** 詳細と留保は [`docs/future_work.md`](docs/future_work.md) を参照。

### 実環境での補助検証案（構想段階）

大学の建物で360°カメラを用い、正解ルート上の画像を収集して開ループ評価を行う構想がある。
**現時点では研究案であり、撮影・データ整備は行っていない。** 実環境で評価済み・閉ループ評価が可能になった、とは主張しない。

---

## 7. リポジトリ構成

```
.
├── README.md                          このファイル（研究の全体像）
├── docs/
│   ├── research_progress.md           再現実験の進捗・結果・限界・次の課題
│   ├── future_work.md                 独自研究案（表示方向）と実環境補助検証案（いずれも未実施）
│   ├── technical_notes/               後輩向けの技術的検証記録
│   │   ├── 01_scipy_heading_versions.md        SciPyバージョンによる heading 計算差
│   │   ├── 02_episode_id_vs_trajectory_id.md   episode_id と trajectory_id の取り違え
│   │   └── 03_rgb_coordinate_rounding.md       RGB描画の座標丸めによる差異
│   └── reproduction/                  原著再現のための一次資料（2026-11-05, 調査機）
│       ├── FP_NAV_FEASIBILITY_REPORT.md   適格性調査レポート
│       ├── FP_NAV_INFERENCE_SPEC.md       推論仕様（忠実再現の固定条件）
│       ├── LAB_MAC_SETUP.md               研究室Macセットアップ手順
│       └── REPRODUCTION_CHECKLIST.md      再現チェックリスト
├── src/
│   └── run_single_step.py             1ステップ推論スクリプト（Habitat非依存／mac対応, ★未実行・未検証★）
└── LICENSE                            CC BY 4.0（本文・成果物）
```

### 本リポジトリに含めないもの（再配布しない）

- FP-Nav 公開モデルの重み（HF `keeehan/FloorPlan-VLN`, 16.6GB）
- Matterport3D のシーン（.glb）・RGBデータ（要規約同意・非商用学術限定）
- 評価用 GT データ（`val_*_gt.json.gz` 等）
- 大容量の実験中間生成物・再現実験の一次ログ（研究室Mac上に保持）

これらは各配布元の規約に従って各自取得すること。取得手順は [`docs/reproduction/LAB_MAC_SETUP.md`](docs/reproduction/LAB_MAC_SETUP.md) を参照。

---

## 8. 参考文献・公式リポジトリ

- 原著論文: FloorPlan-VLN, arXiv **2603.17437** — https://arxiv.org/abs/2603.17437
- 公式実装: Chenkehan21/FloorPlan-VLN — https://github.com/Chenkehan21/FloorPlan-VLN （License Apache-2.0）
- 公開モデル: keeehan/FloorPlan-VLN — https://huggingface.co/keeehan/FloorPlan-VLN
- Matterport3D — https://niessner.github.io/Matterport/ （要規約同意・非商用学術）
- 関連: FloNa: Floor Plan Guided Embodied Visual Navigation, AAAI 2025, arXiv:2412.18335

参照コード・行番号・一次資料の確認日は [`docs/reproduction/FP_NAV_FEASIBILITY_REPORT.md`](docs/reproduction/FP_NAV_FEASIBILITY_REPORT.md) §10 に記録。

---

## License

本研究の本文・成果物は、古橋研究室のルールに従い **CC BY 4.0** で公開する。
ただし FP-Nav の公開モデル重み・Matterport3D 等の外部データは本リポジトリに含めず、各配布元の条件に従う。

© Furuhashi Laboratory / Rito Yamasaki, CC BY 4.0

## 質疑応答

質問はこのリポジトリの Issue で受け付けます → [Issues](https://github.com/furuhashilab/2026gsc_RitoYamasaki/issues)
