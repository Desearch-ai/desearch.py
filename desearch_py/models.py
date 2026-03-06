from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict

# ─── Enums ────────────────────────────────────────────────────────────────────


class Tool(str, Enum):
    WEB = "web"
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    WIKIPEDIA = "wikipedia"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    ARXIV = "arxiv"


class WebTool(str, Enum):
    WEB = "web"
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    WIKIPEDIA = "wikipedia"
    YOUTUBE = "youtube"
    ARXIV = "arxiv"


class DateFilter(str, Enum):
    PAST_24_HOURS = "PAST_24_HOURS"
    PAST_2_DAYS = "PAST_2_DAYS"
    PAST_WEEK = "PAST_WEEK"
    PAST_2_WEEKS = "PAST_2_WEEKS"
    PAST_MONTH = "PAST_MONTH"
    PAST_2_MONTHS = "PAST_2_MONTHS"
    PAST_YEAR = "PAST_YEAR"
    PAST_2_YEARS = "PAST_2_YEARS"


class ResultType(str, Enum):
    ONLY_LINKS = "ONLY_LINKS"
    LINKS_WITH_FINAL_SUMMARY = "LINKS_WITH_FINAL_SUMMARY"


class Sort(str, Enum):
    TOP = "Top"
    LATEST = "Latest"


# ─── Twitter / X Models ──────────────────────────────────────────────────────


class Rect(BaseModel):
    model_config = ConfigDict(extra="allow")

    x: int
    y: int
    w: int
    h: int


class MediaSize(BaseModel):
    model_config = ConfigDict(extra="allow")

    w: int
    h: int
    resize: Optional[str] = None


class TwitterScraperEntitiesMediaAdditionalInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    monetizable: Optional[bool] = None
    source_user: Optional[Dict[str, Any]] = None


class TwitterScraperEntitiesMediaAllowDownloadStatus(BaseModel):
    model_config = ConfigDict(extra="allow")

    allow_download: Optional[bool] = None


