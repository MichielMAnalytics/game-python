import requests
from typing import List


def create_agent(
        base_url: str,
        api_key: str,
        name: str,
        description: str,
        goal: str) -> str:
    """
    API call to create an agent instance (worker or agent with task generator)
    """

    payload = {
        "data": {
            "name": name,
            "goal": goal,
            "description": description
        }
    }

    response = requests.post(
        f"{base_url}/agents",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=payload
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    agent_id = response_json["data"]["id"]

    return agent_id


def create_workers(base_url: str,
                   api_key: str,
                   workers: List) -> str:
    """
    API call to create workers and worker description for the task generator (agent)
    """

    payload = {
        "data": {
            "locations": [
                {"id": w.id, "name": w.id, "description": w.worker_description}
                for w in workers
            ]
        }
    }

    response = requests.post(
        f"{base_url}/maps",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=payload
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    map_id = response_json["data"]["id"]

    return map_id

def set_worker_task(base_url: str, api_key: str, agent_id: str, task: str):
    """
    API call to set worker task (for standalone worker)
    """

    payload = {
        "data": {
            "task": task
        }
    }

    response = requests.post(
        f"{base_url}/agents/{agent_id}/tasks",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=payload
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    return response_json["data"]

def get_worker_action(base_url: str, api_key: str, agent_id: str, submission_id: str, data: dict):
    """
    API call to get worker actions (for standalone worker)
    """

    response = requests.post(
        f"{base_url}/agents/{agent_id}/tasks/{submission_id}/next",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=data
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    return response_json["data"]

def get_agent_action(base_url: str, api_key: str, agent_id: str, data: dict):
    """
    API call to get agent actions/next step (for agent)
    """

    response = requests.post(
        f"{base_url}/agents/{agent_id}/actions",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key
        },
        json=data
    )

    response_json = response.json()
    if response.status_code != 200:
        raise ValueError(f"Failed to post data: {response_json}")

    return response_json["data"]
