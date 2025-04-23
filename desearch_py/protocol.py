from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


def format_enum_values(enum):
    values = [value.value for value in enum]
    values = ", ".join(values)

    return f"Options: {values}"


class ToolEnum(str, Enum):
    web = "web"
    hacker_news = "hackernews"
    reddit = "reddit"
    wikipedia = "wikipedia"
    youtube = "youtube"
    twitter = "twitter"
    arxiv = "arxiv"


class WebToolEnum(str, Enum):
    web = ToolEnum.web.value
    hacker_news = ToolEnum.hacker_news.value
    reddit = ToolEnum.reddit.value
    wikipedia = ToolEnum.wikipedia.value
    youtube = ToolEnum.youtube.value
    arxiv = ToolEnum.arxiv.value


class ModelEnum(Enum):
    NOVA = "NOVA"
    ORBIT = "ORBIT"
    HORIZON = "HORIZON"


class DateFilterEnum(Enum):
    PAST_24_HOURS = "PAST_24_HOURS"
    PAST_2_DAYS = "PAST_2_DAYS"
    PAST_WEEK = "PAST_WEEK"
    PAST_2_WEEKS = "PAST_2_WEEKS"
    PAST_MONTH = "PAST_MONTH"
    PAST_2_MONTHS = "PAST_2_MONTHS"
    PAST_YEAR = "PAST_YEAR"
    PAST_2_YEARS = "PAST_2_YEARS"


class ResultTypeEnum(Enum):
    ONLY_LINKS = "ONLY_LINKS"
    LINKS_WITH_SUMMARIES = "LINKS_WITH_SUMMARIES"
    LINKS_WITH_FINAL_SUMMARY = "LINKS_WITH_FINAL_SUMMARY"


class AISearchPayload(BaseModel):
    prompt: str = Field(
        ...,
        description="Search query prompt",
        example="Bittensor",
    )
    tools: List[ToolEnum] = Field(
        ...,
        description="A list of tools to be used for the search",
        example=[
            ToolEnum.web.value,
            ToolEnum.hacker_news.value,
            ToolEnum.reddit.value,
            ToolEnum.wikipedia.value,
            ToolEnum.youtube.value,
            ToolEnum.twitter.value,
            ToolEnum.arxiv.value,
        ],
    )
    model: ModelEnum = Field(
        ...,
        description="The model to be used for the search",
        example=ModelEnum.NOVA,
    )

    date_filter: Optional[DateFilterEnum] = Field(
        description="The date filter to be used for the search",
        example=DateFilterEnum.PAST_24_HOURS,
    )
    streaming: bool = Field(
        ...,
        description="Whether to stream results",
        example=True,
    )


class TwitterSearchPayload(BaseModel):
    query: str = Field(
        ...,
        description="Search query. For syntax, check https://github.com/igorbrigadir/twitter-advanced-search",
        example="from:elonmusk #AI since:2023-01-01 until:2023-12-31",
    )

    sort: Optional[str] = Field(
        pattern="^(Top|Latest)$",
        description="Sort by Top or Latest",
        example="Top",
    )
    user: Optional[str] = Field(description="User to search for", example="elonmusk")
    start_date: Optional[str] = Field(
        description="Start date in UTC (YYYY-MM-DD format)", example="2025-01-01"
    )
    end_date: Optional[str] = Field(
        description="End date in UTC (YYYY-MM-DD format)", example="2025-01-30"
    )
    lang: Optional[str] = Field(
        description="Language code (e.g., en, es, fr)", example="en"
    )
    verified: Optional[bool] = Field(
        description="Filter for verified users", example=True
    )
    blue_verified: Optional[bool] = Field(
        description="Filter for blue checkmark verified users", example=True
    )
    is_quote: Optional[bool] = Field(
        description="Include only tweets with quotes", example=True
    )
    is_video: Optional[bool] = Field(
        description="Include only tweets with videos", example=True
    )
    is_image: Optional[bool] = Field(
        description="Include only tweets with images", example=True
    )
    min_retweets: Optional[Union[int, str]] = Field(
        description="Minimum number of retweets", example=1
    )
    min_replies: Optional[Union[int, str]] = Field(
        description="Minimum number of replies", example=1
    )
    min_likes: Optional[Union[int, str]] = Field(
        description="Minimum number of likes", example=1
    )


