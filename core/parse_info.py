import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

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
) -> dict | None:
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
    pub_str = snippet.get("publishedAt", "")
    published_at = (
        datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else None
    )

    return {
        "title": snippet.get("title", ""),
        "description": snippet.get("description", ""),
        "tags": snippet.get("tags", []),
        "engagement": int(statistics.get("likeCount", 0))
        + int(statistics.get("commentCount", 0)),
        "views": int(statistics.get("viewCount", 0)),
        "duration": parse_iso_duration_to_seconds(
            content_details.get("duration", "PT0S")
        )
        // 60,
        "published_at": published_at,
    }


def fetch_page_info(
    url: str,
    platform: str = "unknown",
    proxy: str | None = None,
    proxy_type: str = "socks5",
) -> dict | None:
    info = {}
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

    soup = BeautifulSoup(response.text, "html.parser")

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        info["title"] = og_title["content"]
    else:
        title_tag = soup.find("title")
        if title_tag:
            info["title"] = title_tag.text.strip()

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        info["description"] = og_desc["content"]
    else:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            info["description"] = meta_desc["content"]

    if platform == "habr":
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            content = meta_keywords.get("content")
            if content and isinstance(content, str):
                info["tags"] = [
                    t.strip().lower() for t in content.split(",") if t.strip()
                ]
        if not info.get("tags", 0):
            hubs = soup.find_all(class_="tm-publication-hubs__hub")
            info["tags"] = []
            for hub in hubs:
                text = hub.get_text(strip=True)
                if text:
                    info["tags"].append(text.lower())
    else:
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords:
            content = meta_keywords.get("content")
            if content and isinstance(content, str):
                info["tags"] = [
                    t.strip().lower() for t in content.split(",") if t.strip()
                ]

    time_tag = soup.find("time", datetime=True)
    if time_tag:
        dt_str = time_tag.get("datetime")
        if isinstance(dt_str, str):
            try:
                info["published_at"] = datetime.fromisoformat(
                    dt_str.replace("Z", "+00:00")
                )
            except ValueError:
                pass

    try:
        pinia_script = soup.find(
            "script",
            string=lambda t: isinstance(t, str) and "window.__PINIA_STATE__" in t,
        )
        if pinia_script:
            raw = pinia_script.string
            if not isinstance(raw, str):
                raise ParseError("PINIA script has no string content")
            start = raw.index("window.__PINIA_STATE__=") + len(
                "window.__PINIA_STATE__="
            )
            end = raw.index("};(function", start) + 1
            json_str = raw[start:end]
            data = json.loads(json_str)

            article_id = list(data["articlesList"]["articlesList"].keys())[0]
            stats = data["articlesList"]["articlesList"][article_id]["statistics"]

            info["reading_time"] = data["articlesList"]["articlesList"][article_id].get(
                "readingTime"
            )
            info["engagement"] = (
                int(stats.get("favoritesCount", 0))
                + int(stats.get("commentsCount", 0))
                + int(stats.get("score", 0))
            )
            info["views"] = stats.get("readingCount", 0)
    except Exception as e:
        raise ParseError(f"Не удалось распарсить PINIA данные: {e}") from e

    return {
        "title": info.get("title", "Без названия"),
        "description": info.get("description", None),
        "tags": info.get("tags", None),
        "duration": info.get("reading_time", 0),
        "views": info.get("views", 0),
        "engagement": info.get("engagement", 0),
        "published_at": info.get("published_at", None),
    }
