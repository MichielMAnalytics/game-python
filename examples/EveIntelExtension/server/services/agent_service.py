import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import time
import re

# Import directly from the chat_agent in the same directory
from .chat_agent import ChatAgent, action_space, debug_function_call, initialize_twitter_plugin, twitter_plugin, get_twitter_user_info, get_prompt

# Load environment variables
load_dotenv()

class AgentService:
    """Service for managing chat agent instances"""
    
    def __init__(self):
        """Initialize the agent service"""
        self.chat_instances = {}
        self.last_activity = {}
        self.api_key = os.getenv('GAME_API_KEY')
        # We'll check for the API key in process_message instead of raising an error here
    
    def _create_chat_instance(self, user_id: str):
        """Create a new chat instance for a user"""
        # Check if we have API key 
        if not self.api_key:
            raise ValueError("GAME_API_KEY is not set. Cannot create chat instance.")
        
        # First try to get Twitter user info from storage
        twitter_id, twitter_name = self.get_stored_twitter_user_info()
        
        # If not found in storage but Twitter is authenticated, try to get it directly
        if (not twitter_id or not twitter_name) and self.is_twitter_authenticated():
            # No need to re-import since we're now using relative imports
            twitter_id, twitter_name = get_twitter_user_info()
        
        # Use Twitter info if available, otherwise use provided user_id
        partner_id = twitter_id if twitter_id else user_id
        partner_name = twitter_name if twitter_name else f"User_{user_id[:8]}"
               
        # Get a personalized system prompt using the helper from chat_agent
        personalized_system_prompt = get_prompt(partner_name)
        
        # Now create the agent with the personalized prompt
        agent = ChatAgent(
            prompt=personalized_system_prompt,
            api_key=self.api_key
        )
        
        chat = agent.create_chat(
            partner_id=partner_id,
            partner_name=partner_name,
            action_space=action_space,
        )
        
        self.chat_instances[user_id] = chat
        self.last_activity[user_id] = time.time()
        
        return chat
    
    def _get_or_create_chat(self, user_id: str):
        """Get an existing chat instance or create a new one"""
        if user_id not in self.chat_instances:
            return self._create_chat_instance(user_id)
        
        # Update last activity time
        self.last_activity[user_id] = time.time()
        return self.chat_instances[user_id]
    
    def is_twitter_authenticated(self):
        """Check if Twitter authentication is set up"""
        # Check if the token exists in environment variables
        token = os.getenv('GAME_TWITTER_ACCESS_TOKEN')
        if token:
            return True
        
        # Check if we have stored tokens
        token_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.tokens')
        if os.path.exists(token_dir) and os.listdir(token_dir):
            # We have tokens, so authentication has happened
            return True
        
        return False
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Process a message through the chat agent"""
        # First check if we have a GAME_API_KEY
        if not self.api_key:
            return {
                "response": "The GAME API key is not set up. You need to provide your API key during authentication.",
                "functionCall": None,
                "isFinished": False,
                "authentication_required": True
            }
        
        # Then check if Twitter is authenticated
        if not self.is_twitter_authenticated():
            return {
                "response": "Twitter authentication is not set up. Please set up authentication first.",
                "functionCall": None,
                "isFinished": False,
                "authentication_required": True
            }
        
        # Initialize Twitter in chat_agent if not already done
        if twitter_plugin is None:
            # This will update the global twitter_plugin variable
            initialize_twitter_plugin()
        
        chat = self._get_or_create_chat(user_id)
        
        # Get response from agent
        response = chat.next(message)
        
        # Format the response
        result = {
            "response": response.message if response.message else "",
            "functionCall": None,
            "isFinished": response.is_finished
        }
        
        # Add function call details if present
        if response.function_call:
            # Debug the function call object
            try:
                debug_function_call(response.function_call)
            except Exception as debug_error:
                print(f"Debug error: {debug_error}")
            
            # Create a structure that will work with our frontend
            fn_details = {
                "name": response.function_call.fn_name,
                "args": {}
            }
            
            # Extract function arguments in a more robust way
            try:
                # Try to get args attribute
                if hasattr(response.function_call, 'args'):
                    fn_details["args"] = response.function_call.args
                # Try fn_args if it exists
                elif hasattr(response.function_call, 'fn_args'):
                    fn_details["args"] = response.function_call.fn_args
                # Try to get via fields or dict method
                elif hasattr(response.function_call, 'model_dump'):
                    dump = response.function_call.model_dump()
                    if 'fn_args' in dump:
                        fn_details["args"] = dump['fn_args']
                # Last resort - try to parse from response message
                else:
                    # Extract args from message if possible
                    if result["response"] and "tweet" in response.function_call.fn_name.lower():
                        match = re.search(r"Tweet posted successfully: '(.+?)'", result["response"])
                        if match:
                            fn_details["args"] = {"tweet_content": match.group(1)}
            except Exception as args_error:
                print(f"Error extracting args: {args_error}")
            
            result["functionCall"] = fn_details
        
        return result
    
    def reset_chat(self, user_id: str) -> bool:
        """Reset a user's chat session"""
        if user_id in self.chat_instances:
            del self.chat_instances[user_id]
            if user_id in self.last_activity:
                del self.last_activity[user_id]
            return True
        return False
    
    def cleanup_inactive_sessions(self, max_idle_time: int = 3600):
        """Clean up inactive chat sessions (default: 1 hour)"""
        current_time = time.time()
        users_to_remove = []
        
        for user_id, last_active in self.last_activity.items():
            if current_time - last_active > max_idle_time:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            self.reset_chat(user_id)
        
        return len(users_to_remove)
    
    def get_stored_twitter_user_info(self):
        """Get stored Twitter user info from token file."""
        token_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', '.tokens')
        if os.path.exists(token_dir):
            # Look for user info files
            user_files = [f for f in os.listdir(token_dir) if f.endswith('.user')]
            if user_files:
                # Use the most recent user info
                latest_user_file = user_files[-1]
                with open(os.path.join(token_dir, latest_user_file), 'r') as f:
                    user_info = f.read().strip()
                    
                    # Parse user_info in format "id:name"
                    if ':' in user_info:
                        parts = user_info.split(':', 1)
                        return parts[0], parts[1]
        
        return None, None 