class WebSearchPayload(BaseModel):
    query: str
    num: int
    start: int


class WebLinksPayload(BaseModel):
    prompt: str = Field(
        ...,
        description="Search query prompt",
        example="What are the recent sport events?",
    )
    tools: List[ToolEnum] = Field(
        ...,
        description="List of tools to search with",
        example=[
            ToolEnum.web.value,
            ToolEnum.hacker_news.value,
            ToolEnum.reddit.value,
            ToolEnum.wikipedia.value,
            ToolEnum.youtube.value,
            ToolEnum.twitter.value,
            ToolEnum.arxiv.value,
        ],
    )

    model: Optional[ModelEnum] = Field(
        default=ModelEnum.NOVA,
        description=f"Model to use for scraping. {format_enum_values(ModelEnum)}",
        example=ModelEnum.NOVA.value,
    )


class TwitterLinksPayload(BaseModel):
    prompt: str = Field(
        ...,
        description="Search query prompt",
        example="What are the recent sport events?",
    )

    model: Optional[ModelEnum] = Field(
        default=ModelEnum.NOVA,
        description=f"Model to use for scraping. {format_enum_values(ModelEnum)}",
        example=ModelEnum.NOVA.value,
    )


class OrganicResults(BaseModel):
    title: str = Field(example="Example Title")
    url: str = Field(example="https://example.com")
    link: str = Field(example="https://example.com/link")
    snippet: str = Field(example="This is an example snippet from the search result.")
    summary_description: str = Field(
        example="This is a summary description of the search result."
    )


class BaseSearchResult(BaseModel):
    organic_results: Optional[Union[List[OrganicResults], Dict]]


class TextChunk(BaseModel):
    twitter_summary: List[str]


class Key_tweets(BaseModel):
    text: str = Field(example="This is an example tweet text.")
    url: str = Field(example="https://twitter.com/example_tweet")


class Completion(BaseModel):
    key_tweets: List[Key_tweets]
    twitter_summary: str = Field(example="This is an example Twitter summary.")
    summary: str = Field(example="This is an example summary.")


