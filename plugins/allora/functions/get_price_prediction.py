from typing import Tuple
from game_sdk.game.custom_types import Function, FunctionResultStatus
from game_sdk.hosted_game.agent import FunctionArgument
from allora_sdk.v2.api_client import AlloraAPIClient, PricePredictionToken, PricePredictionTimeframe


class GetPricePrediction(Function):
    def __init__(self, client: AlloraAPIClient):
        super().__init__(
            fn_name="get_price_prediction",
            fn_description="Fetches from Allora Network the future price prediction for a given crypto asset and timeframe.",
            args=[
                FunctionArgument(
                    name="asset",
                    description="The crypto asset symbol to get the price prediction for. Example: BTC, ETH, SOL, SHIB, etc.",
                    type="string",
                ),
                FunctionArgument(
                    name="timeframe",
                    description="The timeframe to get the price prediction for. Example: 5m, 8h, 24h, etc.",
                    type="string",
                )
            ],
            hint="",
            executable=self.get_price_prediction,
        )
        self.client = client

    async def get_price_prediction(
        self, asset: PricePredictionToken, timeframe: PricePredictionTimeframe, **kwargs
    ) -> Tuple[FunctionResultStatus, str, dict]:
        try:
            price_prediction = await self.client.get_price_prediction(asset, timeframe)
            normalized_price_prediction = (
                price_prediction.inference_data.network_inference_normalized
            )
            return (
                FunctionResultStatus.DONE,
                f"The price prediction for {asset} in {timeframe} is: {normalized_price_prediction}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                    "complete_price_prediction_data": price_prediction,
                    "normalized_price_prediction": normalized_price_prediction,
                },
            )
        except Exception as e:
            return (
                FunctionResultStatus.FAILED,
                f"An error occurred while fetching price prediction from Allora Network: {str(e)}",
                {
                    "asset": asset,
                    "timeframe": timeframe,
                },
            )
