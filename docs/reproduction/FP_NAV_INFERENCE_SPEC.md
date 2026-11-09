# FP-Nav 推論仕様（厳密版）

> 目的: 著者の推論を**忠実に再現**するための仕様。改変してよい点・いけない点を明示する。
> 出典: GitHub `Chenkehan21/FloorPlan-VLN` @ `eac1989137f46fce495276a6f85ce69a63e5e117`（確認日 2026-11-05）。
> すべて `fp_nav_agent.py` の `Qwen_Agent` クラス由来（特記なき行番号は同ファイル）。

---

## 1. プロンプト（逐語）

`process_inputs_navid()` が組み立てる user content（**`fp_nav_agent.py:180`**）:

```
<video>
Imagine you are a robot programmed for navigation tasks. You have been given a navigation video and your assigned task is: {instruction}. Decide your next action, which could involve turning left or right by a specific degree or moving forward a certain distance or stop.
```

- 先頭の `<video>` は後段で視覚トークンに置換されるプレースホルダ。`\n` が1つ入る。
- `{instruction}` に Habitat の指示文（`observations["instruction"]["text"]`, `:301`）を差し込む。

system メッセージ（**`:78`**）: `"You are a helpful assistant."`

**カスタム chat template**（**`:81`**。既定のQwenテンプレートを上書きしている）:

```jinja
{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}
```

視覚トークン展開（**`:93-122`**）: `<video>` を `<|vision_start|>` + `<|video_pad|>`×N + `<|vision_end|>` に置換（N = `video_grid_thw` を merge_size² で割った数）。`<image>` 用の分岐もあるが**本推論経路は `<video>` のみ使用**。

---

## 2. 入力フレームの作り方

### 2.1 1フレームの構造（デュアルビュー）
- 左 = エゴセントリック RGB `obs['rgb']`（448×448, RGB, HFOV90, 高さ1.5m / `fp-nav-r2r.yaml`）。
- 右 = 間取り図＋軌跡＋方位を描いた画像（448×448）。`FloorplanNavigator.plot_floorplan_traj()`（`floorplan_nav.py:508`）で生成。
- 連結（**`:382-383`, `:413-414`**）:
  ```python
  floorplan_nav_img = floorplan_nav_img[..., ::-1]          # BGR→RGB（cv2描画をRGBへ）
  concat_img = cv2.hconcat([obs['rgb'], floorplan_nav_img]) # → 896×448, [左RGB | 右地図]
  ```
- 不変条件: **幅は必ず 448×2 = 896**。地図は右半分 `frame[:, 448:, :]`（`:347` の assert と一致）。**左右の順序（RGBが左, 地図が右）を入れ替えない**。

### 2.2 動画化（フレームサンプリング）
`process_inputs_navid()`（**`:151-192`**）:
- `nav_list`（各ステップの concat_img を蓄積, `:300`）を入力。
- `avg_fps = 1`, `interval = 1`。
- サンプル枚数 = `min(max(round(video_length/interval), 1), 6)` → **最小1・最大6フレーム**（`:159-166`）。
- `frame_idx = np.unique(np.linspace(0, total-1, target_frames, int))` で等間隔サンプル。

### 2.3 画素前処理（`process_video_frames`, `:133-149`）
- `image_processor.max_pixels = 352800`, `min_pixels = 200704`。
- `size["longest_edge"]=max_pixels`, `size["shortest_edge"]=min_pixels`。
- `fps = len(frame_idx)/video_length`、`second_per_grid_ts = temporal_patch_size / fps`。
- 戻り: `pixel_values_videos`, `video_grid_thw`, `second_per_grid_ts`。

### 2.4 最終入力テンソル（`:181-192`）
`input_ids`（カスタムテンプレート適用後）, `attention_mask`（全1）, `pixel_values_videos`, `video_grid_thw`, `second_per_grid_ts`。`BatchFeature` 化して `model.device` へ（`:196-197`）。

---

## 3. 行動出力の形式

### 3.1 生成（`predict_inference`, `:194-206`）
```python
generated_ids = self.model.generate(**inputs, do_sample=False, use_cache=True, max_new_tokens=512)
# 入力長を除いてデコード → output_text[0].strip()
```
- **greedy 復号**（`do_sample=False`）＝温度/乱数なし。**同一入力→同一出力**（決定的）。
- 出力は**自由文テキスト**（例: `turn left 30 degrees` / `move forward 50` / `stop`）。

