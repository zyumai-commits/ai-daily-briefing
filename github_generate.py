"""Generate AI card-news images + a GitHub Pages site.

Reads NEWS_FEEDS (comma separated RSS urls) and OPENAI_API_KEY / OPENAI_MODEL
from the environment, picks recent AI news, asks the model to turn each item
into a short Korean card (title + bullets), and renders PNG cards plus an
index.html into ./site. Only feedparser, Pillow, and requests are required
(no openai SDK — the Chat Completions endpoint is called directly).
"""
import json
import os
import re
import textwrap
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from PIL import Image, ImageDraw, ImageFont

# ---------- config ----------
DEFAULT_FEEDS = [
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://www.artificialintelligence-news.com/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://www.technologyreview.com/feed/",
]
FEEDS = [f.strip() for f in os.environ.get("NEWS_FEEDS", "").split(",") if f.strip()] or DEFAULT_FEEDS
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
MAX_CARDS = int(os.environ.get("MAX_CARDS", "5"))
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "48"))

FONT_DIR = "/usr/share/fonts/opentype/noto"
FONT_BOLD = os.path.join(FONT_DIR, "NotoSansCJK-Bold.ttc")
FONT_REGULAR = os.path.join(FONT_DIR, "NotoSansCJK-Regular.ttc")

OUT_DIR = "site"
IMG_DIR = os.path.join(OUT_DIR, "images")


def strip_html(text):
    return re.sub("<[^<]+?>", "", text or "").strip()


def collect_entries():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=LOOKBACK_HOURS)
    entries = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[warn] feed failed: {url} ({e})")
            continue
        for e in feed.entries:
            published = None
            for key in ("published_parsed", "updated_parsed"):
                if getattr(e, key, None):
                    published = datetime(*e[key][:6], tzinfo=timezone.utc)
                    break
            entries.append({
                "title": e.get("title", "").strip(),
                "summary": e.get("summary", e.get("description", "")).strip(),
                "link": e.get("link", ""),
                "source": feed.feed.get("title", url),
                "published": published,
            })

    fresh = [e for e in entries if e["published"] and e["published"] >= cutoff]
    pool = fresh if len(fresh) >= MAX_CARDS else entries
    pool.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    seen_titles = set()
    picked = []
    for e in pool:
        key = e["title"].lower()
        if not e["title"] or key in seen_titles:
            continue
        seen_titles.add(key)
        picked.append(e)
        if len(picked) >= MAX_CARDS:
            break
    return picked


def summarize_kr(entry):
    prompt = (
        "다음 AI 뉴스를 한국어 카드뉴스용으로 요약해줘.\n"
        f"제목: {entry['title']}\n"
        f"본문 요약: {strip_html(entry['summary'])[:800]}\n\n"
        "JSON으로만 답해. 형식:\n"
        '{"title_kr": "18자 이내 헤드라인", "bullets": ["핵심1", "핵심2", "핵심3"]}\n'
        "bullets는 각각 25자 이내, 개조식으로 작성."
    )
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    content = content.strip("`")
    if content.lower().startswith("json"):
        content = content[4:].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        return json.loads(content[start:end + 1])


def wrap_kr(text, width):
    return textwrap.wrap(text, width=width, break_long_words=True, break_on_hyphens=False)


