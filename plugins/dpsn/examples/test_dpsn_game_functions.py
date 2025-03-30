import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)

from dpsn_plugin_gamesdk.dpsn_plugin import plugin
import json
from datetime import datetime

async def test_dpsn_connection():
    """Test DPSN connection and basic functionality"""
    print("\n🔄 Testing DPSN Connection...")
    
    # Initialize DPSN client
    result = await plugin.initialize()
    if not result["success"]:
        print(f"❌ Failed to initialize DPSN: {result.get('error')}")
        return False
    
    print("✅ DPSN initialized successfully")
    return True

  
async def test_subscribe_and_receive():
    """Test subscribing to topics and receiving messages"""
    print("\n🔄 Testing Subscription and Message Reception...")
    
    # Define message handler first
    async def message_handler(message):
        print(f"\n📨 Received Message:")
        print(f"Topic: {message['topic']}")
        print(f"Payload: {message['payload']}")
        print(f"Time: {message['timestamp']}")
        print("-" * 50)

    # Set the callback before subscribing
    plugin.set_message_callback(message_handler)
    
    # Test topic
    topic = "0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ticker"
    
    # Subscribe to topic
    result = await plugin.subscribe(topic)
    if not result["success"]:
        print(f"❌ Failed to subscribe to topic: {result.get('error')}")
        return False
    
    print(f"✅ Subscribed to topic: {topic}")
    
    # Wait for messages with shorter intervals to see if we're receiving them
    print("⏳ Waiting for messages (30 seconds)...")
    for _ in range(6):  # Check every 5 seconds for 30 seconds total
        await asyncio.sleep(5)
        print("Checking for messages...")
    
    return True

async def test_shutdown():
    """Test graceful shutdown"""
    print("\n🔄 Testing Shutdown...")
    
    result = await plugin.shutdown()
    if not result["success"]:
        print(f"❌ Failed to shutdown: {result.get('error')}")
        return False
    
    print("✅ Shutdown successful")
    return True

async def main():
    """Main test function"""
    print("🚀 Starting DPSN Plugin Tests...")
    
    try:
        # Test connection
        if not await test_dpsn_connection():
            return
        
        # Test subscription and message reception
        if not await test_subscribe_and_receive():
            return
        
        # Test shutdown
        if not await test_shutdown():
            return
        
        print("\n✨ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
    finally:
        # Ensure we shutdown properly
        await plugin.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