class AISearchResponse(BaseModel):
    wikipedia_search_results: Optional[Union[List[BaseSearchResult], Dict]]
    youtube_search_results: Optional[Union[List[BaseSearchResult], Dict]]
    arxiv_search_results: Optional[Union[List[BaseSearchResult], Dict]]
    reddit_search_results: Optional[Union[List[BaseSearchResult], Dict]]
    hacker_news_search_results: Optional[Union[List[BaseSearchResult], Dict]]
    text_chunks: Optional[Union[List[TextChunk], str]]
    completion_links: Optional[List[str]]
    search_completion_links: Optional[List[str]]
    completion: Optional[Completion]

    class Config:
        schema_extra = {
            "example": {
                "youtube_search_results": {
                    "organic_results": [
                        {
                            "title": "Did The FED Do The Impossible? [Huge Implications For Bitcoin]",
                            "link": "https://www.youtube.com/watch?v=Ycq1u2zWfr8",
                            "snippet": "Did we avoid a recession and is there still more upside for Bitcoin? GET MY FREE NEWSLETTER ...",
                            "summary_description": "Did The FED Do The Impossible? [Huge Implications For Bitcoin]",
                        },
                    ]
                },
                "hacker_news_search_results": {
                    "organic_results": [
                        {
                            "title": "latest",
                            "link": "https://news.ycombinator.com/latest?id=42816511",
                            "snippet": "The streaming app for the Paris Olympics was a revolution from which I can never go back to OTA coverage. I watched so many more competitions ...",
                            "summary_description": "",
                        },
                    ]
                },
                "reddit_search_results": {
                    "organic_results": [
                        {
                            "title": "6 New Sports at Los Angeles 2028 Olympics",
                            "link": "https://www.reddit.com/r/olympics/comments/1ert9av/6_new_sports_at_los_angeles_2028_olympics/",
                            "snippet": "Baseball and softball are not new olympic sports, but returning. Up to Tokyo, baseball was at every olympics since 1984 except London and Rio.",
                            "summary_description": "",
                        }
                    ]
                },
                "arxiv_search_results": {
                    "organic_results": [
                        {
                            "title": "[2304.02655] Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                            "link": "https://arxiv.org/abs/2304.02655",
                            "snippet": "Abstract page for arXiv paper 2304.02655: Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                            "with_metadata": True,
                            "summary_description": "[2304.02655] Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                        },
                    ]
                },
                "wikipedia_search_results": {
                    "organic_results": [
                        {
                            "title": "List of bitcoin companies - Wikipedia",
                            "link": "https://en.wikipedia.org/wiki/List_of_Bitcoin_companies",
                            "snippet": "",
                            "with_metadata": True,
                            "summary_description": "List of bitcoin companies - Wikipedia",
                        }
                    ]
                },
                "text_chunks": {"twitter_summary": ["<string>"]},
                "search_completion_links": [
                    "https://www.youtube.com/watch?v=Ycq1u2zWfr8",
                    "https://news.ycombinator.com/latest?id=42816511",
                    "https://www.reddit.com/r/olympics/comments/1ert9av/6_new_sports_at_los_angeles_2028_olympics/",
                    "https://en.wikipedia.org/wiki/List_of_Bitcoin_companies",
                ],
                "completion_links": [
                    "https://news.ycombinator.com/latest?id=42816511",
                    "https://www.youtube.com/watch?v=Ycq1u2zWfr8",
                ],
                "completion": {
                    "key_posts": [
                        {
                            "text": "This is an example post text.",
                            "url": "https://x.com/example_post",
                        }
                    ],
                    "key_tweets": [
                        {
                            "text": "This is an example tweet text.",
                            "url": "https://x.com/example_tweet",
                        }
                    ],
                    "key_news": [
                        {
                            "text": "This is an example news text.",
                            "url": "https://news.example.com/123",
                        }
                    ],
                    "key_sources": [
                        {
                            "text": "This is an example source text.",
                            "url": "https://www.example.com",
                        }
                    ],
                    "twitter_summary": "This is an example Twitter summary.",
                    "summary": "This is an example summary.",
                    "reddit_summary": "This is an example summary.",
                    "hacker_news_summary": "This is an example summary.",
                },
            }
        }


class Inline(BaseModel):
    title: Optional[str] = Field(
        ..., title="Web title", example="Example Web Page Title"
    )
    link: Optional[str] = Field(..., title="Web link", example="https://example.com")


class Web(BaseModel):
    position: Optional[int]
    title: Optional[str] = Field(title="Web title", example="Example Web Page Title")
    link: Optional[str] = Field(..., title="Web link", example="https://example.com")
    redirect_link: Optional[str] = Field(
        title="Web redirect link",
        example="https://example.com/redirect",
    )
    displayed_link: Optional[str] = Field(
        title="Web displayed link",
        example="https://example.com/displayed",
    )
    favicon: Optional[str] = Field(
        title="Web favicon",
        example="https://example.com/favicon.ico",
    )
    date: Optional[str] = Field(title="Web date", example="17 hours ago")
    snippet: Optional[str] = Field(
        title="Web snippet",
        example="This is an example snippet from the web page.",
    )
    snippet_highlighted_words: Optional[List[str]] = Field(
        title="Web snippet highlighted words",
        example=["example", "snippet"],
    )
    source: Optional[str] = Field(title="Web source", example="On Location")
    inline: Optional[Union[List[Inline], Dict]] = Field(
        title="Web inline",
        example=[{"title": "Example Web Page Title", "link": "https://example.com"}],
    )
    summary_description: Optional[str] = Field(
        title="Summary Description", example="List of bitcoin companies - Wikipedia"
    )


class WebSearchResults(BaseModel):
    organic_results: Optional[Union[List[Web], Dict]] = Field()


class WebLinksSearchResponse(BaseModel):
    youtube_search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Youtube search results"
    )
    hacker_news_search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Hacker News search results"
    )
    reddit_search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Reddit search results"
    )
    arxiv_search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Arxiv search results"
    )
    wikipedia_search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Wikipedia search results"
    )
    search_results: Optional[Union[WebSearchResults, List, Dict]] = Field(
        description="Search results"
    )

    class Config:
        schema_extra = {
            "example": {
                "youtube_search_results": [
                    {
                        "title": "Did The FED Do The Impossible? [Huge Implications For Bitcoin]",
                        "link": "https://www.youtube.com/watch?v=Ycq1u2zWfr8",
                        "snippet": "Did we avoid a recession and is there still more upside for Bitcoin? GET MY FREE NEWSLETTER ...",
                        "summary_description": "Did The FED Do The Impossible? [Huge Implications For Bitcoin]",
                    },
                ],
                "hacker_news_search_results": {
                    "organic_results": [
                        {
                            "position": 1,
                            "title": "latest",
                            "link": "https://news.ycombinator.com/latest?id=42816511",
                            "redirect_link": "https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://news.ycombinator.com/latest%3Fid%3D42816511&ved=2ahUKEwiVgOLj45qLAxVJkIkEHQHrOzwQFnoECAgQAQ",
                            "displayed_link": "https://news.ycombinator.com › latest",
                            "favicon": "https://serpapi.com/searches/679a0a9dc12f1fe12103d57c/images/6e61b1f70b2f0d460b331310ebc59ded6780dc83d9e6763c5e07eea31b8c9155.png",
                            "date": "17 hours ago",
                            "snippet": "The streaming app for the Paris Olympics was a revolution from which I can never go back to OTA coverage. I watched so many more competitions ...",
                            "snippet_highlighted_words": ["competitions"],
                            "source": "Hacker News",
                        },
                    ],
                },
                "reddit_search_results": {
                    "organic_results": [
                        {
                            "position": 2,
                            "title": "6 New Sports at Los Angeles 2028 Olympics",
                            "link": "https://www.reddit.com/r/olympics/comments/1ert9av/6_new_sports_at_los_angeles_2028_olympics/",
                            "redirect_link": "https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.reddit.com/r/olympics/comments/1ert9av/6_new_sports_at_los_angeles_2028_olympics/&ved=2ahUKEwiFyNfj45qLAxUBLFkFHd0hOr0QFnoECCIQAQ",
                            "displayed_link": "2.7K+ comments · 5 months ago",
                            "favicon": "https://serpapi.com/searches/679a0a9da515cccc50df9203/images/a48c8b9ec22ae0600eaafcee75444cac0b05a09b6c4f36ae69a23b1ec299d102.png",
                            "snippet": "Baseball and softball are not new olympic sports, but returning. Up to Tokyo, baseball was at every olympics since 1984 except London and Rio.",
                            "snippet_highlighted_words": ["sports"],
                            "source": "Reddit · r/olympics",
                        },
                    ],
                },
                "arxiv_search_results": [
                    {
                        "title": "[2304.02655] Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                        "link": "https://arxiv.org/abs/2304.02655",
                        "snippet": "Abstract page for arXiv paper 2304.02655: Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                        "with_metadata": True,
                        "summary_description": "[2304.02655] Deciphering the Blockchain: A Comprehensive Analysis of Bitcoin's Evolution, Adoption, and Future Implications",
                    },
                ],
                "wikipedia_search_results": [
                    {
                        "title": "List of bitcoin companies - Wikipedia",
                        "link": "https://en.wikipedia.org/wiki/List_of_Bitcoin_companies",
                        "snippet": "",
                        "with_metadata": True,
                        "summary_description": "List of bitcoin companies - Wikipedia",
                    }
                ],
                "search_results": {
                    "organic_results": [
                        {
                            "position": 1,
                            "title": "Latest sports news, videos, interviews and comment",
                            "link": "https://www.cnn.com/sport",
                            "redirect_link": "https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.cnn.com/sport&ved=2ahUKEwj5yNTj45qLAxWqHNAFHXpCGUoQFnoECBgQAQ",
                            "displayed_link": "https://www.cnn.com › sport",
                            "favicon": "https://serpapi.com/searches/679a0a9dca85264e50d1e39f/images/e52955875acc356934b40dfd33c4b0e8191710f0c1b820d80a006163f68f2197.png",
                            "snippet": "Latest sports news from around the world with in-depth analysis, features, photos and videos covering football, tennis, motorsport, golf, rugby, sailing, ...",
                            "snippet_highlighted_words": ["Latest sports"],
                            "sitelinks": {
                                "inline": [
                                    {
                                        "title": "Football",
                                        "link": "https://www.cnn.com/sport/football",
                                    },
                                    {
                                        "title": "Tennis",
                                        "link": "https://www.cnn.com/sport/tennis",
                                    },
                                    {
                                        "title": "Golf",
                                        "link": "https://www.cnn.com/sport/golf",
                                    },
                                    {
                                        "title": "US Sports",
                                        "link": "https://www.cnn.com/sport/us-sports",
                                    },
                                ]
                            },
                            "source": "CNN",
                        },
                    ],
                },
            }
        }