def render_card(index, total, entry, card, date_str):
    W, H = 1080, 1080
    bg = (18, 20, 28)
    accent = (255, 209, 102)
    fg = (245, 245, 245)
    sub = (170, 175, 190)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    font_tag = ImageFont.truetype(FONT_BOLD, 34)
    font_title = ImageFont.truetype(FONT_BOLD, 64)
    font_body = ImageFont.truetype(FONT_REGULAR, 40)
    font_footer = ImageFont.truetype(FONT_REGULAR, 28)

    draw.rectangle([(0, 0), (W, 12)], fill=accent)
    draw.text((60, 60), f"AI 카드뉴스 {index}/{total}", font=font_tag, fill=accent)
    draw.text((60, 110), date_str, font=font_footer, fill=sub)

    y = 220
    for line in wrap_kr(card["title_kr"], 14):
        draw.text((60, y), line, font=font_title, fill=fg)
        y += 78

    y += 40
    for bullet in card.get("bullets", [])[:3]:
        for i, line in enumerate(wrap_kr(bullet, 22)):
            prefix = "· " if i == 0 else "  "
            draw.text((60, y), prefix + line, font=font_body, fill=fg)
            y += 56
        y += 16

    draw.line([(60, H - 140), (W - 60, H - 140)], fill=(60, 63, 75), width=2)
    for line in wrap_kr(entry["source"], 40)[:1]:
        draw.text((60, H - 110), line, font=font_footer, fill=sub)

    path = os.path.join(IMG_DIR, f"card_{index}.png")
    img.save(path, "PNG")
    return path


def build_index_html(cards, date_str):
    sections = []
    for i, c in enumerate(cards):
        title = c["card"]["title_kr"]
        bullets = c["card"].get("bullets", [])
        link = c["entry"]["link"]
        source = c["entry"]["source"]
        bullet_html = "".join(f"<li>{b}</li>" for b in bullets)
        sections.append(
            "\n        <section class=\"card\">\n"
            f'          <img src="images/card_{i + 1}.png" alt="{title}">\n'
            f"          <h2>{title}</h2>\n"
            f"          <ul>{bullet_html}</ul>\n"
            f'          <a class="src" href="{link}" target="_blank" rel="noopener">원문: {source}</a>\n'
            "        </section>"
        )
    items = "\n".join(sections)
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 카드뉴스 - {date_str}</title>
<style>
  body {{ background:#0f1116; color:#eee; font-family: 'Noto Sans KR', sans-serif; margin:0; padding:24px; }}
  h1 {{ font-size:28px; margin-bottom:4px; }}
  .date {{ color:#9aa; margin-bottom:24px; }}
  .card {{ max-width:520px; margin:0 auto 40px; background:#161923; border-radius:16px; overflow:hidden; box-shadow:0 6px 20px rgba(0,0,0,.4); }}
  .card img {{ width:100%; display:block; }}
  .card h2 {{ padding:16px 20px 0; font-size:20px; }}
  .card ul {{ padding:8px 36px 16px; margin:0; color:#ccc; }}
  .card .src {{ display:block; padding:0 20px 16px; color:#7fb0ff; font-size:13px; text-decoration:none; }}
</style>
</head>
<body>
  <h1>오늘의 AI 카드뉴스</h1>
  <div class="date">{date_str}</div>
  {items}
</body>
</html>"""
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    date_str = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    entries = collect_entries()
    if not entries:
        raise SystemExit("수집된 뉴스가 없습니다. NEWS_FEEDS를 확인하세요.")

    cards = []
    for entry in entries:
        try:
            card = summarize_kr(entry)
        except Exception as e:
            print(f"[warn] summarize 실패, 원문 제목 사용: {entry['title']} ({e})")
            card = {"title_kr": entry["title"][:18], "bullets": [strip_html(entry["summary"])[:25]]}
        cards.append({"entry": entry, "card": card})

    for i, c in enumerate(cards, start=1):
        render_card(i, len(cards), c["entry"], c["card"], date_str)

    build_index_html(cards, date_str)

    data = {
        "date": date_str,
        "cards": [
            {
                "title_kr": c["card"]["title_kr"],
                "bullets": c["card"].get("bullets", []),
                "source": c["entry"]["source"],
                "link": c["entry"]["link"],
                "image": f"images/card_{i+1}.png",
            }
            for i, c in enumerate(cards)
        ],
    }
    with open(os.path.join(OUT_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"생성 완료: 카드 {len(cards)}개")


if __name__ == "__main__":
    main()
