from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from .captcha_handler import CaptchaHandler
import configparser
import time
import os
import random
import logging
import traceback

class DVSABot:
    """Bot to navigate the DVSA test booking site with advanced captcha handling."""
    
    def __init__(self, config_path, logger=None):
        """Initialize the bot with configuration."""
        # Setup logging
        self.logger = logger or logging.getLogger(__name__)
        
        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Create screenshots directory if needed
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        
        # Setup chrome driver
        self.driver = self._setup_driver()
        self.wait_time = int(self.config.get('webdriver', 'wait_time', fallback='15'))
        self.wait = WebDriverWait(self.driver, self.wait_time)
        
        # Initialize captcha handler
        self.captcha_handler = CaptchaHandler(self.driver, self.wait, self.logger)
        
        # Track navigation state
        self.current_page = None
        
    def _setup_driver(self):
        """Set up and configure Chrome WebDriver with enhanced anti-detection measures."""
        self.logger.info("Setting up Chrome WebDriver")
        options = Options()
        
        # Set headless mode from config
        if self.config.getboolean('webdriver', 'headless', fallback=False):
            self.logger.info("Running in headless mode")
            options.add_argument("--headless=new")
        
        # Add enhanced anti-detection measures
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Disable images for faster loading if configured
        if self.config.getboolean('webdriver', 'disable_images', fallback=False):
            options.add_argument("--blink-settings=imagesEnabled=false")
        
        # Add user agent rotation if configured
        use_random_agent = self.config.getboolean('webdriver', 'random_user_agent', fallback=False)
        if use_random_agent:
            user_agent = self._get_random_user_agent()
            self.logger.info(f"Using random user agent: {user_agent}")
            options.add_argument(f"user-agent={user_agent}")
        
        # Add extensions if configured
        extension_path = self.config.get('webdriver', 'extension_path', fallback=None)
        if extension_path and os.path.exists(extension_path):
            self.logger.info(f"Loading extension from: {extension_path}")
            options.add_extension(extension_path)
        else:
            self.logger.warning(f"Extension not found at path: {extension_path}")
            
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Add custom preferences to avoid detection
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            # Create driver using webdriver manager to download the correct driver
            self.logger.info("Initializing Chrome driver")
            driver = webdriver.Chrome(options=options)
            
            # Execute CDP commands to prevent detection
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Overwrite the 'plugins' property to use a custom getter
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    // Overwrite the 'languages' property to use a custom getter
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Spoof permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """
            })
            
            self.logger.info("Chrome driver initialized successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Error setting up Chrome driver: {e}")
            self.logger.error(traceback.format_exc())
            raise
    
    def _get_random_user_agent(self):
        """Return a random user agent string to prevent fingerprinting."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 OPR/119.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
        ]
        return random.choice(user_agents)
        
    def _random_sleep(self, base_time, variance=1.0):
        """Sleep for a random amount of time to appear more human-like."""
        sleep_time = base_time + random.uniform(0, variance)
        self.logger.debug(f"Sleeping for {sleep_time:.2f} seconds")
        time.sleep(sleep_time)
        return sleep_time
    
    def _take_screenshot(self, name):
        """Take a screenshot for debugging purposes."""
        try:
            filename = f"screenshots/{name}_{int(time.time())}.png"
            self.driver.save_screenshot(filename)
            self.logger.info(f"Saved screenshot to {filename}")
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
        
    def check_and_handle_captcha(self):
        """Check for captcha and handle it if present."""
        captcha_type = self.captcha_handler.detect_captcha()
        
        if captcha_type:
            self.logger.info(f"Detected {captcha_type} captcha, attempting to solve...")
            self._take_screenshot(f"captcha_{captcha_type}_detected")
            
            success = self.captcha_handler.solve_captcha(captcha_type)
            
            if success:
                self.logger.info("Successfully handled captcha!")
                self._random_sleep(1.0)
                return True
            else:
                self.logger.warning("Failed to automatically solve captcha.")
                
                # Check if we should wait for manual intervention
                if self.config.getboolean('captcha', 'allow_manual_solve', fallback=True):
                    manual_timeout = int(self.config.get('captcha', 'manual_solve_timeout', fallback='60'))
                    self.logger.info(f"Waiting {manual_timeout} seconds for manual intervention...")
                    self._random_sleep(manual_timeout)
                    
                    # Check if captcha is still present after waiting
                    if not self.captcha_handler.detect_captcha():
                        self.logger.info("Captcha appears to be solved after waiting")
                        return True
                
                return False
        
        return True  # No captcha detected
        
    def navigate_to_first_page(self):
        """Navigate to the DVSA booking first page with enhanced captcha handling."""
        self.logger.info("Navigating to DVSA website...")
        
        # Check if we should use the queue URL instead of direct access
        use_queue = self.config.getboolean('dvsa', 'use_queue_url', fallback=True)
        
        try:
            if use_queue:
                queue_url = "https://queue.driverpracticaltest.dvsa.gov.uk/?c=dvsatars&e=ibsredirectprod0915&t=https%3A%2F%2Fdriverpracticaltest.dvsa.gov.uk%2Fapplication&cid=en-GB"
                self.logger.info(f"Using queue URL: {queue_url}")
                self.driver.get(queue_url)
            else:
                self.logger.info("Using direct URL: https://driverpracticaltest.dvsa.gov.uk/application")
                self.driver.get("https://driverpracticaltest.dvsa.gov.uk/application")
            
            self.current_page = "application"
        except WebDriverException as e:
            self.logger.error(f"Error navigating to DVSA website: {e}")
            self._take_screenshot("navigation_error")
            return False
        
        # Sleep briefly to let page load before checking for captcha
        self._random_sleep(3.0)
        
        # Take screenshot after initial load
        self._take_screenshot("initial_load")
        
        # Handle potential captcha
        if not self.check_and_handle_captcha():
            self.logger.error("Failed to handle initial captcha")
            return False
        
        # Check for 403 Forbidden
        if "403" in self.driver.title or "Forbidden" in self.driver.page_source:
            self.logger.warning("Received 403 Forbidden - attempting to handle...")
            self._take_screenshot("forbidden_403")
            self.captcha_handler.handle_403_error()
            
            # Try refreshing and checking again
            self._random_sleep(2.0)
            if "403" in self.driver.title or "Forbidden" in self.driver.page_source:
                self.logger.error("Still receiving 403 Forbidden after handling")
                return False
        
        # Handle cookies if present
        try:
            cookie_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "accept-all-cookies"))
            )
            cookie_button.click()
            self.logger.info("Accepted cookies")
            self._random_sleep(1.0)
        except (TimeoutException, NoSuchElementException):
            self.logger.info("No cookie prompt found or already accepted")
        
        return True
    
    def select_car_test(self):
        """Select the car test option on the first page."""
        self.logger.info("Selecting car test option...")
        try:
            # Check for captcha before proceeding
            if not self.check_and_handle_captcha():
                self.logger.error("Failed to handle captcha before selecting car test")
                return False
                
            # Find and click the car test button
            car_test_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "test-type-car"))
            )
            car_test_button.click()
            self.logger.info("Selected Car test option")
            self._random_sleep(1.5)
            
            # Check for captcha after clicking
            if not self.check_and_handle_captcha():
                self.logger.error("Failed to handle captcha after selecting car test")
                return False
            
            # Verify we've moved to the license details page
            self.wait.until(EC.presence_of_element_located((By.ID, "driving-licence-number")))
            self.logger.info("Successfully moved to license details page!")
            return True
        except Exception as e:
            self.logger.error(f"Error selecting car test: {e}")
            self._take_screenshot("select_car_test_error")
            return False
    
    def enter_credentials(self, license_number, booking_reference):
        """Enter license and booking reference details."""
        self.logger.info("Entering license and booking details...")
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
                
            # Take screenshot before submitting
            self._take_screenshot("credentials_entered")
                
            # Click submit button
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "booking-login"))
            )
            submit_button.click()
            self.logger.info("Submitted credentials")
            self._random_sleep(2.0)
            
            # Take screenshot after submitting
            self._take_screenshot("after_credentials_submit")
            
            # Check for captcha after submission
            if not self.check_and_handle_captcha():
                return False
                
            # Check for error messages
            error_message = None
            try:
                error_message = self.driver.find_element(By.CLASS_NAME, "error-message")
            except NoSuchElementException:
                pass
                
            if error_message and error_message.is_displayed():
                self.logger.error(f"Login error: {error_message.text}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error entering credentials: {e}")
            self._take_screenshot("credentials_error")
            return False
    
    def wait_for_queue(self, max_wait_minutes=30):
        """Wait for the DVSA queue to complete if present."""
        self.logger.info("Checking for queue...")
        
        # Take screenshot to see if we're in the queue
        self._take_screenshot("check_queue")
        
        # Check if we're in the queue
        if "queue.driverpracticaltest.dvsa.gov.uk" in self.driver.current_url:
            self.logger.info("Queue detected, waiting...")
            
            queue_start_time = time.time()
            max_wait_seconds = max_wait_minutes * 60
            
            while time.time() - queue_start_time < max_wait_seconds:
                if "queue.driverpracticaltest.dvsa.gov.uk" not in self.driver.current_url:
                    self.logger.info("Queue complete!")
                    self._random_sleep(2.0)
                    self._take_screenshot("queue_complete")
                    return True
                    
                # Check for captcha in the queue
                if self.check_and_handle_captcha():
                    self.logger.info("Handled captcha in queue")
                
                # Wait and check again
                minutes_elapsed = int((time.time() - queue_start_time) / 60)
                self.logger.info(f"Still in queue... ({minutes_elapsed} minutes elapsed)")
                
                # Take occasional screenshots to monitor queue progress
                if minutes_elapsed % 5 == 0:
                    self._take_screenshot(f"queue_progress_{minutes_elapsed}min")
                
                self._random_sleep(10.0, 5.0)
                
            self.logger.warning(f"Queue wait time exceeded {max_wait_minutes} minutes")
            return False
        else:
            self.logger.info("No queue detected")
            return True
    
    def cleanup(self):
        """Close the browser."""
        if self.driver:
            self.logger.info("Closing browser")
            self.driver.quit()