class User(BaseModel):
    id: str = Field(..., title="User ID", example="123456789")
    url: Optional[str] = Field(
        None, title="User profile URL", example="https://twitter.com/example_user"
    )
    name: Optional[str] = Field(None, title="User name", example="John Doe")
    username: str = Field(..., title="User username", example="johndoe")
    created_at: Optional[str] = Field(
        None, title="User creation date", example="2023-01-01T00:00:00Z"
    )
    description: Optional[str] = Field(
        None, title="User description", example="This is an example user description."
    )
    favourites_count: Optional[int] = Field(
        None, title="User favourites count", example=100
    )
    followers_count: Optional[int] = Field(
        None, title="User followers count", example=1500
    )
    listed_count: Optional[int] = Field(None, title="User listed count", example=10)
    media_count: Optional[int] = Field(None, title="User media count", example=50)
    profile_image_url: Optional[str] = Field(
        None, title="User profile image URL", example="https://example.com/profile.jpg"
    )
    statuses_count: Optional[int] = Field(
        None, title="User statuses count", example=500
    )
    verified: Optional[bool] = Field(
        None, title="User verification status", example=True
    )


class Tweet(BaseModel):
    user: Optional[User] = Field(..., title="Tweet user")
    id: Optional[str] = Field(..., title="Tweet ID", example="987654321")
    text: Optional[str] = Field(
        ..., title="Tweet text", example="This is an example tweet."
    )
    reply_count: Optional[int] = Field(title="Tweet reply count", example=10)
    retweet_count: Optional[int] = Field(title="Tweet retweet count", example=5)
    like_count: Optional[int] = Field(title="Tweet like count", example=100)
    view_count: Optional[int] = Field(title="Tweet view count", example=1000)
    quote_count: Optional[int] = Field(title="Tweet quote count", example=2)
    impression_count: Optional[int] = Field(
        title="Tweet impression count", example=1500
    )
    bookmark_count: Optional[int] = Field(title="Tweet bookmark count", example=3)
    url: Optional[str] = Field(
        ..., title="Tweet URL", example="https://twitter.com/example_tweet"
    )
    created_at: Optional[str] = Field(
        ..., title="Tweet creation date", example="2023-01-01T00:00:00Z"
    )
    media: Optional[List] = Field(..., title="Tweet media", example=[])
    is_quote_tweet: Optional[bool] = Field(
        title="Tweet is a quote tweet", example=False
    )
    is_retweet: Optional[bool] = Field(title="Tweet is a retweet", example=False)
    entities: Optional[Dict] = Field(..., title="Tweet entities", example={})
    summary_description: Optional[str] = Field(
        ...,
        title="Tweet summary description",
        example="This is a summary of the tweet.",
    )


