import sys
import os
from pathlib import Path
import time
from datetime import datetime

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

from dpsn_plugin_gamesdk.dpsn_plugin import plugin

def test_dpsn_connection():
    """Test DPSN connection and basic functionality"""
    print("\n🔄 Testing DPSN Connection...")
    
    # Initialize DPSN client (without options since the method doesn't accept them)
    result = plugin.initialize()
    if not result["success"]:
        print(f"❌ Failed to initialize DPSN: {result.get('error')}")
        return False
    
    # Wait for connection to stabilize
    time.sleep(1)
    print("✅ DPSN initialized successfully")
    return True

def test_subscribe_and_receive():
    """Test subscribing to topics and receiving messages"""
    print("\n🔄 Testing Subscription and Message Reception...")
    
    # Define message handler
    def handle_message(message_data):
        topic = message_data['topic']
        payload = message_data['payload']
        print(f"Received message on {topic}: {payload}")

    # Set the callback
    plugin.set_message_callback(handle_message)
    
    # Test topic
    topic = "0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ohlc"
    
    print(f"Subscribing to topic: {topic}")
    result = plugin.subscribe(topic)
    if not result["success"]:
        print(f"❌ Failed to subscribe to topic: {result.get('error')}")
        return False
    
    print("Subscription successful!")
    print("\nWaiting for messages... (Press Ctrl+C to exit)")
    
    try:
        while True:
            if not plugin.client.dpsn_broker.is_connected():
                print("Connection lost, attempting to reconnect...")
                plugin.initialize()
                time.sleep(1)
                plugin.subscribe(topic)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return True
    
    return True

def test_shutdown():
    """Test graceful shutdown"""
    print("\n🔄 Testing Shutdown...")
    
    result = plugin.shutdown()
    if not result["success"]:
        print(f"❌ Failed to shutdown: {result.get('error')}")
        return False
    
    print("✅ Shutdown successful")
    return True

def main():
    """Main test function"""
    print("🚀 Starting DPSN Plugin Tests...")
    
    try:
        # Test connection
        if not test_dpsn_connection():
            return
        
        # Test subscription and message reception
        if not test_subscribe_and_receive():
            return
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
    finally:
        # Ensure we shutdown properly
        test_shutdown()

if __name__ == "__main__":
    main()
