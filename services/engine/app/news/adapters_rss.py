import time
from concurrent.futures import ThreadPoolExecutor, wait
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

    _MAX_WORKERS = 4
    _PER_FEED_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        feeds: Optional[List[Dict[str, str]]] = None,
        overall_timeout_seconds: float = 8.0,
    ):
        self.feeds = feeds if feeds is not None else DEFAULT_FEEDS
        self.overall_timeout_seconds = overall_timeout_seconds

    def fetch(self, team: str, since: datetime.datetime) -> List[RawArticle]:
        team_lower = team.lower()
        articles: List[RawArticle] = []
        seen_urls = set()

        if not self.feeds:
            return articles

        max_workers = min(len(self.feeds), self._MAX_WORKERS)
        deadline = time.monotonic() + max(0.0, self.overall_timeout_seconds)
        executor = ThreadPoolExecutor(max_workers=max_workers)
        future_to_index = {
            executor.submit(self._fetch_feed, feed_config, team_lower, since): index
            for index, feed_config in enumerate(self.feeds)
        }

        try:
            timeout = max(0.0, deadline - time.monotonic())
            done, not_done = wait(future_to_index, timeout=timeout)

            feed_results: Dict[int, List[RawArticle]] = {}
            for future in done:
                index = future_to_index[future]
                try:
                    feed_results[index] = future.result()
                except Exception:
                    feed_results[index] = []

            for index in sorted(feed_results):
                for article in feed_results[index]:
                    if article.url in seen_urls:
                        continue
                    articles.append(article)
                    seen_urls.add(article.url)

            for future in not_done:
                future.cancel()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        return articles

    def _fetch_feed(
        self,
        feed_config: Dict[str, str],
        team_lower: str,
        since: datetime.datetime,
    ) -> List[RawArticle]:
        feed_url = feed_config["url"]
        source_domain = feed_config["source_domain"]
        articles: List[RawArticle] = []

        try:
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=self._PER_FEED_TIMEOUT_SECONDS) as response:
                raw_data = response.read()

            feed_data = feedparser.parse(raw_data)

            # Check if it was malformed or failed
            if feed_data.get('bozo') and getattr(feed_data.bozo_exception, 'getMessage', lambda: '')() == 'timeout':
                return articles

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
                if not url:
                    continue

                article = RawArticle(
                    source_domain=source_domain,
                    url=url,
                    title=title,
                    body=body,
                    published_at=dt,
                )
                articles.append(article)

        except Exception:
            # Skip feed if any error occurs
            return []

        return articles