class TwitterLinksSearchResponse(BaseModel):
    miner_tweets: Optional[Union[List[Tweet], Dict, None]] = Field(
        ..., description="Miner tweets"
    )


class TwitterScraperMedia(BaseModel):
    media_url: str = ""
    type: str = ""


class TwitterScraperUser(BaseModel):
    # Available in both, scraped and api based tweets.
    id: Optional[str] = Field(example="123456789")
    url: Optional[str] = Field(example="https://twitter.com/example_user")
    name: Optional[str] = Field(example="John Doe")
    username: Optional[str] = Field(example="johndoe")
    created_at: Optional[str] = Field(example="2023-01-01T00:00:00Z")

    # Only available in scraped tweets
    description: Optional[str] = Field(example="This is an example user description.")
    favourites_count: Optional[int] = Field(example=100)
    followers_count: Optional[int] = Field(example=1500)
    listed_count: Optional[int] = Field(example=10)
    media_count: Optional[int] = Field(example=50)
    profile_image_url: Optional[str] = Field(example="https://example.com/profile.jpg")
    statuses_count: Optional[int] = Field(example=500)
    verified: Optional[bool] = Field(example=True)


class BasicTwitterSearchResponse(BaseModel):
    # Available in both, scraped and api based tweets.
    user: Optional[TwitterScraperUser]
    id: Optional[str] = Field(example="987654321")
    text: Optional[str] = Field(example="This is an example tweet.")
    reply_count: Optional[int] = Field(example=10)
    retweet_count: Optional[int] = Field(example=5)
    like_count: Optional[int] = Field(example=100)
    view_count: Optional[int] = Field(example=1000)
    quote_count: Optional[int] = Field(example=2)
    impression_count: Optional[int] = Field(example=1500)
    bookmark_count: Optional[int] = Field(example=3)
    url: Optional[str] = Field(example="https://twitter.com/example_tweet")
    created_at: Optional[str] = Field(example="2023-01-01T00:00:00Z")
    media: Optional[List[TwitterScraperMedia]] = Field(default_factory=list, example=[])

    # Only available in scraped tweets
    is_quote_tweet: Optional[bool] = Field(example=False)
    is_retweet: Optional[bool] = Field(example=False)


