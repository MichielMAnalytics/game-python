import os
import sys
from pathlib import Path
import json
from datetime import datetime

parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import FunctionResult
from dpsn_plugin_gamesdk.dpsn_plugin import plugin

# --- Add Message Handler --- 
def handle_incoming_message(message_data: dict):
    """Callback function to process messages received via the plugin."""
    try:
        topic = message_data.get('topic', 'N/A')
        payload = message_data.get('payload', '{}')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n--- Message Received ({timestamp}) ---")
        print(f"Topic: {topic}")
        # Pretty print payload if it's likely JSON/dict
        if isinstance(payload, (dict, list)):
            print(f"Payload:\n{json.dumps(payload, indent=2)}")
            return json.dumps(payload)
        else:
            print(f"Payload: {payload}")
            return str(payload)
    except Exception as e:
        print(f"Error in message handler: {e}")
        return str(e)

# Set the callback in the plugin instance *before* running the agent
plugin.set_message_callback(handle_incoming_message)
# --- End Message Handler Setup ---

def get_agent_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """Update state based on the function results"""
    init_state = {}

    if current_state is None:
        return init_state

    if function_result.info is not None:
        current_state.update(function_result.info)

    return current_state

def get_worker_state(function_result: FunctionResult, current_state: dict) -> dict:
    """Update state based on the function results"""
    init_state = {}

    if current_state is None:
        return init_state

    if function_result.info is not None:
        current_state.update(function_result.info)

    return current_state


subscription_worker = WorkerConfig(
    id="subscription_worker",
    worker_description="Worker specialized in managing DPSN topic subscriptions, unsubscriptions, message handling, and shutdown.",
    get_state_fn=get_worker_state,
    action_space=[
        plugin.get_function("subscribe"),
        plugin.get_function("unsubscribe"),
        plugin.get_function("shutdown")
    ],
)

# Initialize the agent
agent = Agent(
    api_key=os.environ.get("GAME_API_KEY"),
    name="DPSN Market Data Agent",
    agent_goal="Monitor SOLUSDT market data from DPSN, process messages for 2 minutes, then clean up.",
    agent_description=(
        "You are an AI agent specialized in DPSN market data processing. Follow these steps in order:\n\n"
        
        "1. IMMEDIATELY subscribe to this DPSN topic: 0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ohlc\n"
        
        "2. Once subscribed, inform the user that you are listening for market data updates.\n"
        
        "3. When you receive messages on this topic:\n"
        "   - Report that you received a message\n"
        
        "4. After receiving messages for 2 minutes (or at least 3 messages, whichever comes first):\n"
        "   - Unsubscribe from the topic using the unsubscribe function\n"
        "   - Report that you have unsubscribed\n"
        
        "5. After unsubscribing:\n"
        "   - Shut down the DPSN client connection using the shutdown function\n"
        "   - Report that the connection has been closed\n"
        
        "Available functions:\n"
        "- subscribe: Subscribe to a DPSN topic to receive data\n"
        "- unsubscribe: Unsubscribe from a DPSN topic\n"
        "- shutdown: Close the DPSN client connection\n\n"
        
        "Available topic:\n"
        "- 0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ohlc"
    ),
    get_agent_state_fn=get_agent_state_fn,
    workers=[
        subscription_worker
    ]
)

try:
    agent.compile()
    agent.run() 
except Exception as e:
    print(f"Error running agent:{e}")
    import traceback
    traceback.print_exc()