### 3.2 テキスト→行動（`extract_result`, `:208-231`）
- `"stop"`→ `(0, None)`
- `"forward"`→ `(1, float(最初の整数))`
- `"left"`→ `(2, float(最初の整数))`
- `"right"`→ `(3, float(最初の整数))`
- どれも無ければ `(None, None)`。数値は正規表現 `-?\d+` の最初の一致。

### 3.3 量子化（`act`, `:309-327`）
- 前進: `for _ in range(min(3, int(num/25)))` → 0.25m×N（`FORWARD_STEP_SIZE=0.25`）。
- 左旋回: `min(3, int(num/15))` → 15°×N（`TURN_ANGLE=15`）。右も同様。
- stop → action 0。
- パース失敗 or 空 → `random.randint(1,3)`（`:324`。「パイプライン補完用で基本未使用」とコメント）。
- 離散行動列は `pending_action_list` に積まれ、1ステップ1アクションずつ消費（`:293-299`）。

> **判断レベルの研究に使うべき値**: `extract_result` 前の**生テキスト `navigation`（`:302`）**と、`(action_index, num)`。量子化後の離散列は制御側の都合なので、VLMの「判断」としては生テキストを一次情報にする。

---

## 4. モデルのロードと生成パラメータ

`Qwen_Agent.__init__`（**`:36-43`**）:
```python
Qwen2_5_VLForConditionalGeneration.from_pretrained(
    model_path,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",   # CUDA専用
    device_map="auto",
)
AutoProcessor.from_pretrained(model_path)
processor.tokenizer.padding_side = 'left'
```
生成: `do_sample=False, use_cache=True, max_new_tokens=512`（`:198`）。

モデル実体（HF config.json）: `model_type=qwen2_5_vl`, `Qwen2_5_VLForConditionalGeneration`, `torch_dtype=bfloat16`, `hidden_size=3584`, 計16.6GB。**微調整済み FP-Nav**（素のQwenではない）。

---

## 5. 変更してはいけない条件（著者再現のため固定）

1. **プロンプト文言**（§1 の英文・`<video>`・`\n`）をそのまま使う。
2. **カスタム chat template と system メッセージ**（`:78,81`）。既定Qwenテンプレートに戻さない。
3. **左右連結順**（左=RGB, 右=地図）と **896×448** の形状。
4. **フレーム数の上下限（min1/max6）とサンプリング方法**（`:159-166`）。
5. **画素上下限** `max_pixels=352800 / min_pixels=200704`（`:135-136`）。
6. **greedy 復号**（`do_sample=False`）と `max_new_tokens=512`。
7. **微調整済みモデル**を使うこと（素のQwen2.5-VLは別物＝研究対象でない）。
8. `tokenizer.padding_side='left'`。

---

## 6. Mac実行のために変更が必要な条件（数値影響つき）

| 変更箇所 | 変更前 | 変更後(mac) | 数値への影響 |
|---|---|---|---|
| attention実装 `:39` | `flash_attention_2` | `"sdpa"`（または`"eager"`） | 同じSDPAの実装差。**数学的に同等**、差は丸め程度。greedyなら出力ほぼ不変の見込み（要検証） |
| device `:41` | `device_map="auto"` | `.to("mps")` / `"cpu"` | 計算場所のみ。MPSカーネル差で微小数値差の可能性（greedyで通常同一トークン、要検証） |
| dtype `:38` | `torch.bfloat16` | 原則維持。MPSで不安定なら `float16` | **float16は別精度**。範囲/丸めが変わり得るので使用時は明記しbf16と比較 |

- 上記はすべて「**同じモデルの実装・精度差**」であり、**量子化（4bit等）は別モデル化**なので比較可能性を損なう。最初から前提にしない（必要なら別実験として明示）。
- 変更の妥当性は `run_single_step.py` の生出力を、可能なら既知の正解挙動（学習動画の指示に沿う動き）と突き合わせて確認する。

---

## 7. 1ステップ推論を Habitat から切り離せる根拠

- `predict_inference(instruction, navigation_video)`（`:194`）は **frames（numpy画像のlist）と instruction 文字列のみ**に依存。Habitat の `Env` も `sim` も参照しない。
- 必要なのは「(RGB|地図) の 896幅フレーム列」と「指示文」だけ。これらは配布の **学習動画 `.mp4`**（既に連結済み）や、自前で用意した画像列から作れる。
- よって **シミュレータ無しで 1 判断を実行・記録・比較**できる（`run_single_step.py` がこの経路を実装）。
- 地図を変える実験は、右半分 `frame[:,448:,:]` を差し替えるだけで原理的に可能（ただし**著者推論の再現を確認してから**着手）。
