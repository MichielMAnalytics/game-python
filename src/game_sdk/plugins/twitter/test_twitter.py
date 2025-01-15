import os
from game_sdk.plugins.twitter.twitter_plugin import TwitterPlugin

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
twitter_plugin.post_tweet_function("Hi! Hello world! This is a test tweet from the Twitter Plugin!")
print("Posted tweet!")

# Test case 2: Reply to a Tweet
print("\nRunning Test Case 3: Reply to a Tweet")
tweet_id = "enter-a-valid-tweet-id-here"  # Replace with a valid tweet ID for testing
twitter_plugin.reply_tweet_function(tweet_id=1879472470362816626, reply="Hey! This is a test reply!")
print("Liked tweet!")

# Test case 3: Like a Tweet
print("\nRunning Test Case 4: Like a Tweet")
twitter_plugin.like_tweet_function(tweet_id=1879472470362816626)
print("Liked tweet!")

# Test case 4: Quote a Tweet
print("\nRunning Test Case 5: Quote a Tweet")
twitter_plugin.quote_tweet_function(tweet_id=1879472470362816626, quote="Hey! This is a test quote tweet!")
print("Quoted tweet!")

# Test case 5: Get Metrics
print("\nRunning Test Case 6: Get Metrics")
metrics = twitter_plugin.get_metrics()
print("Metrics:", metrics)