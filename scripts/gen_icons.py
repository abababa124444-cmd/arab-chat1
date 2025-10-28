from PIL import Image, ImageDraw, ImageFont
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'core', 'static', 'core', 'icons')
OUT_DIR = os.path.abspath(OUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)

GREEN = '#25D366'
TEXT = 'ARAB\nCHAT'


def make_icon(size: int):
    img = Image.new('RGBA', (size, size), GREEN)
    d = ImageDraw.Draw(img)

    # Try multiple font sizes to fit nicely in the icon
    candidates = [0.55, 0.5, 0.45, 0.4, 0.35]
    font = None
    for scale in candidates:
        try:
            font = ImageFont.truetype('arial.ttf', int(size * scale))
        except Exception:
            font = ImageFont.load_default()
        lines = TEXT.split('\n')
        # measure
        line_heights = []
        max_w = 0
        total_h = 0
        for line in lines:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            max_w = max(max_w, w)
            line_heights.append(h)
        total_h = sum(line_heights) + int(size * 0.06)
        if max_w <= size * 0.88 and total_h <= size * 0.88:
            break

    # center text
    y = (size - total_h) / 2
    for line, lh in zip(lines, line_heights):
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        x = (size - w) / 2
        d.text((x, y), line, fill='white', font=font)
        y += lh

    out_path = os.path.join(OUT_DIR, f'icon-{size}.png')
    img.save(out_path)
    print('Wrote', out_path)


if __name__ == '__main__':
    make_icon(192)
    make_icon(512)
    print('Done')
