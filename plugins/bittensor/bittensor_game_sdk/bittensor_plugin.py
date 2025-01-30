import aiohttp
from typing import Dict, Any, Optional
from game_sdk.game_sdk import GameSDK, GameSDKInterface
import requests
import os

class BittensorPlugin(GameSDKInterface):
    """
    Bittensor Plugin for interacting with Bittensor subnets via BitMind API
    """
    
    def __init__(self, game_sdk: GameSDK):
        """Initialize the Bittensor plugin"""
        super().__init__(game_sdk)
        self.api_key = self.game_sdk.get_env("BITMIND_API_KEY")
        self.api_base_url = "https://subnet-api.bitmind.ai/v1"
        
    async def initialize(self):
        """Initialize the plugin"""
        if not self.api_key:
            raise ValueError("BITMIND_API_KEY environment variable is required")

    async def call_subnet(
        self,
        subnet_id: int,
        payload: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an inference call to a specific Bittensor subnet
        
        Args:
            subnet_id (int): The ID of the subnet to call
            prompt (str): The prompt/input to send to the subnet
            parameters (Optional[Dict[str, Any]]): Additional parameters for the API call
            
        Returns:
            Dict[str, Any]: The response from the subnet
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "subnet_id": subnet_id,
            "payload": payload
        }
        
        if parameters:
            data.update(parameters)
            
        if subnet_id == 34:
            return self.detect_image(payload['image'])
            

    async def get_subnet_info(self, subnet_id: int) -> Dict[str, Any]:
        """
        Get information about a specific subnet
        
        Args:
            subnet_id (int): The ID of the subnet
            
        Returns:
            Dict[str, Any]: Information about the subnet
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base_url}/subnets/{subnet_id}",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Bitmind API error: {error_text}")
                    
                return await response.json()

    async def list_subnets(self) -> Dict[str, Any]:
        """
        Get a list of available subnets
        
        Returns:
            Dict[str, Any]: List of available subnets and their information
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_base_url}/subnets",
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Bitmind API error: {error_text}")
                    
                return await response.json()

    def detect_image(img_url: str) -> dict:
        """
        Function to detect the image's fakeness using Trinity API
        """
        response = requests.post(
            'https://subnet-api.bitmindlabs.ai/detect-image',
            headers={
                "Authorization": f"Bearer {os.environ.get('BITMINDLABS_API_KEY')}",
                'Content-Type': 'application/json'
            },
            json={
                'image': img_url
            }
        )
        return response.json()