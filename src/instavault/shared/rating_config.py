from dataclasses import dataclass


@dataclass(frozen=True)
class RatingConfig:
    # Smoothing constants
    view_smoothing: int = 100
    engagement_smoothing: int = 5

    # YouTube specific
    video_view_norm: float = 500.0
    video_reach_multiplier: float = 18.0
    video_engagement_rate_multiplier: float = 100.0
    video_engagement_multiplier: float = 22.0

    # Habr specific
    habr_view_smoothing: int = 50
    habr_engagement_smoothing: int = 2
    habr_view_norm: float = 200.0
    habr_reach_multiplier: float = 17.0
    habr_engagement_rate_multiplier: float = 500.0
    habr_engagement_multiplier: float = 10.0

    # Personal rating
    personal_rating_multiplier: float = 20.0
    max_personal_rating: int = 5
    max_score: float = 100.0

    # Blending weights
    platform_weight: float = 0.7
    personal_weight: float = 0.3


RATING_CONFIG = RatingConfig()
