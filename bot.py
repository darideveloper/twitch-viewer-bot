import os
import json
import random
from time import sleep
from dotenv import load_dotenv
from scraping.web_scraping import WebScraping
from api import Api

load_dotenv ()

DEBUG = os.getenv ("DEBUG") == "true"

class Bot (WebScraping):
    """ Bot for watch Twitch stream, using cookies to login """
    
    # Control if error was send to api
    error_send = False
    
    # Manage status of the current bots
    bots_status = []
        
    def __init__ (self, username:str, cookies:list, stream:str, proxies:list,
                  headless:bool=False, width:int=1920, height:int=1080, take_screenshots:bool=False,
                  bots_running:list=[]) -> bool:
        """ Contructor of class. Start viwer bot

        Args:
            username (str): name of user to login
            cookies (list): cookies for login, generated with chrome extension "EditThisCookie"
            stream (str): user stream to watch
            proxies (list): list of proxies to use
            headless (bool, optional): use headless mode (hide browser). Defaults to False
            width (int, optional): width of browser window. Defaults to 1920
            height (int, optional): height of browser window. Defaults to 1080
            take_screenshots (bool, optional): take screenshots in headless mode. Defaults to False   
            bots_running (list, optional): list of bots already running. Defaults to [] 
        """
        
        # Save class variables and start browser
        self.username = username
        self.cookies = cookies
        self.stream = stream
        self.proxies = proxies
        self.headless = headless
        self.width = width
        self.height = height
        self.take_screenshots = take_screenshots
        self.bots_running = bots_running
        
        # Urls and status
        self.twitch_url = f"https://www.twitch.tv/"
        self.twitch_url_login = f"https://www.twitch.tv/login/"
        self.twitch_url_stream = f"https://www.twitch.tv/{self.stream}"
        self.twitch_url_pupup = f"https://player.twitch.tv/?channel={self.stream}&enableExtensions=true&muted=true&parent=twitch.tv&player=popout&quality=160p30&volume=0.5"
        self.twitch_url_chat = f"https://www.twitch.tv/popout/{self.stream}/chat?popout="
        self.status = "running"
        
        # Css selectors
        self.selectors = {
            "twitch_login_btn": 'button[data-a-target="login-button"]',
            'start-stream-btn': 'button[data-a-target*="start-watching"]',
            "offline_status": '.home .channel-status-info.channel-status-info--offline', 
            'player': '.persistent-player',           
            "play_btn": '[data-a-target="player-play-pause-button"]', 
        }
        
        # paths
        current_folder = os.path.dirname (__file__)
        self.log_path = os.path.join (current_folder, ".log")
        self.screenshots_folder = os.path.join (current_folder, "screenshots")
        self.screenshots_errors_folder = os.path.join (self.screenshots_folder, "errors")
        
        # Create folders
        os.makedirs (self.screenshots_errors_folder, exist_ok=True)
        
        # Api connection
        self.api = Api ()
        
    def __get_random_proxy__ (self) -> dict:
        """ Get random proxy from list and remove it

        Returns:
            dict: random proxy
        """
        
        # Validate if there are proxies free
        if not self.proxies:
            return False
        
        proxy = random.choice (self.proxies)
        self.proxies.remove (proxy)
        
        return proxy
    
    def auto_run (self) -> str:
        """ Auto start browser, watch stream and close browser in background

        Returns:
            bool: True if browser started, False if not
        """
        
        print (f"({self.stream} - {self.username}) Starting bot...")
        
        # Add new status to list
        Bot.bots_status.append ("loading")
        
        # Start bot and catch load page error
        started = self.__start_bot__ ()
        
        # Remove loading status from list, and add watching status
        Bot.bots_status.remove ("loading")
        Bot.bots_status.append ("watching")
        
        if started:
            
            # Save bot in list of bots running
            self.bots_running.append (self)
            
            print (f"\t({self.stream} - {self.username}) Bot running (total bots in all stream: {len (self.bots_running)})")
            
            # Delete current instance
            del self
            
        else:
            # Force end bot
            self.driver.quit ()
                
    def __load_twitch__ (self) -> bool:
        """ Try to load twitch page and validate if proxy is working

        Returns:
            bool: True if twitch load, else False
        """
        
        try:
            self.set_page ("http://ipinfo.io/json")
            self.set_page (self.twitch_url_login)
            self.refresh_selenium ()
        except:
            return False
        else:
            return True
        
    def __set_quality_mute__ (self): 
        """ Set video quality to lower and mute stream, with local storage """
        
        try:
            self.set_local_storage ("video-quality", '{"default":"160p30"}')
            self.set_local_storage ("volume", "0")
        except:
            pass
        
    def __start_bot__ (self) -> bool:
        """ Start browser and watch stream

        Returns:
            bool: True if browser started, False if not
        """
        
        # Load fot load page and find proxy
        while True:
        
            # Get random proxy for current bot
            proxy = self.__get_random_proxy__ ()
            
            # Try to start chrome
            try:
                super().__init__ (headless=self.headless, time_out=30,
                                proxy_server=proxy["host"], proxy_port=proxy["port"],
                                width=self.width, height=self.height)
                
            
            except Exception as error:
                
                error = f"\t({self.stream} - {self.username}): error opening browser ({error})"
                print (error)
                
                # Save error details
                with open (self.log_path, "a", encoding='UTF-8') as file:
                    file.write (error)
                
                # Save error in api only one time
                if not Bot.error_send:
                    self.api.log_error (error)
                    Bot.error_send = True    
                    
                quit ()            

            proxy_working = self.__load_twitch__ ()    
            
            if not proxy_working:
                error = f"\t({self.stream} - {self.username}) proxy error: {proxy['host']}:{proxy['port']}. Retrying..."
                print (error)
                
                # End if there are not proxies
                if not self.proxies:
                    print (f"\t({self.stream} - {self.username}) No more proxies available")                    
                    return False
                
                # Try again with other proxy
                continue
            
            # End loop if proxy is working
            break
            
        # Load cookies
        if self.username != "no-user":
            self.set_cookies (self.cookies)
            self.__set_quality_mute__ ()
        
        # Open stream
        try:
            self.set_page (self.twitch_url_stream)
        except Exception as e:
            error = f"\t({self.stream} - {self.username}) proxy error: {proxy['host']}:{proxy['port']} bot"
            return False
        
        # Validte session with cookies
        login_button = self.get_elems (self.selectors["twitch_login_btn"])
        if login_button and self.username != "no-user":
            error = f"\t({self.stream} - {self.username}) cookie error"
            print (error)
            
            # Disable user in backend
            self.api.disable_user (self.username)
            
            return False
        
        # Check if stream is offline
        self.refresh_selenium ()
        offline_status = self.get_elems (self.selectors["offline_status"])
        if offline_status:
            error = f"\t({self.stream} - {self.username}) stream offline"
            print (error)
            
            return False
        
        # Accept mature content
        start_stream_elem = self.get_elems (self.selectors["start-stream-btn"])
        if start_stream_elem:
            self.click_js (self.selectors["start-stream-btn"])
            sleep (5)
            self.refresh_selenium ()
    
        # Pause video
        sleep (5)
        self.refresh_selenium ()
        play_buttons = self.get_elems (self.selectors["play_btn"])
        if play_buttons:
            self.click_js (self.selectors["play_btn"])
    
        # Hide video
        player = self.get_elems (self.selectors["player"])
        if player:
            script = f"document.querySelector ('{self.selectors['player']}').style.display = 'none'"
            self.driver.execute_script (script)
        
        # Take screenshot
        if self.take_screenshots:
            screenshot_path = os.path.join(self.screenshots_folder, f"{self.stream} - {self.username}.png")
            self.screenshot (screenshot_path)
        
        return True
        
