from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")

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


class PeoplePlatform(str, Enum):
    X = "x"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"


class PeopleTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


# Statuses after which a People Search task never changes again.
PEOPLE_TASK_ENDED_STATUSES = frozenset(
    {
        PeopleTaskStatus.COMPLETED.value,
        PeopleTaskStatus.PARTIAL.value,
        PeopleTaskStatus.FAILED.value,
        PeopleTaskStatus.CANCELLED.value,
        PeopleTaskStatus.EXPIRED.value,
    }
)


class PeopleCompletionReason(str, Enum):
    """Why a People Search ended (``PeopleTask.completion_reason``).

    ``COUNT_REACHED``: it found ``count`` profiles. ``ROUNDS_EXHAUSTED``: it ran
    every search it planned and found fewer. ``NO_CANDIDATES``: its searches
    found nobody to check. ``ZERO_QUALIFIED``: it checked the people its
    searches found and none fit. ``CANDIDATE_BUDGET``, ``COST_LIMIT`` and
    ``TIME_LIMIT``: a budget stopped it (see ``PeopleTask.coverage_limited``).
    ``CANCELLED``: it was cancelled. ``FAILED``: an error ended it.
    """

    COUNT_REACHED = "count_reached"
    ROUNDS_EXHAUSTED = "rounds_exhausted"
    NO_CANDIDATES = "no_candidates"
    ZERO_QUALIFIED = "zero_qualified"
    CANDIDATE_BUDGET = "candidate_budget"
    COST_LIMIT = "cost_limit"
    TIME_LIMIT = "time_limit"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PeopleCriterionVerdict(str, Enum):
    """Verdict of one ``PeopleCriterionCheck``."""

    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"


class PeopleEnrichment(str, Enum):
    """``Person.attributes["enrichment"]``: whether the profile was read after search."""

    OK = "ok"
    FAILED = "failed"


class PeopleEnrichmentError(str, Enum):
    """``Person.attributes["enrichment_error"]``: why the profile could not be read."""

    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    UPSTREAM_ERROR = "upstream_error"
    REQUEST_ERROR = "request_error"


class PeopleProfileSort(str, Enum):
    SCORE = "score"
    RECENT = "recent"
    AUDIENCE = "audience"


class PeopleExportFormat(str, Enum):
    CSV = "csv"
    JSONL = "jsonl"


class PeopleChannel(str, Enum):
    """Channels accepted by the ``has`` result filter."""

    EMAIL = "email"
    WEBSITE = "website"
    X = "x"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


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




# ─── Response Metadata Models ────────────────────────────────────────────────


class DesearchCostMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    cost_usd: Optional[float] = None
    usage_count: Optional[int] = None
    service: Optional[str] = None
    currency: Optional[str] = None


class DesearchResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T
    metadata: DesearchCostMetadata

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
    cost_usd: Optional[float] = None
    usage_count: Optional[int] = None
    service: Optional[str] = None
    currency: Optional[str] = None


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


# ─── People Search Request Models ────────────────────────────────────────────
#
# Bodies for POST /desearch/people/search/{x,youtube,linkedin,tiktok}. The API
# validates ranges (count 5-200, min_score 0-100, query 3-1000 characters) and
# returns 422 when a value is out of range or a filter is not supported. It also
# validates ``metadata``: at most 10 keys, keys of 1-40 characters from a-z, 0-9,
# '_', '.' and '-', and string values of at most 200 characters.


