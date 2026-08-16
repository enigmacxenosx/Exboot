from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ASSETS = Path(__file__).parent

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REGULAR_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def radial_glow(size, center, radius, color, alpha):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    px = layer.load()
    cx, cy = center
    for y in range(size[1]):
        for x in range(size[0]):
            distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            strength = max(0.0, 1.0 - distance / radius)
            strength = strength * strength
            px[x, y] = (*color, int(alpha * strength))
    return layer


def draw_ex_mark(canvas, box):
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box
    # The splash component uses a bold white EX wordmark with a tight tracking feel.
    mark_font = font(FONT_PATH, int((y1 - y0) * 0.39))
    text = "EX"
    bbox = draw.textbbox((0, 0), text, font=mark_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) / 2 - bbox[0]
    ty = y0 + (y1 - y0 - th) / 2 - bbox[1] - 3

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.text((tx, ty), text, font=mark_font, fill=(255, 255, 255, 170), stroke_width=3)
    glow = glow.filter(ImageFilter.GaussianBlur(max(5, int((y1 - y0) * 0.05))))
    canvas.alpha_composite(glow)
    draw = ImageDraw.Draw(canvas)
    draw.text((tx, ty), text, font=mark_font, fill=(255, 255, 255, 255))


def draw_glass_mark(size):
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    center = size // 2
    canvas.alpha_composite(radial_glow((size, size), (center, center), size * 0.56, (0, 242, 255), 125))

    panel = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    radius = int(size * 0.24)
    panel_draw.rounded_rectangle(
        (int(size * 0.05), int(size * 0.05), int(size * 0.95), int(size * 0.95)),
        radius=radius,
        fill=(255, 255, 255, 24),
        outline=(255, 255, 255, 74),
        width=max(2, int(size * 0.008)),
    )
    canvas.alpha_composite(panel)
    draw_ex_mark(canvas, (int(size * 0.1), int(size * 0.1), int(size * 0.9), int(size * 0.9)))
    return canvas


def make_square_logo():
    size = 1024
    image = Image.new("RGBA", (size, size), (5, 5, 5, 255))
    image.alpha_composite(draw_glass_mark(760), (132, 80))
    return image


def make_wizard_image():
    width, height = 328, 628
    image = Image.new("RGBA", (width, height), (5, 5, 5, 255))
    image.alpha_composite(radial_glow((width, height), (width // 2, 235), 260, (0, 242, 255), 90))
    mark = draw_glass_mark(226)
    image.alpha_composite(mark, ((width - mark.width) // 2, 118))

    draw = ImageDraw.Draw(image)
    small = font(REGULAR_FONT_PATH, 13)
    name = font(REGULAR_FONT_PATH, 24)
    label = "from"
    label_box = draw.textbbox((0, 0), label, font=small)
    draw.text(((width - (label_box[2] - label_box[0])) / 2, 462), label, font=small, fill=(255, 255, 255, 95))
    brand = "Enosx Technologies"
    brand_box = draw.textbbox((0, 0), brand, font=name)
    draw.text(((width - (brand_box[2] - brand_box[0])) / 2, 486), brand, font=name, fill=(255, 255, 255, 205))
    draw.rectangle((0, height - 3, width, height), fill=(0, 242, 255, 220))
    return image


def save_ico(square_image):
    icon = square_image.convert("RGBA")
    icon.save(
        ASSETS / "enosx-ai-splash-logo.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    square = make_square_logo()
    square.save(ASSETS / "enosx-ai-splash-logo.png")
    make_wizard_image().save(ASSETS / "enosx-ai-splash-wizard.png")
    save_ico(square)
    print("Created Enosx AI splash assets")
