#!/usr/bin/env python3
"""
run_single_step.py — FP-Nav 最小1ステップ推論（Habitat 非依存 / Apple Silicon 対応）

状態: ★未実行・未検証★
  このスクリプトは 16GB の調査用 Mac では実行していない（モデル未ロード）。
  研究室の 32GB+ Mac で実モデルをロードして初めて「動作確認済み」と言える。

目的:
  著者の推論前処理（fp_nav_agent.py の process_inputs_navid / preprocess_qwen_2_visual /
  process_video_frames / extract_result）を忠実に再現しつつ、Habitat とシミュレータ無しで
  「(RGB|間取り図) フレーム列 + 指示文 → モデルの生テキスト行動」を1回だけ実行する。

著者実装との対応（GitHub Chenkehan21/FloorPlan-VLN @ eac1989137f46fce495276a6f85ce69a63e5e117）:
  - プロンプト:            fp_nav_agent.py:180
  - chat template/system: fp_nav_agent.py:78,81
  - 視覚トークン展開:      fp_nav_agent.py:93-122
  - フレームサンプリング:  fp_nav_agent.py:151-166（min1 / max6）
  - 画素前処理:            fp_nav_agent.py:133-149（max_pixels=352800 / min_pixels=200704）
  - 生成パラメータ:        fp_nav_agent.py:198（do_sample=False, max_new_tokens=512, use_cache=True）
  - 行動パース:            fp_nav_agent.py:208-231

Mac 向けに変更した点（詳細は FP_NAV_INFERENCE_SPEC.md §6）:
  - attn_implementation: "flash_attention_2"(CUDA専用) → "sdpa"
  - device:             device_map="auto" → "mps" / "cpu"（引数で選択）
  これらは「同じモデルの実装/計算場所の差」であり、量子化のような別モデル化ではない。

使い方:
  python run_single_step.py --model-path <FP-Navモデルのパス> \
      --video episode.mp4 --instruction "Go from the living room to the kitchen and stop."
  # または
  python run_single_step.py --model-path <...> --frames f0.png f1.png --instruction "..."

入力フレームの要件:
  各フレームは幅 896 = 448(左:RGB) + 448(右:間取り図) の RGB 画像であること。
  配布の学習用 .mp4 は既にこの連結形式。RGBのみの動画を使う場合は、右に間取り図(448x448)を
  連結してから渡すこと（著者の cv2.hconcat([rgb, floorplan]) と同じ順序: 左RGB・右地図）。
"""
import os
import re
import copy
import argparse
from typing import List, Sequence

import cv2
import numpy as np
import torch
from transformers.feature_extraction_utils import BatchFeature
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

EXPECTED_WIDTH = 448 * 2  # 896。著者の assert（fp_nav_agent.py:347）と一致


# ---- 著者 preprocess_qwen_2_visual の再現（fp_nav_agent.py:71-131）----
def preprocess_qwen_2_visual(content: str, tokenizer, grid_thw_video: List = None):
    system_message = "You are a helpful assistant."
    tokenizer = copy.deepcopy(tokenizer)
    tokenizer.chat_template = (
        "{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' "
        "+ message['content'] + '<|im_end|>' + '\n'}}{% endfor %}"
        "{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"
    )
    input_ids = tokenizer.apply_chat_template(
        [{"role": "system", "content": system_message}]
    )
    visual_idx = 0
    if "<video>" in content:
        parts = content.split("<video>")
        new_parts = []
        for i in range(len(parts) - 1):
            new_parts.append(parts[i])
            new_parts.append(
                "<|vision_start|>" + "<|video_pad|>" * grid_thw_video[visual_idx] + "<|vision_end|>"
            )
            visual_idx += 1
        new_parts.append(parts[-1])
        content = "".join(new_parts)
    input_ids += tokenizer.apply_chat_template([{"role": "user", "content": content}])
    return {"input_ids": torch.tensor([input_ids], dtype=torch.long)}


# ---- 著者 process_video_frames の再現（fp_nav_agent.py:133-149）----
def process_video_frames(video, frame_idx, video_length, processor):
    image_processor = copy.deepcopy(processor.image_processor)
    image_processor.max_pixels = 352800
    image_processor.min_pixels = 200704
    image_processor.size["longest_edge"] = image_processor.max_pixels
    image_processor.size["shortest_edge"] = image_processor.min_pixels
    fps = len(frame_idx) / video_length
    video_processed = image_processor.preprocess(images=None, videos=video, return_tensors="pt")
    video_tensor = video_processed["pixel_values_videos"]
    grid_thw = video_processed["video_grid_thw"][0]
    second_per_grid_ts = [image_processor.temporal_patch_size / fps] * len(grid_thw)
    return video_tensor, grid_thw, second_per_grid_ts


