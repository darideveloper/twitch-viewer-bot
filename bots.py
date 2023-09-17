import os
import random
from time import sleep
from threading import Thread
from api import Api
from bot import Bot
from dotenv import load_dotenv

load_dotenv ()

DEBUG = os.getenv ("DEBUG") == "true"
DEBUG_USERS = os.getenv ("DEBUG_USERS")
if DEBUG_USERS and DEBUG_USERS != "":
    DEBUG_USERS = DEBUG_USERS.split (",")
DIABLE_THREADS = os.getenv ("DIABLE_THREADS") == "true"

class BotsManager ():
    """ Watch Twitch stream with a multiple users, using cookies to login """
    
    def __init__ (self):     
        
        # Connect to api
        api = Api ()
        self.api = api
        
        self.streams = api.get_streams ()
        
        # Show error and stop when no stream founnd
        if not self.streams:
            print (f"No streams found.")
            return None
        
        self.users = api.get_users ()
        self.settings = api.get_settings ()
        self.proxies = api.get_proxies ()
        
        # Separator
        print ()
                
        bots_running = {}
        for stream in self.streams:
            bots_running[stream] = []
            
        # Headless mode
        headless = self.settings["headless"]
        if DEBUG:
            # Force headless mode
            headless = False
        
        # Copy bots for each streamer
        stream_users =  [self.users.copy (), self.users.copy ()]
        
        # Create bots to each stream
        current_stream_id = 0
        bots_total = self.settings["viwers-stream"]*len(self.streams)
        current_bots = 0
        for _ in range(bots_total):
            
            # Get current stream
            stream = self.streams[current_stream_id]
            
            if not self.proxies:
                continue
  
            # Get random user
            if stream_users[current_stream_id]:
                user = random.choice (stream_users[current_stream_id])
                stream_users[current_stream_id].remove (user)
                
                # Only start debug users
                if DEBUG_USERS and user["name"] not in DEBUG_USERS:
                    continue
                
            else:
                break           
            
            # Wait random time before create bot
            sleep (random.randint (1, 10))
            
            try:
                bot = Bot (user["name"], user["cookies"], stream, self.proxies,
                        headless=headless, width=self.settings["window-width"], height=self.settings["window-height"],
                        take_screenshots=self.settings["screenshots"], bots_running=bots_running[stream])
            except Exception as e:
                error = f"{self.stream} - {self.username}: Error creating bot instance: {str(e)}\n"
                print (error)
                
                # Save error details
                with open (self.log_path, "a", encoding='UTF-8') as file:
                    file.write (error)
                
                # Save error in api
                self.api.log_error (error)
                
                quit ()
                
            else:
                thread = Thread (target=self.__auto_run_bot__, args=(bot,))
                thread.start ()
                
                # Wait random time 
                sleep (random.randint (1, 10)/10)
                
                # Increase current bots
                current_bots += 1
                
                # Start bot in a thread if no error
                if DIABLE_THREADS:
                    continue
                
                # End of threads, wait 1 minute
                elif current_bots == self.settings["threads"]:
                    
                    # Change stream
                    current_stream_id += 1
                    if current_stream_id == len(self.streams):
                        current_stream_id = 0
                    
                    # Wait before next bots
                    current_bots = 0
                    
                    # Wait until all bots ends running
                    status = Bot.bots_status
                    while not status or "loading" in status:
                        sleep (5)
                        
        # Infinity loop to watch stream
        print (">>>>>>>>>> All bots launched...")
        while True:
            sleep (60)
    
    def __auto_run_bot__ (self, bot:Bot):
        """ Run single bot instance, with threading

        Args:
            bot (Bot): bot instance
        """
        
        # Random delay to start
        delay = random.randint (1, 30)/5
        sleep (delay)
        
        bot.auto_run ()
        
if __name__ == "__main__":
    # Test class
    
    BotsManager ()