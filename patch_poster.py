"""Patch four text regions on the exhibition poster and write a one-page PDF.

Loads original_poster.png at its native size. Paints over only the old words
and draws the replacements. Logos, icons, the chart, the QR code, borders,
and the architecture drawing are left untouched.
"""

from pathlib import Path

import img2pdf
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "original_poster.png"
PREVIEW = ROOT / "poster_patched.png"
PDF = ROOT / "poster_final_final.pdf"

FONT = "/usr/share/fonts/truetype/macos/Inter-Medium.ttf"
FONT_REG = "/usr/share/fonts/truetype/macos/Inter-Regular.ttf"

INK = (55, 62, 74)
MUTED = (90, 98, 108)


def font(path, size):
    return ImageFont.truetype(path, size)


def sample_bg(im, box):
    """Median of the light pixels in a box, so the fill matches the card."""
    x0, y0, x1, y1 = box
    px = im.load()
    lights = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            r, g, b = px[x, y]
            if min(r, g, b) > 220:
                lights.append((r, g, b))
    if not lights:
        return (244, 246, 250)
    lights.sort()
    return lights[len(lights) // 2]


def fill(draw, im, box):
    draw.rectangle(box, fill=sample_bg(im, box))


def text_size(face, text):
    box = face.getbbox(text)
    return box[2] - box[0], box[3] - box[1]


def wrap(face, text, width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if text_size(face, trial)[0] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines(draw, lines, xy, face, fill, line_gap):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += text_size(face, line)[1] + line_gap
    return y


def fit_label(base, text, center, top, max_width, color):
    """Draw one score label, scaled so it stays inside its column."""
    face = font(FONT, 28)
    width, height = text_size(face, text)
    scale = min(1.0, max_width / width)
    canvas = Image.new("RGBA", (width + 4, height + 4), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((1, 0), text, font=face, fill=color + (255,))
    resized = canvas.resize(
        (max(1, int(canvas.width * scale)), max(1, int(canvas.height * scale))),
        Image.Resampling.LANCZOS,
    )
    x = int(center - resized.width / 2)
    base.paste(resized, (x, top), resized)


def patch(im):
    draw = ImageDraw.Draw(im)

    # 1. The four "was N/N" lines under the Study Agent scores.
    # Green rules sit on y=136. The old "was" glyphs are y=152-156.
    # Columns are centered on those rules and are about 52px apart.
    labels = [
        (797, "baseline 50/75 → final 74/75"),
        (852, "baseline 7/10 → final 10/10"),
        (908, "baseline 5/10 → final 10/10"),
        (961, "baseline 12/15 → final 14/15"),
    ]
    for center, _ in labels:
        fill(draw, im, (center - 26, 150, center + 26, 158))
    for center, label in labels:
        fit_label(im, label, center, 150, 50, MUTED)

    # 2. The three-line rules note under the architecture diagram.
    # The blue bar at x≈294 stays. Text occupies y=294-323.
    note_box = (300, 291, 752, 326)
    fill(draw, im, note_box)
    note = (
        "Rules: client proposes the course_id; server authorizes it "
        "(CourseMembership). Ask Triage and Help Coach run on local models "
        "and never send student text outside the app. Study Agent sends only "
        "the student's question and approved course chunks to Gemini "
        "(no student IDs or grades)."
    )
    note_font = font(FONT_REG, 8)
    note_lines = wrap(note_font, note, note_box[2] - note_box[0] - 2)
    draw_lines(draw, note_lines, (302, 293), note_font, INK, 1)

    # 3. Pilot kicker, then the workflow caption on the right only.
    kicker_box = (772, 322, 962, 333)
    fill(draw, im, kicker_box)
    kicker = "PILOT EVALUATION  ·  N = 7  ·  SCALE 1 TO 5"
    kicker_font = font(FONT, 8)
    draw.text((774, 322), kicker, font=kicker_font, fill=INK)

    # The caption row is y=370-376. The left phrase ends at the gap x=863-886.
    flow_box = (866, 369, 998, 378)
    fill(draw, im, flow_box)
    fit_label(
        im,
        "workflow value · 7/7 pilot participants agree",
        932,
        369,
        124,
        MUTED,
    )

    # 4. Roadmap items 2, 3, and 4. Items 1, 5, and 6 stay.
    # On the 1024px source: item 2 is y≈496, item 3 y≈520, the PRODUCT
    # pill is y≈548, item 4 is y≈567. Circles end by x=790.
    items = [
        (488, 514, "Live classroom pilot in an active AUI course next semester"),
        (514, 544, "Expanded multi-course evaluation with larger student & TA cohorts"),
        (558, 586, "Multi-language support (French & Arabic) and broader LMS integration"),
    ]
    body = font(FONT_REG, 7)
    for y0, y1, text in items:
        box = (792, y0, 1002, y1)
        fill(draw, im, box)
        lines = wrap(body, text, box[2] - box[0] - 8)
        draw_lines(draw, lines, (804, y0 + 2), body, INK, 0)


def main():
    im = Image.open(SOURCE).convert("RGB")
    if im.size != (1024, 702):
        raise SystemExit(f"expected 1024x702, got {im.size}")
    patch(im)
    im.save(PREVIEW, format="PNG")
    # One page, no margin, page shape equal to the image.
    layout = img2pdf.get_layout_fun(pagesize=(1024, 702), fit=img2pdf.FitMode.fill)
    PDF.write_bytes(img2pdf.convert(PREVIEW.as_posix(), layout_fun=layout))
    print(f"wrote {PREVIEW}")
    print(f"wrote {PDF}")


if __name__ == "__main__":
    main()
