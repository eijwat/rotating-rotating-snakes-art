#!/usr/bin/env python3
"""
"Which One Is Real?" — 蛇の回転錯視 × 現代アート
MP4 / GIF 生成スクリプト

北岡明佳教授の蛇の回転錯視画像から、
1個のディスクだけが本当に回転するアニメーションを生成する。

必要環境:
  pip install Pillow
  ffmpeg（パスが通っていること）

使い方:
  python generate_animation.py

出力（カレントディレクトリ）:
  rotating_snakes.mp4        — 展示・SNS投稿用（高画質・小サイズ）
  rotating_snakes.gif        — GIF版（Twitter/X 自動再生対応）
"""

from PIL import Image, ImageDraw
import subprocess
import sys
import os
import random

# ═══════════════════════════════════════════════════════
# 設定（展示環境に合わせて変更してください）
# ═══════════════════════════════════════════════════════

IMAGE_PATH = "KitaokaPosi_640.jpg"   # 元画像パス

# アニメーション
ROTATION_SPEED = 20.0    # 1回転にかかる秒数（大きいほどゆっくり＝判別困難）
ROTATION_SECS = 20.0     # ディスクを回転させる時間（秒）
PAUSE_SECS = 5.0         # 回転後の静止時間（秒）
NUM_CYCLES = 3           # サイクル数（何回ディスクが入れ替わるか）
DISK_PLAN = None         # 回転するディスクの順番（0-5）。Noneで毎回ランダム選択
                         # 例: [4, 1, 3] で固定順、None でランダム
ROTATION_DIRECTION = "random"  # "cw"=時計回り / "ccw"=反時計回り / "random"=毎回ランダム
SEED = None              # ランダムシード（整数で固定、Noneで毎回異なる結果）

# 出力品質
MP4_FPS = 15             # MP4 のフレームレート
GIF_FPS = 5              # GIF のフレームレート
GIF_WIDTH = 480          # GIF の横幅（px）
GIF_MAX_COLORS = 128     # GIF のパレット色数

# ディスク定義（変更不要）
DISK_RADIUS = 78
DISK_CENTERS = [
    (160, 160), (320, 160), (480, 160),   # 上段 [0] [1] [2]
    (160, 320), (320, 320), (480, 320),   # 下段 [3] [4] [5]
]

# ═══════════════════════════════════════════════════════


