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


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "ja,en;q=0.8",
}
READER_HEADERS = {"User-Agent": "Feedly/1.0 (+http://www.feedly.com/fetcher.html; like FeedFetcher-Google)", "Accept": "*/*"}


def get_with(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def substack_items(limit):
    """Substackの新着。RSS（ブラウザ風／フィード読み取り風）→ 記事一覧API の順に試す。"""
    base = SUBSTACK_FEED.rsplit("/feed", 1)[0]
    tries = []
    for name, hdr in (("RSS/ブラウザ風", BROWSER_HEADERS), ("RSS/リーダー風", READER_HEADERS)):
        def run(hdr=hdr):
            root = ET.fromstring(get_with(SUBSTACK_FEED, hdr))
            items = []
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                pub = it.findtext("pubDate")
                if title and link and pub:
                    d = parsedate_to_datetime(pub).astimezone(JST).date().isoformat()
                    items.append({"title": clean_title(title), "url": link, "date": d})
                if len(items) >= limit:
                    break
            return items
        tries.append((name, run))

    def api():
        hdr = dict(BROWSER_HEADERS, Accept="application/json")
        posts = json.loads(get_with(f"{base}/api/v1/archive?sort=new&limit={limit}", hdr))
        items = []
        for x in posts:
            d = (x.get("post_date") or "")[:10]
            if x.get("title") and x.get("canonical_url") and d:
                items.append({"title": clean_title(x["title"]), "url": x["canonical_url"], "date": d})
        return items[:limit]
    tries.append(("記事一覧API", api))

    reasons = []
    for name, fn in tries:
        try:
            items = fn()
            if items:
                return items
            reasons.append(f"{name}: 0件")
        except Exception as e:
            reasons.append(f"{name}: {e}")
    raise RuntimeError(" / ".join(reasons))



SUBSTACK_HANDLE = "wiseowllab"
NOTES = 3


def substack_notes(limit):
    """SubstackのNotes（自分の投稿のみ。他の人への返信は除く）。非公式の入口を使う。"""
    hdr = dict(BROWSER_HEADERS, Accept="application/json")
    prof = json.loads(get_with(f"https://substack.com/api/v1/user/{SUBSTACK_HANDLE}/public_profile", hdr))
    uid = prof["id"]
    feed = json.loads(get_with(f"https://substack.com/api/v1/reader/feed/profile/{uid}", hdr))
    notes = []
    for it in feed.get("items", []):
        c = it.get("comment")
        if not c or c.get("user_id") != uid or c.get("ancestor_path"):
            continue  # 自分のNotesだけ（返信・他人の投稿は除く）
        body = re.sub(r"\s+", " ", (c.get("body") or "")).strip()
        if not body or not c.get("date") or not c.get("id"):
            continue
        text = body if len(body) <= 48 else body[:48].rstrip() + "…"
        d = parsedate_to_datetime(c["date"]).astimezone(JST).date().isoformat() if not c["date"][:4].isdigit() else             datetime.fromisoformat(c["date"].replace("Z", "+00:00")).astimezone(JST).date().isoformat()
        notes.append({"text": text, "url": f"https://substack.com/@{SUBSTACK_HANDLE}/note/c-{c['id']}", "date": d, "_k": c["date"]})
    notes.sort(key=lambda n: n["_k"], reverse=True)
    for n in notes:
        n.pop("_k")
    if not notes:
        raise RuntimeError("Notesが0件")
    return notes[:limit]


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
    warnings = []

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
        data["substack"]["latest"] = substack_items(LATEST)
    except Exception as e:
        warnings.append(f"Substack: {e}")
    try:
        data["substack"]["notes"] = substack_notes(NOTES)
    except Exception as e:
        warnings.append(f"SubstackのNotes: {e}")

    for msg in warnings:  # 失敗しても保存は続ける。実行画面に警告として残す
        print("::warning title=Substackを取得できませんでした（前回の値を残します）::" + str(msg).replace(chr(10), " ")[:400])
    if errors:
        print("取得できなかった項目（前回の値を残します）:", *errors, sep="\n  ", file=sys.stderr)
        for msg in errors:  # GitHubの実行画面の「Annotations」に、失敗した項目と理由を表示する
            print("::error title=データ取得に失敗::" + str(msg).replace(chr(10), " ")[:300])

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
