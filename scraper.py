import os
import time
from distutils.dir_util import copy_tree
from scraping_manager.automate import WebScraping

class TwitchBot (WebScraping):
    """"""
    
    def __init__ (self, user, password, stream_link):
        """ Constructor for TwitchBot

        Args:
            user (str): twitch user for login
            password (str): twitch password for login
            stream_link (str): twitch stream link
        """
        
        self.user = user
        self.password = password
        self.stream_link = stream_link
        self.login_link = "https://www.twitch.tv/login"
        self.chrome_folder = os.path.join (os.path.dirname(__file__), "chrome_data", user)
        self.chrome_default_folder = os.path.join (os.path.dirname(__file__), "chrome_data", "default")
        
        self.selectors = {
            "login_user": "#login-username",
            "login_password": "#password-input", 
            "login_submit": 'button[data-a-target="passport-login-button"]'
        }
        
        # Create  chrome folder if not exists
        self.__create_chrome_folder__ ()
        
        # Open browser
        super().__init__ (chrome_folder=self.chrome_folder)
        
    def __create_chrome_folder__ (self):
        """ Create chrome folder for the current user, if not exists """
        
        if not os.path.isdir (self.chrome_folder):
            print (f"Preparing for the user {self.user}, please wait...")
            copy_tree (self.chrome_default_folder, self.chrome_folder)
            time.sleep (5)
        
    def __login__ (self, wait_login=True):
        """ Login to twitch account

        Args:
            wait_login (bool, optional): Wait after submit email and password. Defaults to True.
        """
        
        # Load login page
        self.set_page (self.login_link)
        self.refresh_selenium ()
        
        current_page = self.driver.current_url
        if current_page == self.login_link:
            
            # Clean inputs
            self.clean_input (self.selectors["login_user"])
            self.clean_input (self.selectors["login_password"])
            self.refresh_selenium ()
            
            # Login if itys required
            self.send_data (self.selectors["login_user"], self.user)
            self.send_data (self.selectors["login_password"], self.password)
            self.click_js (self.selectors["login_submit"])
            
            # Wait for manual login required
            if wait_login:
                input (f"Logging in for user {self.user}. Press enter to continue...")
                
        else:
            
            print (f"user {self.user} already logged in")
        
    def auto_run (self):
        
        self.__login__ ()
        
        print ("running...")
        time.sleep (300)