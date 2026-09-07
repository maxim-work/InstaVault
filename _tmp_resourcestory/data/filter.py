import re
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from core.enum import ResourcePlatform
from core.models.resource import Resource, ResourceKind, ResourceStatus, ResourceType
from data.exceptions import InvalidFilterError

TRANSLIT_MAP: dict[str, str] = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


@dataclass
class ResourceFilter:
    tg_id: int

    resource_type: ResourceType | None = None
    status: ResourceStatus | None = ResourceStatus.TO_TEACH
    platform: ResourcePlatform | None = None
    kind: ResourceKind | None = None
    tags: list[str] | None = None

    sort_by_my_rating: bool = True
    my_rating_min: int | None = None
    sort_by_rating: bool = True
    rating_min: float | None = None

    newest_published: bool = True
    oldest_published: bool = False
    uncompleted_only: bool = True
    recently_completed: bool = False
    long_ago_completed: bool = False

    keywords: str | None = None
    max_duration: int | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        if self.newest_published and self.oldest_published:
            raise InvalidFilterError(
                "newest_published и oldest_published не могут быть True одновременно"
            )
        if self.recently_completed and self.long_ago_completed:
            raise InvalidFilterError(
                "recently_completed и long_ago_completed не могут быть True одновременно"
            )


def levenshtein_ratio(s1: str, s2: str) -> float:
    """How similar two strings are: 1.0 means identical, 0.0 means completely different.

    Also checks transliterated versions for better matching.
    """
    if not s1 or not s2:
        return 0.0

    original_ratio = _calc_levenshtein(s1, s2)
    s1_translit = _transliterate(s1)
    s2_translit = _transliterate(s2)

    translit_ratio = _calc_levenshtein(s1_translit, s2_translit)
    cross_ratio1 = _calc_levenshtein(s1, s2_translit)
    cross_ratio2 = _calc_levenshtein(s1_translit, s2)

    return max(original_ratio, translit_ratio, cross_ratio1, cross_ratio2)


def _transliterate(text: str) -> str:
    result = ""

    for char in text.lower():
        result += TRANSLIT_MAP.get(char, char)

    return result


