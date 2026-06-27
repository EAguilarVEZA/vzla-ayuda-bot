#!/usr/bin/env python3
"""Generate the one-tap entry assets: a wa.me deep link + a printable QR.

The QR is what goes on the café posters. Scanning it opens WhatsApp with "Hola"
pre-typed so the person just hits send to start the bot.

Usage:
    python scripts/make_entry_qr.py +14155238886
    python scripts/make_entry_qr.py +14155238886 --text "Hola" --out dashboard/entry_qr.png

The number must be the bot's WhatsApp number in E.164 (digits, leading +).
For the Twilio sandbox you normally can't deep-link past the join code, so use
this once you have an approved WhatsApp Business sender.
"""
import argparse
import sys
from urllib.parse import quote


def build_link(number: str, text: str) -> str:
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        sys.exit("error: provide the bot's phone number, e.g. +14155238886")
    return f"https://wa.me/{digits}?text={quote(text)}"


def main():
    ap = argparse.ArgumentParser(description="Generate wa.me link + QR for the bot.")
    ap.add_argument("number", help="bot WhatsApp number in E.164, e.g. +14155238886")
    ap.add_argument("--text", default="Hola", help="prefilled first message (default: Hola)")
    ap.add_argument("--out", default="entry_qr.png", help="output PNG path")
    args = ap.parse_args()

    link = build_link(args.number, args.text)
    print("Entry link (put behind buttons / share in groups):")
    print("  " + link)

    try:
        import qrcode
    except ImportError:
        print("\nQR not generated — install the library first:")
        print("  pip install 'qrcode[pil]'")
        print("Then re-run. The link above already works on its own.")
        return

    qr = qrcode.QRCode(box_size=12, border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f2747", back_color="white")
    img.save(args.out)
    print(f"\nQR saved -> {args.out}")
    print("Drop it onto poster.html / the café posters. Scanning it opens the bot.")


if __name__ == "__main__":
    main()
