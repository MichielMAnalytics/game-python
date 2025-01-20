import asyncio
import json
from typing import Dict, List, Optional, Tuple
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus
from allora_sdk.v2.api_client import (
    AlloraAPIClient,
    ChainSlug,
    PricePredictionToken,
    PricePredictionTimeframe,
)

DEFAULT_ALLORA_BASE_API_URL = "https://api.allora.network/v2"
DEFAULT_ALLORA_API_KEY = "UP-17f415babba7482cb4b446a1"


class AlloraPlugin:
    """
    Allora Network pluging.

    Example:
        from allora_sdk.v2.api_client import ChainSlug

        client = AlloraPlugin(
            chain_slug=os.environ.get("ALLORA_CHAIN_SLUG"),
            api_key=os.environ.get("ALLORA_API_KEY"),
            base_api_url=os.environ.get("ALLORA_API_URL"),
        )

        all_topics_fn = client.get_function("get_all_topics")
        get_inference_by_topic_id_fn = client.get_function("get_inference_by_topic_id")
        get_price_prediction_fn = client.get_function("get_price_prediction")
    """

    def __init__(
        self,
        chain_slug: Optional[ChainSlug] = ChainSlug.TESTNET,
        api_key: Optional[str] = DEFAULT_ALLORA_API_KEY,
        base_api_url: Optional[str] = DEFAULT_ALLORA_BASE_API_URL,
    ):
        """
        Initialize the Allora client.

        Args:
            chain_slug (str): The chain slug to use for the Allora client
            api_key (str): Allora API key
            base_api_url (str): The base API URL to use for the Allora client
        """
        self.allora_api_client = AlloraAPIClient(
            chain_slug=chain_slug,
            api_key=api_key,
            base_api_url=base_api_url,
        )

        # Available client functions
        self._functions: Dict[str, Function] = {
            "get_all_topics": Function(
                fn_name="get_all_topics",
                fn_description="Get all the topics available on Allora Network.",
                args=[],
                hint="This function is used to get all the topics available on Allora Network.",
                executable=self.get_all_topics,
            ),
            "get_inference_by_topic_id": Function(
                fn_name="get_inference_by_topic_id",
                fn_description="Fetches an inference from Allora Network given a topic id.",
                args=[
                    Argument(
                        name="topic_id",
                        description="The topic_id corresponds to the unique id of one of an active topic on Allora Network",
                        type="number",
                    )
                ],
                hint="This function is used to get the inference by topic id. For obtaining the topic id associated to a certain inference/price prediction, use the get_all_topics function.",
                executable=self.get_inference_by_topic_id,
            ),
            "get_price_prediction": Function(
                fn_name="get_price_prediction",
                fn_description="Fetches from Allora Network the future price prediction for a given crypto asset and timeframe.",
                args=[
                    Argument(
                        name="asset",
                        description="The crypto asset symbol to get the price prediction for. Example: BTC, ETH, SOL, SHIB, etc.",
                        type="string",
                    ),
                    Argument(
                        name="timeframe",
                        description="The timeframe to get the price prediction for. Example: 5m, 8h, 24h, etc.",
                        type="string",
                    ),
                ],
                hint="This function is used to get the price prediction for a given crypto asset and timeframe.",
                executable=self.get_price_prediction,
            ),
        }

    @property
    def available_functions(self) -> List[str]:
        """Get list of available function names."""
        return list(self._functions.keys())

    def get_function(self, fn_name: str) -> Function:
        """
        Get a specific function by name.

        Args:
            fn_name: Name of the function to retrieve

        Raises:
            ValueError: If function name is not found

        Returns:
            Function object
        """
        if fn_name not in self._functions:
            raise ValueError(
                f"Function '{fn_name}' not found. Available functions: {', '.join(self.available_functions)}"
            )
        return self._functions[fn_name]

    def get_all_topics(self, **kwargs) -> Tuple[FunctionResultStatus, str, dict]:
        """Get all topics available on Allora Network.

        Returns:
            Tuple[FunctionResultStatus, str, dict]: The status of the function, the feedback message, and the dictionary with the topics retrieved.
        """
        try:
            topics = asyncio.run(self.allora_api_client.get_all_topics())
            topics_dict = [topic.__dict__ for topic in topics]
            topics_json = json.dumps(topics_dict, indent=4)
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved all topics from Allora Network. The topics available on Allora Network are:\n\n{topics_json}",
                {
                    "topics": topics_json,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching Allora Network topics: {str(e)}",
                {},
            )

    def get_inference_by_topic_id(
        self, topic_id: int, **kwargs
    ) -> Tuple[FunctionResultStatus, str, dict]:
        """Get inference by topic id.

        Returns:
            Tuple[FunctionResultStatus, str, dict]: The status of the function, the feedback message, and the dictionary with the inference details.
        """
        try:
            inference_res = asyncio.run(
                self.allora_api_client.get_inference_by_topic_id(topic_id)
            )
            normalized_inference = (
                inference_res.inference_data.network_inference_normalized
            )
            return (
                FunctionResultStatus.DONE,
                f"Successfully retrieved inference for topic with id {topic_id}. The inference is: {normalized_inference}",
                {
                    "topic_id": topic_id,
                    "inference": normalized_inference,
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

    def get_price_prediction(
        self, asset: PricePredictionToken, timeframe: PricePredictionTimeframe, **kwargs
    ) -> Tuple[FunctionResultStatus, str, dict]:
        """Get price prediction of a given asset for a given timeframe.

        Returns:
            Tuple[FunctionResultStatus, str, dict]: The status of the function, the feedback message, and the dictionary with the price prediction details.
        """
        asset = asset.upper()
        timeframe = timeframe.lower()

        # Get asset enum key by value
        asset_enum_key = [
            key
            for key, value in PricePredictionToken.__members__.items()
            if value == asset
        ]
        if len(asset_enum_key) == 0:
            return (
                FunctionResultStatus.FAILED,
                f"Unsupported asset: {asset}. Supported assets are: {', '.join([token.value for token in PricePredictionToken])}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )
        else:
            asset_enum_key = asset_enum_key[0]

        # Get timeframe enum key by value
        timeframe_enum_key = [
            key
            for key, value in PricePredictionTimeframe.__members__.items()
            if value == timeframe
        ]
        if len(timeframe_enum_key) == 0:
            return (
                FunctionResultStatus.FAILED,
                f"Unsupported timeframe: {timeframe}. Supported timeframes are: {', '.join([timeframe.value for timeframe in PricePredictionTimeframe])}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )
        else:
            timeframe_enum_key = timeframe_enum_key[0]

        try:
            price_prediction = asyncio.run(
                self.allora_api_client.get_price_prediction(
                    PricePredictionToken[asset_enum_key],
                    PricePredictionTimeframe[timeframe_enum_key],
                )
            )
            normalized_price_prediction = (
                price_prediction.inference_data.network_inference_normalized
            )
            return (
                FunctionResultStatus.DONE,
                f"The price prediction for {asset} in {timeframe} is: {normalized_price_prediction}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                    "price_prediction": normalized_price_prediction,
                },
            )
        except Exception as e:
            print(
                f"An error occurred while fetching price prediction from Allora Network: {str(e)}"
            )
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching price prediction from Allora Network: {str(e)}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )
