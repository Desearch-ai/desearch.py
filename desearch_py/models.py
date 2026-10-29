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
    TWITTER = "twitter"
    ARXIV = "arxiv"


class WebTool(str, Enum):
    WEB = "web"
    HACKERNEWS = "hackernews"
    REDDIT = "reddit"
    WIKIPEDIA = "wikipedia"
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


class CompanyTaskType(str, Enum):
    """``type`` filter of ``list_company_tasks``: Company Search or Company Enrich tasks."""

    SEARCH = "search"
    ENRICH = "enrich"


class CompanyRole(str, Enum):
    """Leaders a Company Search or Company Enrich looks for (``roles``).

    The API default is ``CEO``, ``FOUNDER``, ``CTO`` and ``CFO``. A managing
    director (Geschäftsführer) counts as ``CEO`` when ``CEO`` is asked for.
    """

    CEO = "ceo"
    FOUNDER = "founder"
    CTO = "cto"
    CFO = "cfo"
    COO = "coo"
    CMO = "cmo"
    PRESIDENT = "president"
    OWNER = "owner"
    MANAGING_DIRECTOR = "managing_director"


class CompanyRequirement(str, Enum):
    """What every delivered company must have (``CompanySearchFilters.require``).

    ``LINKEDIN`` is the company's LinkedIn page, ``LEADER`` one of the
    request's ``roles``, ``LEADER_EMAIL`` a leader with an email.
    """

    EMAIL = "email"
    PHONE = "phone"
    LINKEDIN = "linkedin"
    LEADER = "leader"
    LEADER_EMAIL = "leader_email"


class CompanyCompletionReason(str, Enum):
    """Why a Company Search or Company Enrich task ended (``CompanyTask.completion_reason``).

    The People Search reasons (see ``PeopleCompletionReason``) plus
    ``ALL_DOMAINS_PROCESSED``: a Company Enrich task read every domain.
    """

    COUNT_REACHED = "count_reached"
    ALL_DOMAINS_PROCESSED = "all_domains_processed"
    ROUNDS_EXHAUSTED = "rounds_exhausted"
    NO_CANDIDATES = "no_candidates"
    ZERO_QUALIFIED = "zero_qualified"
    CANDIDATE_BUDGET = "candidate_budget"
    COST_LIMIT = "cost_limit"
    TIME_LIMIT = "time_limit"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CompanyEmailStatus(str, Enum):
    """``CompanyEmailVerification.status``: the result of an email's checks.

    ``RISKY``: a catch-all domain, or no MX record but an A record.
    ``UNKNOWN``: nothing could confirm or refute it.
    """

    VALID = "valid"
    INVALID = "invalid"
    RISKY = "risky"
    UNKNOWN = "unknown"


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


def _unverified_checks(
    checks: List[PeopleCriterionCheck],
) -> List[PeopleCriterionCheck]:
    """Checks a result does not confirm: see ``PeopleScore.unverified_criteria``."""
    return [
        check
        for check in checks
        if check.criterion
        and (check.verdict == PeopleCriterionVerdict.MET.value) == check.disqualifier
    ]


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
        return _unverified_checks(self.criteria_checks)


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


def _enum_values(value: Any) -> Any:
    """A list of enum members or strings as plain values (``None`` stays ``None``)."""
    if isinstance(value, (list, tuple)):
        return [_enum_value(item) for item in value]
    return value


# ─── Company Search Request Models ───────────────────────────────────────────
#
# Bodies for POST /desearch/companies/search and POST /desearch/companies/enrich.
# Both run as People Search tasks. The API validates ranges (query 3-1000
# characters, count 5-200, min_score 0-100, exclude up to 1000 domains, 1-200
# domains, up to 20 countries), the ``roles`` and ``require`` names, and
# ``metadata`` with the People Search rules; it returns 422 otherwise.