class WebSearchResultItem(BaseModel):
    title: str = Field(
        ..., description="EXCLUSIVE Major coffee buyers face losses as Colombia ..."
    )
    snippet: str = Field(
        ...,
        description="Coffee farmers in Colombia, the world's No. 2 arabica producer, have failed to deliver up to 1 million bags of beans this year or nearly 10% ...",
    )
    link: str = Field(
        ...,
        description="https://www.reuters.com/world/americas/exclusive-major-coffee-buyers-face-losses-colombia-farmers-fail-deliver-2021-10-11/",
    )
    date: Optional[str] = Field(
        None, description="21 hours ago"
    )  # Optional, as it might not always be present
    source: str = Field(..., description="Reuters")

    author: Optional[str] = Field(None, description="Reuters")

    image: Optional[str] = Field(
        None,
        description="https://static.reuters.com/resources/2021/10/11/Reuters/Reuters_20211011_0000_01.jpg?w=800&h=533&q=80&crop=1",
    )
    favicon: Optional[str] = Field(
        None,
        description="https://static.reuters.com/resources/2021/10/11/Reuters/Reuters_20211011_0000_01.jpg?w=800&h=533&q=80&crop=1",
    )
    highlights: Optional[List[str]] = Field(
        None, description="List of highlights as strings."
    )

    class Config:
        schema_extra = {
            "example": {
                "title": "EXCLUSIVE Major coffee buyers face losses as Colombia ...",
                "snippet": "Coffee farmers in Colombia, the world's No. 2 arabica producer, have failed to deliver up to 1 million bags of beans this year or nearly 10% ...",
                "link": "https://www.reuters.com/world/americas/exclusive-major-coffee-buyers-face-losses-colombia-farmers-fail-deliver-2021-10-11/",
                "date": "21 hours ago",
                "source": "Reuters",
                "author": "Reuters",
                "image": "https://static.reuters.com/resources/2021/10/11/Reuters/Reuters_20211011_0000_01.jpg?w=800&h=533&q=80&crop=1",
                "favicon": "https://static.reuters.com/resources/2021/10/11/Reuters/Reuters_20211011_0000_01.jpg?w=800&h=533&q=80&crop=1",
                "highlights": ["Such requests are not allowed."],
            }
        }


