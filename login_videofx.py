import os
from server.core.videofx_client import VideoFXClient

def main():
    print("==================================================")
    print("Google VideoFX Authentication Setup")
    print("==================================================")
    print("A browser window will now open. Please log into your Google Account.")
    print("Once you are logged in and can see the VideoFX prompt area, close the browser window.")
    
    profile_path = os.path.join(os.path.dirname(__file__), "videofx_profile")
    client = VideoFXClient(profile_path)
    client.login_if_needed()
    
    print("==================================================")
    print("Setup complete! Your session is now saved.")
    print("The pipeline can now generate videos using Google VideoFX autonomously in the background.")
    print("==================================================")

if __name__ == "__main__":
    main()