class CompanySearchFilters(BaseModel):
    """``countries``: where the companies should be, as ISO 3166-1 alpha-2
    codes (``DE``) or country names, up to 20; scoring treats them as a
    location criterion. ``require``: only deliver companies that have all of
    these (see ``CompanyRequirement``): ``email``, ``phone``, ``linkedin``,
    ``leader``, ``leader_email``. A company that does not have them once the
    stage that can show them has run is not delivered and not billed."""

    model_config = ConfigDict(extra="allow")

    countries: Optional[List[str]] = None
    require: Optional[List[str]] = None

    @field_validator("require", mode="before")
    @classmethod
    def _require_values(cls, value: Any) -> Any:
        return _enum_values(value)


class CompanySearchRequest(BaseModel):
    """Find companies from a description and collect their public contact data."""

    model_config = ConfigDict(extra="allow")

    query: str
    count: Optional[int] = None
    min_score: Optional[int] = None
    exclude: Optional[List[str]] = None
    roles: Optional[List[str]] = None
    infer_emails: Optional[bool] = None
    verify_emails: Optional[bool] = None
    filters: Optional[CompanySearchFilters] = None
    metadata: Optional[Dict[str, str]] = None

    @field_validator("roles", mode="before")
    @classmethod
    def _roles_values(cls, value: Any) -> Any:
        return _enum_values(value)


class CompanyEnrichRequest(BaseModel):
    """Collect public contact data for companies you already know, by domain."""

    model_config = ConfigDict(extra="allow")

    domains: List[str]
    roles: Optional[List[str]] = None
    infer_emails: Optional[bool] = None
    verify_emails: Optional[bool] = None
    metadata: Optional[Dict[str, str]] = None

    @field_validator("roles", mode="before")
    @classmethod
    def _roles_values(cls, value: Any) -> Any:
        return _enum_values(value)


# ─── Company Search Response Models ──────────────────────────────────────────
#
# A company is published as soon as the stages its request needs have run, and
# the later stages fill it in while you read it. Every field the worker writes
# after the first stage is optional, and every model keeps extra fields.


class CompanyTaskWarning(BaseModel):
    """Something that made part of a task less reliable without failing it,
    e.g. ``code`` ``enrichment_time_limit``."""

    model_config = ConfigDict(extra="allow")

    code: str
    message: Optional[str] = None


class CompanyTask(BaseModel):
    """A Company Search or Company Enrich task. Timestamps are ISO 8601 strings.

    ``search_type`` is ``company_search`` or ``company_enrich``, and
    ``platform`` (the task's service) ``company`` or ``company_enrich``.
    ``query`` is the description (Company Search) or a short label of the
    domains such as ``acme.com, beta.io and 3 more`` (Company Enrich).
    ``count`` is the companies asked for (Company Enrich: the domains left
    after deduplication). ``request`` is the normalized request.

    ``stage`` is ``planning``, ``searching``, ``processing``, ``enriching``
    (every company is published and only later stages of some are left) or
    ``finalizing``. ``progress`` counts ``candidates_found``,
    ``candidates_processed``, ``qualified``, ``filtered`` (by reason:
    ``unreachable``, ``not_a_company``, ``below_min_score``,
    ``no_<requirement>``), ``enrichment`` (``published``, ``complete``,
    ``pending``, ``failed``) and ``email_checks`` (``checked``, ``valid``,
    ``invalid``, ``risky``, ``unknown``).

    ``completion_reason`` says why the task ended (a ``CompanyCompletionReason``
    value; ``None`` while it is queued, running or paused), and
    ``coverage_limited`` is true when a budget stopped it before ``count``.
    ``cost_usd`` and ``usage_count`` are set on the response of the call that
    created the task (what it reserved).
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
    request: Optional[Dict[str, Any]] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
    interpreted: Optional[Dict[str, Any]] = None
    progress: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Any] = Field(default_factory=list)
    completion_reason: Optional[str] = None
    coverage_limited: bool = False
    warnings: List[CompanyTaskWarning] = Field(default_factory=list)
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


class CompanyTaskList(BaseModel):
    model_config = ConfigDict(extra="allow")

    tasks: List[CompanyTask]
    next_cursor: Optional[str] = None


class CompanyEmailChecks(BaseModel):
    """What an email check found. ``mx``: ``ok``, ``implicit``, ``none``,
    ``error``. ``smtp``: ``accepted``, ``rejected``, ``catch_all``,
    ``unreachable``, ``skipped``. ``web``: ``found``, ``not_found``,
    ``skipped``."""

    model_config = ConfigDict(extra="allow")

    syntax: Optional[bool] = None
    mx: Optional[str] = None
    smtp: Optional[str] = None
    web: Optional[str] = None


class CompanyEmailVerification(BaseModel):
    """``status`` (a ``CompanyEmailStatus`` value): ``valid``, ``invalid``,
    ``risky`` (catch-all domain, or no MX but an A record) or ``unknown``
    (nothing could confirm or refute it)."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    checks: Optional[CompanyEmailChecks] = None
    checked_at: Optional[str] = None


