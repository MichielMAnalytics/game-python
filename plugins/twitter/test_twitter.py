import os
from twitter_game_sdk.twitter_plugin import TwitterPlugin

# Define your options with the necessary credentials
options = {
    "id": "test_twitter_worker",
    "name": "Test Twitter Worker",
    "description": "An example Twitter Plugin for testing.",
    "credentials": {
        "apiKey": os.environ.get("TWITTER_API_KEY"),
        "apiSecretKey": os.environ.get("TWITTER_API_SECRET_KEY"),
        "accessToken": os.environ.get("TWITTER_ACCESS_TOKEN"),
        "accessTokenSecret": os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    },
}

# Initialize the TwitterPlugin with your options
twitter_plugin = TwitterPlugin(options)

# Test case 1: Post a Tweet
print("Running Test Case 1: Post a Tweet")
post_tweet_fn = twitter_plugin.get_function('post_tweet')
post_tweet_fn("Hi! Hello world! This is a test tweet from the Twitter Plugin!")
print("Posted tweet!")

# Test case 2: Reply to a Tweet
print("\nRunning Test Case 2: Reply to a Tweet")
reply_tweet_fn = twitter_plugin.get_function('reply_tweet')
reply_tweet_fn(tweet_id=1879472470362816626, reply="Hey! This is a test reply!")
print("Liked tweet!")

# Test case 3: Like a Tweet
print("\nRunning Test Case 3: Like a Tweet")
like_tweet_fn = twitter_plugin.get_function('like_tweet')
like_tweet_fn(tweet_id=1879472470362816626)
print("Liked tweet!")

# Test case 4: Quote a Tweet
print("\nRunning Test Case 4: Quote a Tweet")
quote_tweet_fn = twitter_plugin.get_function('quote_tweet')
quote_tweet_fn(tweet_id=1879472470362816626, quote="Hey! This is a test quote tweet!")
print("Quoted tweet!")

# Test case 5: Get Metrics
print("\nRunning Test Case 5: Get Metrics")
get_metrics_fn = twitter_plugin.get_function('get_metrics')
metrics = get_metrics_fn()
print("Metrics:", metrics)