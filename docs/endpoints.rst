Search API, social media, and network stats
===========================================

Methods added in desearch-py 1.8.0. Every method is a coroutine on the async
``Desearch`` client and takes the keyword-only ``include_metadata`` argument.
With ``include_metadata=True`` it returns a ``DesearchResponse`` whose ``data``
is the usual return value and whose ``metadata`` (``DesearchCostMetadata``)
holds the cost headers and, for social list routes, ``next_cursor``.
``stream_network_stats`` is the exception: it is an async iterator and has no
``include_metadata``.

HTTP errors raise ``DesearchAPIError`` (``status``, ``message``, ``body``) with
the API key redacted.

.. code-block:: python

   import asyncio

   from desearch_py import Desearch


   async def main() -> None:
       async with Desearch(api_key="your_api_key") as client:
           posts = await client.tiktok_hashtag("ai", count=5)
           print([post.id for post in posts])


   asyncio.run(main())


Search API
----------

``search_api(query, mode=None, count=None, start_date=None, end_date=None, highlights=None, page_text=None)``
   ``POST /search``. Searches the web and returns ranked pages, each with the
   passage that best matches the query. Returns ``SearchApiResponse``
   (``results``: a list of ``SearchApiResult`` with ``url``, ``title``,
   ``published_date``, ``highlights`` and ``page_text``; plus ``cost_usd``,
   ``usage_count``, ``service`` and ``currency``).

   * ``mode``: ``SearchApiMode.FAST`` / ``"fast"`` returns results sooner;
     ``"balanced"`` (the API default) favors relevance.
   * ``count``: 10 (the API default), 15 or 20.
   * ``start_date`` / ``end_date``: ``YYYY-MM-DD``.
   * ``highlights``: include the best matching passage (the API default is
     ``True``). ``page_text``: include the full page text (default ``False``).

   Unset arguments are not sent. The SDK has no method named plain ``search``.

.. code-block:: python

   response = await client.search_api(
       "Who won the 2024 Nobel Prize in Physics?", mode="fast", count=10
   )
   for result in response.results:
       print(result.title, result.url, result.highlights)


TikTok
------

``tiktok_search(query, count=None, cursor=None, sort=None)``
   ``POST /desearch/tiktok/search``. Returns ``List[TikTokPost]``. ``count``
   1-100 (the API default is 10). Paginates; send the cursor back with the
   same ``query`` and ``sort``.

``tiktok_post_by_id(id)``
   ``GET /desearch/tiktok/post/{id}``. Returns ``TikTokPost``.

``tiktok_profile(username)``
   ``GET /desearch/tiktok/profile/{username}``. Username without ``@``.
   Returns ``TikTokProfile``.

``tiktok_profile_posts(username, count=None, cursor=None)``
   ``GET /desearch/tiktok/profile/{username}/posts``. Returns
   ``List[TikTokPost]``. Paginates.

``tiktok_comments(video_id, count=None, cursor=None)``
   ``GET /desearch/tiktok/comments/{video_id}``. ``video_id`` is
   ``TikTokPost.id``. Returns ``List[TikTokComment]``. Paginates.

``tiktok_hashtag(tag, count=None, cursor=None)``
   ``GET /desearch/tiktok/hashtag/{tag}``. Tag without ``#``. Returns
   ``List[TikTokPost]``. Paginates.

``tiktok_trending(region=None, count=None)``
   ``GET /desearch/tiktok/trending``. ``region`` is a two-letter code (the API
   default is ``US``). Returns ``List[TikTokPost]``. Does not paginate.


Instagram
---------

``instagram_search(query, count=None)``
   ``POST /desearch/instagram/search``. Finds profiles. Returns
   ``List[InstagramSearchResult]`` (``type`` is ``profile``, ``hashtag`` or
   ``media``). One page only: the API rejects a cursor, so the method takes
   none.

``instagram_media(id)``
   ``GET /desearch/instagram/media/{id}``. A shortcode, media ID, or public
   post URL. Returns ``InstagramMedia``.

``instagram_profile(username)``
   ``GET /desearch/instagram/profile/{username}``. Returns
   ``InstagramProfile``.

``instagram_profile_posts(username, count=None, cursor=None)``
   ``GET /desearch/instagram/profile/{username}/posts``. Returns
   ``List[InstagramMedia]`` (about 12 per page). Paginates.

``instagram_comments(shortcode, count=None, cursor=None)``
   ``GET /desearch/instagram/comments/{shortcode}``. ``shortcode`` is the code
   in ``instagram.com/p/<shortcode>/`` (``InstagramMedia.shortcode``); a
   numeric media ID returns 404. Returns ``List[InstagramComment]``. Paginates.

``instagram_hashtag(tag, count=None, cursor=None)``
   ``GET /desearch/instagram/hashtag/{tag}``. Returns ``List[InstagramMedia]``.
   Paginates.


Facebook
--------

``facebook_search(query, count=None, cursor=None)``
   ``POST /desearch/facebook/search``. Searches the public Meta Ad Library, not
   organic posts. Returns ``List[FacebookPost]`` with the ad fields set
   (``linkUrl``, ``cta``, ``headline``, ``linkDescription``, ``endDate``,
   ``active``, ``platforms``). Paginates.

``facebook_post_by_id(id)``
   ``GET /desearch/facebook/post/{id}``. Returns ``FacebookPost``.

``facebook_profile(profile_id)``
   ``GET /desearch/facebook/profile/{profile_id}``. A profile or page ID,
   username, or vanity handle. Returns ``FacebookProfile``.

``facebook_profile_posts(profile_id, count=None, cursor=None)``
   ``GET /desearch/facebook/profile/{profile_id}/posts``. Returns
   ``List[FacebookPost]`` (about 3 per page). Paginates.

``facebook_comments(post_id, count=None, cursor=None)``
   ``GET /desearch/facebook/comments/{post_id}``. Returns
   ``List[FacebookComment]`` (about 10 per page). Paginates.

``facebook_hashtag(tag, count=None, cursor=None)``
   ``GET /desearch/facebook/hashtag/{tag}``. Meta Ad Library records for the
   keyword. Returns ``List[FacebookPost]``. Paginates.

Notes for every social method:

* ``count`` is a maximum, 1-100. The API default is 10 for the search methods
  and 20 elsewhere.
* Path parameters are percent-encoded as one segment, ``/`` included.
* Model fields keep the API's camelCase names (``createTime``, ``playCount``)
  and are all optional. Models keep unknown fields.
* A list method returns the raw ``dict`` when the API answers with an object
  instead of a list.


Pagination
----------

Social list methods return one page. The API puts the cursor for the next page
in the ``x-desearch-next-cursor`` response header; the SDK exposes it as
``metadata.next_cursor`` when you pass ``include_metadata=True``:

.. code-block:: python

   cursor = None
   for _ in range(3):  # read up to three pages
       page = await client.instagram_profile_posts(
           "instagram", count=12, cursor=cursor, include_metadata=True
       )
       for media in page.data:
           print(media.shortcode, media.caption)
       cursor = page.metadata.next_cursor
       if cursor is None:  # the last page has no cursor
           break

* Send the cursor back unchanged, to the same method with the same target
  (username, tag, post ID, or query). It is opaque: never build or edit one.
* A cursor is valid for 24 hours. An expired cursor, one from another route
  or target, or a value the API did not issue gets HTTP 422 and is not
  charged.
* A page shorter than ``count`` is not the end; only a missing
  ``next_cursor`` is.
* ``tiktok_trending`` and ``instagram_search`` do not paginate.


Network stats
-------------

Public routes: the API does not check the API key and does not charge.

``network_stats()``
   ``GET /network/stats``. Returns ``NetworkStatsResponse``: the counters
   ``total_searchable_pages``, ``searches_completed_today`` and
   ``urls_crawled_today``, their ``rates_per_second``, ``started_at``,
   ``updated_at``, and ``telemetry_kind`` / ``methodology`` (today
   ``estimated`` / ``fixed_rate_projection``).

``network_stats_history()``
   ``GET /network/stats/history``. Returns ``NetworkStatsHistoryResponse``: one
   ``NetworkStatsHistoryPoint`` per second for the last 20 minutes.

``stream_network_stats(*, last_event_id=None)``
   ``GET /network/stats/stream``. An async iterator of ``NetworkStatsEvent``
   (``id``, ``event`` and ``data``, a ``NetworkStatsResponse``), one per second.
   Pass the last ``event.id`` as ``last_event_id`` to resume; the API replays
   up to 20 minutes. It does not reconnect on its own. There is no total
   timeout; it fails if no data arrives for 60 seconds.

.. code-block:: python

   from contextlib import aclosing

   last_event_id = None
   async with aclosing(client.stream_network_stats()) as events:
       async for event in events:
           last_event_id = event.id
           print(event.data.updated_at, event.data.total_searchable_pages)
           if event.data.searches_completed_today > 1_000_000:
               break
