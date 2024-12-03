from typing import Union
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

# Load environment variables from the .env file
load_dotenv()

# Get values from environment variables
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 3003))

# URLs for Oracle and Athena services
ORACLE_URL = os.getenv("ORACLE_URL", "http://127.0.0.1:3002")
ATHENA_URL = os.getenv("ATHENA_URL", "http://127.0.0.1:3001")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Reporting from Hermes Service!"


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/alerts", response_model=dict)
async def get_alerts(latitude: float, longitude: float, radius: float = 5):
    """
    Fetch alerts/insights from Athena service.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ATHENA_URL}/insights/alerts",
                json={"latitude": latitude, "longitude": longitude, "radius": radius},
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error contacting Athena service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/predictions", response_model=dict)
async def get_predictions():
    """
    Fetch dummy predictions from Oracle service.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ORACLE_URL}/predictions")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error contacting Oracle service: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/combined", response_model=dict)
async def get_combined(latitude: float, longitude: float, radius: float = 5):
    """
    Fetch alerts from Athena and predictions from Oracle, then combine them.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Fetch alerts
            alerts_response = await client.post(
                f"{ATHENA_URL}/insights/alerts",
                json={"latitude": latitude, "longitude": longitude, "radius": radius},
            )
            alerts_response.raise_for_status()
            alerts = alerts_response.json()

            # Fetch predictions
            predictions_response = await client.get(f"{ORACLE_URL}/predictions")
            predictions_response.raise_for_status()
            predictions = predictions_response.json()

        # Combine results
        combined_response = {
            "alerts": alerts,
            "predictions": predictions,
        }
        return combined_response

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error contacting services: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=response.status_code, detail=response.text)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, log_level="info")