# 研究室Mac（32GB+ Apple Silicon）セットアップ手順 — FP-Nav

> 対象コミット `eac1989137f46fce495276a6f85ce69a63e5e117` / 確認日 2026-11-05
> **本手順は未検証（見込み）**。研究室Macで実行し、成否を `REPRODUCTION_CHECKLIST.md` に記録すること。
> 目的は **1ステップ推論を Habitat 無しで動かす**こと（フルHabitat評価はmac非対応、§5参照）。

---

## 0. 全体方針

- 動かすのは **微調整済み FP-Nav モデル（16.6GB, `qwen2_5_vl`）**。**素の `Qwen/Qwen2.5-VL-7B-Instruct` とは別物**。混同しないこと。
- **推論経路のみ**を立てる。学習（4×H100想定）とHabitatフル評価（CUDA/Linux想定）は対象外。
- `flash_attention_2` と `device_map="auto"` は CUDA 前提なので **mac向けに改変**する（§4）。
- `decord`/`torchcodec` は**学習データ読込専用**。推論では使わず `opencv`/`imageio` で代替しインストール不要。

---

## 1. 環境確認（最初に実行）

```bash
# チップ・メモリ・macOS
sysctl -n machdep.cpu.brand_string ; uname -m
echo "RAM(GB): $(($(sysctl -n hw.memsize)/1024/1024/1024))"
sw_vers
# ディスク空き（モデル16.6GB + 作業領域で最低 40GB 以上を推奨）
df -h ~
# ツール
python3 --version   # 3.12 系を推奨（3.14 だと一部wheel未提供の恐れ）
git --version
git lfs version || echo "git-lfs 未導入 → brew install git-lfs"
```

**成功条件**: RAM ≥ 32GB、`~` の空き ≥ 40GB、arm64。
**失敗時**: 空き不足ならモデル取得前に整理。RAM不足なら非量子化は困難。

---

## 2. リポジトリ取得（コードのみ・LFS blob除外）

```bash
mkdir -p ~/research/fp-nav-study/work && cd ~/research/fp-nav-study/work
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/Chenkehan21/FloorPlan-VLN.git
cd FloorPlan-VLN
git checkout eac1989137f46fce495276a6f85ce69a63e5e117   # 調査時点に固定（再現性）
```

- コードのみで約28MB。モデル重みはこのcloneには含まれない（別途§5）。

---

## 3. Python環境（推論専用・最小）

```bash
# conda 推奨（著者は 3.12.7）
conda create -n fpnav python=3.12.7 -y
conda activate fpnav

# PyTorch（Apple Silicon = MPS。CUDA版は入れない）
pip install torch torchvision          # arm64 既定wheelでMPS対応
python -c "import torch; print('mps:', torch.backends.mps.is_available())"

# 著者指定＋推論に必要な最小依存
pip install "transformers==4.51.3" accelerate
pip install opencv-python numpy pillow scipy imageio tqdm
# qwen-vl-utils（同梱版 or PyPI）
pip install -e ~/research/fp-nav-study/work/FloorPlan-VLN/qwen-vl-utils  # 失敗時: pip install qwen-vl-utils
```

**入れないもの**（推論には不要・macで問題になりがち）:
- `flash-attn`（CUDA専用。ビルド不可）
- `decord` / `torchcodec`（学習データ読込専用。arm64で不安定）
- `habitat-sim` / `habitat-lab`（§「Habitatについて」参照）

**注意**: `transformers==4.51.3` は Qwen2.5-VL の該当バージョン。**勝手に上げない**（入力テンソルの扱いが変わると著者の前処理と不整合になり得る）。

---

## 4. モデルを mac で読むためのコード改変（必須）

`fp_nav_agent.py:36-42` は CUDA 前提。推論スクリプト側で以下へ置換する（**元ファイルは変更せず** `run_single_step.py` 側で対応済み。手で直す場合の指針）:

```python
# 変更前（fp_nav_agent.py:36-42）
self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    model_path, torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",   # ← CUDA専用
    device_map="auto",                          # ← CUDA前提
)

# 変更後（mac / MPS）
device = "mps" if torch.backends.mps.is_available() else "cpu"
self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,       # MPSのbf16で不安定なら torch.float16 を試す（数値影響は§参照）
    attn_implementation="sdpa",        # flash-attn の代替。数学的には同等（下記）
).to(device)
```

**数値への影響（卒論で説明すべき点）**
- `flash_attention_2` → `sdpa`: どちらも同じ scaled-dot-product attention の実装違い。**数学的に同じ計算**で、差は浮動小数の丸め程度（greedy復号なら出力はほぼ不変の見込み、要確認）。
- `bfloat16` → `float16`: 代替した場合は**別の数値精度**。桁あふれ/アンダーフローの挙動が変わり得るため、使うなら明記し bf16 と出力比較する。
- MPS カーネルは CUDA と実装が異なるため**微小な数値差**が出る可能性。greedy なので通常は同一トークン列になる見込みだが、**要検証**。
- → これらは「同じモデルの実装/精度差」であり、**量子化（別モデル化）とは区別**する。

---

## 5. 微調整済みモデルの取得（研究室Macで実行。**この16GB調査機では取得しない**）

