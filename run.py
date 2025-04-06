from src.bot import DVSABot
import os
import time
import sys
import argparse
import logging

def setup_logging(verbose=False):
    """Configure logging for the application."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure file handler
    file_handler = logging.FileHandler("logs/dvsa_bot.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='DVSA Bot with enhanced captcha handling')
    
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
    
    parser.add_argument('--verbose', 
                        action='store_true',
                        help='Enable verbose logging')
    
    return parser.parse_args()

def main():
    """Run the DVSA bot with enhanced captcha handling."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    logger.info("Starting DVSA Bot")
    
    # Get the absolute path to the config file
    config_path = os.path.abspath(args.config)
    if not os.path.exists(config_path):
        logger.error(f"Error: Config file not found at {config_path}")
        sys.exit(1)
        
    logger.info(f"Using config file: {config_path}")
    
    # Create the bot
    bot = DVSABot(config_path, logger)
    
    # Override config settings if specified in command line
    if args.manual_captcha:
        logger.info("Manual captcha solving mode enabled")
        bot.config.set('captcha', 'allow_manual_solve', 'true')
        
    if args.wait_time is not None:
        logger.info(f"Setting manual captcha wait time to {args.wait_time} seconds")
        bot.config.set('captcha', 'manual_solve_timeout', str(args.wait_time))
    
    try:
        # Navigate to DVSA website
        if not bot.navigate_to_first_page():
            logger.error("❌ Failed to navigate to DVSA website")
            return
            
        # Wait for any queue
        if not bot.wait_for_queue():
            logger.error("❌ Queue timeout exceeded")
            return
        
        if args.mode == 'test':
            # Proof of concept complete
            logger.info("✅ Proof of concept successful!")
            
            # Keep the browser open for a moment to see the result
            logger.info("Keeping browser open for 5 seconds...")
            time.sleep(5)
        else:
            # Full booking mode
            license_number = bot.config.get('dvsa', 'license_number', fallback='')
            booking_reference = bot.config.get('dvsa', 'booking_reference', fallback='')
            
            if not license_number or not booking_reference:
                logger.error("❌ License number and booking reference must be set in the config file for full mode")
                return
                
            # Select car test type
            if not bot.select_car_test():
                logger.error("❌ Failed to select car test")
                return
                
            # Enter credentials
            if not bot.enter_credentials(license_number, booking_reference):
                logger.error("❌ Failed to log in with provided credentials")
                return
                
            logger.info("✅ Login successful!")
            
            # Check if we need to implement the rest of the booking process
            logger.info("Full booking mode not fully implemented yet")
                
    except Exception as e:
        logger.exception(f"❌ An error occurred: {e}")
    finally:
        # Let user decide whether to close the browser
        close_browser = input("Close the browser? (y/n): ").lower() == 'y'
        if close_browser:
            bot.cleanup()
        else:
            logger.info("Browser left open for inspection. Remember to close it manually when done.")

if __name__ == "__main__":
    main()