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
            return payload
        else:
            print(f"Payload: {payload}")
            return payload
        print("-----------------------------------")
    except Exception as e:
        print(f"Error in message handler: {e}")

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
    agent_goal="Monitor SOLUSDT market data from DPSN and process real-time updates.",
    agent_description=(
        "You are an AI agent specialized in DPSN market data processing"
        "You can subscribe dpsn topic"
        "after 5 minutes unsubscribe the topic"
        "next 5 minutes close the connection"
        "\n\nAvailable topics:"
        "\n- 0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ohlc"
    ),
    get_agent_state_fn=get_agent_state_fn,
    workers=[
        # connection_worker,
        subscription_worker
    ]
)

# Compile and run the agent
agent.compile()
agent.run() 