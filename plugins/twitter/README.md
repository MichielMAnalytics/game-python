# Twitter Plugin for GAME SDK

The Twitter plugin is a lightweight wrapper over commonly-used twitter API calls. It can be used as a executable on its own or by combining multiple of these into an executable.

## Installation

From this directory (`twitter`), run the installation:

```bash
poetry install
```

## Usage

The Twitter plugin can be initialized in one of two ways:

1. Using GAME's X enterprise API credentials (higher rate limits)

   - To get the access token for this option, run the following command:

     ```bash
     poetry run twitter-plugin-gamesdk auth -k <GAME_API_KEY>
     ```

     You will see the following output:

     ```bash
     Waiting for authentication...

     Visit the following URL to authenticate:
     https://x.com/i/oauth2/authorize?response_type=code&client_id=VVdyZ0t4WFFRMjBlMzVaczZyMzU6MTpjaQ&redirect_uri=http%3A%2F%2Flocalhost%3A8714%2Fcallback&state=866c82c0-e3f6-444e-a2de-e58bcc95f08b&code_challenge=K47t-0Mcl8B99ufyqmwJYZFB56fiXiZf7f3euQ4H2_0&code_challenge_method=s256&scope=tweet.read%20tweet.write%20users.read%20offline.access
     ```

     After authenticating, you will receive the following message:

     ```bash
     Authenticated! Here's your access token:
     apx-<xxx>
     ```

   - Set the access token as an environment variable called `GAME_TWITTER_ACCESS_TOKEN` (e.g. using a `.bashrc` or a `.zshrc` file).
   - Import and initialize the plugin to use in your worker:

     ```python
     import os
     from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin

     # Define your options with the necessary credentials
     options = {
         "credentials": {
             "gameTwitterAccessToken": os.environ.get("GAME_TWITTER_ACCESS_TOKEN")
         },
     }
     # Initialize the TwitterPlugin with your options
     twitter_plugin = TwitterPlugin(options)

     # Post a tweet
     post_tweet_fn = twitter_plugin.get_function('post_tweet')
     post_tweet_fn("Hello world!")
     ```

2. Using your own X API credentials

   - If you don't already have one, create a X (twitter) account and navigate to the [developer portal](https://developer.x.com/en/portal/dashboard).
   - Create a project app, generate the following credentials and set them as environment variables (e.g. using a `.bashrc` or a `.zshrc` file):
     - `TWITTER_BEARER_TOKEN`
     - `TWITTER_API_KEY`
     - `TWITTER_API_SECRET_KEY`
     - `TWITTER_ACCESS_TOKEN`
     - `TWITTER_ACCESS_TOKEN_SECRET`
   - Import and initialize the plugin to use in your worker:

     ```python
     import os
     from twitter_plugin_gamesdk.twitter_plugin import TwitterPlugin

     # Define your options with the necessary credentials
     options = {
         "credentials": {
             "bearerToken": os.environ.get("TWITTER_BEARER_TOKEN"),
             "apiKey": os.environ.get("TWITTER_API_KEY"),
             "apiSecretKey": os.environ.get("TWITTER_API_SECRET_KEY"),
             "accessToken": os.environ.get("TWITTER_ACCESS_TOKEN"),
             "accessTokenSecret": os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
         },
     }
     # Initialize the TwitterPlugin with your options
     twitter_plugin = TwitterPlugin(options)

     # Post a tweet
     post_tweet_fn = twitter_plugin.twitter_client.create_tweet
     post_tweet_fn(text="Hello world! This is a test tweet from the Twitter Plugin!")
     ```

For detailed documentation on each function's parameters and usage, please refer to the [Tweepy Client Documentation](https://docs.tweepy.org/en/stable/client.html).

Example usage:

You can refer to the example files in the `examples` directory for more examples on how to call the twitter functions.
