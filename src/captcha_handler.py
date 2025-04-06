import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class CaptchaHandler:
    """Handles different types of captchas encountered on the DVSA site."""
    
    def __init__(self, driver, wait=None, timeout=10):
        """Initialize with WebDriver instance."""
        self.driver = driver
        self.wait = wait if wait else WebDriverWait(driver, timeout)
        
    def detect_captcha(self):
        """Detect if a captcha is present on the page."""
        # Look for common captcha indicators
        captcha_types = {
            "imperva": self._is_imperva_captcha_present(),
            "recaptcha": self._is_google_recaptcha_present(),
            "incapsula": self._is_incapsula_present(),
        }
        
        for captcha_type, present in captcha_types.items():
            if present:
                print(f"Detected {captcha_type} captcha")
                return captcha_type
                
        return None
    
    def solve_captcha(self, captcha_type=None):
        """
        Attempt to solve the detected captcha.
        Returns True if solved, False otherwise.
        """
        if not captcha_type:
            captcha_type = self.detect_captcha()
            
        if not captcha_type:
            print("No captcha detected")
            return True
            
        # Call appropriate solver based on captcha type
        if captcha_type == "imperva":
            return self._solve_imperva_captcha()
        elif captcha_type == "recaptcha":
            return self._solve_google_recaptcha()
        elif captcha_type == "incapsula":
            return self._solve_incapsula_captcha()
        else:
            print(f"No handler for {captcha_type} captcha")
            return False
    
    def _is_imperva_captcha_present(self):
        """Check if Imperva captcha is present."""
        try:
            # Look for the Imperva checkbox or message
            imperva_elements = [
                (By.XPATH, "//div[@id='checkbox']"),
                (By.XPATH, "//div[contains(text(), 'Why am I seeing this page?')]"),
                (By.XPATH, "//div[contains(text(), 'verify that an actual human')]"),
                (By.XPATH, "//img[contains(@src, 'imperva')]")
            ]
            
            for by, selector in imperva_elements:
                try:
                    # Use a short timeout to check quickly
                    result = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if result:
                        return True
                except:
                    continue
                    
            return False
        except:
            return False
    
    def _is_google_recaptcha_present(self):
        """Check if Google reCAPTCHA is present."""
        try:
            recaptcha_elements = [
                (By.CSS_SELECTOR, "iframe[src*='recaptcha']"),
                (By.CSS_SELECTOR, ".g-recaptcha"),
                (By.XPATH, "//div[@data-sitekey]"),
                (By.XPATH, "//div[contains(@class, 'recaptcha')]")
            ]
            
            for by, selector in recaptcha_elements:
                try:
                    result = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if result:
                        return True
                except:
                    continue
                    
            return False
        except:
            return False
    
    def _is_incapsula_present(self):
        """Check if Incapsula security is present."""
        return "Incapsula incident ID" in self.driver.page_source
    
    def _solve_imperva_captcha(self):
        """Attempt to solve Imperva captcha."""
        try:
            # Try to find the checkbox by different possible selectors
            checkbox_selectors = [
                (By.ID, "checkbox"),
                (By.XPATH, "//div[@aria-haspopup='true' and @role='checkbox']"),
                (By.XPATH, "//div[@aria-checked='false' and @role='checkbox']"),
                (By.CSS_SELECTOR, "div[role='checkbox']")
            ]
            
            checkbox = None
            for by, selector in checkbox_selectors:
                try:
                    checkbox = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    if checkbox:
                        break
                except:
                    continue
            
            if checkbox:
                print("Found Imperva checkbox, attempting to click...")
                # Execute click using JavaScript for better reliability with hidden elements
                self.driver.execute_script("arguments[0].click();", checkbox)
                
                # Wait a moment for the page to process the click
                time.sleep(2)
                
                # Check if we're still on the captcha page
                if not self._is_imperva_captcha_present():
                    print("Successfully passed Imperva captcha check")
                    return True
                
                print("Still on Imperva captcha page after clicking checkbox")
            else:
                print("Could not find Imperva checkbox to click")
            
            # Take a screenshot to help debug
            self._take_debug_screenshot("imperva_captcha")
            return False
            
        except Exception as e:
            print(f"Error solving Imperva captcha: {e}")
            self._take_debug_screenshot("imperva_error")
            return False
            
    def _solve_google_recaptcha(self):
        """Attempt to solve Google reCAPTCHA."""
        try:
            print("Attempting to solve Google reCAPTCHA")
            
            # First try to find the reCAPTCHA iframe
            try:
                iframe = self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']")
                    )
                )
                self.driver.switch_to.frame(iframe)
                print("Switched to reCAPTCHA iframe")
            except Exception as e:
                print(f"Error switching to reCAPTCHA iframe: {e}")
                return False
                
            # Try to click the checkbox
            try:
                checkbox = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "div.recaptcha-checkbox-border")
                    )
                )
                checkbox.click()
                print("Clicked reCAPTCHA checkbox")
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                
                # Wait a moment to see if we need to solve a challenge
                time.sleep(2)
                
                # Check if we still have a captcha challenge
                if not self._is_google_recaptcha_present():
                    print("Successfully passed reCAPTCHA check")
                    return True
                else:
                    print("reCAPTCHA still present after checkbox click")
                    self._take_debug_screenshot("recaptcha_challenge")
                    
                    # Manual intervention might be needed
                    print("Manual intervention may be required for reCAPTCHA challenge")
                    self._wait_for_manual_solve(20)  # Wait for manual solving
                    
                    # Check again if captcha is solved
                    if not self._is_google_recaptcha_present():
                        print("reCAPTCHA appears to be solved")
                        return True
                
            except Exception as e:
                print(f"Error clicking reCAPTCHA checkbox: {e}")
                self.driver.switch_to.default_content()  # Make sure we get back to main frame
            
            return False
            
        except Exception as e:
            print(f"Error solving Google reCAPTCHA: {e}")
            self._take_debug_screenshot("recaptcha_error")
            return False
    
    def _solve_incapsula_captcha(self):
        """Attempt to solve Incapsula challenge."""
        try:
            print("Detected Incapsula challenge")
            self._take_debug_screenshot("incapsula_challenge")
            
            # Refresh the page and wait
            print("Refreshing page...")
            self.driver.refresh()
            time.sleep(5)
            
            # Check if the challenge is still present
            if "Incapsula incident ID" not in self.driver.page_source:
                print("Successfully passed Incapsula check after refresh")
                return True
                
            # If still present, might need manual intervention
            print("Incapsula challenge still present, waiting for manual solve...")
            self._wait_for_manual_solve(30)
            
            # Check again
            if "Incapsula incident ID" not in self.driver.page_source:
                print("Incapsula challenge appears to be solved")
                return True
                
            return False
            
        except Exception as e:
            print(f"Error handling Incapsula challenge: {e}")
            return False
    
    def _take_debug_screenshot(self, name):
        """Take a debug screenshot."""
        try:
            # Create screenshots directory if it doesn't exist
            if not os.path.exists("screenshots"):
                os.makedirs("screenshots")
                
            filename = f"screenshots/captcha_{name}_{int(time.time())}.png"
            self.driver.save_screenshot(filename)
            print(f"Saved debug screenshot to {filename}")
        except Exception as e:
            print(f"Error taking screenshot: {e}")
    
    def _wait_for_manual_solve(self, timeout=30):
        """
        Wait for manual human intervention to solve a captcha.
        Displays a message and waits for the specified timeout.
        """
        print(f"\n{'='*50}")
        print(f"MANUAL INTERVENTION REQUIRED")
        print(f"Please solve the captcha in the browser window")
        print(f"Waiting for {timeout} seconds...")
        print(f"{'='*50}\n")
        
        time.sleep(timeout)