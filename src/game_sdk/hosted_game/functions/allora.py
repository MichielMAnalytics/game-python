from enum import Enum
from typing import Dict, List, Optional
from game_sdk.hosted_game.agent import Function, FunctionConfig, FunctionArgument

DEFAULT_ALLORA_API_KEY = "UP-17f415babba7482cb4b446a1"

class AlloraChainSlug(str, Enum):
    TESTNET = "testnet"
    MAINNET = "mainnet"

class SignatureFormat(str, Enum):
    ETHEREUM_SEPOLIA = "ethereum-11155111"


class AlloraClient:
    """
    Allora Network plugin. 

    Initialize with your API key to create Allora API functions.

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
        chain_slug: Optional[AlloraChainSlug] = AlloraChainSlug.TESTNET,
        api_key: Optional[str] = DEFAULT_ALLORA_API_KEY,
        base_api_url: Optional[str] = "https://api.allora.network/v2",
    ):
        """
        Initialize the Allora client.

        Args:
            api_key (str): Your Allora API key
            chain_slug (str): The chain slug to use for the Allora client
        """
        # TODO: use allora-sdk when available

        self.chain_id = (
            AlloraChainSlug.TESTNET
            if chain_slug == AlloraChainSlug.TESTNET
            else AlloraChainSlug.MAINNET
        ).value
        self.api_key = api_key
        self.base_api_url = base_api_url if base_api_url else "https://api.allora.network/v2"

        self._functions: Dict[str, Function] = {
            "get_all_allora_topics": self._create_get_all_topics(),
            "get_allora_topic_inference": self._create_get_inference_by_topic_id()
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
        hint="When asked to provide price predictions or other predictions, get_all_topics needs to be executed first, to get more context on the topic id needed to queried for getting the actual inference.",
        config=FunctionConfig(
          method="get",
          url=self.get_request_url(f"allora/{self.chain_id}/topics"),
          headers={
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
          },
          success_feedback=(
              "Successfully queried Allora Network topics and fetched {{response.data.topics.length}} topics."
              "Here are the details of the topics retrieved:\n\n"
              "{{#response.data.topics}}\n"
              "Topic ID: {{topic_id}}\n"
              "Topic Name: {{topic_name}}\n"
              "Topic Description: {{description}}\n"
              "Topic is Active: {{is_active}}\n"
              "Topic epoch length: {{epoch_length}}\n"
              "Topic ground truth lag: {{ground_truth_lag}}\n"
              "Topic loss method: {{loss_method}}\n"
              "Topic updated at: {{updated_at}}\n"
              "{{/response.data.topics}}\n"
          ),
          error_feedback="An error occurred while fetching Allora Network topics. Status code: {{response.status_code}}. Please try again later.",
        )
      )

      return get_all_topics
    
    def _create_get_inference_by_topic_id(self) -> Function:
      get_inference_by_topic_id = Function(
        fn_name="get_inference_by_topic_id",
        fn_description="Fetches the inference from Allora Network given a topic id.",
        args=[
          FunctionArgument(
            name="topic_id",
            description="The topic_id corresponds to the unique id of one of the active topics on Allora Network",
            type="number"
          )
        ],
        hint="",
        config=FunctionConfig(
          method="get",
          url=self.get_request_url(f"allora/{self.chain_id}/consumer/{SignatureFormat.ETHEREUM_SEPOLIA}?allora_topic_id={{topic_id}}&inference_value_type=uint256"),
          headers={
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
          },
          success_feedback=(
             "I successfully queried Allora Network topic inference for topic with id {{topic_id}}. "
             "Here is the inference:\n\n"
             "{{response.data.inference_data.network_inference_normalized}}"

          ),
          error_feedback="An error occurred while fetching inference from Allora Network. Status code: {{response.status_code}}. Please try again later."
        )
      )

      return get_inference_by_topic_id

    def get_request_url(self, endpoint: str) -> str:
      """
      Constructs the full request URL for a given endpoint.

      :param endpoint: The API endpoint
      :return: The full request URL
      """
      api_url = self.base_api_url.rstrip("/")
      endpoint = endpoint.lstrip("/")
      return f"{api_url}/{endpoint}"
