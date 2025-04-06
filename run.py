from src.bot import DVSABot
import os
import time
import sys
import argparse

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='DVSA Bot with captcha handling')
    
    parser.add_argument('--config', 
                        type=str, 
                        default='config/config.ini',
                        help='Path to config file')
    
    parser.add_argument('--mode', 
                        type=str, 
                        choices=['test', 'full'], 
                        default='test',
                        help='Bot operation mode: test (proof of concept) or full (complete booking)')
    
    parser.add_argument('--manual-captcha', 
                        action='store_true',
                        help='Always wait for manual captcha solving')
    
    parser.add_argument('--wait-time', 
                        type=int, 
                        default=None,
                        help='Override the wait time for manual captcha solving (seconds)')
    
    return parser.parse_args()

def main():
    """Run the DVSA bot with enhanced captcha handling."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Get the absolute path to the config file
    config_path = os.path.abspath(args.config)
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
        
    print(f"Using config file: {config_path}")
    
    # Create the bot
    bot = DVSABot(config_path)
    
    # Override config settings if specified in command line
    if args.manual_captcha:
        print("Manual captcha solving mode enabled")
        bot.config.set('captcha', 'allow_manual_solve', 'true')
        
    if args.wait_time is not None:
        print(f"Setting manual captcha wait time to {args.wait_time} seconds")
        bot.config.set('captcha', 'manual_solve_timeout', str(args.wait_time))
    
    try:
        # Navigate to DVSA website
        if not bot.navigate_to_first_page():
            print("❌ Failed to navigate to DVSA website")
            return
            
        # Wait for any queue
        if not bot.wait_for_queue():
            print("❌ Queue timeout exceeded")
            return
            
        # Select car test type
        if not bot.select_car_test():
            print("❌ Failed to select car test")
            return
            
        if args.mode == 'test':
            # Proof of concept complete
            print("✅ Proof of concept successful!")
            
            # Keep the browser open for a moment to see the result
            print("Keeping browser open for 5 seconds...")
            time.sleep(5)
        else:
            # Full booking mode
            license_number = bot.config.get('dvsa', 'license_number', fallback='')
            booking_reference = bot.config.get('dvsa', 'booking_reference', fallback='')
            
            if not license_number or not booking_reference:
                print("❌ License number and booking reference must be set in the config file for full mode")
                return
                
            # Enter credentials
            if not bot.enter_credentials(license_number, booking_reference):
                print("❌ Failed to log in with provided credentials")
                return
                
            print("✅ Login successful!")
            
            # TODO: Implement the rest of the booking flow
            # This would include:
            # 1. Reading current booking details
            # 2. Navigating to change test center/date
            # 3. Searching for available dates
            # 4. Selecting and confirming a booking
            
            print("Full booking mode not fully implemented yet")
                
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        # Let user decide whether to close the browser
        close_browser = input("Close the browser? (y/n): ").lower() == 'y'
        if close_browser:
            bot.cleanup()
        else:
            print("Browser left open for inspection. Remember to close it manually when done.")

if __name__ == "__main__":
    main()