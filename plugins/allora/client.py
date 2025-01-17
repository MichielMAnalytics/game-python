from typing import Dict, List, Optional
from game_sdk.hosted_game.agent import Function
from allora_sdk.v2.api_client import AlloraAPIClient, ChainSlug

from plugins.allora.functions.get_all_topics import GetAllTopics
from plugins.allora.functions.get_inference_by_topic_id import GetInferenceByTopicId
from plugins.allora.functions.get_price_prediction import GetPricePrediction

DEFAULT_ALLORA_BASE_API_URL = "https://api.allora.network/v2"
DEFAULT_ALLORA_API_KEY = "UP-17f415babba7482cb4b446a1"

class AlloraNetworkClient:
    """
    Allora Network client.

    Example:
        client = AlloraNetworkClient(
            chain_slug=AlloraChainSlug.TESTNET,
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
            "get_all_topics": GetAllTopics(self.allora_api_client),
            "get_inference_by_topic_id": GetInferenceByTopicId(self.allora_api_client),
            "get_price_prediction": GetPricePrediction(self.allora_api_client),
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