from src.bot import DVSABot
import os
import time

def main():
    """Run the DVSA bot proof of concept."""
    # Get the absolute path to the config file
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.ini')
    
    # Create the bot
    bot = DVSABot(config_path)
    
    try:
        # Navigate to DVSA website
        bot.navigate_to_first_page()
        
        # Select car test type
        success = bot.select_car_test()
        
        if success:
            print("✅ Proof of concept successful!")
            
            # Keep the browser open for a moment to see the result
            print("Keeping browser open for 5 seconds...")
            time.sleep(5)
        else:
            print("❌ Proof of concept failed")
    finally:
        # Always clean up
        bot.cleanup()

if __name__ == "__main__":
    main()