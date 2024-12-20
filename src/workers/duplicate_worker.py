import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime
import time

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.db.database import init_db
from src.core.contact_manager import ContactManager
from src.core.app_state import app_state

async def run_duplicate_check():
    print("Duplicate worker starting...")
    
    # Initialize a separate database connection
    db_session = await init_db("sqlite+aiosqlite:///contacts.db")
    print("Database connection initialized")
    
    # Wait for web app to initialize (30 seconds max)
    for _ in range(30):
        try:
            with open("web_app_ready.txt", "r") as f:
                if f.read().strip() == "ready":
                    print("Web app is ready, starting duplicate checks")
                    break
        except FileNotFoundError:
            print("Waiting for web app to initialize...")
            await asyncio.sleep(1)
    else:
        print("Web app did not become ready in time.")
        return
    
    # Initial delay to let the web app fully load
    await asyncio.sleep(5)
    
    while True:
        try:
            print("Starting duplicate check...")
            async with db_session() as session:
                manager = ContactManager(session)
                await manager.update_duplicate_cache()
                
            status = {
                "last_update": datetime.utcnow().isoformat(),
                "status": "success"
            }
            with open("duplicate_cache_status.json", "w") as f:
                json.dump(status, f)
            
            print("Duplicate check completed successfully")
            print("Waiting 5 minutes before next check...")
            await asyncio.sleep(300)
            
        except Exception as e:
            print(f"Error in duplicate worker: {str(e)}")
            import traceback
            print(traceback.format_exc())
            print("Retrying in 60 seconds...")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_duplicate_check()) 