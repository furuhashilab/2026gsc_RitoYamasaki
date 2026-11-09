# FP-Nav 再現チェックリスト（研究室 32GB Mac）

> 使い方: 上から順に実施し、各段階の「成功条件」を満たしてから次へ。満たせなければ「失敗条件/対処」を記録。
> 原則: **著者の推論（素の地図付き入力）を再現できるまで、地図改変実験には進まない。**
> 「動作確認済み」と書けるのは**実際にモデルをロードして出力を得た段階のみ**。

---

## 段階0: 計画固定
- [ ] 対象コミット `eac1989137f46fce495276a6f85ce69a63e5e117` をチェックアウトした
- [ ] 使用モデルは **微調整済み FP-Nav**（`fp-nav-vision-r2r-rxr-lr-4e-5-videoframe6`）で、素のQwenでないと確認した
- **成功条件**: repo と対象コミットが手元にある / **失敗条件**: cloneできない（ネットワーク・LFS設定を確認）

## 段階1: 環境
- [ ] RAM ≥ 32GB / arm64 / `~` 空き ≥ 40GB を確認（`LAB_MAC_SETUP.md §1`）
- [ ] `torch.backends.mps.is_available()` が True
- [ ] `transformers==4.51.3`, `accelerate`, `opencv-python`, `numpy`, `pillow`, `scipy`, `imageio` を導入
- **成功条件**: 上記すべて真 / **失敗条件**: RAM<32GB（非量子化困難）、mps False（CPUのみ=非常に遅い）

## 段階2: モデル取得
- [ ] `huggingface-cli download keeehan/FloorPlan-VLN --include "fp-nav-...videoframe6/*"` 完了（16.6GB）
- [ ] 取得先 `config.json` に `model_type: qwen2_5_vl` を確認
- [ ] モデルの **revision / commit** を記録した
- **成功条件**: 16.6GB 揃い config 確認 / **失敗条件**: DL中断（`HF_HUB_ENABLE_HF_TRANSFER=1` で再試行）

## 段階3: mac用改変
- [ ] `run_single_step.py` が `attn_implementation="sdpa"` かつ device=mps/cpu でロードする（flash-attnを使わない）
- [ ] flash-attn / decord / habitat を**インストールしていない**
- **成功条件**: モデルが MPS/CPU 上にロードできた（`.to(device)` 成功）/ **失敗条件**: `No module flash_attn`→sdpaへ、`MPS bf16`エラー→float16/cpu

## 段階4: 最小入力の用意（Habitat不要）
- [ ] 入力に使う (RGB|地図) 896幅フレーム列を用意（配布 `.mp4` 1本、または自作画像列）
- [ ] 指示文（instruction）を1つ用意（学習JSONの例文などを流用可）
- **成功条件**: 896×448 の frame が1枚以上ある / **失敗条件**: `assert frame.shape[1]==448*2` で落ちる→連結形状を修正

## 段階5: 1ステップ推論（最重要）
- [ ] `run_single_step.py` を実行し、**モデルの生テキスト**が得られた
- [ ] `extract_result` の `(action_index, num)` が妥当（stop/forward/left/right のいずれか）
- [ ] 生テキストと解析結果を**ファイルに保存**した
- **成功条件**: 例 `move forward 50` のような合理的な行動文が出る（＝「このモデルは地図付き入力で行動を判断する」の実証）
- **失敗条件**: 空出力/無関係文 → プロンプト・frame構成・frame数・画素上下限を `FP_NAV_INFERENCE_SPEC.md §5` に厳密一致させる

## 段階6: 地図利用の独立確認（任意だが推奨）
- [ ] 同一RGB・同一指示で「地図を全マスク（右半分を塗り潰す）」vs「正規地図」の生出力を比較
- [ ] 出力が**変化する**ことを確認（＝モデルが地図を実際に参照している傍証。論文の+60%主張の手元確認）
- **成功条件**: マスク有無で判断が変わる / **失敗条件**: 全く変わらない→地図が効いていない可能性。入力形状・学習時頑健化の影響を精査

## 段階7（任意・mac範囲外）: Habitatフル評価
- [ ] 研究室/学内の **Linux+NVIDIA** 機で Habitat-sim/lab v0.1.7 を構築
- [ ] 小規模 split で `eval_fp_nav.sh`→`analyze_results.py`
- **著者再現の判断基準**: 論文の val_unseen 成功率レンジに概ね入る（厳密一致は環境差で困難。**レンジ/順位の一致**で判断）

---

## 再現性のために保存すべき情報（各実験）
- repo コミット `eac1989...` / モデル revision / `transformers` バージョン
- 復号設定（`do_sample=False`＝乱数なし / `max_new_tokens=512`）
- device・dtype（mps/bf16 等。変更したら理由と影響）
- 入力フレーム（画像そのもの or mp4パス＋サンプルframe_idx）・指示文
- **モデルの生出力テキスト**（一次情報）＋ `(action_index, num)`
- 使った地図（正規 / マスク / 差替え。差替え時は差替え手順）

## 「著者の評価を再現できた」と判断する条件
- 段階5で**合理的な行動文**が決定的（greedy）に得られる、かつ
- 段階6で**地図の有無が判断に影響**する、かつ
- （可能なら）段階7で成功率が論文レンジに整合する。
- 上記を満たして初めて「著者推論を再現」とみなし、**その後に**地図改変（誤地図）実験へ進む。

## やらないこと（今回のスコープ）
- 大容量DLをこの16GB調査機で行う（研究室Macで実施）
- 実モデル未ロード段階で「動作確認済み」と書く
- 量子化を前提にする（比較可能性を損なうため）
- 実機ロボットの安全性主張
