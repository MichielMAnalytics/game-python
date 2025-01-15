import tweepy
import traceback

class TwitterPlugin:
    def __init__(self, options):
        self.id = options.get("id", "twitter_plugin")
        self.name = options.get("name", "Twitter Plugin")
        self.description = options.get(
            "description",
            "A plugin that will execute tasks within the Twitter."
            "It is capable of posting, replying, quoting, and liking tweets."
        )
        credentials = options["credentials"]
        self.twitter_client = tweepy.Client(
            consumer_key=credentials["apiKey"],
            consumer_secret=credentials["apiSecretKey"],
            access_token=credentials["accessToken"],
            access_token_secret=credentials["accessTokenSecret"]
        )

    def get_metrics(self):
        user = self.twitter_client.get_me(user_fields=["public_metrics"])
        public_metrics = user.data.public_metrics
        return {
            "followers": public_metrics.get("followers_count", 0),
            "following": public_metrics.get("following_count", 0),
            "tweets": public_metrics.get("tweet_count", 0),
        }

    def reply_tweet_function(self, tweet_id, reply):
        try:
            self.twitter_client.create_tweet(in_reply_to_tweet_id=tweet_id, text=reply)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()

    def post_tweet_function(self, tweet):
        try:
            self.twitter_client.create_tweet(text=tweet)
        except Exception as e:
            return {"status": "Failed", "message": f"Error: {str(e)}"}
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()

    def like_tweet_function(self, tweet_id):
        try:
            self.twitter_client.like(tweet_id)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()

    def quote_tweet_function(self, tweet_id, quote):
        try:
            self.twitter_client.create_tweet(quote_tweet_id=tweet_id, text=quote)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            traceback.print_exc()