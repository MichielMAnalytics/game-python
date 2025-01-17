from typing import Tuple
from game_sdk.game.custom_types import Function, FunctionResultStatus
from game_sdk.hosted_game.agent import FunctionArgument
from allora_sdk.v2.api_client import AlloraAPIClient


class GetInferenceByTopicId(Function):
    def __init__(self, client: AlloraAPIClient):
        super().__init__(
            fn_name="get_inference_by_topic_id",
            fn_description="Fetches an inference from Allora Network given a topic id.",
            args=[
                FunctionArgument(
                    name="topic_id",
                    description="The topic_id corresponds to the unique id of one of the active topics on Allora Network",
                    type="number",
                )
            ],
            hint="",
            executable=self.get_inference_by_topic_id,
        )
        self.client = client

    async def get_inference_by_topic_id(
        self, topic_id: int, **kwargs
    ) -> Tuple[FunctionResultStatus, str, dict]:
        """Get inference by topic id.

        Returns:
            Tuple[FunctionResultStatus, str, dict]: The status of the function, the feedback message, and the dictionary with the inference details.
        """
        try:
            inference_res = await self.client.get_inference_by_topic_id(topic_id)
            normalized_inference = (
                inference_res.inference_data.network_inference_normalized
            )
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved inference for topic with id {topic_id}. The inference is: {normalized_inference}",
                {
                    "topic_id": topic_id,
                    "complete_inference_data": inference_res,
                    "normalized_inference": normalized_inference,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching inference from Allora Network: {str(e)}",
                {
                    "topic_id": topic_id,
                },
            )
