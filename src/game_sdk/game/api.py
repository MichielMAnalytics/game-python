import requests
from typing import List


def get_access_token(api_key) -> str:
    """
    API call to get access token
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
    API call to post data
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


def create_agent(
        base_url: str,
        api_key: str,
        name: str,
        description: str,
        goal: str) -> str:
    """
    API call to create an agent instance (worker or agent with task generator)
    """

    create_agent_response = post(
        base_url,
        api_key,
        endpoint="/v2/agents",
        data={
            "name": name,
            "description": description,
            "goal": goal,
        }
    )

    return create_agent_response["id"]


def create_workers(base_url: str,
                   api_key: str,
                   workers: List) -> str:
    """
    API call to create workers and worker description for the task generator (for agent)
    """

    res = post(
        base_url,
        api_key,
        endpoint="/v2/maps",
        data={
            "locations": [
                {"id": w.id, "name": w.id, "description": w.worker_description}
                for w in workers
            ]
        },
    )

    return res["id"]


def set_worker_task(base_url: str, api_key: str, agent_id: str, task: str):
    """
    API call to set worker task (for standalone worker)
    """
    response = post(base_url=base_url,
                    api_key=api_key,
                    endpoint=f"/v2/agents/{agent_id}/tasks",
                    data={"task": task},
                )
    
    return response

def get_worker_action(base_url: str, api_key: str, agent_id: str, submission_id: str, data: dict):
    """
    API call to get worker actions (for standalone worker)
    """

    response = post(base_url=base_url,
                    api_key=api_key,
                    endpoint=f"/v2/agents/{agent_id}/tasks/{submission_id}/next",
                    data=data,
                )
    
    return response

def get_agent_action(base_url: str, api_key: str, agent_id: str, data: dict):
    """
    API call to get agent actions/next step (for agent)
    """

    response = post(base_url=base_url,
                api_key=api_key,
                endpoint=f"/v2/agents/{agent_id}/actions",
                data=data,
            )
    
    return response