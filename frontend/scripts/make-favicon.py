from pathlib import Path

from PIL import Image, ImageDraw


def make(size: int, path: str) -> Image.Image:
    im = Image.new("RGBA", (size, size), (253, 251, 247, 255))
    d = ImageDraw.Draw(im)
    m = size / 64
    d.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=int(14 * m),
        fill=(253, 251, 247, 255),
    )
    d.ellipse(
        (int(16 * m), int(26 * m), int(48 * m), int(54 * m)),
        fill=(255, 248, 232, 255),
        outline=(42, 34, 24, 255),
        width=max(1, int(2 * m)),
    )
    d.rounded_rectangle(
        (int(20 * m), int(18 * m), int(44 * m), int(40 * m)),
        radius=int(6 * m),
        fill=(244, 247, 250, 255),
        outline=(42, 34, 24, 255),
        width=max(1, int(2 * m)),
    )
    r = max(1, int(2.4 * m))
    d.ellipse((int(27 * m) - r, int(28 * m) - r, int(27 * m) + r, int(28 * m) + r), fill=(42, 34, 24, 255))
    d.ellipse((int(37 * m) - r, int(28 * m) - r, int(37 * m) + r, int(28 * m) + r), fill=(42, 34, 24, 255))
    d.line(
        [(int(14 * m), int(28 * m)), (int(8 * m), int(37 * m))],
        fill=(255, 153, 51, 255),
        width=max(2, int(3 * m)),
    )
    d.line(
        [(int(50 * m), int(28 * m)), (int(56 * m), int(37 * m))],
        fill=(255, 153, 51, 255),
        width=max(2, int(3 * m)),
    )
    d.rounded_rectangle(
        (int(26 * m), int(44 * m), int(38 * m), int(52 * m)),
        radius=int(2 * m),
        fill=(255, 153, 51, 255),
        outline=(42, 34, 24, 255),
        width=max(1, int(1 * m)),
    )
    im.save(path)
    return im


root = Path("/w/public")
img32 = make(32, str(root / "favicon-32.png"))
make(180, str(root / "apple-touch-icon.png"))
img48 = make(48, "/tmp/favicon-48.png")
img32.save(str(root / "favicon.ico"), format="ICO", sizes=[(32, 32), (48, 48)])
# Pillow ICO from multiple sizes:
Image.new("RGBA", (48, 48)).save(
    str(root / "favicon.ico"),
    format="ICO",
    append_images=[img32, img48],
    sizes=[(32, 32), (48, 48)],
)
print("ok", (root / "favicon.ico").stat().st_size)
