import unittest

from desearch_py import TwitterScraperCard, TwitterScraperTweet

TWEET = {
    "id": "2101254595058024720",
    "text": "Starship Flight 14 https://t.co/hVHgyxtOZ9",
    "reply_count": 37,
    "retweet_count": 1,
    "like_count": 13,
    "quote_count": 1,
    "bookmark_count": 1,
    "created_at": "Sat Sep 19 10:18:29 +0000 2026",
}

CARD = {
    "type": "summary_large_image",
    "url": "https://t.co/hVHgyxtOZ9",
    "title": "Starship | Starlink Group 31-1 (Starship Flight 14)",
    "description": "14th test flight of the two-stage Starship launch vehicle.",
    "domain": "www.missionstatus.com",
    "image": "https://pbs.twimg.com/card_img/2104931127370690560/nssO7aWi?format=jpg&name=800x419",
    "image_alt": "launch card",
    "player_url": None,
    "broadcast_url": None,
    "state": None,
}


class TwitterCardTest(unittest.TestCase):
    def test_card_is_typed(self):
        tweet = TwitterScraperTweet.model_validate({**TWEET, "card": CARD})

        self.assertIsInstance(tweet.card, TwitterScraperCard)
        self.assertEqual(tweet.card.title, CARD["title"])
        self.assertEqual(tweet.card.domain, "www.missionstatus.com")

    def test_card_in_replies(self):
        reply = {**TWEET, "id": "2", "card": {"type": "broadcast", "state": "ENDED"}}
        tweet = TwitterScraperTweet.model_validate({**TWEET, "replies": [reply]})

        self.assertEqual(tweet.replies[0].card.state, "ENDED")

    def test_missing_card_is_none(self):
        self.assertIsNone(TwitterScraperTweet.model_validate(TWEET).card)
        self.assertIsNone(
            TwitterScraperTweet.model_validate({**TWEET, "card": None}).card
        )


if __name__ == "__main__":
    unittest.main()