def extract_disk(pil_img, center, radius):
    """円形マスク付きでディスクを切り出す"""
    cx, cy = center
    size = radius * 2
    crop = pil_img.crop((cx - radius, cy - radius,
                         cx + radius, cy + radius)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    crop.putalpha(mask)
    return crop


def pick_direction():
    """回転方向の符号を返す（+1=時計回り, -1=反時計回り）"""
    if ROTATION_DIRECTION == "cw":
        return 1
    elif ROTATION_DIRECTION == "ccw":
        return -1
    else:
        return random.choice([1, -1])


def check_ffmpeg():
    """ffmpeg の存在確認"""
    try:
        subprocess.run(["ffmpeg", "-version"],
                       capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def generate_mp4(img_rgb, disk_images, plan, out_path):
    """フレームをパイプ経由で ffmpeg に送り MP4 を生成"""
    w, h = img_rgb.size
    n_rot = int(ROTATION_SECS * MP4_FPS)
    n_pause = int(PAUSE_SECS * MP4_FPS)
    total_frames = len(plan) * (n_rot + n_pause)

    proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(MP4_FPS),
        "-i", "pipe:0",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "medium",
        "-movflags", "+faststart",
        out_path
    ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    frame_count = 0
    for cycle, disk_idx in enumerate(plan):
        cx, cy = DISK_CENTERS[disk_idx]
        direction = pick_direction()
        label = "↻" if direction == 1 else "↺"
        print(f"  サイクル {cycle}: ディスク {disk_idx} ({cx},{cy}) {label}")

        # 回転フレーム
        for f in range(n_rot):
            t = f / MP4_FPS                          # 経過秒数
            angle = direction * (t / ROTATION_SPEED) * 360.0  # ROTATION_SPEED秒で1回転
            frame = img_rgb.copy()
            rotated = disk_images[disk_idx].rotate(
                -angle, resample=Image.BICUBIC, expand=False)
            frame.paste(rotated,
                        (cx - DISK_RADIUS, cy - DISK_RADIUS), rotated)
            proc.stdin.write(frame.tobytes())
            frame_count += 1

            if frame_count % 100 == 0:
                pct = frame_count / total_frames * 100
                print(f"\r    進捗: {pct:.0f}%", end="", flush=True)

        # 静止フレーム
        static_bytes = img_rgb.tobytes()
        for f in range(n_pause):
            proc.stdin.write(static_bytes)
            frame_count += 1

    print(f"\r    進捗: 100%   ")

    proc.stdin.close()
    proc.wait()

    if proc.returncode != 0:
        err = proc.stderr.read().decode()
        print(f"  [エラー] ffmpeg: {err[-300:]}")
        return False
    return True


def generate_gif(mp4_path, out_path):
    """MP4 から ffmpeg のパレット最適化で GIF を生成"""
    vf = (f"fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,"
          f"split[s0][s1];"
          f"[s0]palettegen=max_colors={GIF_MAX_COLORS}:stats_mode=diff[p];"
          f"[s1][p]paletteuse=dither=bayer:bayer_scale=3")

    result = subprocess.run(
        ["ffmpeg", "-y", "-i", mp4_path, "-vf", vf, out_path],
        capture_output=True)

    return result.returncode == 0


def main():
    print()
    print("  ╔═══════════════════════════════════════════╗")
    print("  ║  Which One Is Real?                       ║")
    print("  ║  蛇の回転錯視 × 現代アート                ║")
    print("  ║  MP4 / GIF ジェネレーター                  ║")
    print("  ╚═══════════════════════════════════════════╝")
    print()

    # 前提チェック
    if not os.path.exists(IMAGE_PATH):
        print(f"  [エラー] 画像が見つかりません: {IMAGE_PATH}")
        print(f"  → KitaokaPosi_640.jpg をこのスクリプトと同じフォルダに配置してください")
        sys.exit(1)

    if not check_ffmpeg():
        print("  [エラー] ffmpeg が見つかりません")
        print("  → ffmpeg をインストールしてパスを通してください")
        print("     macOS:   brew install ffmpeg")
        print("     Ubuntu:  sudo apt install ffmpeg")
        print("     Windows: https://ffmpeg.org/download.html")
        sys.exit(1)

    # 初期化
    if SEED is not None:
        random.seed(SEED)

    img = Image.open(IMAGE_PATH).convert("RGBA")
    img_rgb = img.convert("RGB")
    disk_images = [extract_disk(img, c, DISK_RADIUS) for c in DISK_CENTERS]

    # ディスク順を決定
    if DISK_PLAN is not None:
        plan = DISK_PLAN[:NUM_CYCLES]
    else:
        plan = []
        for _ in range(NUM_CYCLES):
            idx = random.randint(0, 5)
            while plan and idx == plan[-1]:
                idx = random.randint(0, 5)
            plan.append(idx)

    duration = NUM_CYCLES * (ROTATION_SECS + PAUSE_SECS)
    print(f"  設定: {NUM_CYCLES}サイクル, {ROTATION_SPEED}秒/回転速度, "
          f"{ROTATION_SECS}秒/回転表示, {PAUSE_SECS}秒/休止 → 合計 {duration:.0f}秒")
    print(f"  回転方向: {ROTATION_DIRECTION}")
    print()

    # === MP4 ===
    mp4_path = "rotating_snakes.mp4"
    print(f"[1/2] MP4 生成中 ({MP4_FPS}fps, {img_rgb.size[0]}x{img_rgb.size[1]})...")
    if generate_mp4(img_rgb, disk_images, plan, mp4_path):
        mp4_mb = os.path.getsize(mp4_path) / 1024 / 1024
        print(f"  → {mp4_path} ({mp4_mb:.1f} MB)")
    else:
        print("  → MP4 生成に失敗しました")
        sys.exit(1)

    # === GIF ===
    gif_path = "rotating_snakes.gif"
    print(f"\n[2/2] GIF 生成中 ({GIF_FPS}fps, {GIF_WIDTH}px幅)...")
    if generate_gif(mp4_path, gif_path):
        gif_mb = os.path.getsize(gif_path) / 1024 / 1024
        print(f"  → {gif_path} ({gif_mb:.1f} MB)")
    else:
        print("  → GIF 生成に失敗しました")

    # === 完了 ===
    print()
    print("  ────────────────────────────────────")
    print(f"  ✓ {mp4_path:<30s} ({mp4_mb:.1f} MB)  展示・SNS投稿用")
    print(f"  ✓ {gif_path:<30s} ({gif_mb:.1f} MB)  Twitter/X・プレビュー用")
    print("  ────────────────────────────────────")
    print()


if __name__ == "__main__":
    main()
