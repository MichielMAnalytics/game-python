import os
from game_sdk.hosted_game.agent import Agent
from game_sdk.plugins.allora.allora import AlloraNetworkClient

# Initialize the agent
agent = Agent(
    api_key=os.getenv("VIRTUALS_API_KEY"),
    goal="Help users get inferences from Allora Network",
    description=(
        "You are an AI agent specialized in Allora Network."
        "You are able to get inferences from Allora Network and provide users insights into Allora topic inferences."
        "You are also able to get price predictions from Allora Network and provide users insights into future price of different crypto assets."
    ),
    world_info=(
        "Allora Network empowers users and AI agents with real-time, advanced, "
        "self-improving AI inferences, delivering high-performance insights without "
        "introducing any additional complexity. Among multiple use-cases, Allora offers "
        "price, volatility or volume predictions for a broad variety of assets and timeframes"
    )
)

# Add Allora functions to the agent
allora_network_client = AlloraNetworkClient()

agent.add_custom_function(
    allora_network_client.get_function("get_all_topics"),
    allora_network_client.get_function("get_inference_by_topic_id"),
    allora_network_client.get_function("get_price_prediction")
)

# Test different queries
queries = [
    "What's the price of BTC in 5min?",
    "What's the price of ETH in 25min?",
    "What's the price of SOL in 24h?",
    "What's the price of SHIB in 25min?",
    "What are the active topics on Allora?",
    "What is are the topic ids for predicting future BTC prices?",
]

for query in queries:
    response = agent.react(
        session_id="test_session_1",
        platform="telegram",
        event=query,
        task="Help users get inferences by leveraging Allora Network."
    )

    print(f"Query: {query}")
    print(f"Response: {response}\n")