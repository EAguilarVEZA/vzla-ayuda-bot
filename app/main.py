"""FastAPI entry point — the Twilio WhatsApp/SMS webhook.

Inbound flow:  user's phone -> WhatsApp -> Twilio -> POST /whatsapp -> here
Normal replies go back as TwiML (works on the Twilio WhatsApp sandbox out of the
box). The one exception is the main menu: when the native interactive list is
enabled (Business API), it's sent out-of-band and we return an empty TwiML so
the user doesn't also get the text version. If that send fails — or we're on the
sandbox/SMS — we fall back to the grouped text menu automatically.
"""
import logging

from fastapi import FastAPI, Form, Response, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse

log = logging.getLogger("main")

from .bot import handle
from .matching import init_db
from .menu import MenuReply, MediaReply
from .send import send_interactive_list
from . import analytics, partners
from .sim import SIM_HTML

app = FastAPI(title="Ayuda Venezuela Bot")

# The dashboards (standalone files or another host) read the metrics + partner
# API. Allow cross-origin GET/POST; metrics are anonymized aggregates, and the
# partner API is protected by an API key (never exposes citizen PII).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---- partner API (org-facing portal) ----
def require_partner(x_api_key: str = Header(default="")):
    p = partners.get_partner(x_api_key)
    if not p:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return p


class CapacityIn(BaseModel):
    type: str
    location: str
    name: str
    detail: str = ""
    status: str = "open"


class ClaimIn(BaseModel):
    category: str
    location: str
    note: str = ""


@app.get("/api/summary")
def api_summary(days: int = 14, partner=Depends(require_partner)):
    return analytics.daily_summary(days=max(1, min(days, 90)))


@app.get("/api/needs")
def api_needs(days: int = 14, partner=Depends(require_partner)):
    s = analytics.daily_summary(days=max(1, min(days, 90)))
    return {"needs_heatmap": s["needs_heatmap"], "hero_network": s["hero_network"],
            "by_intent": s["by_intent"], "claims": partners.list_claims()}


@app.get("/api/capacity")
def api_capacity_list(type: str = None, location: str = None,
                      partner=Depends(require_partner)):
    return {"capacity": partners.list_capacity(type_=type, location=location)}


@app.post("/api/capacity")
def api_capacity_add(body: CapacityIn, partner=Depends(require_partner)):
    cid = partners.add_capacity(partner["name"], body.type, body.location,
                                body.name, body.detail, body.status)
    return {"ok": True, "id": cid}


@app.get("/api/claims")
def api_claims_list(category: str = None, location: str = None,
                    partner=Depends(require_partner)):
    return {"claims": partners.list_claims(category=category, location=location)}


@app.post("/api/claims")
def api_claims_add(body: ClaimIn, partner=Depends(require_partner)):
    cid = partners.add_claim(partner["name"], body.category, body.location, body.note)
    return {"ok": True, "id": cid}


def _build_response(user: str, body: str, lat=None, lon=None) -> Response:
    # handle() is crash-proof, but guard the whole webhook so Twilio always gets
    # a valid 200 TwiML (a 500 triggers retries and a bad user experience).
    try:
        reply = handle(user=user, body=body, lat=lat, lon=lon)
        if isinstance(reply, MenuReply) and send_interactive_list(user, reply):
            return Response(content=str(MessagingResponse()),
                            media_type="application/xml")
    except Exception:
        log.exception("webhook error for user=%s", user)
        reply = "⚠️ Please try again in a moment."

    twiml = MessagingResponse()
    m = twiml.message(str(reply))
    if isinstance(reply, MediaReply):
        for url in reply.media:        # attach images (e.g. a missing person's photo)
            m.media(url)
    return Response(content=str(twiml), media_type="application/xml")


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/")
def health():
    return {"status": "ok", "service": "ayuda-venezuela-whatsapp-bot"}


# ---- built-in simulator (test the bot in a browser, no Twilio needed) ----
class SimIn(BaseModel):
    user: str
    body: str = ""


@app.get("/sim", response_class=HTMLResponse)
def sim_page():
    return SIM_HTML


@app.post("/sim/send")
def sim_send(msg: SimIn):
    return {"reply": str(handle(user=msg.user, body=msg.body))}


@app.get("/metrics/daily")
def metrics_daily(days: int = 14):
    """Anonymized, aggregated metrics for the management dashboard + heatmap.
    Contains no PII. `days` controls the look-back window."""
    return analytics.daily_summary(days=max(1, min(days, 90)))


@app.post("/whatsapp")
async def whatsapp(From: str = Form(...), Body: str = Form(""),
                   Latitude: str = Form(None), Longitude: str = Form(None)):
    """Twilio posts 'From' and 'Body'; a shared location adds Latitude/Longitude."""
    return _build_response(user=From, body=Body, lat=Latitude, lon=Longitude)


# Same handler also works for plain SMS if you point an SMS number here.
@app.post("/sms")
async def sms(From: str = Form(...), Body: str = Form("")):
    return _build_response(user=From, body=Body)
