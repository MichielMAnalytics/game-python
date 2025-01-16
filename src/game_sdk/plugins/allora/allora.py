from typing import Dict, List, Optional
from game_sdk.hosted_game.agent import Function, FunctionConfig, FunctionArgument
from allora_sdk.v2.api_client import AlloraAPIClient, ChainSlug, SignatureFormat

DEFAULT_ALLORA_BASE_API_URL = "https://api.allora.network/v2"
DEFAULT_ALLORA_API_KEY = "UP-17f415babba7482cb4b446a1"


# TODO: Update example
class AlloraNetworkClient:
    """
    Allora Network client.

    Example:
        client = AlloraClient(
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
        self.allora_client = AlloraAPIClient(
            chain_slug=chain_slug,
            api_key=api_key,
            base_api_url=base_api_url,
        )

        # Available client functions
        self._functions: Dict[str, Function] = {
            "get_all_topics": self._create_get_all_topics(),
            "get_inference_by_topic_id": self._create_get_inference_by_topic_id(),
            "get_price_prediction": self._create_get_price_prediction(),
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

    def _create_get_all_topics(self) -> Function:
        get_all_topics = Function(
            fn_name="get_all_topics",
            fn_description="Fetches all the topics available on Allora Network.",
            args=[],
            hint="When requested to provide an inference for a topic, get_all_topics needs to be executed first, to get more context on the topic id needed to queried for getting the actual inference.",
            config=FunctionConfig(
                method="get",
                url=self.allora_client.get_request_url(
                    f"allora/{self.allora_client.chain_id}/topics"
                ),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.allora_client.api_key,
                },
                success_feedback=(
                    "The topics available on Allora Network are:\n\n"
                    "{{#response.data.topics}}\n"
                    "Topic ID: {{topic_id}}\n"
                    "Topic Name: {{topic_name}}\n"
                    "Topic Description: {{description}}\n"
                    "Topic is Active: {{is_active}}\n"
                    "Topic epoch length: {{epoch_length}}\n"
                    "Topic ground truth lag: {{ground_truth_lag}}\n"
                    "Topic loss method: {{loss_method}}\n"
                    "Topic updated at: {{updated_at}}\n"
                    "----------------------------------------\n"
                    "{{/response.data.topics}}\n"
                ),
                error_feedback="An error occurred while fetching Allora Network topics. Status code: {{response.status_code}}. Please try again later.",
            ),
        )

        return get_all_topics

    def _create_get_inference_by_topic_id(self) -> Function:
        get_inference_by_topic_id = Function(
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
            config=FunctionConfig(
                method="get",
                url=self.allora_client.get_request_url(
                    f"allora/{self.allora_client.chain_id}/consumer/{SignatureFormat.ETHEREUM_SEPOLIA}?allora_topic_id={{topic_id}}&inference_value_type=uint256"
                ),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.allora_client.api_key,
                },
                success_feedback=(
                    "The inference for topic with id {{topic_id}} is:\n"
                    "{{response.data.inference_data.network_inference_normalized}}"
                ),
                error_feedback="An error occurred while fetching inference from Allora Network. Status code: {{response.status_code}}. Please try again later.",
            ),
        )

        return get_inference_by_topic_id

    def _create_get_price_prediction(self) -> Function:
        get_price_prediction = Function(
            fn_name="get_price_prediction",
            fn_description="Fetches from Allora Network the future price prediction for a given crypto asset and timeframe.",
            args=[
                FunctionArgument(
                    name="asset",
                    description="The asset symbol to get the price prediction for. Example: BTC, ETH, SOL, SHIB, etc.",
                    type="string",
                ),
                FunctionArgument(
                    name="timeframe",
                    description="The timeframe to get the price prediction for. Example: 5m, 8h, 24h, etc.",
                    type="string",
                )
            ],
            hint="",
            config=FunctionConfig(
                method="get",
                url=self.allora_client.get_request_url(
                    f"allora/consumer/price/{SignatureFormat.ETHEREUM_SEPOLIA}/{{asset}}/{{timeframe}}"
                ),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.allora_client.api_key,
                },
                success_feedback=(
                    "The price prediction for {{asset}} in {{timeframe}} is:\n"
                    "{{response.data.inference_data.network_inference_normalized}}"
                ),
                error_feedback="An error occurred while fetching price prediction from Allora Network. Status code: {{response.status_code}}. Please try again later.",
            ),
        )

        return get_price_prediction
