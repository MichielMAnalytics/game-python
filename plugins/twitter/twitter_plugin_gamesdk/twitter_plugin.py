"""
Twitter Plugin for the GAME SDK.

This plugin provides a wrapper around the Twitter API using tweepy, enabling
GAME SDK agents to interact with Twitter programmatically. It supports common
Twitter operations like posting tweets, replying, quoting, and getting metrics.

Example:
    ```python
    options = {
        "id": "twitter_agent",
        "name": "Twitter Bot",
        "description": "A Twitter bot that posts updates",
        "credentials": {
            "bearerToken": "your_bearer_token",
            "apiKey": "your_api_key",
            "apiSecretKey": "your_api_secret",
            "accessToken": "your_access_token",
            "accessTokenSecret": "your_access_token_secret"
        }
    }
    
    twitter_plugin = TwitterPlugin(options)
    post_tweet_fn = twitter_plugin.get_function('post_tweet')
    post_tweet_fn("Hello, World!")
    ```
"""

import tweepy
import logging
from typing import Dict, Any

class TwitterPlugin:
    """
    A plugin for interacting with Twitter through the GAME SDK.

    This class provides a set of functions for common Twitter operations,
    wrapped in a format compatible with the GAME SDK's plugin system.

    Args:
        options (Dict[str, Any]): Configuration options including:
            - id (str): Unique identifier for the plugin instance
            - name (str): Display name for the plugin
            - description (str): Plugin description
            - credentials (Dict[str, str]): Twitter API credentials

    Attributes:
        id (str): Plugin identifier
        name (str): Plugin name
        description (str): Plugin description
        twitter_client (tweepy.Client): Authenticated Twitter API client
        logger (logging.Logger): Plugin logger

    Raises:
        ValueError: If required Twitter API credentials are missing
    """

    def __init__(self, options: Dict[str, Any]) -> None:
        # Set credentials
        self.base_url = options.get("base_url", "https://twitter.game.virtuals.io") + '/tweets'
        credentials = options.get("credentials")
        if not credentials:
            raise ValueError("Twitter API credentials are required.")
        # Init Tweepy client
        self.twitter_client: tweepy.Client = tweepy.Client(
            bearer_token = credentials.get("bearerToken"),
            consumer_key = credentials.get("apiKey"),
            consumer_secret = credentials.get("apiSecretKey"),
            access_token = credentials.get("accessToken"),
            access_token_secret=credentials.get("accessTokenSecret"),
            return_type = dict,
            game_twitter_access_token = credentials.get("gameTwitterAccessToken"),
        )
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger: logging.Logger = logging.getLogger(__name__)
        
        self.game_twitter_access_token = credentials.get("gameTwitterAccessToken")
        

