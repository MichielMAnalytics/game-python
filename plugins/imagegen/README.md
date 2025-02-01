# Image Generator Plugin for GAME SDK

TogetherAI has a free flux schnell image generator, which we'll use here because it's free.
Can change endpoints, params, etc to suit your needs.

## Features
- Generate images based on prompt
- Receive images as temporary URL or B64 objects

## Avilable Functions

1. `generate_image(prompt: str)` - Generates image based on prompt

## Setup and configuration
1. Set the following environment variables:
  - `TOGETHER_API_KEY`: Create an API key by [creating an account](https://together.ai).

2. Import and initialize the plugin to use in your worker:
```python
from plugins.imagegen.imagegen_plugin import ImageGenPlugin

imagegen_plugin = AlloraPlugin(
  api_key=os.environ.get("TOGETHER_API_KEY", "UP-17f415babba7482cb4b446a1"),
)
```

**Basic worker example:**
```python
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

price_inference_worker = Worker(
    api_key=os.environ.get("GAME_API_KEY"),
    description="Worker specialized in using Allora Network to get price inferences",
    get_state_fn=get_state_fn,
    action_space=[
        allora_network_plugin.get_function("get_price_inference"),
    ],
)

price_inference_worker.run("Query the price of BTC in 5min")
```

## Running examples

To run the examples showcased in the plugin's directory, follow these steps:

1. Install dependencies:
```
poetry install
```

2. Set up environment variables:
```
export GAME_API_KEY="your-game-api-key"
export TOGETHER_API_KEY="your-together-api-key" # Default key: UP-17f415babba7482cb4b446a1
```

3. Run example scripts:

Example worker:
```
poetry run python ./examples/example-worker.py  
```

Example agent:
```
poetry run python ./examples/example-agent.py
```