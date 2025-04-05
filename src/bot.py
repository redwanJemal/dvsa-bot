from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import configparser
import time

class DVSABot:
    """Simple bot to navigate the DVSA test booking site."""
    
    def __init__(self, config_path):
        """Initialize the bot with configuration."""
        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Set up webdriver
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(self.driver, 10)  # 10 second wait
        
    def _setup_driver(self):
        """Set up and configure Chrome WebDriver."""
        options = Options()
        
        # Set headless mode from config
        if self.config.getboolean('webdriver', 'headless'):
            options.add_argument("--headless=new")
        
        # Basic anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        
        # Create driver using webdriver manager to download the correct driver
        driver = webdriver.Chrome(options=options)
        return driver
        
    def navigate_to_first_page(self):
        """Navigate to the DVSA booking first page."""
        print("Navigating to DVSA website...")
        self.driver.get("https://driverpracticaltest.dvsa.gov.uk/application")
        
        # Handle cookies if present
        try:
            cookie_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "accept-all-cookies"))
            )
            cookie_button.click()
            print("Accepted cookies")
        except:
            print("No cookie prompt found or already accepted")
        
        return True
        
    def select_car_test(self):
        """Select the car test option on the first page."""
        print("Selecting car test option...")
        try:
            # Find and click the car test button
            car_test_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "test-type-car"))
            )
            car_test_button.click()
            print("Selected Car test option")
            
            # Verify we've moved to the license details page
            self.wait.until(EC.presence_of_element_located((By.ID, "driving-licence")))
            print("Successfully moved to license details page!")
            return True
        except Exception as e:
            print(f"Error selecting car test: {e}")
            return False
    
    def cleanup(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            print("Browser closed")