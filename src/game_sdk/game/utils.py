import requests
from typing import List, Dict, Any


def get_access_token(api_key: str) -> str:
    """
    Retrieves an access token from the Virtuals.io API.

    Args:
        api_key (str): The API key for authentication.

    Returns:
        str: The access token for subsequent API calls.

    Raises:
        ValueError: If the API call fails or returns a non-200 status code.

    Note:
        This token is required for all authenticated API calls to the GAME SDK.
    """
    response = requests.post(
        "https://api.virtuals.io/api/accesses/tokens",
        json={"data": {}},
        headers={"x-api-key": api_key}
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to get token: {response_json}")

    return response_json["data"]["accessToken"]


def post(base_url: str, api_key: str, endpoint: str, data: dict) -> dict:
    """
    Makes an authenticated POST request to the GAME SDK API.

    This function handles the complete request flow including:
    1. Getting an access token
    2. Formatting the request with proper headers
    3. Making the POST request
    4. Processing the response

    Args:
        base_url (str): The base URL for the API.
        api_key (str): The API key for authentication.
        endpoint (str): The API endpoint to call.
        data (dict): The data payload to send.

    Returns:
        dict: The response data from the API.

    Raises:
        ValueError: If the API call fails or returns a non-200 status code.
    """
    access_token = get_access_token(api_key)

    response = requests.post(
        f"{base_url}/prompts",
        json={
            "data":
                {
                    "method": "post",
                    "headers": {
                        "Content-Type": "application/json",
                    },
                    "route": endpoint,
                    "data": data,
                },
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    return response_json["data"]


def create_agent(base_url: str, api_key: str, agent_name: str, agent_goal: str, agent_description: str) -> dict:
    """
    Creates a new agent in the GAME SDK system.

    This function initializes a new agent with the specified parameters and registers
    it with the GAME SDK API.

    Args:
        base_url (str): The base URL for the API.
        api_key (str): The API key for authentication.
        agent_name (str): Name of the agent.
        agent_goal (str): The high-level goal or purpose of the agent.
        agent_description (str): Detailed description of the agent's capabilities.

    Returns:
        dict: The created agent's data from the API.

    Example:
        ```python
        agent_data = create_agent(
            base_url="https://game.virtuals.io",
            api_key="your_api_key",
            agent_name="TextProcessor",
            agent_goal="Process and analyze text data",
            agent_description="An agent that performs text analysis tasks"
        )
        ```
    """
    create_agent_response = post(
        base_url,
        api_key,
        endpoint="/v2/agents",
        data={
            "name": agent_name,
            "description": agent_description,
            "goal": agent_goal,
        }
    )

    return create_agent_response


def create_workers(base_url: str, api_key: str, workers: List[Dict[str, Any]]) -> dict:
    """
    Creates and registers workers with the GAME SDK system.

    This function sets up multiple workers with their respective configurations and
    registers them with the task generator.

    Args:
        base_url (str): The base URL for the API.
        api_key (str): The API key for authentication.
        workers (List[Dict[str, Any]]): List of worker configurations.
            Each worker config should contain:
            - id: Unique identifier for the worker
            - description: Worker's role and capabilities
            - instruction: Additional behavioral instructions

    Returns:
        dict: The created workers' data from the API.

    Example:
        ```python
        workers_data = create_workers(
            base_url="https://game.virtuals.io",
            api_key="your_api_key",
            workers=[
                {
                    "id": "text_processor",
                    "description": "Processes text data",
                    "instruction": "Focus on sentiment analysis"
                }
            ]
        )
        ```
    """
    res = post(
        base_url,
        api_key,
        endpoint="/v2/maps",
        data={
            "locations": [
                {"id": w["id"], "name": w["id"], "description": w["description"]}
                for w in workers
            ]
        },
    )

    return res
