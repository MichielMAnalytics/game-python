import os
import sys
from typing import Any, Tuple
from game_sdk.game.chat_agent import ChatAgent
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus
from twitter_plugin_gamesdk.game_twitter_plugin import GameTwitterPlugin
import requests
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

# Get the system prompt - absolute import approach
def get_prompt(partner_name=None):
    """Get the system prompt directly from server config."""
    # Add the server directory to sys.path to make absolute imports work
    server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    
    # Now use an absolute import
    from config import get_system_prompt
    return get_system_prompt(partner_name)

# ACTION SPACE

# Initialize Twitter Plugin - but only when needed
def initialize_twitter_plugin():
    """Initialize the Twitter plugin with the stored token."""
    access_token = os.getenv("GAME_TWITTER_ACCESS_TOKEN")
    if not access_token:
        # In production, you would handle this differently
        # For now, we'll return None
        return None
    
    # Clean any potential whitespace from the token
    access_token = access_token.strip()
    
    twitter_options = {
        "id": "twitter_agent",
        "name": "Twitter Bot",
        "description": "A Twitter bot that posts updates",
        "credentials": {
            "gameTwitterAccessToken": access_token
        }
    }
    return GameTwitterPlugin(twitter_options)

# Create a placeholder that will be initialized when needed
twitter_plugin = None

# Twitter posting function with lazy initialization
def post_to_twitter(tweet_content: str) -> Tuple[FunctionResultStatus, str, dict[str, Any]]:
    """Post a tweet to Twitter"""
    global twitter_plugin
    
    # Initialize plugin if needed
    if twitter_plugin is None:
        twitter_plugin = initialize_twitter_plugin()
        if twitter_plugin is None:
            return FunctionResultStatus.FAILED, "Twitter is not authenticated. Please set up authentication first.", {}
    
    try:
        # First try with the plugin
        post_tweet_fn = twitter_plugin.get_function('post_tweet')
        cleaned_tweet = tweet_content.strip()
        result = post_tweet_fn(tweet=cleaned_tweet, media_ids=[])
        
        # Extract the tweet ID from the result - IMPROVED EXTRACTION
        tweet_id = None
        tweet_text = None
        
        # Print the raw response for debugging
        print(f"Twitter API response: {result}")
        
        if isinstance(result, dict):
            # Extract data directly from the response structure
            # First try data.id format
            if 'data' in result and isinstance(result['data'], dict):
                data = result['data']
                if 'id' in data:
                    tweet_id = data['id']
                if 'text' in data:
                    tweet_text = data['text']
            # Also check for direct id field
            elif 'id' in result:
                tweet_id = result['id']
        
        # Include the tweet ID directly in the success message for easier parsing
        if tweet_id:
            success_message = f"Tweet posted successfully: '{cleaned_tweet}' with ID: {tweet_id}"
            return FunctionResultStatus.DONE, success_message, {
                "tweet_content": cleaned_tweet,
                "tweet_id": tweet_id,
                "tweet_text": tweet_text
            }
        else:
            success_message = f"Tweet posted successfully: '{cleaned_tweet}'"
            return FunctionResultStatus.DONE, success_message, {"tweet_content": cleaned_tweet}
            
    except Exception as plugin_error:
        try:
            # If plugin fails, try direct approach for debugging
            print(f"Plugin error: {str(plugin_error)}")
            print("Attempting direct request approach...")
            
            base_url = "https://twitter.game.virtuals.io/tweets"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": os.getenv("GAME_TWITTER_ACCESS_TOKEN", "").strip()
            }
            
            payload = {"content": tweet_content.strip()}
            response = requests.post(f"{base_url}/post", headers=headers, json=payload)
            
            if response.status_code == 200 or response.status_code == 201:
                # Try to parse the response to get the tweet ID
                response_data = response.json()
                tweet_id = None
                
                # Extract tweet ID from different possible response formats
                if isinstance(response_data, dict):
                    if 'data' in response_data and isinstance(response_data['data'], dict):
                        data = response_data['data']
                        if 'id' in data:
                            tweet_id = data['id']
                    elif 'id' in response_data:
                        tweet_id = response_data['id']
                
                if tweet_id:
                    return FunctionResultStatus.DONE, f"Tweet posted successfully via direct request with ID: {tweet_id}", {
                        "tweet_content": tweet_content.strip(),
                        "tweet_id": tweet_id
                    }
                else:
                    return FunctionResultStatus.DONE, f"Tweet posted successfully via direct request", {
                        "tweet_content": tweet_content.strip()
                    }
            else:
                return FunctionResultStatus.FAILED, f"Direct request failed: {response.status_code} - {response.text}", {}
        except Exception as direct_error:
            return FunctionResultStatus.FAILED, f"Both plugin and direct request failed. Last error: {str(direct_error)}", {}