class TwitterScraperEntitiesMediaExtAvailability(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None


class TwitterScraperEntitiesMediaFeature(BaseModel):
    model_config = ConfigDict(extra="allow")

    faces: Optional[List[Rect]] = None


class TwitterScraperEntitiesMediaFeatures(BaseModel):
    model_config = ConfigDict(extra="allow")

    large: Optional[TwitterScraperEntitiesMediaFeature] = None
    medium: Optional[TwitterScraperEntitiesMediaFeature] = None
    small: Optional[TwitterScraperEntitiesMediaFeature] = None
    orig: Optional[TwitterScraperEntitiesMediaFeature] = None


class TwitterScraperEntitiesMediaOriginalInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    height: int
    width: int
    focus_rects: Optional[List[Rect]] = None


class TwitterScraperEntitiesMediaSizes(BaseModel):
    model_config = ConfigDict(extra="allow")

    large: Optional[MediaSize] = None
    medium: Optional[MediaSize] = None
    small: Optional[MediaSize] = None
    thumb: Optional[MediaSize] = None


class TwitterScraperEntitiesMediaVideoInfoVariant(BaseModel):
    model_config = ConfigDict(extra="allow")

    content_type: str
    url: str
    bitrate: Optional[int] = None


class TwitterScraperEntitiesMediaVideoInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    duration_millis: Optional[int] = None
    aspect_ratio: Optional[List[int]] = None
    variants: Optional[List[TwitterScraperEntitiesMediaVideoInfoVariant]] = None


class TwitterScraperEntitiesMediaResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    media_key: str


class TwitterScraperEntitiesMediaResults(BaseModel):
    model_config = ConfigDict(extra="allow")

    result: Optional[TwitterScraperEntitiesMediaResult] = None


class TwitterScraperEntitiesMedia(BaseModel):
    model_config = ConfigDict(extra="allow")

    display_url: Optional[str] = None
    expanded_url: Optional[str] = None
    id_str: Optional[str] = None
    indices: Optional[List[int]] = None
    media_key: Optional[str] = None
    media_url_https: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    additional_media_info: Optional[TwitterScraperEntitiesMediaAdditionalInfo] = None
    ext_media_availability: Optional[TwitterScraperEntitiesMediaExtAvailability] = None
    features: Optional[TwitterScraperEntitiesMediaFeatures] = None
    sizes: Optional[TwitterScraperEntitiesMediaSizes] = None
    original_info: Optional[TwitterScraperEntitiesMediaOriginalInfo] = None
    allow_download_status: Optional[TwitterScraperEntitiesMediaAllowDownloadStatus] = (
        None
    )
    video_info: Optional[TwitterScraperEntitiesMediaVideoInfo] = None
    media_results: Optional[TwitterScraperEntitiesMediaResults] = None


class TwitterScraperEntitiesSymbol(BaseModel):
    model_config = ConfigDict(extra="allow")

    indices: List[int]
    text: str


class TwitterScraperEntitiesUserMention(BaseModel):
    model_config = ConfigDict(extra="allow")

    id_str: str
    name: str
    screen_name: str
    indices: List[int]


class TwitterScraperEntityUrl(BaseModel):
    model_config = ConfigDict(extra="allow")

    display_url: str
    expanded_url: Optional[str] = None
    url: str
    indices: List[int]


class TwitterScraperEntities(BaseModel):
    model_config = ConfigDict(extra="allow")

    hashtags: Optional[List[TwitterScraperEntitiesSymbol]] = None
    media: Optional[List[TwitterScraperEntitiesMedia]] = None
    symbols: Optional[List[TwitterScraperEntitiesSymbol]] = None
    timestamps: Optional[List[Any]] = None
    urls: Optional[List[TwitterScraperEntityUrl]] = None
    user_mentions: Optional[List[TwitterScraperEntitiesUserMention]] = None


class TwitterScraperExtendedEntities(BaseModel):
    model_config = ConfigDict(extra="allow")

    media: Optional[List[TwitterScraperEntitiesMedia]] = None


class TwitterScraperMedia(BaseModel):
    model_config = ConfigDict(extra="allow")

    media_url: str = ""
    type: str = ""


class TwitterScraperUserEntitiesDescription(BaseModel):
    model_config = ConfigDict(extra="allow")

    urls: Optional[List[TwitterScraperEntityUrl]] = None


class TwitterScraperUserEntities(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: Optional[TwitterScraperUserEntitiesDescription] = None
    url: Optional[TwitterScraperUserEntitiesDescription] = None


class TwitterScraperUserProfessionalCategory(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str


class TwitterScraperUserProfessional(BaseModel):
    model_config = ConfigDict(extra="allow")

    professional_type: str
    category: List[TwitterScraperUserProfessionalCategory] = []


class TwitterScraperUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    url: Optional[str] = None
    name: Optional[str] = None
    username: str
    created_at: Optional[str] = None
    description: Optional[str] = None
    favourites_count: Optional[int] = None
    followers_count: Optional[int] = None
    followings_count: Optional[int] = None
    listed_count: Optional[int] = None
    media_count: Optional[int] = None
    profile_image_url: Optional[str] = None
    profile_banner_url: Optional[str] = None
    statuses_count: Optional[int] = None
    verified: Optional[bool] = None
    is_blue_verified: Optional[bool] = None
    entities: Optional[TwitterScraperUserEntities] = None
    can_dm: Optional[bool] = None
    can_media_tag: Optional[bool] = None
    location: Optional[str] = None
    pinned_tweet_ids: Optional[List[str]] = None
    professional: Optional[TwitterScraperUserProfessional] = None


class TwitterScraperTweet(BaseModel):
    model_config = ConfigDict(extra="allow")

    user: Optional[TwitterScraperUser] = None
    id: str
    text: str
    reply_count: int
    view_count: Optional[int] = None
    retweet_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    url: Optional[str] = None
    created_at: str
    media: Optional[List[TwitterScraperMedia]] = None
    is_quote_tweet: Optional[bool] = None
    is_retweet: Optional[bool] = None
    lang: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_screen_name: Optional[str] = None
    in_reply_to_status_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    quoted_status_id: Optional[str] = None
    quote: Optional[TwitterScraperTweet] = None
    replies: Optional[List[TwitterScraperTweet]] = None
    display_text_range: Optional[List[int]] = None
    entities: Optional[TwitterScraperEntities] = None
    extended_entities: Optional[TwitterScraperExtendedEntities] = None
    retweet: Optional[TwitterScraperTweet] = None


# ─── Web Search Models ───────────────────────────────────────────────────────


class WebSearchResultItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    snippet: str
    link: str


class WebSearchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    youtube_search_results: Optional[List[WebSearchResultItem]] = None
    hacker_news_search_results: Optional[List[WebSearchResultItem]] = None
    reddit_search_results: Optional[List[WebSearchResultItem]] = None
    arxiv_search_results: Optional[List[WebSearchResultItem]] = None
    wikipedia_search_results: Optional[List[WebSearchResultItem]] = None
    search_results: Optional[List[WebSearchResultItem]] = None


class WebSearchResultsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: List[WebSearchResultItem]


# ─── AI Search Response Model ────────────────────────────────────────────────


class ResponseData(BaseModel):
    model_config = ConfigDict(extra="allow")

    hacker_news_search: Optional[List[Dict[str, Any]]] = None
    reddit_search: Optional[List[Dict[str, Any]]] = None
    search: Optional[List[Dict[str, Any]]] = None
    youtube_search: Optional[List[Dict[str, Any]]] = None
    tweets: Optional[List[Dict[str, Any]]] = None
    text: Optional[str] = None
    miner_link_scores: Optional[Dict[str, str]] = None
    completion: Optional[str] = None


# ─── X Links Search Response ─────────────────────────────────────────────────


class XLinksSearchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    miner_tweets: List[TwitterScraperTweet]


# ─── X Retweeters Response ───────────────────────────────────────────────────


class XRetweetersResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    users: List[TwitterScraperUser]
    next_cursor: Optional[str] = None


# ─── X User Posts Response ────────────────────────────────────────────────────


class XUserPostsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    user: TwitterScraperUser
    tweets: List[TwitterScraperTweet]
    next_cursor: Optional[str] = None


# ─── X Trends Models ─────────────────────────────────────────────────────────


class XTrendItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    query: Optional[str] = None
    rank: Optional[int] = None


class XTrendsWoeid(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    id: int


class XTrendsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    trends: List[XTrendItem]
    woeid: Optional[XTrendsWoeid] = None


# ─── Error Response Models ────────────────────────────────────────────────────


class ValidationError(BaseModel):
    model_config = ConfigDict(extra="allow")

    loc: List[Union[str, int]]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: Optional[List[ValidationError]] = None


class UnauthorizedResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: Dict[str, Union[str, int]]


class TooManyRequestsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: Dict[str, Union[str, int]]


class InternalServerErrorResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: Dict[str, Union[str, int]]


class MovedPermanentlyResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    detail: Dict[str, Union[str, int]]
