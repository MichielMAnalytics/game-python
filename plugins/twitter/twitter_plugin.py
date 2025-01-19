import tweepy
import logging
from typing import Dict, Callable, Any, Optional, List, Callable


class TwitterPlugin:
    def __init__(self, options: Dict[str, Any]) -> None:
        self.id: str = options.get("id", "twitter_plugin")
        self.name: str = options.get("name", "Twitter Plugin")
        self.description: str = options.get(
            "description",
            "A plugin that executes tasks within Twitter, capable of posting, replying, quoting, and liking tweets, and getting metrics.",
        )
        # Ensure credentials are provided
        credentials: Optional[Dict[str, str]] = options.get("credentials")
        if not credentials:
            raise ValueError("Twitter API credentials are required.")
        
        self.twitter_client: tweepy.Client = tweepy.Client(
            consumer_key=credentials.get("apiKey"),
            consumer_secret=credentials.get("apiSecretKey"),
            access_token=credentials.get("accessToken"),
            access_token_secret=credentials.get("accessTokenSecret"),
        )
        # Define internal function mappings
        self._functions: Dict[str, Callable[..., Any]] = {
            "get_metrics": self._get_metrics,
            "reply_tweet": self._reply_tweet,
            "post_tweet": self._post_tweet,
            "like_tweet": self._like_tweet,
            "quote_tweet": self._quote_tweet,
        }
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger: logging.Logger = logging.getLogger(__name__)

    @property
    def available_functions(self) -> List[str]:
        """Get list of available function names."""
        return list(self._functions.keys())

    def get_function(self, fn_name: str) -> Callable:
        """
        Get a specific function by name.

        Args:
            fn_name: Name of the function to retrieve

        Raises:
            ValueError: If function name is not found

        Returns:
            Function object
        """
        if fn_name not in self._functions:
            raise ValueError(
                f"Function '{fn_name}' not found. Available functions: {', '.join(self.available_functions)}"
            )
        return self._functions[fn_name]

    def _get_metrics(self) -> Dict[str, int]:
        try:
            user = self.twitter_client.get_me(user_fields=["public_metrics"])
            if not user or not user.data:
                self.logger.warning("Failed to fetch user metrics.")
                return {}
            public_metrics = user.data.public_metrics
            return {
                "followers": public_metrics.get("followers_count", 0),
                "following": public_metrics.get("following_count", 0),
                "tweets": public_metrics.get("tweet_count", 0),
            }
        except tweepy.TweepyException as e:
            self.logger.error(f"Failed to fetch metrics: {e}")
            return {}

    def _reply_tweet(self, tweet_id: int, reply: str) -> None:
        try:
            self.twitter_client.create_tweet(in_reply_to_tweet_id=tweet_id, text=reply)
            self.logger.info(f"Successfully replied to tweet {tweet_id}.")
        except tweepy.TweepyException as e:
            self.logger.error(f"Failed to reply to tweet {tweet_id}: {e}")

    def _post_tweet(self, tweet: str) -> Dict[str, Any]:
        try:
            self.twitter_client.create_tweet(text=tweet)
            self.logger.info("Tweet posted successfully.")
        except tweepy.TweepyException as e:
            self.logger.error(f"Failed to post tweet: {e}")

    def _like_tweet(self, tweet_id: int) -> None:
        try:
            self.twitter_client.like(tweet_id)
            self.logger.info(f"Tweet {tweet_id} liked successfully.")
        except tweepy.TweepyException as e:
            self.logger.error(f"Failed to like tweet {tweet_id}: {e}")

    def _quote_tweet(self, tweet_id: int, quote: str) -> None:
        try:
            self.twitter_client.create_tweet(quote_tweet_id=tweet_id, text=quote)
            self.logger.info(f"Successfully quoted tweet {tweet_id}.")
        except tweepy.TweepyException as e:
            self.logger.error(f"Failed to quote tweet {tweet_id}: {e}")