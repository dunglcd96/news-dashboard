import feedparser
import re
from flask import Flask, render_template, jsonify
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

SOURCES = {
    "Reuters": {
        "url": "https://feeds.reuters.com/reuters/topNews",
        "bias": "neutral",
        "color": "#185FA5"
    },
    "AP News": {
        "url": "https://feeds.apnews.com/apnews/topnews",
        "bias": "neutral",
        "color": "#0F6E56"
    },
    "Nikkei Asia": {
        "url": "https://asia.nikkei.com/rss/feed/bbe3a1f4",
        "bias": "neutral",
        "color": "#993C1D"
    },
    "Fox News": {
        "url": "https://feeds.foxnews.com/foxnews/world",
        "bias": "right",
        "color": "#A32D2D"
    },
}

CATEGORIES = {
    "Politics": ["election", "president", "government", "congress", "senate", "minister", "parliament", "policy", "vote", "diplomatic", "sanction", "treaty", "political"],
    "Economy": ["economy", "economic", "market", "stock", "trade", "inflation", "gdp", "bank", "finance", "currency", "recession", "investment", "oil", "price", "tariff"],
    "War & Conflict": ["war", "attack", "military", "troops", "missile", "bomb", "conflict", "ceasefire", "ukraine", "russia", "israel", "gaza", "weapon", "soldier", "killed"],
    "Technology": ["tech", "ai", "artificial intelligence", "cyber", "data", "software", "chip", "semiconductor", "elon", "tesla", "apple", "google", "microsoft", "openai"],
    "Asia": ["china", "japan", "korea", "taiwan", "india", "asean", "asia", "beijing", "tokyo", "seoul", "hong kong", "singapore", "vietnam", "thailand"],
    "Climate": ["climate", "environment", "carbon", "emission", "renewable", "energy", "flood", "drought", "temperature", "cop", "green", "solar", "fossil"],
    "Health": ["health", "disease", "virus", "pandemic", "vaccine", "hospital", "cancer", "who", "medicine", "drug", "outbreak", "mental health"],
}

def detect_category(title, summary):
    text = (title + " " + summary).lower()
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if keyword in text:
                return category
    return "General"

def extract_image(entry):
    # 1. media:content or media:thumbnail
    if hasattr(entry, "media_content") and entry.media_content:
        for m in entry.media_content:
            if m.get("type", "").startswith("image") and m.get("url"):
                return m["url"]
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url")
        if url:
            return url

    # 2. enclosures (podcasts/images)
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image") and enc.get("href"):
                return enc["href"]

    # 3. Parse img tag from summary/content
    html = ""
    if hasattr(entry, "summary"):
        html += entry.summary
    if hasattr(entry, "content") and entry.content:
        html += entry.content[0].get("value", "")
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
    if img_match:
        return img_match.group(1)

    return None

def fetch_news():
    all_articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for source_name, info in SOURCES.items():
        try:
            feed = feedparser.parse(info["url"])
            for entry in feed.entries:
                pub_dt = None
                published_str = ""

                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        published_str = pub_dt.strftime("%d/%m %H:%M")
                    except Exception:
                        pass

                if pub_dt and pub_dt < cutoff:
                    continue

                summary = ""
                if hasattr(entry, "summary"):
                    clean = re.sub(r"<[^>]+>", "", entry.summary)
                    summary = clean[:200]

                title = entry.get("title", "No title")
                category = detect_category(title, summary)
                image = extract_image(entry)

                all_articles.append({
                    "source": source_name,
                    "color": info["color"],
                    "bias": info["bias"],
                    "title": title,
                    "link": entry.get("link", "#"),
                    "published": published_str,
                    "pub_dt": pub_dt.isoformat() if pub_dt else "",
                    "summary": summary,
                    "category": category,
                    "image": image,
                })
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    all_articles.sort(key=lambda x: x["pub_dt"], reverse=True)
    return all_articles

@app.route("/")
def index():
    articles = fetch_news()
    sources = list(SOURCES.keys())
    categories = list(CATEGORIES.keys()) + ["General"]
    now = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    return render_template("index.html",
                           articles=articles,
                           sources=sources,
                           categories=categories,
                           now=now)

@app.route("/api/news")
def api_news():
    articles = fetch_news()
    return jsonify(articles)

if __name__ == "__main__":
    print("\nDashboard dang chay tai: http://127.0.0.1:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
