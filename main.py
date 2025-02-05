#Imports
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import socket

# Initialize FastAPI app
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def fetch_ip():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        print("IP Address: ", ip)
        return ip
    except:
        ip = "0.0.0.0"


@app.get("/")
def read_root():
    return FileResponse("static/index.html")

#Fetches all cards from the Scryfall API
@app.get("/fetch_all")
async def fetch_all():
    async with httpx.AsyncClient() as client:
        try:
            scryfall_response = await client.get("https://api.scryfall.com/cards/search?q=order")
            print(scryfall_response.request.url)
            scryfall_response.raise_for_status()
            print(scryfall_response)
            scryfall_data = scryfall_response.json()
            print(scryfall_data)

            cards_with_details = []
            for card in scryfall_data.get("data", []):
                card_details = {
                    "name": card.get("name"),
                    "type": card.get("type_line"),
                    "imageUrl": card.get("image_uris", {}).get("normal"),
                    "setName": card.get("set_name"),
                    "price_usd": card.get("prices", {}).get("usd", "N/A"),
                    "legalities": card.get("legalities", {}),
                }
                cards_with_details.append(card_details)

            return {"cards": cards_with_details}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch cards from Scryfall API")
        
@app.get("/cards/")
async def search_cards(query: str = None, format: str = None, mana: str = None):
    valid_formats = {"standard", "modern", "legacy", "pauper", "vintage", "commander", "oathbreaker", "paupercommander", "duel", "predh"}
    valid_mana_types = {"red", "black", "blue", "green", "white"}

    if format and format.lower() not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format parameter. Valid options are: {', '.join(valid_formats)}")

    mana_colors = []
    if mana:
        mana_colors = mana.split(',')
        for color in mana_colors:
            if color.lower() not in valid_mana_types:
                raise HTTPException(status_code=400, detail=f"Invalid mana type. Valid options are: {', '.join(valid_mana_types)}")

    async with httpx.AsyncClient() as client:
        try:
            scryfall_query = query if query else "order:name"
            if mana_colors:
                scryfall_query += " " + " ".join([f"color:{color[0].upper()}" for color in mana_colors])

            scryfall_response = await client.get(f"https://api.scryfall.com/cards/search?q={scryfall_query}")
            scryfall_response.raise_for_status()
            scryfall_data = scryfall_response.json()

            cards_with_details = []
            for card in scryfall_data.get("data", []):
                card_details = {
                    "name": card.get("name"),
                    "type": card.get("type_line"),
                    "imageUrl": card.get("image_uris", {}).get("normal"),
                    "setName": card.get("set_name"),
                    "price_usd": card.get("prices", {}).get("usd", "N/A"),
                    "legalities": card.get("legalities", {}),
                }

                if format and card_details["legalities"].get(format.lower()) != 'legal':
                    continue

                cards_with_details.append(card_details)

            return {"cards": cards_with_details}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail="Failed to fetch cards from Scryfall API")

if __name__ == "__main__":
    import uvicorn
    ip = fetch_ip()
    uvicorn.run(app, host=ip, port=8000)