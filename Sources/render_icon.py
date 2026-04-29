#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
ASSETS = ROOT / "Assets"


def rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_app_icon(size: int) -> Image.Image:
    scale = 4
    base = 1024
    canvas = Image.new("RGBA", (base * scale, base * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    s = base * scale

    shadow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((80 * scale, 96 * scale, 944 * scale, 944 * scale), radius=220 * scale, fill=(0, 0, 0, 92))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24 * scale))
    canvas.alpha_composite(shadow)

    bg = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg)
    bg_draw.rounded_rectangle((80 * scale, 80 * scale, 944 * scale, 944 * scale), radius=220 * scale, fill=(13, 18, 32, 255))
    bg_draw.polygon(
        [(580 * scale, 944 * scale), (944 * scale, 944 * scale), (944 * scale, 420 * scale)],
        fill=(15, 118, 110, 230),
    )
    mask = Image.new("L", (s, s), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((80 * scale, 80 * scale, 944 * scale, 944 * scale), radius=220 * scale, fill=255)
    bg.putalpha(mask)
    canvas.alpha_composite(bg)

    # N body.
    draw.polygon(
        [
            (342 * scale, 236 * scale), (510 * scale, 236 * scale), (688 * scale, 560 * scale),
            (688 * scale, 236 * scale), (814 * scale, 236 * scale), (814 * scale, 788 * scale),
            (660 * scale, 788 * scale), (468 * scale, 440 * scale), (468 * scale, 788 * scale),
            (342 * scale, 788 * scale),
        ],
        fill=(229, 249, 255, 255),
    )

    # Lightning center.
    draw.polygon(
        [
            (588 * scale, 178 * scale), (330 * scale, 550 * scale), (492 * scale, 550 * scale),
            (438 * scale, 846 * scale), (700 * scale, 462 * scale), (536 * scale, 462 * scale),
        ],
        fill=(103, 232, 249, 238),
    )

    draw.ellipse((724 * scale, 192 * scale, 832 * scale, 300 * scale), fill=(52, 211, 153, 255))
    draw.ellipse((756 * scale, 224 * scale, 800 * scale, 268 * scale), fill=(236, 253, 245, 255))

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def render_status_icon(size: int = 44) -> Image.Image:
    scale = 4
    img = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size * scale

    # Template image: black alpha glyph. macOS tints it automatically.
    draw.rounded_rectangle((4 * scale, 4 * scale, (size - 4) * scale, (size - 4) * scale), radius=10 * scale, outline=(0, 0, 0, 255), width=4 * scale)
    draw.polygon(
        [
            (26 * scale, 8 * scale), (12 * scale, 25 * scale), (22 * scale, 25 * scale),
            (18 * scale, 38 * scale), (33 * scale, 20 * scale), (23 * scale, 20 * scale),
        ],
        fill=(0, 0, 0, 255),
    )
    return img.resize((size, size), Image.Resampling.LANCZOS)


def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)

    iconset = BUILD / "NextSentinel.iconset"
    iconset.mkdir(parents=True, exist_ok=True)

    for base in [16, 32, 128, 256, 512]:
        render_app_icon(base).save(iconset / f"icon_{base}x{base}.png")
        render_app_icon(base * 2).save(iconset / f"icon_{base}x{base}@2x.png")

    render_status_icon().save(ASSETS / "StatusIcon.png")


if __name__ == "__main__":
    main()
