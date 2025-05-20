import json
from typing import Any, Dict, List, Optional, Callable, Iterable, Literal, Union
from functools import wraps

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat_model import ChatModel


class DesearchOpenAICompletion:
    """Desearch wrapper for OpenAI completion."""

    def __init__(self, desearch_result: Optional[Any], **kwargs):
        # Copy all attributes from the completion
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.desearch_result = desearch_result

    @classmethod
    def from_completion(cls, desearch_result: Optional[Any], completion: Any):
        """Create a new DesearchOpenAICompletion from an existing completion."""
        kwargs = {key: value for key, value in completion.__dict__.items()}
        return cls(desearch_result=desearch_result, **kwargs)


def extract_query(completion) -> Optional[str]:
    """Extract query from completion if it exists."""
    if not completion.choices[0].message.tool_calls:
        return None

    for tool_call in completion.choices[0].message.tool_calls:
        if tool_call.function.name == "search":
            query = json.loads(tool_call.function.arguments).get("query")
            return query

    return None


def prepare_messages(completion, messages, desearch_result) -> List[Dict[str, Any]]:
    """Add assistant message and desearch result to messages list.
    Also remove previous desearch call and results."""
    assistant_message = completion.choices[0].message

    # Remove previous desearch call and results to prevent blowing up history
    messages = [
        message for message in messages if not (message.get("role") == "function")
    ]

    # Add new messages
    messages.extend(
        [
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    tool_call.model_dump() for tool_call in assistant_message.tool_calls
                ],
            },
            {
                "role": "tool",
                "name": "search",
                "tool_call_id": assistant_message.tool_calls[0].id,
                "content": format_desearch_result(desearch_result),
            },
        ]
    )

    return messages


def format_desearch_result(desearch_result: Any, max_results: int = 10) -> str:
    """Format desearch result for chat display."""

    formatted_results = []

    # Handle AI search response
    completion = desearch_result.get("completion", {})
    if completion:
        summary = completion.get("summary")
        if summary:
            formatted_results.append(f"Summary: {summary}")

        # Add key sources if available
        key_sources = completion.get("key_sources", [])
        for idx, source in enumerate(key_sources[:max_results], 1):
            formatted_results.append(f"Source {idx}:")
            formatted_results.append(f"Text: {source.get('text', 'No text available')}")
            formatted_results.append(f"URL: {source.get('url', 'No URL available')}")
            formatted_results.append("")

    # Handle web results
    web_results = []

    for result_type in [
        "wikipedia_search_results",
        "youtube_search_results",
        "reddit_search_results",
        "hacker_news_search_results",
        "arxiv_search_results",
    ]:
        results = desearch_result.get(result_type, [])
        organic_results = (
            results.get("organic_results") if isinstance(results, dict) else results
        )

        if organic_results:
            for result in organic_results[:max_results]:
                web_results.append(
                    {
                        "title": result.get("title", "No title available"),
                        "url": result.get("link", "No link available"),
                        "snippet": result.get("snippet", "No snippet available"),
                        "source": result_type.replace(
                            "_search_results", ""
                        ).capitalize(),
                    }
                )

    # Add web results to formatted results
    for idx, result in enumerate(web_results[:max_results], 1):
        formatted_results.append(f"Result {idx}:")
        formatted_results.append(f"Title: {result['title']}")
        formatted_results.append(f"URL: {result['url']}")
        formatted_results.append(f"Snippet: {result['snippet']}")
        formatted_results.append(f"Source: {result['source']}")
        formatted_results.append("")

    return "\n".join(formatted_results) if formatted_results else "No results found."


# Moved from Desearch class
def create_with_search_tool(
    desearch_client,
    create_fn: Callable,
    messages: List[Dict],
    create_kwargs: Dict,
    desearch_kwargs: Dict,
) -> DesearchOpenAICompletion:
    """Create a completion enhanced with Desearch search results"""
    # Define the search tool
    search_tool = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search the web for relevant information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for.",
                        },
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    # Add tool to the create kwargs
    create_kwargs["tools"] = search_tool

    # Call the original function to get initial completion
    initial_completion = create_fn(messages=messages, **create_kwargs)

    # Extract search query if present
    search_query = extract_query(initial_completion)

    # If no search query, return the original completion
    if not search_query:
        return DesearchOpenAICompletion.from_completion(
            completion=initial_completion, desearch_result=None
        )

    # Perform search with Desearch
    search_results = desearch_client.ai_search(
        prompt=search_query,
        **{k: v for k, v in desearch_kwargs.items() if v is not None},
    )

    # Add search results to messages
    updated_messages = prepare_messages(initial_completion, messages, search_results)

    # Get final completion with search results included
    final_completion = create_fn(messages=updated_messages, **create_kwargs)

    # Return wrapped completion with search results
    return DesearchOpenAICompletion.from_completion(
        completion=final_completion, desearch_result=search_results
    )


# Moved from Desearch class
def wrap_openai_client(desearch_client, openai_client: OpenAI) -> OpenAI:
    """
    Enhance an OpenAI client with Desearch search capabilities.

    This wrapper intercepts calls to the chat.completions.create method
    and enhances them with relevant search results from Desearch.

    Args:
        desearch_client: The Desearch client to use for searches
        openai_client: The OpenAI client to wrap

    Returns:
        The enhanced OpenAI client
    """

    # Store the original create function
    original_create = openai_client.chat.completions.create

    # Define the enhanced create function
    @wraps(original_create)
    def enhanced_create(
        # Required OpenAI parameters
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        # Desearch parameters
        disabled: Optional[bool] = False,
        desearch_tools: Optional[List] = None,
        desearch_model: Optional[Any] = None,
        date_filter: Optional[Any] = None,
        result_type: Optional[Any] = None,
        system_message: Optional[str] = None,
        # Other OpenAI parameters
        **openai_kwargs,
    ):
        # Skip Desearch if explicitly disabled
        if disabled:
            return original_create(messages=messages, model=model, **openai_kwargs)

        # Use default tools if none provided
        if desearch_tools is None:
            # Import inside function to avoid circular imports
            from .protocol import ToolEnum

            desearch_tools = [ToolEnum.web, ToolEnum.twitter]

        # Import model enum if needed
        if desearch_model is None:
            from .protocol import ModelEnum

            desearch_model = ModelEnum.NOVA

        # Prepare Desearch-specific parameters
        desearch_params = {
            "tools": [tool.value for tool in desearch_tools],
            "model": desearch_model.value,
            "date_filter": date_filter.value if date_filter else None,
            "result_type": result_type.value if result_type else None,
            "system_message": system_message,
            "streaming": False,
        }

        # Prepare OpenAI-specific parameters
        openai_params = {
            "model": model,
            **openai_kwargs,
        }

        # Use the search tool creation function
        return create_with_search_tool(
            desearch_client=desearch_client,
            create_fn=original_create,
            messages=list(messages),
            create_kwargs=openai_params,
            desearch_kwargs=desearch_params,
        )

    # Replace the original method with our enhanced version
    openai_client.chat.completions.create = enhanced_create

    return openai_client