if __name__ == "__main__":
    
    # Test class
    cookies_json = """[{"id": 1, "name": "api_token", "path": "/", "value": "7ba5cab4ca07322c9803c7151483f07c", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "unspecified", "expirationDate": 1696216775.896431}, {"id": 2, "name": "auth-token", "path": "/", "value": "xvb4ei69yqexvkwenmw30vvy07hxje", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction", "expirationDate": 1682378752.10728}, {"id": 3, "name": "experiment_overrides", "path": "/", "value": "{%22experiments%22:{}%2C%22disabled%22:[]}", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction", "expirationDate": 1682378741.012931}, {"id": 4, "name": "last_login", "path": "/", "value": "2023-04-05T03:19:35Z", "domain": ".twitch.tv", "secure": false, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "unspecified", "expirationDate": 1696216775.896358}, {"id": 5, "name": "login", "path": "/", "value": "darideveloper", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction", "expirationDate": 1682378752.108888}, {"id": 6, "name": "name", "path": "/", "value": "darideveloper", "domain": ".twitch.tv", "secure": false, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "unspecified", "expirationDate": 1696216775.896309}, {"id": 7, "name": "persistent", "path": "/", "value": "733167917%3A%3Acfiyupyk2d7rg7j55kmuip4aw9807q", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": true, "sameSite": "unspecified", "expirationDate": 1696216775.896054}, {"id": 8, "name": "server_session_id", "path": "/", "value": "73d10f1f2fab4c54ac25bb5f223082d9", "domain": ".twitch.tv", "secure": true, "session": true, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction"}, {"id": 9, "name": "twilight-user", "path": "/", "value": "{%22authToken%22:%22xvb4ei69yqexvkwenmw30vvy07hxje%22%2C%22displayName%22:%22DariDeveloper%22%2C%22id%22:%22733167917%22%2C%22login%22:%22darideveloper%22%2C%22roles%22:{%22isStaff%22:false}%2C%22version%22:2}", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction", "expirationDate": 1682378752.106637}, {"id": 10, "name": "twitch.lohp.countryCode", "path": "/", "value": "MX", "domain": ".twitch.tv", "secure": false, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "unspecified", "expirationDate": 1697325955.778201}, {"id": 11, "name": "unique_id", "path": "/", "value": "KZrp6q8EJWPbyyFKHoHHu1hzVXkDXD1s", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": false, "sameSite": "no_restriction", "expirationDate": 1697325940.182774}, {"id": 12, "name": "unique_id_durable", "path": "/", "value": "KZrp6q8EJWPbyyFKHoHHu1hzVXkDXD1s", "domain": ".twitch.tv", "secure": true, "session": false, "storeId": "0", "hostOnly": false, "httpOnly": true, "sameSite": "no_restriction", "expirationDate": 1697325940.18284}]"""
    
    Bot (
        cookies=json.loads (cookies_json), 
        stream="darideveloper", 
        proxy_host="p.webshare.io", 
        proxy_port=80, 
        headless=False, 
        timeout=0.5
    )
    
    