"""Generate synthetic demo documents (no real personal data).
Run:  python samples/make_samples.py
Creates samples/marksheet_tampered.png, marksheet_clean.png, id_name_mismatch.png"""
import os

from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make(path, lines, seal=True):
    img = Image.new("RGB", (1400, 1000), "white")
    d = ImageDraw.Draw(img)
    y = 50
    for text, size in lines:
        d.text((80, y), text, fill="black", font=font(size))
        y += size + 26
    if seal:
        d.ellipse((1050, 700, 1300, 950), outline=(20, 40, 160), width=8)
        d.ellipse((1075, 725, 1275, 925), outline=(20, 40, 160), width=3)
        d.text((1110, 810), "SEAL", fill=(20, 40, 160), font=font(40))
    img.save(path)


def marksheet(total, name="Harini Sundar"):
    return [
        ("SAMPLE STATE UNIVERSITY", 44),
        ("STATEMENT OF MARKS", 34),
        (f"Name: {name}", 30),
        ("Father's Name: Sundar Raman", 30),
        ("Date of Birth: 14/03/2006", 30),
        ("Register No: 21CS10458", 30),
        ("Mathematics 85", 30), ("Physics 90", 30), ("Programming 95", 30),
        (f"Total Marks: {total}", 30),
        ("Percentage: 90.00", 30),
        ("Date of Issue: 20/06/2024", 30),
        ("Controller of Examinations", 28),
    ]


if __name__ == "__main__":
    make(os.path.join(OUT, "marksheet_clean.png"), marksheet(270))
    make(os.path.join(OUT, "marksheet_tampered.png"), marksheet(280))
    make(os.path.join(OUT, "id_name_mismatch.png"), [
        ("IDENTITY CARD", 44), ("Name: Harini Sunder Rao", 30),
        ("Father's Name: Sundar Raman", 30), ("Date of Birth: 14/03/2006", 30)], seal=False)
    print("Samples written to", OUT)
