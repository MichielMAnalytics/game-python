from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin

# Define your options with the necessary credentials
# Using your own X API credentials
""" options = {
    "credentials": {
        "bearerToken": os.environ.get("TWITTER_BEARER_TOKEN"),
        "apiKey": os.environ.get("TWITTER_API_KEY"),
        "apiSecretKey": os.environ.get("TWITTER_API_SECRET_KEY"),
        "accessToken": os.environ.get("TWITTER_ACCESS_TOKEN"),
        "accessTokenSecret": os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    },
} """

# Using GAME Twitter API credentials
options = {
    "credentials": {
        "gameTwitterAccessToken": "apx-xxx",
    },
}

# Initialize the TwitterPlugin with your options
twitter_plugin = TwitterPlugin(options)

# Test case 1: Post a Tweet
print("\nRunning Test Case 1: Post a Tweet")
post_tweet_fn = twitter_plugin.twitter_client.create_tweet
post_tweet_fn(text="Hello world! This is a test tweet from the Twitter Plugin!")
print("Posted tweet!")

# Test case 2: Post a Tweet with Media
print("\nRunning Test Case 2: Post a Tweet with Media")
print("\nUpload media")
with open("sample_media/media_file.png", "rb") as f:
    media_id = twitter_plugin.twitter_client.upload_media(f)
    print(f"Uploaded media_id: {media_id}")
post_tweet_fn = twitter_plugin.twitter_client.create_tweet
post_tweet_fn(text="Hello world! This is a test tweet with media from the Twitter Plugin!", media_ids=[media_id])
print("Posted tweet with media!")


# Test case 3: Reply to a Tweet
print("\nRunning Test Case 3: Reply to a Tweet")
reply_tweet_fn = twitter_plugin.twitter_client.create_tweet
reply_tweet_fn(in_reply_to_tweet_id=1915274034100809968, text="Hey! This is a test reply!")
print("Replied to tweet!")

# Test case 4: Like a Tweet
print("\nRunning Test Case 4: Like a Tweet")
like_tweet_fn = twitter_plugin.twitter_client.like
like_tweet_fn(tweet_id=1915274034100809968)
print("Liked tweet!")

# Test case 5: Quote a Tweet
print("\nRunning Test Case 5: Quote a Tweet")
quote_tweet_fn = twitter_plugin.twitter_client.create_tweet
quote_tweet_fn(quote_tweet_id=1915274034100809968, text="Hey! This is a test quote tweet!")
print("Quoted tweet!")

# Test case 6: Get Metrics
print("\nRunning Test Case 6: Get Metrics")
get_metrics_fn = twitter_plugin.twitter_client.get_me
metrics = get_metrics_fn(user_fields=["public_metrics"])
print("Metrics:", metrics)

# Test case 7: Get User From Handle
print("\nRunning Test Case 7: Get User From Handle")
get_user_fn = twitter_plugin.twitter_client.get_user
user = get_user_fn(username='celesteanglm', user_fields=["public_metrics"])
print("user:", user)

# Test case 8: Get User Mentions
print("\nRunning Test Case 8: Get User Mentions")
get_user_fn = twitter_plugin.twitter_client.get_user
user = get_user_fn(username="GAME_Virtuals")
get_user_mentions_fn = twitter_plugin.twitter_client.get_users_mentions
user_mentions = get_user_mentions_fn(  id = user['data']['id'], 
                max_results = 10,
                tweet_fields = ["id", "created_at", "text"],
                expansions = ["attachments.media_keys"],
                media_fields = ["url"])
print("user_mentions:", user_mentions)