class XProfileSearchFilters(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    verified_only: Optional[bool] = None
    countries: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


class YouTubeCreatorSearchFilters(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_subscribers: Optional[int] = None
    max_subscribers: Optional[int] = None
    countries: Optional[List[str]] = None
    require_contact: Optional[bool] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


class LinkedInProfileSearchFilters(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    countries: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


class TikTokCreatorSearchFilters(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    require_contact: Optional[bool] = None
    keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


class _PeopleSearchRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    query: str
    count: Optional[int] = None
    min_score: Optional[int] = None
    exclude: Optional[List[str]] = None
    metadata: Optional[Dict[str, str]] = None


class XProfileSearchRequest(_PeopleSearchRequest):
    filters: Optional[XProfileSearchFilters] = None


class YouTubeCreatorSearchRequest(_PeopleSearchRequest):
    filters: Optional[YouTubeCreatorSearchFilters] = None


class LinkedInProfileSearchRequest(_PeopleSearchRequest):
    filters: Optional[LinkedInProfileSearchFilters] = None


class TikTokCreatorSearchRequest(_PeopleSearchRequest):
    filters: Optional[TikTokCreatorSearchFilters] = None


def _enum_value(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


class PeopleResultFilters(BaseModel):
    """Result filters for task exports, the profiles library and its export.

    ``has`` lists channels every person must have (see ``PeopleChannel``). It
    accepts a list or a comma-separated string and is sent comma-separated.
    ``min_audience``/``max_audience`` compare followers (subscribers on
    YouTube). ``verified=True`` keeps only verified accounts (X, TikTok); the
    API ignores ``verified=False``.
    """

    model_config = ConfigDict(extra="allow")

    has: Optional[List[str]] = None
    min_audience: Optional[int] = None
    max_audience: Optional[int] = None
    min_score: Optional[int] = None
    location: Optional[str] = None
    verified: Optional[bool] = None

    @field_validator("has", mode="before")
    @classmethod
    def _split_has(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, Enum)):
            value = [value]
        channels: List[str] = []
        for item in value:
            text = str(_enum_value(item))
            for part in text.split(","):
                part = part.strip()
                if part and part not in channels:
                    channels.append(part)
        return channels

    def to_params(self) -> Dict[str, Union[str, int]]:
        """Return the filters as API query parameters."""
        params: Dict[str, Union[str, int]] = {}
        for key, value in self.model_dump(exclude_none=True).items():
            value = _enum_value(value)
            if isinstance(value, bool):
                params[key] = "true" if value else "false"
            elif isinstance(value, (list, tuple)):
                if value:
                    params[key] = ",".join(str(_enum_value(item)) for item in value)
            else:
                params[key] = value
        return params


# ─── People Search Response Models ───────────────────────────────────────────


class PeopleTaskLinks(BaseModel):
    model_config = ConfigDict(extra="allow")

    self: Optional[str] = None
    results: Optional[str] = None
    export: Optional[str] = None


class PeopleTaskCreatedBy(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: Optional[str] = None
    api_key_id: Optional[str] = None
    via: Optional[str] = None


class PeopleTaskWarning(BaseModel):
    """Something that made part of a search less reliable without failing it.

    ``code`` ``partial_enrichment``: some candidates' profiles could not be
    read after search, so they were scored on what the search returned
    (their results have ``attributes["enrichment"] == "failed"``).
    ``by_reason`` counts failed lookups by reason on LinkedIn and TikTok
    (``not_found``, ``rate_limited``, ``timeout``, ``upstream_error``,
    ``request_error``) and by source on YouTube (``about_page_failed``,
    ``innertube_failed``).
    """

    model_config = ConfigDict(extra="allow")

    code: str
    platform: Optional[str] = None
    attempted: Optional[int] = None
    enriched: Optional[int] = None
    failed: Optional[int] = None
    by_reason: Dict[str, int] = Field(default_factory=dict)
    message: Optional[str] = None


class PeopleTask(BaseModel):
    """A People Search task. Timestamps are ISO 8601 strings.

    ``cost_usd`` and ``usage_count`` are set on the response of the call that
    created the search (what that call reserved). ``final_cost_usd`` is what
    the search cost once it ended. ``metadata`` is the ``metadata`` sent when
    the search was created (``{}`` when none).

    ``completion_reason`` says why the search ended (a
    ``PeopleCompletionReason`` value; ``None`` while it is queued, running or
    paused). ``coverage_limited`` is true when a budget (``cost_limit``,
    ``candidate_budget`` or ``time_limit``) stopped it before it reached
    ``count``; ``status`` is still ``completed`` then. ``warnings`` lists what
    made part of the search less reliable (``[]`` when nothing did).
    """

    model_config = ConfigDict(extra="allow")

    task_id: str
    search_type: str
    platform: str
    status: str
    stage: Optional[str] = None
    query: str
    count: int
    result_count: int
    metadata: Dict[str, str] = Field(default_factory=dict)
    interpreted: Optional[Dict[str, Any]] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Any] = Field(default_factory=list)
    completion_reason: Optional[str] = None
    coverage_limited: bool = False
    warnings: List[PeopleTaskWarning] = Field(default_factory=list)
    reserved_cost_usd: float
    final_cost_usd: Optional[float] = None
    refunded_usd: Optional[float] = None
    cost_usd: Optional[float] = None
    usage_count: Optional[int] = None
    created_by: Optional[PeopleTaskCreatedBy] = None
    created_at: str
    started_at: Optional[str] = None
    paused_at: Optional[str] = None
    finished_at: Optional[str] = None
    results_expire_at: Optional[str] = None
    links: Optional[PeopleTaskLinks] = None

    @property
    def is_finished(self) -> bool:
        """True once the task has ended and will not change again."""
        return self.status in PEOPLE_TASK_ENDED_STATUSES


class PeopleTaskList(BaseModel):
    model_config = ConfigDict(extra="allow")

    tasks: List[PeopleTask]
    next_cursor: Optional[str] = None


class PeopleEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    url: Optional[str] = None
    text: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


# Fallback for checks without `is_disqualifier`: the worker's keyword rule, which
# also sets the flag. Same rule as the API's CSV `unverified_criteria` column;
# re.ASCII keeps `\b` on ASCII word characters, like JavaScript.
_DISQUALIFIER_CRITERION = re.compile(
    r"\b(disqualif(?:y|ier|iers)|exclude|excluding|not a fit|not qualified)\b",
    re.IGNORECASE | re.ASCII,
)


class PeopleCriterionCheck(BaseModel):
    """One of the search's criteria, checked against the person's own profile and posts.

    ``verdict`` (a ``PeopleCriterionVerdict`` value): ``met`` when a quote
    from the profile or a source shows it, ``not_met`` when the evidence
    contradicts it, ``unknown`` when nothing found shows it either way. For a
    disqualifier (``is_disqualifier``), ``met`` means it applies. ``quote`` and
    ``source_url`` back a ``met`` verdict. ``is_disqualifier`` is ``None`` on
    checks scored before the field existed.
    """

    model_config = ConfigDict(extra="allow")

    criterion: str
    verdict: str
    quote: Optional[str] = None
    source_url: Optional[str] = None
    reason: str = ""
    is_disqualifier: Optional[bool] = None

    @property
    def disqualifier(self) -> bool:
        """True when this criterion is a disqualifier: ``is_disqualifier``
        when the API set it, else the API's keyword rule."""
        if isinstance(self.is_disqualifier, bool):
            return self.is_disqualifier
        return bool(_DISQUALIFIER_CRITERION.search(self.criterion or ""))


class PeopleScore(BaseModel):
    """Fit score and reasons.

    ``criteria_checks`` has one check per criterion. It is information only:
    a qualified result can still have ``unknown`` criteria. ``fully_verified``
    is true when every criterion is ``met`` and no disqualifier
    (``is_disqualifier``) is. Results scored before 2026-10-20 have no checks and
    ``fully_verified`` ``None``.
    """

    model_config = ConfigDict(extra="allow")

    value: Optional[float] = None
    qualified: Optional[bool] = None
    summary: Optional[str] = None
    matched_signals: List[str] = Field(default_factory=list)
    profile_fit: List[str] = Field(default_factory=list)
    buying_triggers: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    criteria_checks: List[PeopleCriterionCheck] = Field(default_factory=list)
    fully_verified: Optional[bool] = None

    @property
    def unverified_criteria(self) -> List[PeopleCriterionCheck]:
        """The checks this result does not confirm: every criterion whose
        verdict is not ``met``, plus every disqualifier that is ``met`` (it
        applies). Their ``criterion`` texts are what the CSV export lists in
        ``unverified_criteria``. A returned check with verdict ``met`` is a
        disqualifier that applies. A check without ``is_disqualifier`` (scored
        before it existed) uses the API's keyword rule. Information only: the
        result still qualified."""
        return [
            check
            for check in self.criteria_checks
            if check.criterion
            and (check.verdict == PeopleCriterionVerdict.MET.value)
            == check.disqualifier
        ]


class Person(BaseModel):
    """One qualified profile (X, LinkedIn) or creator (YouTube, TikTok).

    ``links`` items look like ``{"type": "website", "url": ...}`` and
    ``contacts`` items like ``{"type": "email", "value": ...}``.
    ``attributes`` holds platform details such as ``verified`` or ``headline``.
    On LinkedIn, TikTok and YouTube it also has ``enrichment`` (``ok`` or
    ``failed``) and, when the profile could not be read, ``enrichment_error``;
    the ``enrichment`` and ``enrichment_error`` properties read them.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    platform: str
    handle: str
    url: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    links: List[Dict[str, Any]] = Field(default_factory=list)
    contacts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[PeopleEvidence] = Field(default_factory=list)
    score: Optional[PeopleScore] = None

    @property
    def enrichment(self) -> Optional[str]:
        """``ok`` when the profile was read after search, ``failed`` when it
        could not be (a ``PeopleEnrichment`` value), or ``None`` when the
        platform does not report it."""
        value = self.attributes.get("enrichment")
        return value if isinstance(value, str) else None

    @property
    def enrichment_error(self) -> Optional[str]:
        """Why the profile could not be read (a ``PeopleEnrichmentError``
        value) when ``enrichment`` is ``failed``. Fields such as location or
        followers then come from the search hit only or are missing."""
        value = self.attributes.get("enrichment_error")
        return value if isinstance(value, str) else None


class PeopleResultsPage(BaseModel):
    """One page of task results.

    Pass ``next_cursor`` as ``cursor`` on the next call. When ``has_more`` is
    false you have every result found so far; calling again later with the same
    cursor returns only new results.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str
    status: str
    results: List[Person]
    next_cursor: str
    has_more: bool


class PersonFoundBy(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: str
    query: str
    found_at: str
    times_found: int


class PeopleProfile(Person):
    """A person from your searches, with the search that found them."""

    found_by: PersonFoundBy


class PeopleProfilesPage(BaseModel):
    model_config = ConfigDict(extra="allow")

    profiles: List[PeopleProfile]
    total: int
    next_cursor: Optional[str] = None


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
