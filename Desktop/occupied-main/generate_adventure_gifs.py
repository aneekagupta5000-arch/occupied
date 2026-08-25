from pathlib import Path
from PIL import Image, ImageDraw

OUTPUT = Path(__file__).parent
SIZE = (420, 220)
def smooth_frame(image):
    return image.convert("P", palette=Image.Palette.ADAPTIVE)


def make_ice_gif():
    frames = []
    for index in range(12):
        image = Image.new("RGB", SIZE, "#EAF6FB")
        draw = ImageDraw.Draw(image)
        draw.ellipse((120, 18, 300, 198), fill="#FFFFFF")
        melt = index / 11
        ice_bottom = 145 - int(melt * 48)
        draw.rounded_rectangle((145, 62, 275, ice_bottom), radius=14, fill="#CDEEF8")
        draw.ellipse((145, ice_bottom - 10, 275, ice_bottom + 10), fill="#CDEEF8")
        draw.line((170, 78, 158 + int(melt * 18), 116), fill="#FFFFFF", width=7)
        draw.ellipse((170 + index * 4, 151 + int(melt * 30), 184 + index * 4, 166 + int(melt * 30)), fill="#9BD9EA")
        draw.ellipse((230 - index * 3, 155 + int(melt * 24), 242 - index * 3, 168 + int(melt * 24)), fill="#B4E5F0")
        frames.append(smooth_frame(image))
    frames[0].save(OUTPUT / "ice_melting.gif", save_all=True, append_images=frames[1:], duration=170, loop=0, disposal=2)


def make_plane_gif():
    frames = []
    for index in range(12):
        image = Image.new("RGB", SIZE, "#FFF5D6")
        draw = ImageDraw.Draw(image)
        draw.ellipse((120, 18, 300, 198), fill="#FFFFFF")
        x = 54 + index * 25
        y = 92 - int(index * 1.6)
        draw.rounded_rectangle((x, y, x + 106, y + 24), radius=12, fill="#F59BC9")
        draw.polygon([(x + 35, y + 6), (x + 62, y - 30), (x + 75, y + 6)], fill="#FAD6EA")
        draw.polygon([(x + 45, y + 20), (x + 74, y + 52), (x + 84, y + 20)], fill="#FAD6EA")
        draw.ellipse((x + 13, y + 7, x + 21, y + 15), fill="#FFFFFF")
        draw.line((x - 42, y + 38, x - 8, y + 29), fill="#E8A4C7", width=5)
        draw.line((x - 52, y + 51, x - 16, y + 41), fill="#E8A4C7", width=5)
        frames.append(smooth_frame(image))
    frames[0].save(OUTPUT / "flying_airplane.gif", save_all=True, append_images=frames[1:], duration=150, loop=0, disposal=2)


if __name__ == "__main__":
    make_ice_gif()
    make_plane_gif()
    print("Created ice_melting.gif and flying_airplane.gif")
