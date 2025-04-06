#!/usr/bin/env python3
"""
Handler for various captcha types encountered on the DVSA website
"""
import time
import os
import logging
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

class CaptchaHandler:
    """Handles different types of captchas encountered on the DVSA site."""
    
    def __init__(self, driver, wait=None, logger=None, timeout=15):
        """Initialize with WebDriver instance."""
        self.driver = driver
        self.wait = wait if wait else WebDriverWait(driver, timeout)
        self.logger = logger or logging.getLogger(__name__)
        self.timeout = timeout
        
    def detect_captcha(self):
        """Detect if a captcha is present on the page."""
        # Check for 403 Forbidden response
        if "403" in self.driver.title or "Forbidden" in self.driver.page_source:
            self.logger.warning("Detected 403 Forbidden response")
            return "forbidden"
            
        # Look for common captcha indicators
        captcha_types = {
            "imperva": self._is_imperva_captcha_present(),
            "recaptcha": self._is_google_recaptcha_present(),
            "incapsula": self._is_incapsula_present(),
        }
        
        for captcha_type, present in captcha_types.items():
            if present:
                self.logger.info(f"Detected {captcha_type} captcha")
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
            self.logger.info("No captcha detected")
            return True
            
        # Call appropriate solver based on captcha type
        if captcha_type == "imperva":
            return self._solve_imperva_captcha()
        elif captcha_type == "recaptcha":
            return self._solve_google_recaptcha()
        elif captcha_type == "incapsula":
            return self._solve_incapsula_captcha()
        elif captcha_type == "forbidden":
            return self.handle_403_error()
        else:
            self.logger.warning(f"No handler for {captcha_type} captcha")
            return False
    
    def _is_imperva_captcha_present(self):
        """Check if Imperva captcha is present."""
        try:
            # Look for the Imperva checkbox or message
            imperva_elements = [
                (By.XPATH, "//div[@id='checkbox']"),
                (By.XPATH, "//div[contains(text(), 'Why am I seeing this page?')]"),
                (By.XPATH, "//div[contains(text(), 'verify that an actual human')]"),
                (By.XPATH, "//img[contains(@src, 'imperva')]"),
                (By.XPATH, "//img[contains(@src, 'incap')]"),
                (By.XPATH, "//div[contains(@class, 'incap')]"),
                (By.CSS_SELECTOR, "[id*='captcha']"),
                (By.CSS_SELECTOR, "div[style*='captcha'], div[class*='captcha'], div[id*='captcha']")
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
        except Exception as e:
            self.logger.error(f"Error checking for Imperva captcha: {e}")
            return False
    
    def _is_google_recaptcha_present(self):
        """Check if Google reCAPTCHA is present."""
        try:
            recaptcha_elements = [
                (By.CSS_SELECTOR, "iframe[src*='recaptcha']"),
                (By.CSS_SELECTOR, ".g-recaptcha"),
                (By.CSS_SELECTOR, "div[data-sitekey]"),
                (By.CSS_SELECTOR, "div[class*='recaptcha']"),
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
                    
            # Also check for reCAPTCHA iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and "recaptcha" in src:
                    return True
                    
            return False
        except Exception as e:
            self.logger.error(f"Error checking for Google reCAPTCHA: {e}")
            return False
    
    def _is_incapsula_present(self):
        """Check if Incapsula security is present."""
        try:
            incapsula_indicators = [
                "Incapsula incident ID" in self.driver.page_source,
                "/_Incapsula_" in self.driver.page_source,
                "incap_ses_" in str(self.driver.get_cookies()),
                "visid_incap_" in str(self.driver.get_cookies())
            ]
            
            return any(incapsula_indicators)
        except Exception as e:
            self.logger.error(f"Error checking for Incapsula: {e}")
            return False
    
    def handle_403_error(self):
        """Handle 403 Forbidden errors which indicate bot detection."""
        self.logger.warning("⚠️ Detected 403 Forbidden error - site may have detected automation")
        
        # Take a screenshot for debugging
        self._take_debug_screenshot("forbidden_403")
        
        # Check if we're in an Imperva/Incapsula challenge
        imperva_detected = self._is_imperva_captcha_present() or self._is_incapsula_present()
        if imperva_detected:
            self.logger.info("Detected Imperva/Incapsula security challenge within 403 error")
            return self.solve_captcha("imperva" if self._is_imperva_captcha_present() else "incapsula")
        
        # If no specific captcha detected but still getting 403, try refreshing
        self.logger.info("Attempting to refresh the page...")
        self.driver.refresh()
        time.sleep(5)
        
        # Check if refresh helped
        if "403" in self.driver.title or "Forbidden" in self.driver.page_source:
            self.logger.warning("Still getting 403 after refresh, waiting for manual intervention...")
            self._wait_for_manual_solve(60)  # Adjust timeout as needed
            return False
        
        return True
    
    def _solve_imperva_captcha(self):
        """Attempt to solve Imperva captcha."""
        try:
            self.logger.info("Attempting to solve Imperva captcha")
            
            # Try to find the checkbox by different possible selectors
            checkbox_selectors = [
                (By.ID, "checkbox"),
                (By.XPATH, "//div[@aria-haspopup='true' and @role='checkbox']"),
                (By.XPATH, "//div[@aria-checked='false' and @role='checkbox']"),
                (By.CSS_SELECTOR, "div[role='checkbox']"),
                (By.CSS_SELECTOR, "[id*='captcha'] input[type='checkbox']"),
                (By.XPATH, "//div[contains(@class, 'captcha')]//input[@type='checkbox']")
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
                self.logger.info("Found Imperva checkbox, attempting to click...")
                # Execute click using JavaScript for better reliability with hidden elements
                self.driver.execute_script("arguments[0].click();", checkbox)
                
                # Wait a moment for the page to process the click
                time.sleep(2)
                
                # Check if we're still on the captcha page
                if not self._is_imperva_captcha_present():
                    self.logger.info("Successfully passed Imperva captcha check")
                    return True
                
                self.logger.warning("Still on Imperva captcha page after clicking checkbox")
                
                # Try using the Buster extension if present
                try:
                    self.logger.info("Attempting to use Buster extension...")
                    buster_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@id, 'solver-button') or contains(@class, 'solver-button')]")
                    if buster_buttons:
                        self.logger.info("Found Buster button, clicking...")
                        for button in buster_buttons:
                            try:
                                button.click()
                                time.sleep(3)
                                self.logger.info("Clicked Buster button")
                                break
                            except:
                                continue
                except Exception as e:
                    self.logger.error(f"Error using Buster extension: {e}")
                
                # Wait for a moment to see if Buster solved it
                time.sleep(5)
                
                # Check again if captcha is solved
                if not self._is_imperva_captcha_present():
                    self.logger.info("Successfully passed Imperva captcha check after using Buster")
                    return True
                
                # If still not solved, wait for manual intervention
                self.logger.info("Waiting for manual intervention to solve Imperva captcha...")
                manual_timeout = 60  # seconds
                self._wait_for_manual_solve(manual_timeout)
                
                # Check one more time
                if not self._is_imperva_captcha_present():
                    self.logger.info("Successfully passed Imperva captcha check after manual intervention")
                    return True
                
            else:
                self.logger.warning("Could not find Imperva checkbox to click")
                
                # Search for any helpful elements that might indicate how to solve
                self._analyze_captcha_page()
                
                # Wait for manual intervention
                self.logger.info("Waiting for manual intervention to solve Imperva captcha...")
                self._wait_for_manual_solve(60)
                
                # Check if solved after manual intervention
                if not self._is_imperva_captcha_present():
                    self.logger.info("Successfully passed Imperva captcha check after manual intervention")
                    return True
            
            # Take a screenshot to help debug
            self._take_debug_screenshot("imperva_captcha_unsolved")
            return False
            
        except Exception as e:
            self.logger.error(f"Error solving Imperva captcha: {e}")
            self.logger.error(traceback.format_exc())
            self._take_debug_screenshot("imperva_error")
            return False
            
    def _solve_google_recaptcha(self):
        """Attempt to solve Google reCAPTCHA."""
        try:
            self.logger.info("Attempting to solve Google reCAPTCHA")
            
            # First try to find all iframes on the page
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            recaptcha_iframe = None
            
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                if "recaptcha/api2/anchor" in src:
                    recaptcha_iframe = iframe
                    break
            
            if not recaptcha_iframe:
                self.logger.warning("Could not find reCAPTCHA iframe")
                self._take_debug_screenshot("recaptcha_no_iframe")
                
                # Try to find other reCAPTCHA elements
                try:
                    recaptcha_box = self.driver.find_element(By.CSS_SELECTOR, ".g-recaptcha")
                    self.logger.info("Found reCAPTCHA box, but couldn't locate iframe")
                except:
                    self.logger.warning("Could not find any reCAPTCHA elements")
                
                # Wait for manual intervention
                self._wait_for_manual_solve(60)
                
                # Check if captcha is solved
                if not self._is_google_recaptcha_present():
                    self.logger.info("reCAPTCHA appears to be solved after manual intervention")
                    return True
                
                return False
            
            # Switch to the reCAPTCHA iframe
            self.logger.info("Switching to reCAPTCHA iframe")
            self.driver.switch_to.frame(recaptcha_iframe)
            
            # Try to find and click the checkbox
            try:
                checkbox = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".recaptcha-checkbox-border"))
                )
                self.logger.info("Found reCAPTCHA checkbox, clicking...")
                checkbox.click()
                self.logger.info("Clicked reCAPTCHA checkbox")
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                
                # Wait to see if we need to solve a challenge
                time.sleep(3)
                
                # Take a screenshot to see the state
                self._take_debug_screenshot("after_recaptcha_click")
                
                # Check if we still have a captcha challenge
                if not self._is_google_recaptcha_present():
                    self.logger.info("Successfully passed reCAPTCHA check")
                    return True
                
                # Look for challenge iframe
                challenge_iframes = [frame for frame in self.driver.find_elements(By.TAG_NAME, "iframe") 
                                    if "recaptcha/api2/bframe" in (frame.get_attribute("src") or "")]
                
                if challenge_iframes:
                    self.logger.info("reCAPTCHA challenge detected")
                    
                    # Try using the Buster extension if available
                    try:
                        self.logger.info("Attempting to use Buster extension for reCAPTCHA challenge...")
                        # Switch to the challenge iframe
                        self.driver.switch_to.frame(challenge_iframes[0])
                        
                        # Look for Buster button 
                        buster_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@id, 'solver-button') or contains(@class, 'solver-button')]")
                        if buster_buttons:
                            self.logger.info("Found Buster button in reCAPTCHA challenge, clicking...")
                            for button in buster_buttons:
                                try:
                                    button.click()
                                    time.sleep(5)
                                    self.logger.info("Clicked Buster button for reCAPTCHA")
                                    break
                                except:
                                    continue
                        
                        # Switch back to default content
                        self.driver.switch_to.default_content()
                    except Exception as e:
                        self.logger.error(f"Error using Buster for reCAPTCHA challenge: {e}")
                        # Ensure we're back to default content
                        self.driver.switch_to.default_content()
                
                # Wait for manual intervention for the challenge
                self.logger.info("Waiting for manual intervention to solve reCAPTCHA challenge...")
                self._wait_for_manual_solve(90)  # Give extra time for image challenges
                
                # Check if the captcha is solved after manual intervention
                if not self._is_google_recaptcha_present():
                    self.logger.info("reCAPTCHA appears to be solved after manual intervention")
                    return True
                    
            except Exception as e:
                self.logger.error(f"Error clicking reCAPTCHA checkbox: {e}")
                self.driver.switch_to.default_content()  # Make sure we get back to main frame
                self._take_debug_screenshot("recaptcha_click_error")
                
                # Wait for manual intervention
                self._wait_for_manual_solve(60)
                
                # Check if captcha is solved
                if not self._is_google_recaptcha_present():
                    self.logger.info("reCAPTCHA appears to be solved after manual intervention")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error solving Google reCAPTCHA: {e}")
            self.logger.error(traceback.format_exc())
            
            # Make sure we're back in the main frame
            try:
                self.driver.switch_to.default_content()
            except:
                pass
                
            self._take_debug_screenshot("recaptcha_error")
            return False
    
    def _solve_incapsula_captcha(self):
        """Attempt to solve Incapsula challenge."""
        try:
            self.logger.info("Detected Incapsula challenge")
            self._take_debug_screenshot("incapsula_challenge")
            
            # Refresh the page and wait
            self.logger.info("Refreshing page...")
            self.driver.refresh()
            time.sleep(5)
            
            # Check if the challenge is still present
            if "Incapsula incident ID" not in self.driver.page_source:
                self.logger.info("Successfully passed Incapsula check after refresh")
                return True
                
            # If still present, try looking for interactive elements
            try:
                # Check for checkboxes or buttons
                interactive_elements = [
                    (By.CSS_SELECTOR, "input[type='checkbox']"),
                    (By.CSS_SELECTOR, "button"),
                    (By.CSS_SELECTOR, "input[type='button']"),
                    (By.CSS_SELECTOR, "a.button")
                ]
                
                for by, selector in interactive_elements:
                    elements = self.driver.find_elements(by, selector)
                    for element in elements:
                        if element.is_displayed():
                            self.logger.info(f"Found interactive element, attempting to click: {element.get_attribute('outerHTML')}")
                            try:
                                element.click()
                                time.sleep(3)
                                
                                # Check if click helped
                                if "Incapsula incident ID" not in self.driver.page_source:
                                    self.logger.info("Successfully passed Incapsula check after clicking element")
                                    return True
                            except:
                                self.logger.warning("Failed to click interactive element")
            except Exception as e:
                self.logger.error(f"Error finding interactive elements: {e}")
                
            # Need manual intervention
            self.logger.info("Incapsula challenge still present, waiting for manual solve...")
            self._wait_for_manual_solve(60)
            
            # Check again
            if "Incapsula incident ID" not in self.driver.page_source:
                self.logger.info("Incapsula challenge appears to be solved")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error handling Incapsula challenge: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _analyze_captcha_page(self):
        """Analyze the captcha page to find clues about how to solve it."""
        try:
            self.logger.info("Analyzing captcha page structure...")
            
            # Look for forms
            forms = self.driver.find_elements(By.TAG_NAME, "form")
            for i, form in enumerate(forms):
                self.logger.info(f"Found form {i+1}: {form.get_attribute('id') or 'no-id'}")
            
            # Look for iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                src = iframe.get_attribute("src") or "no-src"
                self.logger.info(f"Found iframe {i+1}: {src}")
            
            # Look for buttons
            buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for i, button in enumerate(buttons):
                text = button.text or "no-text"
                self.logger.info(f"Found button {i+1}: {text} - {button.get_attribute('id') or 'no-id'}")
            
            # Look for checkboxes
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            for i, checkbox in enumerate(checkboxes):
                self.logger.info(f"Found checkbox {i+1}: {checkbox.get_attribute('id') or 'no-id'}")
            
            # Get the page title
            self.logger.info(f"Page title: {self.driver.title}")
            
            # Take a screenshot
            self._take_debug_screenshot("captcha_analysis")
            
        except Exception as e:
            self.logger.error(f"Error analyzing captcha page: {e}")
    
    def _take_debug_screenshot(self, name):
        """Take a debug screenshot."""
        try:
            # Create screenshots directory if it doesn't exist
            if not os.path.exists("screenshots"):
                os.makedirs("screenshots")
                
            filename = f"screenshots/captcha_{name}_{int(time.time())}.png"
            self.driver.save_screenshot(filename)
            self.logger.info(f"Saved debug screenshot to {filename}")
        except Exception as e:
            self.logger.error(f"Error taking screenshot: {e}")
    
    def _wait_for_manual_solve(self, timeout=60):
        """
        Wait for manual human intervention to solve a captcha.
        Displays a message and waits for the specified timeout.
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"MANUAL INTERVENTION REQUIRED")
        self.logger.info(f"Please solve the captcha in the browser window")
        self.logger.info(f"Waiting for {timeout} seconds...")
        self.logger.info(f"{'='*50}\n")
        
        # Print to console as well to make sure user notices
        print(f"\n{'='*50}")
        print(f"MANUAL INTERVENTION REQUIRED")
        print(f"Please solve the captcha in the browser window")
        print(f"Waiting for {timeout} seconds...")
        print(f"{'='*50}\n")
        
        time.sleep(timeout)