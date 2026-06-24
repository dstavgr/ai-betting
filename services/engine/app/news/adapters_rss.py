import time
import datetime
import calendar
import urllib.request
from typing import Any, Dict, List, Optional
import feedparser # type: ignore

from app.news.adapters import NewsSourceAdapter
from app.news.models import RawArticle


DEFAULT_FEEDS = [
    {
        "url": "http://feeds.bbci.co.uk/sport/football/rss.xml",
        "source_domain": "bbc.com",
    },
    {
        "url": "https://www.theguardian.com/football/rss",
        "source_domain": "theguardian.com",
    },
    {
        "url": "https://www.skysports.com/rss/12040",
        "source_domain": "skysports.com",
    },
    {
        "url": "https://www.espn.com/espn/rss/soccer/news",
        "source_domain": "espn.com",
    },
]


class RSSNewsAdapter(NewsSourceAdapter):
    """Network-enabled RSS adapter for pulling real news articles."""

    def __init__(self, feeds: Optional[List[Dict[str, str]]] = None):
        self.feeds = feeds if feeds is not None else DEFAULT_FEEDS

    def fetch(self, team: str, since: datetime.datetime) -> List[RawArticle]:
        team_lower = team.lower()
        articles: List[RawArticle] = []
        seen_urls = set()

        for feed_config in self.feeds:
            feed_url = feed_config["url"]
            source_domain = feed_config["source_domain"]

            try:
                req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_data = response.read()

                feed_data = feedparser.parse(raw_data)

                # Check if it was malformed or failed
                if feed_data.get('bozo') and getattr(feed_data.bozo_exception, 'getMessage', lambda: '')() == 'timeout':
                    continue

                for entry in feed_data.get("entries", []):
                    title = entry.get("title", "")

                    body = ""
                    if "summary" in entry:
                        body = entry["summary"]
                    elif "content" in entry and len(entry["content"]) > 0:
                        body = entry["content"][0].get("value", "")

                    if not title and not body:
                        continue

                    # Filter by team name
                    if team_lower not in title.lower() and team_lower not in body.lower():
                        continue

                    # Parse date
                    published_parsed = entry.get("published_parsed")
                    if not published_parsed:
                        continue

                    try:
                        dt = datetime.datetime.fromtimestamp(calendar.timegm(published_parsed), tz=datetime.timezone.utc)
                    except (ValueError, OverflowError, TypeError):
                        continue

                    # Filter by since
                    if dt < since:
                        continue

                    url = entry.get("link")
                    if not url or url in seen_urls:
                        continue

                    article = RawArticle(
                        source_domain=source_domain,
                        url=url,
                        title=title,
                        body=body,
                        published_at=dt,
                    )
                    articles.append(article)
                    seen_urls.add(url)

            except Exception:
                # Skip feed if any error occurs
                continue

        return articles
