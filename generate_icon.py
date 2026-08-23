from pathlib import Path
from PIL import Image

source = Path("icon.ico.png")
destination = Path("life_audit_icon.ico")

with Image.open(source) as image:
    image.convert("RGBA").save(
        destination,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )

print(destination.resolve())