# Add this function after the post_to_twitter function

def post_twitter_thread(thread_content: list) -> Tuple[FunctionResultStatus, str, dict[str, Any]]:
    """
    Post a series of tweets as a thread.
    
    Args:
        thread_content (list): List of strings, each representing one tweet in the thread
    """
    global twitter_plugin
    
    # Initialize plugin if needed
    if twitter_plugin is None:
        twitter_plugin = initialize_twitter_plugin()
        if twitter_plugin is None:
            return FunctionResultStatus.FAILED, "Twitter is not authenticated. Please set up authentication first.", {}
    
    if not thread_content or not isinstance(thread_content, list):
        return FunctionResultStatus.FAILED, "Thread content must be a non-empty list of tweets", {}
    
    try:
        previous_tweet_id = None
        result_ids = []
        
        # Post the first tweet
        first_tweet = thread_content[0].strip()
        if not first_tweet.startswith("1/"):
            first_tweet = f"1/{len(thread_content)}: {first_tweet}"
        
        print(f"Posting first tweet: {first_tweet}")
        post_tweet_fn = twitter_plugin.get_function('post_tweet')
        first_result = post_tweet_fn(tweet=first_tweet, media_ids=[])
        
        # Extract the tweet ID from the response
        first_tweet_id = None
        
        # Try to find the tweet ID in various response formats
        if isinstance(first_result, dict):
            if "id" in first_result:
                first_tweet_id = first_result["id"]
            elif "data" in first_result and isinstance(first_result["data"], dict) and "id" in first_result["data"]:
                first_tweet_id = first_result["data"]["id"]
        
        if not first_tweet_id:
            print(f"Warning: Could not extract tweet ID from response: {first_result}")
            # Try a fallback approach - use a direct API request
            try:
                base_url = "https://twitter.game.virtuals.io/tweets"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": os.getenv("GAME_TWITTER_ACCESS_TOKEN", "").strip()
                }
                
                payload = {"content": first_tweet}
                response = requests.post(f"{base_url}/post", headers=headers, json=payload)
                
                if response.status_code == 200:
                    response_data = response.json()
                    if "id" in response_data:
                        first_tweet_id = response_data["id"]
                    print(f"Successfully posted first tweet via direct API: {first_tweet_id}")
                else:
                    print(f"Direct API request failed: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error in direct API request: {str(e)}")
        
        if not first_tweet_id:
            return FunctionResultStatus.FAILED, "Failed to get ID for the first tweet", {}
        
        result_ids.append(first_tweet_id)
        previous_tweet_id = first_tweet_id
        
        # Wait longer after the first tweet
        print("Waiting 10 seconds before posting next tweet...")
        time.sleep(10)
        
        # Now post the rest of the thread as replies
        for i in range(1, len(thread_content)):
            # Format the tweet content
            tweet = thread_content[i].strip()
            if not any(tweet.startswith(f"{i+1}/") for j in range(10)):
                tweet = f"{i+1}/{len(thread_content)}: {tweet}"
            
            print(f"Posting reply #{i+1} to tweet {previous_tweet_id}: {tweet}")
            
            try:
                # Post as a reply to the previous tweet
                reply_tweet_fn = twitter_plugin.get_function('reply_tweet')
                reply_result = reply_tweet_fn(tweet_id=int(previous_tweet_id), reply=tweet, media_ids=None)
                
                # Try to extract the ID of this reply
                reply_id = None
                if isinstance(reply_result, dict):
                    if "id" in reply_result:
                        reply_id = reply_result["id"]
                    elif "data" in reply_result and isinstance(reply_result["data"], dict) and "id" in reply_result["data"]:
                        reply_id = reply_result["data"]["id"]
                
                if not reply_id:
                    # Fallback: Try to get the ID via direct API call
                    try:
                        base_url = "https://twitter.game.virtuals.io/tweets"
                        headers = {
                            "Content-Type": "application/json",
                            "x-api-key": os.getenv("GAME_TWITTER_ACCESS_TOKEN", "").strip()
                        }
                        
                        payload = {"content": tweet}
                        response = requests.post(f"{base_url}/reply/{previous_tweet_id}", headers=headers, json=payload)
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            if "id" in response_data:
                                reply_id = response_data["id"]
                            print(f"Successfully posted reply via direct API: {reply_id}")
                        else:
                            print(f"Direct API reply request failed: {response.status_code} - {response.text}")
                    except Exception as e:
                        print(f"Error in direct API reply request: {str(e)}")
                
                if reply_id:
                    result_ids.append(reply_id)
                    previous_tweet_id = reply_id
                else:
                    print(f"Warning: Could not get ID for reply #{i+1}, thread may be broken")
                
            except Exception as reply_error:
                print(f"Error posting reply #{i+1}: {str(reply_error)}")
                # Continue with the thread even if one reply fails
            
            # Significantly increased delay between tweets to avoid rate limiting
            wait_time = 5  # 15 seconds between tweets
            print(f"Waiting {wait_time} seconds before posting next tweet...")
            time.sleep(wait_time)
        
        # Include the first tweet ID in the success message to make it easier to parse
        if first_tweet_id:
            success_message = f"Successfully posted a thread with {len(result_ids)} tweets. The first tweet's ID is {first_tweet_id}"
        else:
            success_message = f"Successfully posted a thread with {len(result_ids)} tweets"
        
        return FunctionResultStatus.DONE, success_message, {
            "tweet_ids": result_ids,
            "first_tweet_id": first_tweet_id  # Explicitly include the first tweet ID in the return data
        }
    
    except Exception as e:
        print(f"Thread posting error: {str(e)}")
        return FunctionResultStatus.FAILED, f"Failed to post Twitter thread: {str(e)}", {}

