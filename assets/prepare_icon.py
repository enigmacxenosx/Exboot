from pathlib import Path
from PIL import Image

source = Path(__file__).with_name("exboot_icon_master.png")
output = Path(__file__).with_name("exboot.ico")
image = Image.open(source).convert("RGBA")
pixels = image.load()
for y in range(image.height):
    for x in range(image.width):
        r, g, b, a = pixels[x, y]
        if r > 180 and b > 150 and g < 100:
            pixels[x, y] = (r, g, b, 0)

alpha = image.getchannel("A")
bbox = alpha.getbbox()
if bbox:
    image = image.crop(bbox)
size = max(image.size)
canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
canvas.save(output, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(output)