class CompanyEmail(BaseModel):
    """An email of the company or of one of its leaders.

    ``type``: ``personal``, ``leadership``, ``sales``, ``general``, ``press``,
    ``support``, ``careers``, ``legal`` or ``other``. ``source``: ``website``,
    ``search``, ``linkedin`` or ``inferred``; ``source_url`` is the page it was
    found on (``None`` when inferred). ``confidence`` and ``pattern`` are set
    on inferred emails only: ``high`` when the pattern (e.g. ``first.last``)
    was learned from this company's own addresses, ``low`` for a common one.
    ``verification`` is ``None`` until the email checks have run (or when
    ``verify_emails`` is false).
    """

    model_config = ConfigDict(extra="allow")

    value: str
    type: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    on_domain: Optional[bool] = None
    person: Optional[str] = None
    confidence: Optional[str] = None
    pattern: Optional[str] = None
    verification: Optional[CompanyEmailVerification] = None


class CompanyPhone(BaseModel):
    """``value`` is E.164 when the number parses, otherwise the digits as
    written (``raw`` is the number as written on the page). ``type``:
    ``main``, ``sales``, ``support``, ``mobile`` or ``other``."""

    model_config = ConfigDict(extra="allow")

    value: str
    type: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    raw: Optional[str] = None


class CompanySocial(BaseModel):
    """``type``: ``linkedin``, ``x``, ``facebook``, ``instagram``, ``github``,
    ``youtube``, ``tiktok``, ``crunchbase``, ``discord``, ``telegram`` or
    ``medium``."""

    model_config = ConfigDict(extra="allow")

    type: str
    url: str
    handle: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None


class CompanyPage(BaseModel):
    """A page that was read. ``type``: ``home``, ``contact``, ``about``,
    ``team``, ``imprint``, ``legal`` or ``other``."""

    model_config = ConfigDict(extra="allow")

    type: str
    url: str


class CompanyLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None


class CompanyPersonEvidence(BaseModel):
    """What shows a leader's role, and where (``source``: ``website``,
    ``linkedin`` or ``search``)."""

    model_config = ConfigDict(extra="allow")

    quote: Optional[str] = None
    source_url: Optional[str] = None
    source: Optional[str] = None


