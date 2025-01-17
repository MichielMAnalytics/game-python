import os
from game_sdk.game.worker import Worker
from game_sdk.game.custom_types import FunctionResult
from game_sdk.plugins.allora.client import AlloraNetworkClient
from game_sdk.plugins.allora.functions import (
    GetAllTopics,
    GetInferenceByTopicId,
    GetPricePrediction,
)


def get_state_fn(function_result: FunctionResult, current_state: dict) -> dict:
    """
    Update state based on the function results
    """
    init_state = {
        "info_log": [],
    }

    if current_state is None:
        return init_state

    # Update state with the function result info
    current_state["info_log"].append(function_result.info)

    return current_state


allora_network_client = AlloraNetworkClient()

# Create worker
price_prediction_worker = Worker(
    api_key=os.environ.get("VIRTUALS_API_KEY"),
    description="A worker specialized in getting price predictions from Allora Network",
    get_state_fn=get_state_fn,
    action_space=[GetPricePrediction(allora_network_client)],
)

# Run example query
price_prediction_worker.run("What's the price of BTC in 5min?")


# Allora inferences worker
allora_inferences_worker = Worker(
    api_key=os.environ.get("VIRTUALS_API_KEY"),
    description="A worker specialized in getting inferences from Allora Network",
    get_state_fn=get_state_fn,
    action_space=[
        GetAllTopics(allora_network_client),
        GetInferenceByTopicId(allora_network_client),
    ],
)

allora_inferences_worker.run(
    "What are the active topics on Allora? Of all the active topics, which one is the most relevant for predicting future BTC prices?"
)
allora_inferences_worker.run(
    "What are the topic ids for predicting future ETH prices? Fetch the inferences from one of the topics and provide a summary of the inference (specify which topic you are using and for which asset and timeframe is the inference for)."
)
