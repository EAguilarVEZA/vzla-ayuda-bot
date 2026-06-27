"""Out-of-band sender for the native WhatsApp interactive list.

The interactive list cannot be returned as TwiML in the webhook response — it
must be POSTed to the WhatsApp Business API. So when the menu should render as a
native list, main.py calls send_interactive_list() here, and returns an EMPTY
TwiML so the user doesn't also get the text version.

Everything is best-effort: any failure returns False and the caller falls back
to the grouped text menu. Nothing here runs unless config.WHATSAPP_INTERACTIVE
is on.
"""
from __future__ import annotations

import logging

from . import config, menu

log = logging.getLogger("send")


def _to_number(whatsapp_from: str) -> str:
    """Twilio gives 'whatsapp:+58...'; the Cloud API wants the bare E.164."""
    return whatsapp_from.replace("whatsapp:", "").strip()


def _send_cloud(to: str, payload: dict) -> bool:
    """Meta WhatsApp Cloud API: POST the interactive JSON inline."""
    if not (config.WHATSAPP_CLOUD_TOKEN and config.WHATSAPP_PHONE_ID):
        return False
    import httpx  # local import so the dep is optional until used

    url = f"https://graph.facebook.com/v20.0/{config.WHATSAPP_PHONE_ID}/messages"
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": _to_number(to),
        "type": "interactive",
        "interactive": payload,
    }
    headers = {"Authorization": f"Bearer {config.WHATSAPP_CLOUD_TOKEN}"}
    r = httpx.post(url, json=body, headers=headers, timeout=8.0)
    r.raise_for_status()
    return True


def _send_twilio(to: str, lang: str) -> bool:
    """Twilio path: send a pre-created list-picker Content template by SID.

    Dynamic per-language lists require the template's variables to be populated;
    wiring those variables is deployment-specific, so this returns False unless a
    SID is configured (caller then uses the text menu)."""
    if not (config.TWILIO_LIST_CONTENT_SID and config.TWILIO_ACCOUNT_SID
            and config.TWILIO_AUTH_TOKEN and config.TWILIO_WHATSAPP_FROM):
        return False
    from twilio.rest import Client

    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=config.TWILIO_WHATSAPP_FROM,
        to=to,
        content_sid=config.TWILIO_LIST_CONTENT_SID,
    )
    return True


def send_interactive_list(whatsapp_from: str, reply: "menu.MenuReply") -> bool:
    """Send the menu as a native list. Returns True if it went out-of-band
    (caller then replies with empty TwiML), False to fall back to text."""
    if not config.WHATSAPP_INTERACTIVE:
        return False
    if not whatsapp_from.startswith("whatsapp:"):
        return False  # SMS has no interactive lists
    try:
        if config.WHATSAPP_PROVIDER == "cloud":
            payload = menu.interactive_payload(getattr(reply, "lang", "es"),
                                               body=getattr(reply, "body", None))
            return _send_cloud(whatsapp_from, payload)
        return _send_twilio(whatsapp_from, getattr(reply, "lang", "es"))
    except Exception as e:
        log.warning("interactive list send failed, falling back to text: %s", e)
        return False