class CompanyPerson(BaseModel):
    """A leader of the company.

    ``roles`` lists which of the request's ``roles`` this person holds.
    ``verified`` is true when a quote on the company's own site or the
    person's current LinkedIn position shows the role.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    title: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = None
    x_url: Optional[str] = None
    github_url: Optional[str] = None
    emails: List[CompanyEmail] = Field(default_factory=list)
    phones: List[CompanyPhone] = Field(default_factory=list)
    evidence: Optional[CompanyPersonEvidence] = None
    verified: Optional[bool] = None


class CompanyPrimaryContact(BaseModel):
    """The person to contact first; ``reason`` says why they were picked."""

    model_config = ConfigDict(extra="allow")

    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    reason: Optional[str] = None


class CompanyContactCoverage(BaseModel):
    """What was found, under the same names as ``CompanySearchFilters.require``."""

    model_config = ConfigDict(extra="allow")

    email: Optional[bool] = None
    phone: Optional[bool] = None
    linkedin: Optional[bool] = None
    leader: Optional[bool] = None
    leader_email: Optional[bool] = None


class CompanyEnrichmentStages(BaseModel):
    """Each stage: ``pending``, ``done``, ``failed`` or ``skipped`` (turned
    off by the request, such as ``infer_emails=False``, nothing to do, or cut
    by the task's time limit, which ``CompanyEnrichment.errors`` then says)."""

    model_config = ConfigDict(extra="allow")

    profile: Optional[str] = None
    contacts: Optional[str] = None
    people: Optional[str] = None
    email_patterns: Optional[str] = None
    email_check: Optional[str] = None


class CompanyEnrichmentError(BaseModel):
    model_config = ConfigDict(extra="allow")

    stage: Optional[str] = None
    message: Optional[str] = None


class CompanyEnrichment(BaseModel):
    """``status`` is ``partial`` while any stage is ``pending``, then ``complete``
    (a stage cut by the task's time limit is ``skipped``)."""

    model_config = ConfigDict(extra="allow")

    status: Optional[str] = None
    stages: Optional[CompanyEnrichmentStages] = None
    errors: List[CompanyEnrichmentError] = Field(default_factory=list)


class CompanyScore(BaseModel):
    """Fit score of a Company Search result (Company Enrich has none).

    ``relevance`` is ``high``, ``medium`` or ``low``. ``criteria_checks`` has
    one ``PeopleCriterionCheck`` per criterion: what the company's own pages
    confirm. It is information only. ``fully_verified`` is true when every
    criterion is ``met`` and no disqualifier (``is_disqualifier``) is.
    """

    model_config = ConfigDict(extra="allow")

    value: Optional[float] = None
    qualified: Optional[bool] = None
    relevance: Optional[str] = None
    summary: Optional[str] = None
    matched_signals: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    criteria_checks: List[PeopleCriterionCheck] = Field(default_factory=list)
    fully_verified: Optional[bool] = None

    @property
    def unverified_criteria(self) -> List[PeopleCriterionCheck]:
        """The checks this company does not confirm, as in
        ``PeopleScore.unverified_criteria``: every criterion whose verdict is
        not ``met``, plus every disqualifier that is ``met``. Their
        ``criterion`` texts are what the CSV export lists in
        ``unverified_criteria``."""
        return _unverified_checks(self.criteria_checks)


class CompanyFoundBy(BaseModel):
    """The search that found the company. ``kind`` says how, e.g. ``direct``
    (a hit on the company's own site)."""

    model_config = ConfigDict(extra="allow")

    query: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    kind: Optional[str] = None


class Company(BaseModel):
    """One company (``id`` ``company:<domain>``, ``handle`` its domain).

    Published once the stages its request needs have run; the later stages
    fill it in (``enrichment.status`` is ``partial`` until then). ``emails``
    leaves out system addresses (noreply@, postmaster@ ...) and junk.
    ``primary_email`` is the company's best email: never a ``support``,
    ``legal``, ``careers``, ``press`` or ``other`` address, and an inferred
    one only when it is ``valid``. ``people`` holds the leaders with one of
    the request's ``roles``. ``score`` is ``None`` for Company Enrich.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    platform: str
    handle: str
    domain: str
    url: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    location: Optional[CompanyLocation] = None
    industry: Optional[str] = None
    emails: List[CompanyEmail] = Field(default_factory=list)
    phones: List[CompanyPhone] = Field(default_factory=list)
    socials: List[CompanySocial] = Field(default_factory=list)
    pages: List[CompanyPage] = Field(default_factory=list)
    people: List[CompanyPerson] = Field(default_factory=list)
    primary_email: Optional[CompanyEmail] = None
    primary_contact: Optional[CompanyPrimaryContact] = None
    contact_coverage: Optional[CompanyContactCoverage] = None
    enrichment: Optional[CompanyEnrichment] = None
    score: Optional[CompanyScore] = None
    found_by: List[CompanyFoundBy] = Field(default_factory=list)


class CompanyResultsPage(BaseModel):
    """One page of companies.

    Pass ``next_cursor`` as ``cursor`` on the next call to get only companies
    delivered after this page. Companies already delivered are filled in place
    by later stages: read again without ``cursor`` to get their latest version.
    """

    model_config = ConfigDict(extra="allow")

    task_id: str
    status: str
    results: List[Company]
    next_cursor: str
    has_more: bool


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