def calculate_scores(
    resources: list[Resource],
    f: ResourceFilter,
) -> list[tuple[Resource, int]]:
    """Returns a list of (resource, score) pairs, sorted by score descending.

    First filters by keywords, then scores remaining resources.
    """
    if f.keywords:
        filtered_resources = [r for r in resources if _check_keywords_match(r, f.keywords)]
    else:
        filtered_resources = resources

    with_published = [r for r in filtered_resources if r.published_at is not None]
    with_completed = [r for r in filtered_resources if r.completed_at is not None]

    by_published_new = sorted(
        with_published,
        key=lambda r: cast("datetime", r.published_at),
        reverse=True,
    )
    by_published_old = by_published_new[::-1]

    by_completed_new = sorted(
        with_completed,
        key=lambda r: cast("datetime", r.completed_at),
        reverse=True,
    )
    by_completed_old = by_completed_new[::-1]

    scored: list[tuple[Resource, int]] = []

    for resource in filtered_resources:
        score = _score_one(
            resource,
            f,
            by_published_new,
            by_published_old,
            by_completed_new,
            by_completed_old,
        )
        scored.append((resource, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[: f.limit]


def _calc_levenshtein(s1: str, s2: str) -> float:
    len1, len2 = len(s1), len(s2)

    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev = list(range(len2 + 1))

    for i in range(1, len1 + 1):
        curr = [i] + [0] * len2

        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)

        prev = curr

    distance = prev[len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


def _check_keywords_match(resource: Resource, keywords: str) -> bool:
    if not keywords:
        return True

    search_text = " ".join(
        [
            resource.title,
            " ".join(resource.tags),
            resource.description or "",
        ]
    ).lower()

    query_words = [w for w in re.split(r"\s+", keywords.lower().strip()) if w]

    for q_word in query_words:
        if q_word in search_text:
            continue

        text_words = set(re.split(r"\s+", search_text))
        found = any(levenshtein_ratio(q_word, t_word) >= 0.8 for t_word in text_words)

        if not found:
            return False

    return True


def _score_one(
    resource: Resource,
    f: ResourceFilter,
    by_published_new: list[Resource],
    by_published_old: list[Resource],
    by_completed_new: list[Resource],
    by_completed_old: list[Resource],
) -> int:
    score = 0
    score += _score_keywords(resource, f)
    score += _score_tags(resource, f)
    score += _score_my_rating(resource, f)
    score += _score_platform_rating(resource, f)
    score += _score_published(resource, f, by_published_new, by_published_old)
    score += _score_completed(resource, f, by_completed_new, by_completed_old)
    score += _score_uncompleted(resource, f)
    return score


def _score_keywords(resource: Resource, f: ResourceFilter) -> int:
    if not f.keywords:
        return 0

    search_text = " ".join(
        [resource.title, " ".join(resource.tags), resource.description or ""]
    ).lower()
    query_words = [w for w in re.split(r"\s+", f.keywords.lower().strip()) if w]

    score = 0
    for q_word in query_words:
        score += _score_one_keyword(q_word, resource, search_text)
    return score


def _score_one_keyword(q_word: str, resource: Resource, search_text: str) -> int:
    if q_word in resource.title.lower():
        return 15
    if q_word in " ".join(resource.tags).lower():
        return 12
    if resource.description and q_word in resource.description.lower():
        return 8

    text_words = set(re.split(r"\s+", search_text))
    best_ratio = max(
        (levenshtein_ratio(q_word, t_word) for t_word in text_words),
        default=0.0,
    )

    thresholds = ((0.9, 6), (0.8, 4), (0.7, 2))
    for threshold, bonus in thresholds:
        if best_ratio >= threshold:
            return bonus
    return 0


def _score_tags(resource: Resource, f: ResourceFilter) -> int:
    if not f.tags:
        return 0
    resource_tags_lower = {t.lower() for t in resource.tags}
    if not resource_tags_lower:
        return 0
    matched = sum(1 for tag in f.tags if tag.lower() in resource_tags_lower)
    return int((matched / len(resource_tags_lower)) * 5)


def _score_my_rating(resource: Resource, f: ResourceFilter) -> int:
    if not f.sort_by_my_rating or resource.my_rating is None:
        return 0
    if f.my_rating_min is not None and resource.my_rating < f.my_rating_min:
        return 0
    return resource.my_rating


def _score_platform_rating(resource: Resource, f: ResourceFilter) -> int:
    if not f.sort_by_rating:
        return 0
    if resource.platform not in (ResourcePlatform.YOUTUBE, ResourcePlatform.HABR):
        return 0
    if f.rating_min is not None and resource.score < f.rating_min:
        return 0
    return int(resource.score / 10)


def _score_published(
    resource: Resource,
    f: ResourceFilter,
    by_new: list[Resource],
    by_old: list[Resource],
) -> int:
    if f.newest_published:
        return _rank_position(resource, by_new)
    if f.oldest_published:
        return _rank_position(resource, by_old)
    return 0


def _score_completed(
    resource: Resource,
    f: ResourceFilter,
    by_new: list[Resource],
    by_old: list[Resource],
) -> int:
    if f.recently_completed:
        return _rank_position(resource, by_new)
    if f.long_ago_completed:
        return _rank_position(resource, by_old)
    return 0


def _score_uncompleted(resource: Resource, f: ResourceFilter) -> int:
    if f.uncompleted_only and resource.completed_at is None:
        return 3
    return 0


def _rank_position(
    resource: Resource,
    ranked_list: list[Resource],
    max_rank: int = 10,
) -> int:
    """Awards points for a top-N finish: 1st = +N, Nth = +1, others = 0.

    ranked_list must be pre-sorted.
    """
    try:
        pos = ranked_list.index(resource)
        return max(0, max_rank - pos) if pos < max_rank else 0
    except ValueError:
        return 0
