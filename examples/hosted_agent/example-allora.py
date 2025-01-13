import os
from game_sdk.hosted_game.agent import Agent
from game_sdk.hosted_game.functions.allora import AlloraClient

# Initialize the agent
agent = Agent(
    api_key=os.getenv("VIRTUALS_API_KEY"),
    goal="Help users get inferences from Allora Network",
    description=(
        "You are an AI agent specialized in Allora Network."
        "You are able to get inferences from Allora Network and provide users insights into Allora topic inferences."
    ),
    world_info=(
        "Allora Network empowers users and AI agents with real-time, advanced, "
        "self-improving AI inferences, delivering high-performance insights without "
        "introducing any additional complexity. Among multiple use-cases, Allora offers "
        "price, volatility or volume predictions for a broad variety of assets and timeframes"
    )
)

# Add Allora functions to the agent
allora_client = AlloraClient()

agent.add_custom_function(
    allora_client.get_function("get_all_allora_topics"),
    allora_client.get_function("get_allora_topic_inference")
)

# Test different queries
queries = [
    "What's the price of BTC in 5min?",
    "What's the price of ETH in 25min?",
    "What's the price of SOL in 24h?",
    "What's the price of SHIB in 25min?",
    "What other assets and timeframes are available on Allora?"
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