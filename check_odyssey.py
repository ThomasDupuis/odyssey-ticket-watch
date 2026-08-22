#!/usr/bin/env python3
"""
Watch Cineplex for new bookable sessions of The Odyssey in IMAX 70mm
at Cinema Banque Scotia Montreal, and push a phone notification via ntfy.sh.

Tracks individual sessions (date + time) in a local state file, so it only
notifies about things it has never seen before. The first run seeds the state
and stays quiet.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

FILM_ID = 38376          # The Odyssey: The IMAX Experience in 70MM Film
LOCATION_ID = 9406       # Cinema Banque Scotia Montreal

API = "https://apis.cineplex.com/prod/cpx/theatrical/api"
KEY = "dcdac5601d864addbc2675a2e96cb1f8"   # public key used by cineplex.com itself
MOVIE_URL = "https://www.cineplex.com/movie/imax70-the-odyssey-the-imax-experience-in-7"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
STATE_FILE = os.environ.get("STATE_FILE", "seen_sessions.json")

# Notify about brand-new dates as well as extra showtimes on known dates.
ALERT_ON_NEW_TIMES = os.environ.get("ALERT_ON_NEW_TIMES", "1") != "0"


def get(url, attempts=3):
    """GET with retries, so one transient blip doesn't fail the whole run."""
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": KEY,
                    "Accept": "application/json",
                    "User-Agent": "personal-showtime-watcher/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:                      # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(2 * (i + 1))
    raise last


def push(title, body, priority="urgent"):
    if not NTFY_TOPIC:
        print("!! NTFY_TOPIC is not set - would have sent:")
        print(f"   {title}\n   {body}")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": "film_projector",
            "Click": MOVIE_URL,
        },
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30).read()


def fetch_sessions():
    """One call returns every 70mm session across all bookable dates."""
    data = get(f"{API}/v1/showtimes?language=en-us"
               f"&locationId={LOCATION_ID}&filmId={FILM_ID}")
    out = set()
    for th in data:
        for dd in th.get("dates", []):
            for mv in dd.get("movies", []):
                for ex in mv.get("experiences", []):
                    types = [str(t).lower() for t in ex.get("experienceTypes", [])]
                    if "70mm" not in types:
                        continue
                    for s in ex.get("sessions", []):
                        t = s.get("showStartDateTime") or s.get("startTime") or ""
                        if len(t) >= 16 and not s.get("isInThePast"):
                            out.add(t[:16])          # "YYYY-MM-DDTHH:MM"
    return out


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("seen", []))
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None                                   # None = no state yet


def save_state(seen):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"seen": sorted(seen)}, f, indent=1)
    os.replace(tmp, STATE_FILE)


def main():
    current = fetch_sessions()
    if not current:
        print("WARNING: API returned zero 70mm sessions - not updating state.")
        return 0                                      # never let this wipe the baseline

    dates = sorted({s[:10] for s in current})
    print(f"{len(current)} sessions across {len(dates)} dates "
          f"({dates[0]} -> {dates[-1]})")

    seen = load_state()
    if seen is None:
        save_state(current)
        print(f"First run: seeded {len(current)} sessions. Staying quiet.")
        return 0

    new = current - seen
    if not new:
        print("nothing new")
        return 0

    known_dates = {s[:10] for s in seen}
    new_dates = sorted({s[:10] for s in new} - known_dates)
    new_times = sorted(s for s in new if s[:10] in known_dates)

    if not new_dates and not (ALERT_ON_NEW_TIMES and new_times):
        save_state(current)
        print(f"{len(new_times)} new showtimes on known dates (alerts off)")
        return 0

    lines = []
    for d in new_dates:
        times = sorted(s[11:16] for s in new if s[:10] == d)
        lines.append(f"NEW DATE {d}: {', '.join(times)}")
    if ALERT_ON_NEW_TIMES:
        for s in new_times:
            lines.append(f"extra showtime {s[:10]} at {s[11:16]}")

    body = ("New Odyssey IMAX 70mm at Banque Scotia:\n"
            + "\n".join(lines[:15])
            + ("\n..." if len(lines) > 15 else "")
            + "\nBook now.")
    print(body)
    push("Odyssey 70mm tickets are up", body)
    save_state(current)                               # only after a successful push
    return 0


if __name__ == "__main__":
    sys.exit(main())
