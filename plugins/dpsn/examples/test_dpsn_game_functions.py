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
    
    # Test topic
    topic = "0xe14768a6d8798e4390ec4cb8a4c991202c2115a5cd7a6c0a7ababcaf93b4d2d4/SOLUSDT/ticker"
    
    # Subscribe to topic
    result = await plugin.subscribe(topic)
    if not result["success"]:
        print(f"❌ Failed to subscribe to topic: {result.get('error')}")
        return False
    
    print(f"✅ Subscribed to topic: {topic}")
    
    # Wait for some messages
    print("⏳ Waiting for messages (2 seconds)...")
    await asyncio.sleep(2)
    
    
    # Check received messages
    # messages = plugin.get_messages()
    print(f"\nReceived {len(messages)} messages:")
    for msg in messages:
        print(f"Topic: {msg['topic']}")
        print(f"Payload: {msg['payload']}")
        print(f"Timestamp: {msg['timestamp']}\n")
    
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