# ---- 著者 process_inputs_navid の再現（fp_nav_agent.py:151-192）----
def process_inputs_navid(nav_list, instruction, processor):
    total_frames = len(nav_list)
    avg_fps = 1
    video_length = total_frames / avg_fps
    interval = 1
    num_frames_to_sample = round(video_length / interval)
    target_frames = min(max(num_frames_to_sample, 1), 6)  # min1 / max6
    frame_idx = np.unique(np.linspace(0, total_frames - 1, target_frames, dtype=int))
    video = [nav_list[i] for i in frame_idx]

    video, video_grid_thw, second_per_grid_ts = process_video_frames(
        video, frame_idx, video_length, processor
    )
    video = [video]
    vg = copy.deepcopy(video_grid_thw)
    if not isinstance(video_grid_thw, Sequence):
        vg = [vg]
        video_grid_thw = [video_grid_thw]
    merged = [m.prod() // processor.image_processor.merge_size ** 2 for m in vg]

    content = (
        f"<video>\nImagine you are a robot programmed for navigation tasks. "
        f"You have been given a navigation video and your assigned task is: {instruction}. "
        f"Decide your next action, which could involve turning left or right by a specific "
        f"degree or moving forward a certain distance or stop."
    )
    inputs = preprocess_qwen_2_visual(content, processor.tokenizer, grid_thw_video=merged)
    inputs["attention_mask"] = torch.ones_like(inputs["input_ids"])
    inputs["pixel_values_videos"] = torch.cat(video, dim=0)
    inputs["video_grid_thw"] = torch.cat([thw.unsqueeze(0) for thw in video_grid_thw], dim=0)
    inputs["second_per_grid_ts"] = second_per_grid_ts
    return inputs


# ---- 著者 extract_result の再現（fp_nav_agent.py:208-231）----
def extract_result(output: str):
    # 0:stop 1:forward 2:left 3:right
    if "stop" in output:
        return 0, None
    for key, idx in (("forward", 1), ("left", 2), ("right", 3)):
        if key in output:
            m = re.search(r"-?\d+", output)
            return (idx, float(m.group())) if m else (None, None)
    return None, None


def load_frames_from_video(path: str) -> List[np.ndarray]:
    """opencv で mp4 を読み、RGB フレームの list を返す（decord 不使用）。"""
    cap = cv2.VideoCapture(path)
    frames = []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))  # 著者 nav_list は RGB
    cap.release()
    if not frames:
        raise RuntimeError(f"no frames read from {path}")
    return frames


def load_frames_from_images(paths: List[str]) -> List[np.ndarray]:
    frames = []
    for p in paths:
        bgr = cv2.imread(p)
        if bgr is None:
            raise RuntimeError(f"cannot read image: {p}")
        frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return frames


def main():
    ap = argparse.ArgumentParser(description="FP-Nav minimal single-step inference (Habitat-free, mac)")
    ap.add_argument("--model-path", required=True, help="微調整済み FP-Nav モデルのパス（素のQwenではない）")
    ap.add_argument("--instruction", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--video", help="896幅の (RGB|地図) 連結動画 mp4")
    g.add_argument("--frames", nargs="+", help="896幅の連結フレーム画像（複数可, 最大6枚使用）")
    ap.add_argument("--device", default=None, choices=["mps", "cpu", "cuda"],
                    help="未指定なら mps→cpu の順に自動選択")
    ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float16", "float32"],
                    help="MPSのbf16が不安定なら float16 を試す（別精度＝数値影響あり、要注記）")
    args = ap.parse_args()

    device = args.device or ("mps" if torch.backends.mps.is_available() else "cpu")
    dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[args.dtype]
    print(f"[info] device={device} dtype={args.dtype}")

    frames = load_frames_from_video(args.video) if args.video else load_frames_from_images(args.frames)
    for i, f in enumerate(frames):
        if f.shape[1] != EXPECTED_WIDTH:
            raise AssertionError(
                f"frame {i} width={f.shape[1]} (expected {EXPECTED_WIDTH}=448*2, 左RGB|右地図)。"
                "RGBのみの入力なら右に間取り図(448x448)を連結してから渡すこと。"
            )
    print(f"[info] {len(frames)} frames loaded (最大6枚をサンプル)")

    print("[info] loading model (flash-attn→sdpa, device指定). 16.6GB・初回は時間がかかる…")
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model_path, torch_dtype=dtype, attn_implementation="sdpa",
    ).to(device)
    processor = AutoProcessor.from_pretrained(args.model_path)
    processor.tokenizer.padding_side = "left"

    inputs = process_inputs_navid(frames, args.instruction, processor)
    inputs = BatchFeature(inputs).to(device)

    with torch.no_grad():
        gen = model.generate(**inputs, do_sample=False, use_cache=True, max_new_tokens=512)
    trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, gen)]
    text = processor.batch_decode(trimmed, skip_special_tokens=True,
                                  clean_up_tokenization_spaces=False)[0].strip()

    action_index, num = extract_result(text)
    print("\n================ RESULT ================")
    print(f"instruction : {args.instruction}")
    print(f"raw output  : {text!r}")
    print(f"parsed      : action_index={action_index}  magnitude={num}")
    print("  (0:stop 1:forward 2:left 3:right)")
    print("========================================")
    print("[note] 生出力テキスト(raw output)が VLM の『判断』の一次情報。")


if __name__ == "__main__":
    main()
