# Datura


Datura API in Python


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

```