import os
from game_sdk.game.worker import Worker
from game_sdk.game.custom_types import FunctionResult
from allora_game_sdk.allora_plugin import AlloraPlugin
from allora_sdk.v2.api_client import ChainSlug

def get_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """
    Update state based on the function results
    """
    init_state = {}

    if current_state is None:
        return init_state

    # Update state with the function result info
    current_state.update(function_result.info)

    return current_state


allora_network_plugin = AlloraPlugin(
  chain_slug=os.environ.get("ALLORA_CHAIN_SLUG", ChainSlug.TESTNET),
  api_key=os.environ.get("ALLORA_API_KEY", "UP-17f415babba7482cb4b446a1"),
)

# Create worker
price_prediction_worker = Worker(
    api_key=os.environ.get("GAME_API_KEY"),
    description="Worker specialized in using Allora Network to get price predictions",
    get_state_fn=get_state_fn,
    action_space=[
        allora_network_plugin.get_function("get_price_prediction"),
    ],
)

# # Run example query
queries = [
    "Fetch the price prediction for BTC in 5min",
    "Fetch the price prediction for SOL in 8h",
    "Fetch the price prediction for SHIB in 24h",
    "Fetch the price prediction for ETH in 5m",
]
for query in queries:
    print("-" * 100)
    print(f"Query: {query}")
    price_prediction_worker.run(query)
