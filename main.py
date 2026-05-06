import asyncio
import websockets
import json
import pandas as pd
import os
from datetime import datetime

# Configuration
API_KEY = os.getenv("AIS_API_KEY")
EXCEL_FILE = "ships.xlsx"
SHIP_LIST = [
    "RED NOVA", "AZURE NOVA", "CELESTE NOVA", "ASIAN GLORY", "HORTEN",
    "CAPE TOUCAN", "CAPE KORI", "CAPE SWAN", "CAPE CYGNET", "CAPE HARRIER", "C FORCE"
]

async def get_ship_locations():
    locations = {}
    # Connect to the real-time AIS stream
    async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
        subscribe_msg = {
            "APIKey": API_KEY,
            "BoundingBoxes": [[[-90, -180], [90, 180]]] # Search the whole world
        }
        await websocket.send(json.dumps(subscribe_msg))

        print("Searching for ships... this may take a minute.")
        start_time = datetime.now()
        
        # Listen for 60 seconds to catch as many ships as possible
        while (datetime.now() - start_time).seconds < 120:
            try:
                message = json.loads(await websocket.recv())
                if message.get("MessageType") == "PositionReport":
                    ship_data = message.get("MetaData", {})
                    ship_name = ship_data.get("ShipName", "").strip().upper()
                    
                    if ship_name in SHIP_LIST:
                        pos = message["Message"]["PositionReport"]
                        locations[ship_name] = {
                            "Latitude": pos["Latitude"],
                            "Longitude": pos["Longitude"],
                            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        print(f"Found: {ship_name}")
                        
                        # Stop early if we found all 10
                        if len(locations) == len(SHIP_LIST):
                            break
            except Exception as e:
                continue
    return locations

def update_excel(data):
    if not os.path.exists(EXCEL_FILE):
        # Create the file if it somehow went missing
        df = pd.DataFrame(columns=["Ship Name", "Latitude", "Longitude", "Last Updated"])
        df["Ship Name"] = SHIP_LIST
        df.to_excel(EXCEL_FILE, index=False)

    df = pd.read_excel(EXCEL_FILE)
    
    # Update the rows for the ships we found
    for ship, details in data.items():
        idx = df[df['Ship Name'] == ship].index
        if not idx.empty:
            df.at[idx[0], 'Latitude'] = details['Latitude']
            df.at[idx[0], 'Longitude'] = details['Longitude']
            df.at[idx[0], 'Last Updated'] = details['Timestamp']
            
    df.to_excel(EXCEL_FILE, index=False)

if __name__ == "__main__":
    if not API_KEY:
        print("Error: AIS_API_KEY not found in GitHub Secrets!")
    else:
        found_data = asyncio.run(get_ship_locations())
        if found_data:
            update_excel(found_data)
            print(f"Successfully updated {len(found_data)} ships in Excel.")
        else:
            print("No ships from your list were detected in the last 60 seconds.")

