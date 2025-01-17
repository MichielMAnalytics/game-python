import json
from typing import Tuple
from game_sdk.game.custom_types import Function, FunctionResultStatus
from allora_sdk.v2.api_client import AlloraAPIClient


class GetAllTopics(Function):
    def __init__(self, client: AlloraAPIClient):
        super().__init__(
            fn_name="get_all_topics",
            fn_description="Get all the topics available on Allora Network.",
            args=[],
            hint="This function is used to get all the topics available on Allora Network.",
            executable=self.get_all_topics,
        )
        self.client = client

    async def get_all_topics(self, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
        """Get all topics available on Allora Network.

        Returns:
            Tuple[FunctionResultStatus, str, dict]: The status of the function, the feedback message, and the dictionary with the topics retrieved.
        """
        try:
            topics = await self.client.get_all_topics()
            topics_json = json.dumps(topics, indent=4)
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved all topics. The topics available on Allora Network are:\n\n{topics_json}",
                {
                    "topics": topics,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching Allora Network topics: {str(e)}",
                {},
            )