class BasicWebSearchResponse(BaseModel):
    data: List[WebSearchResultItem]


class TwitterUserEntities(BaseModel):
    description: Dict[str, List[Dict[str, Any]]]
    url: Optional[Dict[str, List[Dict[str, Any]]]]


class TwitterUser(BaseModel):
    id: str
    url: str
    name: str
    username: str
    created_at: str
    description: str
    favourites_count: int
    followers_count: int
    listed_count: int
    media_count: int
    profile_image_url: str
    profile_banner_url: Optional[str]
    statuses_count: int
    verified: bool
    is_blue_verified: bool
    entities: TwitterUserEntities
    can_dm: bool
    can_media_tag: bool
    location: Optional[str]
    pinned_tweet_ids: List[str]


class TwitterTweetEntities(BaseModel):
    hashtags: List[Dict[str, Any]]
    symbols: List[Dict[str, Any]]
    timestamps: List[Dict[str, Any]]
    urls: List[Dict[str, Any]]
    user_mentions: List[Dict[str, Any]]


class TwitterByIdResponse(BaseModel):
    user: TwitterUser
    id: str
    text: str
    reply_count: int
    retweet_count: int
    like_count: int
    quote_count: int
    bookmark_count: int
    url: str
    created_at: str
    media: List[Any]
    is_quote_tweet: bool
    is_retweet: bool
    lang: str
    conversation_id: str
    in_reply_to_screen_name: Optional[str]
    in_reply_to_status_id: Optional[str]
    in_reply_to_user_id: Optional[str]
    quoted_status_id: Optional[str]
    quote: Optional[str]
    display_text_range: List[int]
    entities: TwitterTweetEntities
    extended_entities: Dict[str, Any]


class TwitterUserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    screen_name: str = Field(description="User's screen name")
    is_blue_verified: bool = Field(
        description="Indicates if the user is Blue Tick verified"
    )
    following: bool = Field(description="Indicates if the user is being followed")
    can_dm: bool = Field(description="Indicates if the user can be direct messaged")
    can_media_tag: bool = Field(
        description="Indicates if the user can be tagged in media"
    )
    created_at: str = Field(description="Account creation date")
    default_profile: bool = Field(
        description="Indicates if the user has the default profile"
    )
    default_profile_image: bool = Field(
        description="Indicates if the user has the default profile image"
    )
    description: str = Field(description="User description")
    entities: TwitterUserEntities = Field(description="User entities")
    fast_followers_count: int = Field(description="Count of fast followers")
    favourites_count: int = Field(description="Count of favourites")
    followers_count: int = Field(description="Count of followers")
    friends_count: int = Field(description="Count of friends")
    has_custom_timelines: bool = Field(
        description="Indicates if the user has custom timelines"
    )
    is_translator: bool = Field(description="Indicates if the user is a translator")
    listed_count: int = Field(description="Count of lists the user is on")
    location: str = Field(description="User location")
    media_count: int = Field(description="Count of media")
    name: str = Field(description="User's name")
    normal_followers_count: int = Field(description="Count of normal followers")
    pinned_tweet_ids_str: List[str] = Field(description="List of pinned tweet IDs")
    possibly_sensitive: bool = Field(
        description="Indicates if the user is possibly sensitive"
    )
    profile_banner_url: Optional[HttpUrl] = Field(
        description="URL of the profile banner"
    )
    profile_image_url_https: Optional[HttpUrl] = Field(
        description="HTTPS URL of the profile image"
    )
    profile_interstitial_type: str = Field(description="Profile interstitial type")
    statuses_count: int = Field(description="Count of statuses")
    translator_type: str = Field(description="Translator type")
    verified: bool = Field(description="Indicates if the user is verified")
    want_retweets: bool = Field(description="Indicates if the user wants retweets")
    withheld_in_countries: List[str] = Field(
        description="List of countries where the user is withheld"
    )
