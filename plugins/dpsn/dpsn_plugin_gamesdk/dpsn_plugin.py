import os
from dotenv import load_dotenv
from dpsn_client.client import DpsnClient, DPSNError
from datetime import datetime
from game_sdk.game.custom_types import Function, Argument, FunctionResultStatus
from typing import Dict, Any, Callable, Tuple
import json
import logging

# Load .env variables
load_dotenv()

# Configure logging for the plugin (optional, but good practice)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DpsnPlugin")

class DpsnPlugin:
    """
    DPSN Plugin using the updated DpsnClient for handling connections,
    subscriptions, and message handling.
    """

    def __init__(self):
        self.dpsn_url = os.getenv("DPSN_URL")
        self.pvt_key = os.getenv("PVT_KEY")
        if not self.dpsn_url or not self.pvt_key:
            logger.error("DPSN_URL and PVT_KEY must be set in .env file")
            # Consider raising an error or handling this more gracefully
            # depending on how the game SDK expects plugin failures
        
        self.client: DpsnClient | None = None # Type hint for clarity
        self.message_callback: Callable[[Dict[str, Any]], None] | None = None # Type hint

        self._functions = {
            "initialize": Function(
                fn_name="initialize",
                fn_description="Initialize DPSN client connection",
                args=[],
                hint="Initializes or ensures the DPSN client is connected.",
                executable=self.initialize
            ),
            "subscribe": Function(
                fn_name="subscribe",
                fn_description="Subscribe to a DPSN topic",
                args=[
                    Argument(
                        name="topic",
                        description="The topic string to subscribe to",
                        type="string",
                        required=True
                    )
                ],
                hint="Subscribes to a specific DPSN topic to receive messages.",
                executable=self.subscribe
            ),
            # Added unsubscribe function
            "unsubscribe": Function(
                fn_name="unsubscribe",
                fn_description="Unsubscribe from a DPSN topic",
                args=[
                    Argument(
                        name="topic",
                        description="The topic string to unsubscribe from",
                        type="string",
                        required=True
                    )
                ],
                hint="Unsubscribes from a specific DPSN topic.",
                executable=self.unsubscribe
            ),
            "shutdown": Function(
                fn_name="shutdown",
                fn_description="Shutdown DPSN client connection",
                args=[],
                hint="Disconnects the DPSN client gracefully.",
                executable=self.shutdown
            )
            # Potential future function: publish
        }

    def get_function(self, fn_name: str) -> Function:
        """Get a specific function by name"""
        if fn_name not in self._functions:
            # Log the error as well
            logger.error(f"Function '{fn_name}' not found in DpsnPlugin")
            raise ValueError(f"Function '{fn_name}' not found")
        return self._functions[fn_name]

    def initialize(self) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        """
        Initializes the DpsnClient if not already done, or ensures it's connected.
        Uses configuration from environment variables.
        """
        if not self.dpsn_url or not self.pvt_key:
            logger.error("Cannot initialize: DPSN_URL and PVT_KEY are not set.")
            # Return Tuple: (Status, Message, Info)
            return (
                FunctionResultStatus.FAILED,
                "DPSN_URL and PVT_KEY must be set in .env file", 
                {}
            )

        if self.client and self.client.dpsn_broker and self.client.dpsn_broker.is_connected():
             logger.info("Client already initialized and connected. Re-initializing.")

        chain_options = {
            "network": "testnet", 
            "wallet_chain_type": "ethereum"
        }
        connection_options = {"ssl": True}

        try:
            if not self.client:
                 logger.info(f"Creating DpsnClient for {self.dpsn_url}")
                 self.client = DpsnClient(
                    dpsn_url=self.dpsn_url,
                    private_key=self.pvt_key,
                    chain_options=chain_options,
                    connection_options=connection_options
                 )
                 self.client.on_error += self._handle_client_error

            logger.info("Initializing DpsnClient connection...")
            self.client.init({
                "retry_options": {
                    "max_retries": 3,
                    "initial_delay": 1000, 
                    "max_delay": 5000
                }
            })
            logger.info("DpsnClient initialized successfully.")

            if self.message_callback:
                 try:
                     self.client.on_msg -= self.message_callback
                 except ValueError: 
                     pass
                 self.client.on_msg += self.message_callback
                 logger.info("Message callback re-applied.")
            
            # Return Tuple: (Status, Message, Info)
            return (FunctionResultStatus.DONE, "DPSN client initialized successfully.", {})

        except DPSNError as e:
            logger.error(f"DPSN Initialization Error: Code={e.code}, Msg={e.message}")
            if e.code in [DPSN_ERROR_CODES.INVALID_PRIVATE_KEY, DPSN_ERROR_CODES.BLOCKCHAIN_CONFIG_ERROR]:
                 self.client = None
            # Return Tuple: (Status, Message, Info)
            return (
                FunctionResultStatus.FAILED, 
                f"DPSNError ({e.code.name}): {e.message}", 
                {}
            )
        except Exception as e:
             logger.exception("Unexpected error during DPSN initialization:") 
             self.client = None 
             # Return Tuple: (Status, Message, Info)
             return (
                 FunctionResultStatus.FAILED, 
                 f"Unexpected initialization error: {str(e)}", 
                 {}
             )

    def subscribe(self, topic: str) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        """Subscribes to a specific topic using the initialized client."""
        if not self.client:
             logger.warning("Subscribe called but client is not initialized.")
             return (FunctionResultStatus.FAILED, "Client not initialized", {})
        
        if not self.client.dpsn_broker or not self.client.dpsn_broker.is_connected():
             logger.warning(f"Subscribe attempt failed for topic '{topic}': Client not connected.")
             return (FunctionResultStatus.FAILED, "Client not connected", {})
             
        try:
            logger.info(f"Subscribing to topic: {topic}")
            self.client.subscribe(topic) 
            logger.info(f"Successfully subscribed to topic: {topic}")
            # Return Tuple: (Status, Message, Info - include topic)
            return (FunctionResultStatus.DONE, f"Successfully subscribed to topic: {topic}", {"subscribed_topic": topic})
        except DPSNError as e:
            logger.error(f"DPSN Subscription Error for topic '{topic}': Code={e.code}, Msg={e.message}")
            return (FunctionResultStatus.FAILED, f"Subscription error ({e.code.name}): {e.message}", {"topic": topic})
        except Exception as e:
            logger.exception(f"Unexpected error during subscription to topic '{topic}':")
            return (FunctionResultStatus.FAILED, f"Unexpected subscription error: {str(e)}", {"topic": topic})

    # Added unsubscribe method
    def unsubscribe(self, topic: str) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        """Unsubscribes from a specific topic."""
        if not self.client:
            logger.warning("Unsubscribe called but client is not initialized.")
            return (FunctionResultStatus.FAILED, "Client not initialized", {})

        if not self.client.dpsn_broker or not self.client.dpsn_broker.is_connected():
             logger.warning(f"Unsubscribe attempt failed for topic '{topic}': Client not connected.")
             return (FunctionResultStatus.FAILED, "Client not connected", {})

        try:
            logger.info(f"Unsubscribing from topic: {topic}")
            self.client.unsubscribe(topic)
            logger.info(f"Successfully unsubscribed from topic: {topic}")
            # Return Tuple: (Status, Message, Info - include topic)
            return (FunctionResultStatus.DONE, f"Successfully unsubscribed from topic: {topic}", {"unsubscribed_topic": topic})
        except DPSNError as e:
            logger.error(f"DPSN Unsubscription Error for topic '{topic}': Code={e.code}, Msg={e.message}")
            return (FunctionResultStatus.FAILED, f"Unsubscription error ({e.code.name}): {e.message}", {"topic": topic})
        except Exception as e:
            logger.exception(f"Unexpected error during unsubscription from topic '{topic}':")
            return (FunctionResultStatus.FAILED, f"Unexpected unsubscription error: {str(e)}", {"topic": topic})


    def shutdown(self) -> Tuple[FunctionResultStatus, str, Dict[str, Any]]:
        """Disconnects the DPSN client."""
        if self.client:
            try:
                logger.info("Shutting down DpsnClient connection...")
                self.client.disconnect()
                logger.info("DpsnClient shutdown complete.")
                # Return Tuple: (Status, Message, Info)
                return (FunctionResultStatus.DONE, "DPSN client shutdown complete.", {})
            except DPSNError as e:
                logger.error(f"DPSN Shutdown Error: Code={e.code}, Msg={e.message}")
                return (FunctionResultStatus.FAILED, f"Shutdown error ({e.code.name}): {e.message}", {})
            except Exception as e:
                 logger.exception("Unexpected error during DPSN shutdown:")
                 return (FunctionResultStatus.FAILED, f"Unexpected shutdown error: {str(e)}", {})
        else:
             logger.info("Shutdown called but no active client to shutdown.")
             # Return Tuple: (Status, Message, Info)
             return (FunctionResultStatus.DONE, "No active client to shutdown", {}) 

    def set_message_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Sets the callback function to handle incoming messages.
        The callback receives a dictionary {'topic': str, 'payload': Any}.
        Payload is automatically decoded (string or dict/list if JSON).
        """
        logger.info(f"Setting message callback to: {callback.__name__ if hasattr(callback, '__name__') else callback}")
        
        # Remove old callback if client exists and callback was previously set
        if self.client and self.message_callback:
            try:
                self.client.on_msg -= self.message_callback
            except ValueError:
                 pass # Ignore if it wasn't added

        self.message_callback = callback # Store the new callback

        # Add the new callback if client exists
        if self.client:
            self.client.on_msg += self.message_callback
            logger.info("Message callback applied to existing client.")

    def _handle_client_error(self, error: DPSNError):
         """Internal handler for errors emitted by the DpsnClient."""
         logger.error(f"[DpsnClient EVENT] Error received: Code={error.code.name}, Msg={error.message}, Status={error.status}")
         # You could add more logic here, like notifying the game state

# Create plugin instance
plugin = DpsnPlugin()
    