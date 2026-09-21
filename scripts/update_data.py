#!/usr/bin/env python3
"""note と Substack の公開情報を読み、site/data.json を作る。標準ライブラリのみ。鍵は不要。

取得に失敗した項目は、前回の data.json の値を残す（ページが空にならないように）。
"""
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

NOTE_USER = "wiseowllab"
SUBSTACK_FEED = "https://wiseowllab.substack.com/feed"
NOTE_MAGAZINE = "md3c6f20519b2"  # 「Wise Owl Cafe：灯りのそばの物語」
LATEST = 5

OUT = Path(__file__).resolve().parent.parent / "data.json"
JST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (owl-site data updater)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clean_title(t):
    t = re.sub(r"^🦉\s*", "", t.strip())
    return t


def feed_items(url, limit):
    root = ET.fromstring(get(url))
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate")
        if not (title and link and pub):
            continue
        d = parsedate_to_datetime(pub).astimezone(JST).date().isoformat()
        items.append({"title": clean_title(title), "url": link, "date": d})
        if len(items) >= limit:
            break
    return items


def magazine_count():
    """noteのマガジンページに表示される記事数（note_count）を読む。"""
    d = json.loads(get(f"https://note.com/api/v1/magazines/{NOTE_MAGAZINE}"))["data"]
    n = d["note_count"]
    if not isinstance(n, int) or n <= 0:
        raise RuntimeError(f"想定外の値: {n!r}")
    return n


def main():
    try:
        data = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    data.setdefault("note", {})
    data.setdefault("substack", {})
    errors = []

    try:
        data["note"]["latest"] = feed_items(f"https://note.com/{NOTE_USER}/rss", LATEST)
    except Exception as e:
        errors.append(f"note新着: {e}")
    try:
        data["note"]["magazine_count"] = magazine_count()
        data["note"].pop("ss_count", None)
        data["note"].pop("total", None)
    except Exception as e:
        errors.append(f"note本数: {e}")
    try:
        data["substack"]["latest"] = feed_items(SUBSTACK_FEED, LATEST)
    except Exception as e:
        errors.append(f"Substack: {e}")

    if errors:
        print("取得できなかった項目（前回の値を残します）:", *errors, sep="\n  ", file=sys.stderr)

    # 内容（updated以外）が変わった時だけ、updated を更新して保存する
    def body(d):
        return {k: v for k, v in d.items() if k != "updated"}
    try:
        old_data = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        old_data = {}
    if body(data) != body(old_data):
        data["updated"] = datetime.now(JST).isoformat(timespec="minutes")
    else:
        data["updated"] = old_data.get("updated")

    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if text != old:
        OUT.write_text(text, encoding="utf-8")
        print("data.json を更新しました")
    else:
        print("変更なし")
    # 1つでも失敗したら異常終了にする（GitHubの実行が赤くなり、気づける）。値は前回のまま残る
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
