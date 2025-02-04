#Imports
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

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

# Define a route to serve the index.html file
@app.get("/")
def read_root():
    return FileResponse("static/index.html")


# Get request for the cards
@app.get("/cards/")
async def search_cards(query: str = None, format: str = None):
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")


    valid_formats = {"standard", "modern", "legacy", "pauper", "vintage", "commander", "oathbreaker", "paupercommander", "duel", "predh"}

    if format and format.lower() not in valid_formats:
        raise HTTPException(status_code=400, detail=f"Invalid format parameter. Valid options are: {', '.join(valid_formats)}")

    async with httpx.AsyncClient() as client:
        try:
            if query.startswith("creature:"):
                creature_type = query.split(":", 1)[1].strip()
                scryfall_query = f"type:creature type:{creature_type}"
            else:
                scryfall_query = query

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
    uvicorn.run(app, host="172.16.3.105", port=8000)