import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import time # Import time for sleep

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

from dpsn_plugin_gamesdk.dpsn_plugin import plugin

class DpsnWorker:
    """
    DPSN Worker for processing market data and executing trades (Synchronous Version)
    """
    def __init__(self):
        self.plugin = plugin
        self.trades: List[Dict[str, Any]] = []
        self.is_running = False

    def initialize(self):
        """Initialize the DPSN worker"""
        # Call synchronous initialize
        result = self.plugin.initialize()
        if not result["success"]:
            raise Exception(f"Failed to initialize DPSN: {result.get('error')}")
        print("DPSN Worker Initialized Successfully")
        return True

    def process_message(self, message: Dict[str, Any]):
        """Process incoming messages and execute trades"""
        topic = message['topic']
        payload = message['payload']
        
        # Log the message
        print(f"\n Processing message:")
        print(f"Topic: {topic}")
        print(f"Payload: {payload}")
        
        # Execute trade if conditions are met (synchronous call)
        trade = self.execute_trade(topic, payload)
        if trade:
            self.trades.append(trade)
            print(f"💼 Trade executed: {trade}")

    # Example use case of dpsn plugin worker
    def execute_trade(self, topic: str, payload: Dict[str, Any]) -> Dict[str, Any] | None:
        """Execute trades based on market data"""
        # Example trade execution logic (synchronous)
        if "SOLUSDT" in topic:
            # Ensure payload is a dictionary before accessing keys
            if isinstance(payload, dict):
                try:
                    price = float(payload.get('price', 0))
                    if price > 100:
                        return {
                            "action": "SELL",
                            "price": price,
                            "timestamp": datetime.now().isoformat(),
                            "status": "EXECUTED"
                        }
                except (ValueError, TypeError) as e:
                     print(f"Error processing price from payload: {e}")
            else:
                 print(f"Skipping trade execution: Payload is not a dictionary ({type(payload)})")
        return None

    def start(self):
        """Start the DPSN worker"""
        self.initialize()
        
        # Set up message handler (synchronous)
        self.plugin.set_message_callback(self.process_message)
        
        # Subscribe to topics (synchronous)
        topics = [
            "0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ticker",
            # Add other topics if needed
        ]
        
        print("Subscribing to topics...")
        for topic in topics:
            result = self.plugin.subscribe(topic)
            if not result["success"]:
                print(f"Failed to subscribe to {topic}: {result.get('error')}")
                # Decide how to handle subscription failure (e.g., raise error, skip)
                # continue
                # raise Exception(f"Subscription failed for {topic}")
            else:
                print(f"Successfully subscribed to {topic}")
        
        self.is_running = True
        print("DPSN Worker Started")

    def stop(self):
        """Stop the DPSN worker"""
        print("Stopping DPSN Worker...")
        self.is_running = False
        # Consider unsubscribing from topics here if necessary
        # for topic in topics: self.plugin.unsubscribe(topic)
        self.plugin.shutdown()
        print("DPSN Worker Stopped")

def main():
    worker = DpsnWorker()
    try:
        worker.start()
        print("Worker running... Press Ctrl+C to stop.")
        # Keep the worker running using time.sleep
        while worker.is_running:
            time.sleep(1) # Check status every second
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down worker...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if worker.is_running:
             worker.stop()

if __name__ == "__main__":
    # Run main directly without asyncio
    main() 