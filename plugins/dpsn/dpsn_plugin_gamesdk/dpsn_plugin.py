import asyncio
import os
from dotenv import load_dotenv
from dpsn_client.client import DpsnClient, DPSNError
from datetime import datetime

# Load .env variables
load_dotenv()

class DpsnPlugin:
    """
    DPSN Plugin for handling DPSN client connections and message handling
    """

    def __init__(self):
        self.dpsn_url = os.getenv("DPSN_URL")
        self.pvt_key = os.getenv("PVT_KEY")
        self.client = None
        self.messages = []

    async def initialize(self):
        """Initialize the DPSN client with default configuration"""
        if not self.dpsn_url or not self.pvt_key:
            return {"success": False, "error": "DPSN_URL and PVT_KEY must be set in .env file"}

        chain_options = {
            "network": "testnet",
            "wallet_chain_type": "ethereum"
        }

        connection_options = {
            "ssl": True,
            "connect_timeout": 5000
        }

        try:
            self.client = DpsnClient(
                dpsn_url=self.dpsn_url,
                private_key=self.pvt_key,
                chain_options=chain_options,
                connection_options=connection_options
            )

            self.client.event_bus.on("connected", self._on_connected)
            self.client.event_bus.on("subscribe", self._on_subscribe)
            self.client.event_bus.on("message", self._on_message)

            await self.client.init()
            return {"success": self.client.connected}

        except DPSNError as e:
            return {"success": False, "error": f"DPSNError: {str(e)}"}

    async def subscribe(self, topic: str):
        """Subscribe to a specific topic"""
        if not self.client or not self.client.connected:
            return {"success": False, "error": "Client not initialized or not connected"}
        
        try:
            await self.client.subscribe(topic)
            return {"success": True, "topic": topic}
        except DPSNError as e:
            return {"success": False, "error": f"Subscription error: {str(e)}"}

    async def shutdown(self):
        """Shutdown the DPSN client"""
        if self.client:
            await self.client.shutdown()
            return {"success": True}
        return {"success": False, "error": "No client to shutdown"}

    async def _on_connected(self):
        """Default connected event handler"""
        print("✅ Connected to DPSN")

    async def _on_subscribe(self, info):
        """Default subscribe event handler"""
        print(f"📥 Subscribed to {info['topic']} (QoS:{info['qos']})")

    async def _on_message(self, msg):
        """Default message event handler"""
        message_data = {
            "topic": msg["topic"],
            "payload": msg["payload"],
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(message_data)
        return msg
        # print(f"📨 Message received -> {msg['topic']} : {msg['payload']}")


# Create plugin instance
plugin = DpsnPlugin()
    