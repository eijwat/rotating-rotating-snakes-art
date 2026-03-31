#!/usr/bin/env python3
"""
"Which One Is Real?" - 蛇の回転錯視 × 現代アート
北岡明佳教授の蛇の回転錯視を用いたインタラクティブアート作品

錯視で全てのディスクが回転して見えるが、
実際にはひとつだけ本当に回転している。
どれが本物の回転か、あなたの目は見分けられるか？

展示会用バージョン (Python/Pygame)

使い方:
  1. KitaokaPosi_640.jpg を同じフォルダに配置
  2. python rotating_snakes_exhibition.py で実行
  3. F キーでフルスクリーン切替
  4. ESC/Q で終了

必要ライブラリ: pygame, Pillow
  pip install pygame Pillow
"""

import pygame
import sys
import random
import time
from PIL import Image, ImageDraw

# ═══════════════════════════════════════════════════
# 設定（展示環境に合わせて変更可能）
# ═══════════════════════════════════════════════════
IMAGE_PATH = "KitaokaPosi_640.jpg"
SCALE = 2               # 表示倍率（1=640x480, 2=1280x960, 3=1920x1440）
ROTATION_DURATION = 20.0 # 1回転の秒数（ゆっくりにするほど見分けにくい）
PAUSE_DURATION = 5.0     # 回転間の静止時間（秒）
DISK_RADIUS = 78         # ディスク半径（元画像px）。変更不要
FPS = 60                 # 描画FPS
BG_COLOR = (0, 0, 0)     # 背景色（フルスクリーン時の余白）
FULLSCREEN_START = False  # True にすると起動時フルスクリーン

# 中央6個のディスク中心座標（元画像px）
DISK_CENTERS = [
    (160, 160), (320, 160), (480, 160),   # 上段
    (160, 320), (320, 320), (480, 320),   # 下段
]


def extract_circular_disk(pil_img, center, radius):
    """円形にディスクを切り出し（RGBA）"""
    cx, cy = center
    size = radius * 2
    crop = pil_img.crop((cx - radius, cy - radius,
                         cx + radius, cy + radius)).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    crop.putalpha(mask)
    return crop


def pil_to_surface(pil_img):
    """PIL Image → Pygame Surface"""
    return pygame.image.fromstring(
        pil_img.tobytes(), pil_img.size, pil_img.mode
    )


def main():
    pygame.init()

    # 元画像読み込み
    pil_img = Image.open(IMAGE_PATH).convert("RGB")
    orig_w, orig_h = pil_img.size
    disp_w, disp_h = orig_w * SCALE, orig_h * SCALE

    # ウィンドウ作成
    flags = pygame.FULLSCREEN if FULLSCREEN_START else 0
    screen = pygame.display.set_mode((disp_w, disp_h), flags)
    pygame.display.set_caption("Which One Is Real?")
    clock = pygame.time.Clock()
    is_fullscreen = FULLSCREEN_START

    # スケーリング済み背景
    base_pil = pil_img.resize((disp_w, disp_h), Image.LANCZOS)
    base_surface = pil_to_surface(base_pil.convert("RGBA"))

    # スケーリング済みディスク
    disk_size = DISK_RADIUS * 2 * SCALE
    disk_pils = [extract_circular_disk(pil_img, c, DISK_RADIUS) for c in DISK_CENTERS]
    disk_surfaces = [
        pil_to_surface(d.resize((disk_size, disk_size), Image.LANCZOS))
        for d in disk_pils
    ]

    # 状態
    current_disk = random.randint(0, 5)
    state = "rotating"
    t0 = time.time()

    while True:
        # イベント処理
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit(); sys.exit()
                elif ev.key == pygame.K_f:
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode((disp_w, disp_h))

        elapsed = time.time() - t0

        if state == "rotating":
            if elapsed >= ROTATION_DURATION:
                state = "paused"
                t0 = time.time()
                angle = 0
            else:
                angle = (elapsed / ROTATION_DURATION) * 360.0
        else:  # paused
            if elapsed >= PAUSE_DURATION:
                prev = current_disk
                while current_disk == prev:
                    current_disk = random.randint(0, 5)
                state = "rotating"
                t0 = time.time()
            angle = 0

        # 描画
        screen_w, screen_h = screen.get_size()
        screen.fill(BG_COLOR)

        # フルスクリーン時は中央に配置
        ox = (screen_w - disp_w) // 2
        oy = (screen_h - disp_h) // 2
        screen.blit(base_surface, (ox, oy))

        # 回転ディスクを上書き
        if state == "rotating" and angle != 0:
            idx = current_disk
            cx_s = DISK_CENTERS[idx][0] * SCALE + ox
            cy_s = DISK_CENTERS[idx][1] * SCALE + oy
            rotated = pygame.transform.rotate(disk_surfaces[idx], -angle)
            rect = rotated.get_rect(center=(cx_s, cy_s))
            screen.blit(rotated, rect)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
