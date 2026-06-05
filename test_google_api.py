import json
import logging
from api_clients import GoogleClient

logging.basicConfig(level=logging.INFO)

def run_test():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            
        print("Checking Google API Configuration...")
        client = GoogleClient(config)
        
        if not client.api_key:
            print("❌ GEMINI_API_KEY is not set in config.json")
            return
            
        print("Testing Google Gemini Text Generation (gemini-3-flash-preview)...")
        # Test basic text generation
        response = client._generate_text("Say 'Hello, Google API is working!'")
        print(f"✅ Text Generation Success. Response: {response.strip()}")
        
    except Exception as e:
        print(f"❌ Error testing Google API: {e}")

if __name__ == "__main__":
    run_test()
