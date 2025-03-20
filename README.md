# Datura


Datura API in Python

https://console.datura.ai/

## Installation

`pip install datura-py`

## Usage

Import the package and initialize the Datura client with your API key:

```python
    from datura_py import Datura

    datura = Datura(api_key="your-api-key")
```

## Common requests

```python
    
    # Desearch AI Search
    result = datura.ai_search(
        prompt="Bittensor",
        tools=[
            "Web Search",
            "Hacker News Search",
            "Reddit Search",
            "Wikipedia Search",
            "Youtube Search",
            "Twitter Search",
            "ArXiv Search"
        ],
        model="NOVA",
        date_filter="PAST_24_HOURS",
        streaming=False,
    )

    #Desearch Twitter post search
    result = datura.twitter_links_search(
        prompt="Bittensor",
        model="NOVA",
    )

    #Desearch Web links search
    result = datura.web_links_search(
        prompt="Bittensor",
        tools=[
            "Web Search",
            "Hacker News Search",
            "Reddit Search",
            "Wikipedia Search",
            "Youtube Search",
            "Twitter Search",
            "ArXiv Search"
        ],
        model="NOVA",
    )

    #Basic Twitter search
    result = datura.basic_twitter_search(
        query="Whats going on with Bittensor",
        sort="Top",
        user="elonmusk",
        start_date="2024-12-01",
        end_date="2025-02-25",
        lang="en",
        verified=True,
        blue_verified=True,
        is_quote=True,
        is_video=True,
        is_image=True,
        min_retweets=1,
        min_replies=1,
        min_likes=1
        count=10
    )

    #Basic Web search
    result = datura.basic_web_search(
        query="latest news on AI",
        num=10,
        start=0
    )

    #Fetch Tweets by URLs
    result = datura.twitter_by_urls(
        urls=["https://twitter.com/elonmusk/status/1613000000000000000"]
    )

    #Fetch Tweets by ID
    result = datura.twitter_by_id(id="123456789")

```