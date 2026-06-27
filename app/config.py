"""Central configuration, loaded from environment / .env."""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Haiku by default: cheap + fast for classify/translate at volume.
# Bump to claude-sonnet-4-6 only if you need higher-quality translation.
BOT_MODEL = os.getenv("BOT_MODEL", "claude-haiku-4-5")

# Public one-tap entry link people share (wa.me deep link, prefilled "Hola").
# Set this to your approved WhatsApp Business number once you have it.
PUBLIC_BOT_LINK = os.getenv("PUBLIC_BOT_LINK", "https://wa.me/<your-number>?text=Hola")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")

DB_PATH = os.getenv("DB_PATH", "ayuda.db")

# --- Native interactive-list menu (WhatsApp Business API) --------------------
# OFF by default so the Twilio sandbox keeps working with the grouped text menu.
# Flip on once you have a Business sender; the bot then sends a native list and
# falls back to text automatically if the send fails.
WHATSAPP_INTERACTIVE = os.getenv("WHATSAPP_INTERACTIVE", "0") == "1"
# Which sender to use for the interactive list: "cloud" (Meta WhatsApp Cloud
# API, inline JSON) or "twilio" (Content template SID).
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "cloud")
# Meta Cloud API creds (only needed when WHATSAPP_PROVIDER=cloud).
WHATSAPP_CLOUD_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
# Twilio Content template SID for a list-picker (only when WHATSAPP_PROVIDER=twilio).
TWILIO_LIST_CONTENT_SID = os.getenv("TWILIO_LIST_CONTENT_SID", "")
