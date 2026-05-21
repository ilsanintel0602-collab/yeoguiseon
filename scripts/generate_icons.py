#!/usr/bin/env python3
"""
아이콘 PNG 생성기 (PIL만 사용 - 외부 SVG 변환 도구 불필요)

기존 아이콘이 단순/찌그러진 문제 정비:
- 둥근 사각형 + 녹색 그라데이션
- 흰색 원 + 깔끔한 재활용 심볼 (대칭 3-arrows)
- 작은 잎 액센트
- "여기선" 한글 텍스트

생성: icons/icon-192.png, icon-512.png, apple-touch-icon.png, favicon-32.png
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "icons"))

# 색상
BG_TOP = (52, 211, 153)        # #34d399
BG_MID = (16, 185, 129)        # #10b981
BG_BOTTOM = (15, 118, 110)     # #0f766e
ARROW_COLOR = (15, 118, 110)   # 진한 청록 (흰 원 위 대비)
WHITE = (255, 255, 255)
LEAF_TOP = (163, 230, 53)      # #a3e635
LEAF_BOTTOM = (101, 163, 13)   # #65a30d


def gradient_bg(size):
    """그라데이션 배경 생성"""
    img = Image.new('RGBA', (size, size))
    for y in range(size):
        ratio = y / size
        if ratio < 0.6:
            t = ratio / 0.6
            r = int(BG_TOP[0] * (1 - t) + BG_MID[0] * t)
            g = int(BG_TOP[1] * (1 - t) + BG_MID[1] * t)
            b = int(BG_TOP[2] * (1 - t) + BG_MID[2] * t)
        else:
            t = (ratio - 0.6) / 0.4
            r = int(BG_MID[0] * (1 - t) + BG_BOTTOM[0] * t)
            g = int(BG_MID[1] * (1 - t) + BG_BOTTOM[1] * t)
            b = int(BG_MID[2] * (1 - t) + BG_BOTTOM[2] * t)
        for x in range(size):
            img.putpixel((x, y), (r, g, b, 255))
    return img


def get_font(size_px):
    """한글 폰트 찾기"""
    for fname in ["malgun.ttf", "MalgunGothic.ttf", "NanumGothic.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(fname, size_px)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_icon(size, with_text=True):
    """아이콘 1개 생성"""
    # 1) 그라데이션 배경 + 둥근 모서리 마스크
    gradient = gradient_bg(size)
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = int(size * 0.225)
    mask_draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask)

    # 2) 하이라이트 (좌상단 부드러운 흰색 그라데이션)
    hl = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(hl)
    for r_val in range(int(size * 0.5), 0, -8):
        alpha = int(28 * (1 - r_val / (size * 0.5)))
        if alpha < 1:
            continue
        cx, cy = int(size * 0.4), int(size * 0.3)
        hl_draw.ellipse((cx - r_val, cy - r_val, cx + r_val, cy + r_val),
                       fill=(255, 255, 255, alpha))
    hl_masked = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    hl_masked.paste(hl, (0, 0), mask)
    img = Image.alpha_composite(img, hl_masked)

    draw = ImageDraw.Draw(img)

    # 3) 잎 액센트 (우상단)
    if size >= 64:
        leaf_cx, leaf_cy = int(size * 0.77), int(size * 0.22)
        leaf_w, leaf_h = int(size * 0.085), int(size * 0.045)
        # 단순 타원 (회전 효과는 polygon으로)
        # 회전된 타원: 점 여러 개로 polygon
        pts = []
        cos_a, sin_a = math.cos(math.radians(-30)), math.sin(math.radians(-30))
        for ang in range(0, 360, 10):
            r = math.radians(ang)
            x = leaf_w * math.cos(r)
            y = leaf_h * math.sin(r)
            xr = x * cos_a - y * sin_a + leaf_cx
            yr = x * sin_a + y * cos_a + leaf_cy
            pts.append((xr, yr))
        draw.polygon(pts, fill=LEAF_TOP)
        # 잎 가운데 라인
        mid_x1 = leaf_cx - int(size * 0.07) * cos_a
        mid_y1 = leaf_cy - int(size * 0.07) * sin_a
        mid_x2 = leaf_cx + int(size * 0.07) * cos_a
        mid_y2 = leaf_cy + int(size * 0.07) * sin_a
        draw.line((mid_x1, mid_y1, mid_x2, mid_y2),
                 fill=LEAF_BOTTOM, width=max(2, size // 200))

    # 4) 흰색 원 (재활용 심볼 컨테이너)
    text_offset = 0 if not with_text else int(size * 0.06)
    cx = size // 2
    cy = int(size * 0.43) - text_offset
    r_circle = int(size * 0.245)
    draw.ellipse((cx - r_circle, cy - r_circle, cx + r_circle, cy + r_circle),
                fill=WHITE)
    # 가는 흰색 outer ring
    draw.ellipse((cx - r_circle - 3, cy - r_circle - 3,
                 cx + r_circle + 3, cy + r_circle + 3),
                outline=(255, 255, 255, 100), width=max(2, size // 160))

    # 5) 재활용 심볼 - 3개의 화살표 (120도 대칭)
    arrow_radius = r_circle * 0.78
    tri_w = arrow_radius * 0.50
    tri_h = arrow_radius * 0.35
    stem_h = arrow_radius * 0.42
    stem_w = arrow_radius * 0.18

    for angle_deg in [-90, 30, 150]:  # top, bottom-right, bottom-left
        rad = math.radians(angle_deg)
        # 각 화살표 중심 위치
        ax = cx + (arrow_radius * 0.55) * math.cos(rad)
        ay = cy + (arrow_radius * 0.55) * math.sin(rad)

        # 화살표는 안쪽을 향함 (회전 + 변환)
        # local 좌표계: tip이 위쪽(-y)에 있는 모양을 그린 후 회전
        local_pts = [
            # 화살촉 (triangle)
            (0, -tri_h * 0.9),                  # tip
            (-tri_w * 0.7, -tri_h * 0.1),       # bottom-left
            (-stem_w * 0.7, -tri_h * 0.1),      # stem top-left
            (-stem_w * 0.7, stem_h * 0.55),     # stem bottom-left
            (stem_w * 0.7, stem_h * 0.55),      # stem bottom-right
            (stem_w * 0.7, -tri_h * 0.1),       # stem top-right
            (tri_w * 0.7, -tri_h * 0.1),        # bottom-right
        ]

        # 화살표가 중심을 향하도록 회전 (안쪽 방향 = 중심 방향)
        # 화살표 tip이 중심 방향으로 향하게: angle_deg + 90
        rot = math.radians(angle_deg + 90)
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        rotated_pts = []
        for (px, py) in local_pts:
            xr = px * cos_r - py * sin_r + ax
            yr = px * sin_r + py * cos_r + ay
            rotated_pts.append((xr, yr))
        draw.polygon(rotated_pts, fill=ARROW_COLOR)

    # 6) "여기선" 한글 텍스트
    if with_text and size >= 100:
        text_y = int(size * 0.84)
        text_size_px = int(size * 0.14)
        font = get_font(text_size_px)
        text = "여기선"
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(((size - tw) // 2 - bbox[0],
                      text_y - th // 2 - bbox[1]),
                     text, font=font, fill=WHITE)
        except Exception as e:
            print(f"  warn: text draw failed (size {size}): {e}")

    return img


def main():
    os.makedirs(ICONS_DIR, exist_ok=True)

    targets = [
        ("icon-192.png", 192, True),
        ("icon-512.png", 512, True),
        ("apple-touch-icon.png", 180, True),
        ("favicon-32.png", 32, False),  # 너무 작으면 텍스트 안 보임
        ("icon-192-maskable.png", 192, True),
        ("icon-512-maskable.png", 512, True),
    ]

    for name, size, with_text in targets:
        path = os.path.join(ICONS_DIR, name)
        img = make_icon(size, with_text=with_text)
        img.save(path, 'PNG', optimize=True)
        print(f"  OK  {name} ({size}x{size})")

    print(f"\n  saved to: {ICONS_DIR}")
    print(f"  total: {len(targets)} icons")


if __name__ == "__main__":
    main()