# Debugging function to understand FunctionCallResponse structure
def debug_function_call(function_call):
    """Print the structure of a function call object for debugging"""
    # print(f"Function call type: {type(function_call)}")
    # print(f"Function call dir: {dir(function_call)}")
    print(f"Function name: {function_call.fn_name}")
    
    # Try different ways to access args
    if hasattr(function_call, 'args'):
        print(f"Args attribute: {function_call.args}")
    if hasattr(function_call, 'get_args') and callable(getattr(function_call, 'get_args')):
        print(f"get_args() method: {function_call.get_args()}")

action_space = [
    Function(
        fn_name="post_to_twitter",
        fn_description="Post a tweet to Twitter",
        args=[Argument(name="tweet_content", description="The content of the tweet to post")],
        executable=post_to_twitter,
    ),
    Function(
        fn_name="post_twitter_thread",
        fn_description="Post a series of tweets as a thread on Twitter",
        args=[Argument(name="thread_content", description="List of strings, each representing one tweet in the thread")],
        executable=post_twitter_thread,
    ),
]

# Replace the strict API key check with a function
def get_api_key():
    """Get the API key, returning None if not available."""
    return os.getenv("GAME_API_KEY")

# Create a variable to hold the key without raising an error
api_key = get_api_key()

# Modify the run_interactive function to use our get_prompt helper
def run_interactive():
    """Run the agent in interactive console mode"""
    # Check API key here when needed
    api_key = get_api_key()
    if not api_key:
        print("Error: GAME_API_KEY is not set in .env file. Cannot run interactive mode.")
        return
    
    # Try to get Twitter user info
    user_id, user_name = get_twitter_user_info()
    
    # Default to "User" if we couldn't get Twitter info
    if not user_id:
        user_id = "User"
    if not user_name:
        user_name = "User"
    
    # Get the prompt using our helper function
    prompt = get_prompt(user_name)
    
    agent = ChatAgent(
        prompt=prompt,
        api_key=api_key
    )
    
    chat = agent.create_chat(
        partner_id=user_id,
        partner_name=user_name,
        action_space=action_space,
    )
    
    chat_continue = True
    while chat_continue:
        user_message = input("Enter a message: ")
        
        response = chat.next(user_message)
        
        if response.function_call:
            print(f"Function call: {response.function_call.fn_name}")
        
        if response.message:
            print(f"Response: {response.message}")
        
        if response.is_finished:
            chat_continue = False
            break
    
    print("Chat ended")

# Only run the interactive mode if this script is executed directly
if __name__ == "__main__":
    run_interactive()

def get_twitter_user_info():
    """Get information about the authenticated Twitter user."""
    global twitter_plugin
    
    # Initialize plugin if needed
    if twitter_plugin is None:
        twitter_plugin = initialize_twitter_plugin()
        if twitter_plugin is None:
            return None, None
    
    try:
        # Try to get authenticated user info
        get_user_fn = twitter_plugin.get_function('get_authenticated_user')
        user_info = get_user_fn()
        
        if user_info and 'data' in user_info:
            user_data = user_info['data']
            username = user_data.get('username')
            user_id = user_data.get('id')
            name = user_data.get('name', username)
            
            return user_id, name or username
        
        return None, None
    except Exception as e:
        print(f"Error getting Twitter user info: {str(e)}")
        return None, None