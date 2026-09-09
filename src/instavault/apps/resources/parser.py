import json
import re
from contextlib import suppress
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from core.exceptions import (
    APIResponseError,
    ParseError,
    ProxyRequestError,
    ResourceNotFoundError,
)


def parse_iso_duration_to_seconds(duration: str) -> int:
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    match = pattern.match(duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def fetch_youtube_video_info(
    video_id: str,
    api_key: str,
    proxy: str | None = None,
    proxy_type: str = "socks5",
) -> dict[str, object] | None:
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "id": video_id,
        "key": api_key,
        "part": "snippet,statistics,contentDetails",
    }

    proxies = None
    if proxy:
        proxy_url = proxy if "://" in proxy else f"{proxy_type}://{proxy}"
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.get(url, params=params, proxies=proxies, timeout=30)
    except requests.RequestException as e:
        raise ProxyRequestError(e, proxy) from e

    if response.status_code != 200:
        raise APIResponseError(response.status_code, response.text)

    data = response.json()

    if not data.get("items"):
        raise ResourceNotFoundError(video_id, "youtube")

    item = data["items"][0]
    snippet = item["snippet"]
    statistics = item.get("statistics", {})
    content_details = item.get("contentDetails", {})
    pub_str = snippet.get("publishedAt")
    published_at = datetime.fromisoformat(pub_str) if pub_str else None

    return {
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", []),
        "engagement": int(statistics.get("likeCount", 0)) + int(statistics.get("commentCount", 0)),
        "views": int(statistics.get("viewCount", 0)),
        "duration": parse_iso_duration_to_seconds(content_details.get("duration", "PT0S")) // 60,
        "published_at": published_at,
    }


def fetch_page_info(
    url: str,
    platform: str = "unknown",
    proxy: str | None = None,
    proxy_type: str = "socks5",
) -> dict[str, object]:
    response = _fetch_html(url, proxy, proxy_type)
    soup = BeautifulSoup(response.text, "html.parser")

    info: dict[str, object] = {}
    info["title"] = _extract_title(soup)
    info["description"] = _extract_description(soup)
    info["tags"] = _extract_tags(soup, platform)
    info["published_at"] = _extract_published_at(soup)

    pinia = _extract_pinia(soup)
    info.update(pinia)

    return {
        "title": info.get("title") or "Без названия",
        "description": info.get("description"),
        "tags": info.get("tags"),
        "duration": info.get("reading_time", 0),
        "views": info.get("views", 0),
        "engagement": info.get("engagement", 0),
        "published_at": info.get("published_at"),
    }


def _fetch_html(url: str, proxy: str | None, proxy_type: str) -> requests.Response:
    proxies = None
    if proxy:
        proxy_url = proxy if "://" in proxy else f"{proxy_type}://{proxy}"
        proxies = {"http": proxy_url, "https": proxy_url}

    try:
        response = requests.get(
            url,
            proxies=proxies,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )
    except requests.RequestException as e:
        raise ProxyRequestError(e, proxy) from e

    if response.status_code != 200:
        raise APIResponseError(response.status_code, response.text)

    return response


def _extract_title(soup: BeautifulSoup) -> str | None:
    og_title = soup.find("meta", property="og:title")
    if og_title:
        content = og_title.get("content")
        if isinstance(content, str) and content:
            return content

    title_tag = soup.find("title")
    if title_tag:
        return title_tag.text.strip()
    return None


def _extract_description(soup: BeautifulSoup) -> str | None:
    og_desc = soup.find("meta", property="og:description")
    if og_desc:
        content = og_desc.get("content")
        if isinstance(content, str) and content:
            return content

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        content = meta_desc.get("content")
        if isinstance(content, str) and content:
            return content
    return None


def _extract_tags(soup: BeautifulSoup, platform: str) -> list[str]:
    if platform == "habr":
        return _extract_habr_tags(soup)

    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords:
        content = meta_keywords.get("content")
        if content and isinstance(content, str):
            return [t.strip().lower() for t in content.split(",") if t.strip()]
    return []


def _extract_habr_tags(soup: BeautifulSoup) -> list[str]:
    meta_keywords = soup.find("meta", attrs={"name": "keywords"})
    if meta_keywords:
        content = meta_keywords.get("content")
        if isinstance(content, str) and content:
            return [t.strip().lower() for t in content.split(",") if t.strip()]

    hubs = soup.find_all(class_="tm-publication-hubs__hub")
    tags: list[str] = []
    for hub in hubs:
        text = hub.get_text(strip=True)
        if text:
            tags.append(text.lower())
    return tags


def _extract_published_at(soup: BeautifulSoup) -> datetime | None:
    time_tag = soup.find("time", datetime=True)
    if not time_tag:
        return None

    dt_str = time_tag.get("datetime")
    if not isinstance(dt_str, str):
        return None

    with suppress(ValueError):
        return datetime.fromisoformat(dt_str)
    return None


def _extract_pinia(soup: BeautifulSoup) -> dict[str, object]:
    pinia_script = soup.find(
        "script",
        string=lambda t: isinstance(t, str) and "window.__PINIA_STATE__" in t,
    )
    if not pinia_script:
        return {}

    try:
        return _parse_pinia_script(pinia_script)
    except Exception as e:
        raise ParseError(f"Не удалось распарсить PINIA данные: {e}") from e


def _parse_pinia_script(pinia_script: Tag) -> dict[str, object]:
    raw = pinia_script.string
    if not isinstance(raw, str):
        raise ParseError("PINIA script has no string content")

    start = raw.index("window.__PINIA_STATE__=") + len("window.__PINIA_STATE__=")
    end = raw.index("};(function", start) + 1
    data = json.loads(raw[start:end])

    article_id = next(iter(data["articlesList"]["articlesList"].keys()))
    article = data["articlesList"]["articlesList"][article_id]
    stats = article["statistics"]

    return {
        "reading_time": article.get("readingTime"),
        "engagement": (
            int(stats.get("favoritesCount", 0))
            + int(stats.get("commentsCount", 0))
            + int(stats.get("score", 0))
        ),
        "views": stats.get("readingCount", 0),
    }
