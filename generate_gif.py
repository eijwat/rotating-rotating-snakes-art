#!/usr/bin/env python3
"""
蛇の回転錯視 GIFアニメーション生成スクリプト

SNSデモ用のGIFおよびMP4を生成する。
ffmpegが必要（MP4生成およびGIF最適化に使用）。

使い方:
  python generate_gif.py

出力:
  rotating_snakes_art.mp4      - MP4版（高画質・小サイズ、SNS投稿向け）
  rotating_snakes_sns.gif      - GIF版（フル、3サイクル）
  rotating_snakes_sns_short.gif - GIF版（ショート、1サイクル）
"""

from PIL import Image, ImageDraw
import subprocess
import os
import random
import shutil

# ═══════════════════════════════════════
# 設定
# ═══════════════════════════════════════
IMAGE_PATH = "KitaokaPosi_640.jpg"
DISK_RADIUS = 78
DISK_CENTERS = [
    (160, 160), (320, 160), (480, 160),
    (160, 320), (320, 320), (480, 320),
]
ROTATION_SECS = 20.0    # 1回転の秒数
PAUSE_SECS = 5.0        # 静止時間
MP4_FPS = 15             # MP4のFPS
GIF_FPS = 5              # GIFのFPS
GIF_SCALE = 480          # GIF横幅px
NUM_CYCLES = 3           # サイクル数
DISK_PLAN = [4, 1, 3]   # 回転するディスクの順番（0-5）
SEED = 42                # ランダムシード（Noneでランダム）


def extract_disk(pil_img, center, radius):
    cx, cy = center
    size = radius * 2
    crop = pil_img.crop((cx - radius, cy - radius,
                         cx + radius, cy + radius)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    crop.putalpha(mask)
    return crop


def main():
    print("蛇の回転錯視アート - GIF/MP4生成")
    print("=" * 50)

    img = Image.open(IMAGE_PATH).convert("RGBA")
    img_rgb = img.convert("RGB")
    disk_images = [extract_disk(img, c, DISK_RADIUS) for c in DISK_CENTERS]

    if SEED is not None:
        random.seed(SEED)

    plan = DISK_PLAN[:NUM_CYCLES]

    # === MP4生成 ===
    print("\n[1/3] MP4フレーム生成中...")
    frames_dir = "_tmp_frames"
    os.makedirs(frames_dir, exist_ok=True)

    frame_num = 0
    for cycle, disk_idx in enumerate(plan):
        cx, cy = DISK_CENTERS[disk_idx]
        n_rot = int(ROTATION_SECS * MP4_FPS)
        print(f"  サイクル {cycle}: ディスク {disk_idx} ({cx},{cy})")

        for f in range(n_rot):
            angle = (f / n_rot) * 360.0
            frame = img_rgb.copy()
            rotated = disk_images[disk_idx].rotate(
                -angle, resample=Image.BICUBIC, expand=False
            )
            frame.paste(rotated,
                        (cx - DISK_RADIUS, cy - DISK_RADIUS), rotated)
            frame.save(f"{frames_dir}/f_{frame_num:05d}.jpg", quality=95)
            frame_num += 1

        n_pause = int(PAUSE_SECS * MP4_FPS)
        for f in range(n_pause):
            img_rgb.save(f"{frames_dir}/f_{frame_num:05d}.jpg", quality=95)
            frame_num += 1

    total_secs = frame_num / MP4_FPS
    print(f"  合計: {frame_num}フレーム ({total_secs:.0f}秒)")

    print("\n[2/3] MP4エンコード中...")
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(MP4_FPS),
        "-i", f"{frames_dir}/f_%05d.jpg",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "23", "-preset", "medium",
        "rotating_snakes_art.mp4"
    ], capture_output=True)
    mp4_mb = os.path.getsize("rotating_snakes_art.mp4") / 1024 / 1024
    print(f"  → rotating_snakes_art.mp4 ({mp4_mb:.1f} MB)")

    print("\n[3/3] GIF生成中...")
    # フル版GIF
    subprocess.run([
        "ffmpeg", "-y", "-i", "rotating_snakes_art.mp4",
        "-vf", f"fps={GIF_FPS},scale={GIF_SCALE}:-1:flags=lanczos,"
               "split[s0][s1];[s0]palettegen=max_colors=128:stats_mode=diff[p];"
               "[s1][p]paletteuse=dither=bayer:bayer_scale=3",
        "rotating_snakes_sns.gif"
    ], capture_output=True)
    gif_mb = os.path.getsize("rotating_snakes_sns.gif") / 1024 / 1024
    print(f"  → rotating_snakes_sns.gif ({gif_mb:.1f} MB)")

    # ショート版GIF（1サイクル）
    t_short = ROTATION_SECS + PAUSE_SECS + 1
    subprocess.run([
        "ffmpeg", "-y", "-i", "rotating_snakes_art.mp4",
        "-t", str(t_short),
        "-vf", f"fps={GIF_FPS},scale={GIF_SCALE}:-1:flags=lanczos,"
               "split[s0][s1];[s0]palettegen=max_colors=96:stats_mode=diff[p];"
               "[s1][p]paletteuse=dither=bayer:bayer_scale=4",
        "rotating_snakes_sns_short.gif"
    ], capture_output=True)
    short_mb = os.path.getsize("rotating_snakes_sns_short.gif") / 1024 / 1024
    print(f"  → rotating_snakes_sns_short.gif ({short_mb:.1f} MB)")

    # クリーンアップ
    shutil.rmtree(frames_dir)

    print("\n完了！")
    print(f"  MP4:        rotating_snakes_art.mp4       ({mp4_mb:.1f} MB)")
    print(f"  GIF（フル）: rotating_snakes_sns.gif       ({gif_mb:.1f} MB)")
    print(f"  GIF（短）:   rotating_snakes_sns_short.gif ({short_mb:.1f} MB)")


if __name__ == "__main__":
    main()
