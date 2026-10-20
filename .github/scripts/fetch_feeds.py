"""Fetch the homepage RSS feeds and write them to feeds.json.

Run by .github/workflows/update-feeds.yml. If a feed fails to load, the
previous items for that feed are kept so the page never goes blank.
"""
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

MAX_ITEMS = 6
OUTPUT = pathlib.Path(__file__).resolve().parents[2] / "feeds.json"
FEEDS = {
    "hackernews": "https://feeds.feedburner.com/TheHackersNews",
    "hibp": "https://haveibeenpwned.com/feed/breaches/",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WLHS-APCyber feed updater)"}


def to_iso(pub_date):
    try:
        return parsedate_to_datetime(pub_date).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as res:
        root = ET.fromstring(res.read())
    items = []
    for item in root.iter("item"):
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "pubDate": to_iso(item.findtext("pubDate")),
        })
        if len(items) == MAX_ITEMS:
            break
    if not items:
        raise ValueError("feed returned no items")
    return items


def main():
    try:
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))["feeds"]
    except (FileNotFoundError, KeyError, ValueError):
        previous = {}

    feeds = {}
    for key, url in FEEDS.items():
        try:
            feeds[key] = {"url": url, "items": fetch(url)}
            print(f"{key}: {len(feeds[key]['items'])} items")
        except Exception as err:
            print(f"{key}: failed ({err}); keeping previous items")
            feeds[key] = previous.get(key, {"url": url, "items": []})

    # Only rewrite the file when the items changed, so no-op runs don't commit.
    if feeds == previous:
        print("No changes")
        return
    data = {"updated": datetime.now(timezone.utc).isoformat(), "feeds": feeds}
    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
