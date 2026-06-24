import datetime
import pytest

from app.news.adapters_rss import RSSNewsAdapter
from app.news.models import RawArticle


@pytest.fixture
def mock_feedparser(monkeypatch):
    def _mock_parse(raw_data):
        # Default mock behaviour, can be overridden by specific tests by patching again if needed
        return {
            "entries": []
        }

    class MockResponse:
        def read(self):
            return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", lambda raw_data: _mock_parse("mock"))


def test_rss_adapter_team_name_filtering(monkeypatch):
    def _mock_parse(raw_data):
        return {
            "entries": [
                {
                    "title": "Arsenal win the match",
                    "summary": "Great game.",
                    "published_parsed": (2024, 1, 10, 12, 0, 0, 2, 10, 0),
                    "link": "http://example.com/1"
                },
                {
                    "title": "Chelsea draw",
                    "summary": "Arsenal played well in the second half.",
                    "published_parsed": (2024, 1, 10, 12, 0, 0, 2, 10, 0),
                    "link": "http://example.com/2"
                },
                {
                    "title": "Man Utd win",
                    "summary": "No mention of the target team here.",
                    "published_parsed": (2024, 1, 10, 12, 0, 0, 2, 10, 0),
                    "link": "http://example.com/3"
                }
            ]
        }


    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([{"url": "mock://url", "source_domain": "mock.com"}])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 2
    urls = {a.url for a in articles}
    assert "http://example.com/1" in urls
    assert "http://example.com/2" in urls


def test_rss_adapter_since_filtering(monkeypatch):
    def _mock_parse(raw_data):
        return {
            "entries": [
                {
                    "title": "Arsenal news old",
                    "summary": "old news",
                    "published_parsed": (2023, 12, 31, 12, 0, 0, 6, 365, 0),
                    "link": "http://example.com/old"
                },
                {
                    "title": "Arsenal news new",
                    "summary": "new news",
                    "published_parsed": (2024, 1, 2, 12, 0, 0, 1, 2, 0),
                    "link": "http://example.com/new"
                }
            ]
        }

    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([{"url": "mock://url", "source_domain": "mock.com"}])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 1
    assert articles[0].url == "http://example.com/new"


def test_rss_adapter_malformed_entries(monkeypatch):
    def _mock_parse(raw_data):
        return {
            "entries": [
                {
                    "title": "Arsenal news no date",
                    "summary": "no date",
                    "link": "http://example.com/nodate"
                },
                {
                    "title": "Arsenal news invalid date",
                    "summary": "invalid date",
                    "published_parsed": "not a struct_time",
                    "link": "http://example.com/invaliddate"
                },
                {
                    # No title or summary
                    "published_parsed": (2024, 1, 2, 12, 0, 0, 1, 2, 0),
                    "link": "http://example.com/notitle"
                },
                {
                    "title": "Arsenal news valid",
                    "summary": "valid",
                    "published_parsed": (2024, 1, 2, 12, 0, 0, 1, 2, 0),
                    "link": "http://example.com/valid"
                }
            ]
        }

    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([{"url": "mock://url", "source_domain": "mock.com"}])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 1
    assert articles[0].url == "http://example.com/valid"


def test_rss_adapter_url_deduplication(monkeypatch):
    def _mock_parse(raw_data):
        return {
            "entries": [
                {
                    "title": "Arsenal news 1",
                    "summary": "news",
                    "published_parsed": (2024, 1, 2, 12, 0, 0, 1, 2, 0),
                    "link": "http://example.com/dup"
                },
                {
                    "title": "Arsenal news 2",
                    "summary": "news",
                    "published_parsed": (2024, 1, 2, 13, 0, 0, 1, 2, 0),
                    "link": "http://example.com/dup"
                }
            ]
        }

    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([
        {"url": "mock://url1", "source_domain": "mock1.com"},
        {"url": "mock://url2", "source_domain": "mock2.com"}
    ])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 1
    assert articles[0].title == "Arsenal news 1"


def test_rss_adapter_body_fallback(monkeypatch):
    def _mock_parse(raw_data):
        return {
            "entries": [
                {
                    "title": "Arsenal match",
                    # No summary, fallback to content
                    "content": [{"value": "Detailed content about Arsenal."}],
                    "published_parsed": (2024, 1, 2, 12, 0, 0, 1, 2, 0),
                    "link": "http://example.com/content"
                }
            ]
        }

    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([{"url": "mock://url", "source_domain": "mock.com"}])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 1
    assert articles[0].body == "Detailed content about Arsenal."
    assert articles[0].title == "Arsenal match"

def test_rss_adapter_feed_exception(monkeypatch):
    def _mock_parse(raw_data):
        raise Exception("Network error")


    class MockResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"dummy"
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=None: MockResponse())
    monkeypatch.setattr("feedparser.parse", _mock_parse)

    adapter = RSSNewsAdapter([{"url": "mock://url", "source_domain": "mock.com"}])

    since = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    # Should not raise exception
    articles = adapter.fetch("Arsenal", since)

    assert len(articles) == 0