```bash
pip install -U "huggingface_hub[cli]"
# 微調整済み FP-Nav（16.6GB）。サブフォルダのみ取得
huggingface-cli download keeehan/FloorPlan-VLN \
  --include "fp-nav-vision-r2r-rxr-lr-4e-5-videoframe6/*" \
  --local-dir ~/research/fp-nav-study/models/FP-Nav
# → MODEL_PATH = ~/research/fp-nav-study/models/FP-Nav/fp-nav-vision-r2r-rxr-lr-4e-5-videoframe6
```

- **これが研究対象の本体**。素のQwenではない。`config.json` に `model_type: qwen2_5_vl` を確認。
- 容量16.6GB・DL時間に注意。失敗時は `HF_HUB_ENABLE_HF_TRANSFER=1` で高速化。

---

## 6. データの種類と取得先（混同しないこと）

| 種類 | 用途 | 取得先 | 1ステップ推論に必要か |
|---|---|---|---|
| 間取りJSON `mp3d_floorplan/` | 地図のソース（再描画用） | HF `keeehan/FloorPlan-VLN/mp3d_floorplan` (280ファイル) | 地図を自前再描画するなら要 |
| 微調整JSON `floorplan_vln_*_finetune.json` | **学習**用QA（指示↔正解行動） | 同上(423MB+160MB) | 指示文の例取得に有用（任意） |
| 学習動画 `.mp4` tar | **学習**用 (RGB|地図)連結動画 | 別repo `keeehan/FloorPlan-VLN-R2R`/`-RxR` | 動画1本を入力サンプルに使うなら要 |
| 評価 `val_*_(gt).json.gz` | **Habitat評価**用エピソード/GT | HF `keeehan/FloorPlan-VLN/FloorPlan-VLN-R2R` ほか | Habitatフル評価時のみ |
| MP3Dシーン `.glb` (~15GB) | **Habitatシミュレータ**用 | 公式MP3D（要規約同意, `download_mp.py`/py2.7） | Habitatフル評価時のみ |

- **学習用(mp4)** と **評価用(json.gz)** を混同しない。1ステップ推論は **(RGB|地図)画像列＋指示文** さえあれば動く。
- 最小の動作確認には「学習動画 `.mp4` を1本」取得して入力に使うのが最も手軽（Habitat不要）。

---

## 7. 1ステップ推論の実行

同梱の `run_single_step.py`（Habitat非依存、sdpa/MPS対応）を使う。

```bash
cd ~/research/fp-nav-study/work/FloorPlan-VLN
cp ~/research/fp-nav-study/run_single_step.py .      # repo直下に置くと同梱モジュールをimportしやすい

export MODEL_PATH=~/research/fp-nav-study/models/FP-Nav/fp-nav-vision-r2r-rxr-lr-4e-5-videoframe6

# (A) 配布エピソード動画を入力にする場合（896幅の連結動画 or RGBのみ動画）
python run_single_step.py --model-path "$MODEL_PATH" \
  --video /path/to/episode.mp4 \
  --instruction "Go from the living room to the kitchen and stop."

# (B) 既に用意した896x448の連結フレーム画像（左=RGB,右=地図）を使う場合
python run_single_step.py --model-path "$MODEL_PATH" \
  --frames frame0.png frame1.png frame2.png \
  --instruction "..."
```

**期待出力**: モデルの生テキスト（例 `turn left 30 degrees` / `move forward 50` / `stop`）と、`extract_result` による解析 `(action_index, magnitude)`。

---

## 8. 想定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `No module named flash_attn` / ビルド失敗 | flash-attn は CUDA専用 | §4 の通り `attn_implementation="sdpa"` にする（`run_single_step.py` は既定でsdpa） |
| `RuntimeError: ... MPS ...` / bf16系エラー | MPS の bf16 一部未対応 | `--dtype float16`（または cpu）に切替。出力をbf16と比較し注記 |
| `AssertionError: frame.shape[1] == 448*2` | 入力が896幅でない | 入力は (RGB448 | 地図448) 連結。RGBのみ動画なら地図を右に連結してから渡す |
| メモリ不足で落ちる | 32GBでも同時負荷が高い | 他アプリ終了 / `--device cpu` / frame数を減らす（既定最大6） |
| `transformers` の引数エラー | バージョン不一致 | `transformers==4.51.3` を厳守 |
| decord のインストール失敗 | arm64で不安定 | 推論では不要。入れない（opencvで動画読込） |
| 生成が CUDA を要求 | `.cuda()`/`device_map` 残り | device を `mps`/`cpu` に統一（`run_single_step.py` で対応） |
| 出力が空/乱数行動 | `extract_result` がパース失敗 | 生テキストを確認。プロンプト文言・frame構成を著者仕様（`FP_NAV_INFERENCE_SPEC.md`）に合わせる |

---

## Habitat について（フル評価を試みる場合のみ）

- 著者は Habitat-sim/lab **v0.1.7**＋ `torch==1.10.0+cu111`＋8×3090 を使用（`README.md:148-186`）。
- これは **Apple Silicon 非対応**。mac でフル評価エピソードを回すのは事実上不可。
- フル評価が必要なら **学内/研究室の Linux+NVIDIA 機**を使う（本手順の範囲外）。
- 卒論の「地図の影響」研究は **§7 の1ステップ経路で成立**するため、まずそちらを確立する。
