#!/usr/bin/env python3
"""Opt-in aftershock alerts — poll USGS and queue a warning for subscribers.

Run this on a schedule on the server (e.g. cron every 5 minutes), using the SAME
DB_PATH as the bot so it can read subscribers and queue notifications:

    */5 * * * *  cd /app && python scripts/aftershock_poll.py

It checks USGS for recent significant quakes near the affected region. For each
NEW one it queues a bilingual alert for everyone who opted in (ALERTAS / ALERTS);
the alert is delivered the next time they message the bot.

To also PUSH proactively (before they message), you need an approved WhatsApp
template + outbound credentials — wire that in `_push` once you're off the
sandbox; until then, queued delivery works without any template.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import matching as M  # noqa: E402

# North-central Venezuela (Caracas / La Guaira), the affected region.
LAT, LON, RADIUS_KM, MIN_MAG = 10.6, -66.9, 400, 4.5
STATE_FILE = os.getenv("AFTERSHOCK_STATE", "/data/aftershock_seen.json")
LOOKBACK_MIN = 90


def _seen():
    try:
        return set(json.load(open(STATE_FILE)))
    except Exception:
        return set()


def _save_seen(ids):
    try:
        json.dump(sorted(ids), open(STATE_FILE, "w"))
    except Exception:
        pass


def fetch_recent():
    start = (datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MIN)).strftime("%Y-%m-%dT%H:%M:%S")
    q = urlencode({"format": "geojson", "starttime": start, "latitude": LAT,
                   "longitude": LON, "maxradiuskm": RADIUS_KM, "minmagnitude": MIN_MAG,
                   "orderby": "time"})
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + q
    with urlopen(url, timeout=15) as r:
        return json.load(r).get("features", [])


def alert_text(lang, mag, place):
    if lang == "en":
        return (f"⚠️ Aftershock alert: magnitude {mag} near {place}. If you're indoors "
                "and it's unsafe, move to open ground away from buildings. Stay safe. "
                "Type ALERTS to stop these.")
    return (f"⚠️ Alerta de réplica: magnitud {mag} cerca de {place}. Si estás en un "
            "lugar inseguro, sal a un espacio abierto lejos de edificios. Cuídate. "
            "Escribe ALERTAS para dejar de recibirlas.")


def _push(user, text):
    """Hook for proactive send (needs approved template + outbound creds)."""
    return False  # queued delivery is used until this is wired


def main():
    M.init_db()
    seen = _seen()
    quakes = fetch_recent()
    new = [q for q in quakes if q.get("id") not in seen]
    if not new:
        print("no new quakes")
        return
    subs = M.alert_subscribers()
    for q in new:
        p = q.get("properties", {})
        mag, place = p.get("mag"), p.get("place", "Venezuela")
        for user in subs:
            text = alert_text(M.get_lang(user), mag, place)
            if not _push(user, text):
                M.add_notification(user, text)
        seen.add(q.get("id"))
        print(f"queued M{mag} {place} -> {len(subs)} subscribers")
    _save_seen(seen)


if __name__ == "__main__":
    main()
