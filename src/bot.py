from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from .captcha_handler import CaptchaHandler
import configparser
import time
import os
import random

class DVSABot:
    """Bot to navigate the DVSA test booking site with captcha handling."""
    
    def __init__(self, config_path):
        """Initialize the bot with configuration."""
        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Set up webdriver
        self.driver = self._setup_driver()
        self.wait_time = int(self.config.get('webdriver', 'wait_time', fallback='10'))
        self.wait = WebDriverWait(self.driver, self.wait_time)
        
        # Initialize captcha handler
        self.captcha_handler = CaptchaHandler(self.driver, self.wait)
        
        # Track navigation state
        self.current_page = None
        
    def _setup_driver(self):
        """Set up and configure Chrome WebDriver with anti-detection measures."""
        options = Options()
        
        # Set headless mode from config
        if self.config.getboolean('webdriver', 'headless', fallback=False):
            options.add_argument("--headless=new")
        
        # Add anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Add user agent rotation if configured
        use_random_agent = self.config.getboolean('webdriver', 'random_user_agent', fallback=False)
        if use_random_agent:
            options.add_argument(f"user-agent={self._get_random_user_agent()}")
        
        # Add extensions if configured
        extension_path = self.config.get('webdriver', 'extension_path', fallback=None)
        if extension_path and os.path.exists(extension_path):
            options.add_extension(extension_path)
            
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Create driver using webdriver manager to download the correct driver
        driver = webdriver.Chrome(options=options)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def _get_random_user_agent(self):
        """Return a random user agent string to prevent fingerprinting."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0"
        ]
        return random.choice(user_agents)
        
    def _random_sleep(self, base_time, variance=1.0):
        """Sleep for a random amount of time to appear more human-like."""
        sleep_time = base_time + random.uniform(0, variance)
        time.sleep(sleep_time)
        return sleep_time
        
    def check_and_handle_captcha(self):
        """Check for captcha and handle it if present."""
        captcha_type = self.captcha_handler.detect_captcha()
        
        if captcha_type:
            print(f"Detected {captcha_type} captcha, attempting to solve...")
            success = self.captcha_handler.solve_captcha(captcha_type)
            
            if success:
                print("Successfully handled captcha!")
                self._random_sleep(1.0)
                return True
            else:
                print("Failed to automatically solve captcha.")
                
                # Check if we should wait for manual intervention
                if self.config.getboolean('captcha', 'allow_manual_solve', fallback=True):
                    manual_timeout = int(self.config.get('captcha', 'manual_solve_timeout', fallback='60'))
                    print(f"Waiting {manual_timeout} seconds for manual intervention...")
                    self._random_sleep(manual_timeout)
                    
                    # Check if captcha is still present after waiting
                    if not self.captcha_handler.detect_captcha():
                        print("Captcha appears to be solved after waiting")
                        return True
                
                return False
        
        return True  # No captcha detected
        
    def navigate_to_first_page(self):
        """Navigate to the DVSA booking first page with captcha handling."""
        print("Navigating to DVSA website...")
        self.driver.get("https://driverpracticaltest.dvsa.gov.uk/application")
        self.current_page = "application"
        
        # Handle potential captcha
        if not self.check_and_handle_captcha():
            print("Failed to handle initial captcha")
            return False
        
        # Handle cookies if present
        try:
            cookie_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "accept-all-cookies"))
            )
            cookie_button.click()
            print("Accepted cookies")
            self._random_sleep(1.0)
        except:
            print("No cookie prompt found or already accepted")
        
        return True
        
    def select_car_test(self):
        """Select the car test option on the first page."""
        print("Selecting car test option...")
        try:
            # Check for captcha before proceeding
            if not self.check_and_handle_captcha():
                print("Failed to handle captcha before selecting car test")
                return False
                
            # Find and click the car test button
            car_test_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "test-type-car"))
            )
            car_test_button.click()
            print("Selected Car test option")
            self._random_sleep(1.5)
            
            # Check for captcha after clicking
            if not self.check_and_handle_captcha():
                print("Failed to handle captcha after selecting car test")
                return False
            
            # Verify we've moved to the license details page
            self.wait.until(EC.presence_of_element_located((By.ID, "driving-licence")))
            print("Successfully moved to license details page!")
            return True
        except Exception as e:
            print(f"Error selecting car test: {e}")
            return False
    
    def enter_credentials(self, license_number, booking_reference):
        """Enter license and booking reference details."""
        print("Entering license and booking details...")
        try:
            # Check for captcha before proceeding
            if not self.check_and_handle_captcha():
                return False
                
            # Enter license number with human-like typing
            license_input = self.wait.until(
                EC.element_to_be_clickable((By.ID, "driving-licence-number"))
            )
            license_input.clear()
            for char in license_number:
                license_input.send_keys(char)
                self._random_sleep(random.uniform(0.05, 0.2))
                
            # Enter booking reference with human-like typing
            booking_input = self.wait.until(
                EC.element_to_be_clickable((By.ID, "application-reference-number"))
            )
            booking_input.clear()
            for char in booking_reference:
                booking_input.send_keys(char)
                self._random_sleep(random.uniform(0.05, 0.2))
                
            # Click submit button
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "booking-login"))
            )
            submit_button.click()
            print("Submitted credentials")
            self._random_sleep(2.0)
            
            # Check for captcha after submission
            if not self.check_and_handle_captcha():
                return False
                
            # Check for error messages
            error_message = None
            try:
                error_message = self.driver.find_element(By.CLASS_NAME, "error-message")
            except:
                pass
                
            if error_message and error_message.is_displayed():
                print(f"Login error: {error_message.text}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error entering credentials: {e}")
            return False
    
    def wait_for_queue(self, max_wait_minutes=30):
        """Wait for the DVSA queue to complete if present."""
        print("Checking for queue...")
        
        # Check if we're in the queue
        if "queue.driverpracticaltest.dvsa.gov.uk" in self.driver.current_url:
            print("Queue detected, waiting...")
            
            queue_start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            
            while time.time() - queue_start_time < max_wait_seconds:
                if "queue.driverpracticaltest.dvsa.gov.uk" not in self.driver.current_url:
                    print("Queue complete!")
                    self._random_sleep(2.0)
                    return True
                    
                # Check for captcha in the queue
                if self.check_and_handle_captcha():
                    print("Handled captcha in queue")
                
                # Wait and check again
                print(f"Still in queue... ({int((time.time() - queue_start_time) / 60)} minutes elapsed)")
                self._random_sleep(10.0, 5.0)
                
            print(f"Queue wait time exceeded {max_wait_minutes} minutes")
            return False
        else:
            print("No queue detected")
            return True
    
    def cleanup(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")