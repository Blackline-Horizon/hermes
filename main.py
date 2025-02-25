from typing import Union, List
import uvicorn
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, select, schema, Table, MetaData
from sqlalchemy.orm import sessionmaker
from fastapi.responses import PlainTextResponse, StreamingResponse
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

from io import BytesIO
from reportlab.pdfgen import canvas

from schemas import ReportResponse, ReportCreate
from models import Base, Report, PDFFile

# Load environment variables from the .env file
load_dotenv()

# Get values from environment variables
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", 3003))
DATABASE_URL = os.getenv("DATABASE_URL")

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

# Create synchronous engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
)

# Create sessionmaker with autoflush enabled
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=True,
    bind=engine
)

@app.on_event("startup")
def startup_event():
    # Create the 'report' schema if it doesn't exist
    from sqlalchemy import text
    with engine.connect() as conn:
        if not engine.dialect.has_schema(conn, "report"):
            try:
                conn.execute(schema.CreateSchema("report"))
                conn.commit()
            except Exception as e:
                print(e)
    # Create tables within the 'report' schema
    Base.metadata.create_all(bind=engine)


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Reporting from Hermes Service!"


def generate_pdf(title: str, content: str) -> bytes:
    """Generates a simple PDF and returns it as binary data."""
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, f"Title: {title}")
    p.drawString(100, 730, f"Content: {content}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.read()

@app.post("/report", response_model=ReportResponse)
def create_report(report_data: ReportCreate):
    # return { 'id':2,'title': "Testing File 2",'created_at': "2002-10-22",'industry': "Oil & Gas",'pdf_id': 2}
    db = SessionLocal()
    pdf_data = generate_pdf(report_data.title, report_data.industry)

    # Store PDF first
    new_pdf = PDFFile(pdf_data=pdf_data)
    db.add(new_pdf)
    db.commit()
    db.refresh(new_pdf)

    new_report = Report(
        title=report_data.title,
        created_at = report_data.created_at,
        industry=report_data.industry,
        location=report_data.location, 
        alerts=report_data.alerts,
        pdf_id=new_pdf.id,
        username=report_data.username 
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report  

@app.get("/reports", response_model=List[ReportResponse])
def list_reports(username:str):
    db = SessionLocal()
    statement = select(Report).filter_by(username=username)
    reports = db.execute(statement=statement).scalars().all()
    # reports = [{ 'id':1,'title': "Testing File 1",'created_at': "2002-10-22",'industry': "Transportation",'pdf_id': 1},
    #            { 'id':2,'title': "Testing File 2",'created_at': "2002-10-22",'industry': "Oil & Gas",'pdf_id': 2}]
    return reports if reports else [] 

@app.get("/pdf_report")
def get_pdf_report(pdf_id: int):
    db = SessionLocal()
    # Fetch PDF data from database
    statement = select(PDFFile).where(PDFFile.id == pdf_id)
    pdf = db.execute(statement).scalars().first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    # Convert binary data to BytesIO stream
    pdf_stream = BytesIO(pdf.pdf_data)
    # Return the PDF file as a response
    return StreamingResponse(pdf_stream, media_type="application/pdf")

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