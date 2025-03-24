import io
import os
import json
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use("AGG")
import matplotlib.pyplot as plt  # Not used for charts now, but retained if needed

from dotenv import load_dotenv
load_dotenv()

import httpx

# --- Plotly Imports for Modern Charts ---
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, NextPageTemplate, HRFlowable)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Register Roboto Fonts ===
font_dir = os.path.abspath("./fonts")
fonts = {
    "Roboto-Thin": "Roboto-Thin.ttf",
    "Roboto-Light": "Roboto-Light.ttf",
    "Roboto-Regular": "Roboto-Regular.ttf",
    "Roboto-Medium": "Roboto-Medium.ttf",
    "Roboto-Bold": "Roboto-Bold.ttf"
}
for name, filename in fonts.items():
    path = os.path.join(font_dir, filename)
    if os.path.exists(path):
        pdfmetrics.registerFont(TTFont(name, path))
    else:
        print(f"Font file not found: {path}")

# === Custom Styles ===
custom_styles = {
    "Title": ParagraphStyle("Title", fontName="Roboto-Bold", fontSize=26, textColor=colors.white,
                            alignment=TA_CENTER, spaceAfter=20),
    "Heading1": ParagraphStyle("Heading1", fontName="Roboto-Bold", fontSize=18,
                               textColor=colors.HexColor("#a6192e"), spaceAfter=12),
    "Heading2": ParagraphStyle("Heading2", fontName="Roboto-Medium", fontSize=14,
                               textColor=colors.white, spaceAfter=8),
    "Normal": ParagraphStyle("Normal", fontName="Roboto-Light", fontSize=10.5,
                             textColor=colors.white, leading=14),
    "AI": ParagraphStyle("AI", fontName="Roboto-Light", fontSize=10,
                         textColor=colors.HexColor("#CCCCCC"),
                         backColor=colors.HexColor("#1e1e1e"), spaceBefore=6, spaceAfter=6,
                         leftIndent=6, rightIndent=6),
    "TOC": ParagraphStyle("TOC", fontName="Roboto-Regular", fontSize=11,
                          textColor=colors.HexColor("#a6192e"), spaceAfter=4),
}

# === Data Formatting Functions ===
def formatAthenaData(report_data):
    start = report_data.date_start
    end = report_data.date_end
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day)
    report_dict = {
        "date_start": str(datetime(start.year, start.month, start.day)),
        "date_end": str(datetime(end.year, end.month, end.day)),
        "industry": [industry.lower().replace(" ", "_") for industry in report_data.industry],
        "continents": [continent.replace("", "") for continent in report_data.continents],
        "alerts": report_data.alerts,
        "devices": [device.lower().replace(" ", "_") for device in report_data.devices],
        "resolutions": [resolution.lower().replace(" ", "_") for resolution in report_data.resolutions],
        "events": [event.lower().replace(" ", "_") for event in report_data.events],
    }
    return report_dict

def formatOracleData(report_data):
    end = report_data.date_end
    end = datetime(end.year, end.month, end.day)
    report_dict = {
        "resolution_reason": [resolution.lower().replace(" ", "_") for resolution in report_data.resolutions],
        "device_type": [device.lower().replace(" ", "_") for device in report_data.devices],
        "sensor_type": report_data.alerts,
        "event_type": [event.lower().replace(" ", "_") for event in report_data.events],
        "industry": [industry.lower().replace(" ", "_") for industry in report_data.industry],
        "continent": [continent.replace("", "") for continent in report_data.continents],
        "date_end": str(datetime(end.year, end.month, end.day)),
    }
    return report_dict

# === Data Fetching Functions ===
def getAthenaData(report_data) -> dict:
    ATHENA_URL = os.getenv("ATHENA_URL").rstrip("/")
    with httpx.Client() as client:
        try:
            report_dict = formatAthenaData(report_data)
            response = client.post(f"{ATHENA_URL}/report_data", json=report_dict, timeout=60)
            response.raise_for_status()
            response_dict = json.loads(response.text)
        except Exception as e:
            print("ERROR in getAthenaData:")
            print(e)
            raise e
    return response_dict

def getOracleData(report_data) -> dict:
    ORACLE_URL = os.getenv("ORACLE_URL").rstrip("/")
    with httpx.Client() as client:
        try:
            report_dict = formatOracleData(report_data)
            print("REQUEST:", report_dict)
            response = client.post(f"{ORACLE_URL}/report_data", json=report_dict, timeout=60)
            response.raise_for_status()
            print("RESPONSE:")
            response_dict = json.loads(response.text)
            print(response_dict)
        except Exception as e:
            print("ERROR in getOracleData:")
            print(e)
            response_dict = {}
    return response_dict

# === Chart Generation Functions using Plotly for Modern, Sleek Charts ===
def create_bar_chart(data, labels, title, x_label, y_label):
    n = len(data)
    # Generate a red-based palette using Plotly's Reds scale
    palette = []
    if n == 1:
        palette = ["#a6192e"]
    else:
        for i in range(n):
            col = px.colors.sample_colorscale("Reds", i/(n-1))[0]
            palette.append(col)
    fig = go.Figure(data=[go.Bar(x=labels, y=data, marker_color=palette)])
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="#171717",
        plot_bgcolor="#171717",
        font=dict(color="white"),
    )
    img_bytes = pio.to_image(fig, format="png", scale=2)
    return io.BytesIO(img_bytes)

def create_multi_line_chart(x_values, y_series, title, x_label, y_label):
    fig = go.Figure()
    for label, y_values in y_series.items():
        fig.add_trace(go.Scatter(x=x_values, y=y_values, mode="lines+markers", name=label,
                                 line=dict(width=2)))
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        template="plotly_dark",
        paper_bgcolor="#171717",
        plot_bgcolor="#171717",
        font=dict(color="white"),
    )
    img_bytes = pio.to_image(fig, format="png", scale=2)
    return io.BytesIO(img_bytes)

def create_line_chart(data_points):
    x_values, y_values = zip(*data_points)
    fig = go.Figure(data=go.Scatter(x=x_values, y=y_values, mode="lines+markers", line=dict(width=2)))
    fig.update_layout(
        title="Line Chart",
        xaxis_title="X-Axis (Time)",
        yaxis_title="Y-Axis (Values)",
        template="plotly_dark",
        paper_bgcolor="#171717",
        plot_bgcolor="#171717",
        font=dict(color="white"),
    )
    img_bytes = pio.to_image(fig, format="png", scale=2)
    return io.BytesIO(img_bytes)

# === Data Aggregation & Preparation Functions ===
def prepare_multiline_grouped_data(grouped_data_by_date):
    """
    Converts date-keyed data into (x_values, y_series) suitable for multi-line charts.
    """
    keys = set()
    for values in grouped_data_by_date.values():
        keys.update(values.keys())
    normalized_grouped_data = {}
    for date, values in grouped_data_by_date.items():
        normalized_values = {}
        for k, v in values.items():
            normalized_key = "None" if k == "null" else k
            normalized_values[normalized_key] = v
        normalized_grouped_data[date] = normalized_values
    if "null" in keys:
        keys.remove("null")
        keys.add("None")
    x_values = sorted(normalized_grouped_data.keys())
    y_series = {k: [] for k in keys}
    for date in x_values:
        day_data = normalized_grouped_data.get(date, {})
        for k in keys:
            y_series[k].append(day_data.get(k, 0))
    return x_values, y_series

def aggregate_grouped_values(grouped_data_by_date):
    """
    Aggregates values by key across all dates.
    """
    aggregated = defaultdict(int)
    for day_data in grouped_data_by_date.values():
        for key, value in day_data.items():
            aggregated[key] += value
    return dict(aggregated)

# === Custom Flowable for Charts ===
class ChartImage(Image):
    def __init__(self, chart_func, width=400, height=250, *chart_args, **chart_kwargs):
        img_buffer = chart_func(*chart_args, **chart_kwargs)
        img_buffer.seek(0)
        super().__init__(img_buffer, width=width, height=height)

# === PDF Page Layout Functions ===
def add_background(canvas, doc):
    width, height = doc.pagesize
    canvas.setFillColor(colors.HexColor("#171717"))
    canvas.rect(0, 0, width, height, fill=1)
    canvas.setFillColor(colors.HexColor("#a6192e"))
    canvas.rect(0, height - 5, width, 5, fill=1)
    canvas.setFont("Roboto-Light", 9)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(width / 2, 15, f"Page {doc.page}")

def draw_cover(canvas, doc, report_data):
    width, height = doc.pagesize
    canvas.setFillColor(colors.black)
    canvas.rect(0, 0, width, height, fill=1)
    canvas.setFillColor(colors.HexColor("#a6192e"))
    canvas.rect(0, height - 5, width, 5, fill=1)
    logo_path = "./assets/blackline-horizon.png"
    # Increase logo width by 1.5x (300 vs. 200)
    canvas.drawImage(logo_path, width/2 - 150, height - 250, width=300, height=80, mask='auto')
    canvas.setFont("Roboto-Bold", 32)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(width/2, height - 320, "Blackline Horizon")
    canvas.setFont("Roboto-Light", 18)
    canvas.drawCentredString(width/2, height - 355, "Automated Alert Analytics Report")
    canvas.setFont("Roboto-Light", 12)
    generated_on = datetime.now().strftime("%B %d, %Y")
    canvas.drawCentredString(width/2, height - 385, f"Generated: {generated_on}")

# === Main PDF Generation Function ===
def generate_pdf(report_data):
    buffer = io.BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=letter, title=report_data.title)
    
    # Define frames and page templates:
    cover_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="cover")
    cover_template = PageTemplate(id="Cover", frames=cover_frame,
                                  onPage=lambda c, d: draw_cover(c, d, report_data))
    
    body_frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height - 0.5*inch, id="body")
    body_template = PageTemplate(id="Body", frames=body_frame, onPage=add_background)
    
    doc.addPageTemplates([cover_template, body_template])
    
    elements = []
    # Start with cover page then switch to Body template:
    elements.append(NextPageTemplate("Body"))
    elements.append(PageBreak())
    
    # Table of Contents
    toc = TableOfContents()
    toc.levelStyles = [custom_styles["TOC"]]
    elements.append(Paragraph("Table of Contents", custom_styles["Heading1"]))
    elements.append(toc)
    elements.append(PageBreak())
    
    # Fetch Data
    athena_data = getAthenaData(report_data)
    oracle_data = getOracleData(report_data)
    oracle_blank = not bool(oracle_data)
    
    # --- Core Analytics Section ---
    elements.append(Paragraph("Introduction", custom_styles["Heading1"]))
    intro_text = (
        "This report provides an in-depth analysis of alert data collected over the past year. "
        "It examines system performance, identifies trends, and highlights areas for improvement. "
        "The following analytics sections offer a detailed look at various aspects of the data."
    )
    elements.append(Paragraph(intro_text, custom_styles["Normal"]))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph("Alert Count Over Time", custom_styles["Heading2"]))
    elements.append(Paragraph(
        "The line graph below depicts the overall trend of alerts over the entire date range. "
        "It helps identify periods of high activity which may correlate with system events or external factors.",
        custom_styles["Normal"]
    ))
    dates = athena_data["time_series_overall"]["date_created"]
    alert_counts = athena_data["time_series_overall"]["alert_count"]
    elements.append(ChartImage(create_multi_line_chart, 500, 350, dates, {"Alert Count": alert_counts},
                                 "Alert Count Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "This modern chart uses a clean dark theme with red accents to emphasize spikes and troughs in alert activity. "
        "Such insights are crucial for timely operational adjustments.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Divider before AI Section ---
    if not oracle_blank:
        elements.append(HRFlowable(width="100%", thickness=1, lineCap='round',
                                   color=colors.HexColor("#a6192e"), spaceBefore=12, spaceAfter=12))
        elements.append(Paragraph("The following section contains AI-generated forecasts and insights, "
                                  "providing predictive analysis beyond the core analytics.", custom_styles["Normal"]))
        elements.append(PageBreak())
    
    # --- AI Generated Forecast Section (if available) ---
    if not oracle_blank:
        elements.append(Paragraph("Past Month & Next Month Analysis", custom_styles["Heading1"]))
        elements.append(Paragraph(
            "This section compares actual alert data from the past month with AI-generated forecasts. "
            "The analysis helps to identify discrepancies and refine predictive models.",
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 12))
        
        # Past Month Bar Chart
        elements.append(Paragraph("Past Month Alert Comparison", custom_styles["Heading2"]))
        elements.append(Paragraph(
            "The bar chart below contrasts the actual alert counts from the past 4 weeks with the AI predictions. "
            "The visual representation aids in quickly identifying over- or under-prediction trends.",
            custom_styles["Normal"]
        ))
        actual_last_4w = oracle_data['actual_last_4w']
        monthly_alerts = [actual_last_4w, oracle_data['predicted_last_4w']]
        monthly_alerts_labels = ['Actual Last 4 Weeks', 'Predicted Last 4 Weeks']
        elements.append(ChartImage(create_bar_chart, 400, 300, monthly_alerts, monthly_alerts_labels,
                                     "Past Month Alert Comparison", "Category", "Alert Count"))
        elements.append(Paragraph(
            "The modern bar chart employs shades of red to differentiate between actual and predicted values, "
            "providing a clear and sleek visual comparison.",
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 12))
        
        # Next Month Forecast
        elements.append(Paragraph("Next Month Forecast", custom_styles["Heading2"]))
        trend = "increase" if oracle_data['predicted_next_4w'] > actual_last_4w else "decrease"
        elements.append(Paragraph(
            f"The AI model projects an {trend} in alert counts for the next four weeks. "
            "This forecast acts as an early warning system, enabling proactive resource allocation.",
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 6))
        forecast_table = Table([
            ["Expected Alerts"],
            [str(oracle_data['predicted_next_4w'])]
        ], style=[("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                  ("ALIGN", (0,0), (-1,-1), "CENTER")])
        elements.append(forecast_table)
        elements.append(Paragraph(
            "The forecast table succinctly summarizes the AI prediction, complementing the visual data presented above.",
            custom_styles["Normal"]
        ))
        elements.append(PageBreak())
    
    # --- Resolutions Analysis Section ---
    elements.append(Paragraph("Resolutions Analysis", custom_styles["Heading1"]))
    resolutions = athena_data['grouped_data']['resolution_reason']
    resolutions_grouped = aggregate_grouped_values(resolutions)
    elements.append(ChartImage(create_bar_chart, 500, 500, list(resolutions_grouped.values()), list(resolutions_grouped.keys()),
                                 "Resolution Analysis", "Resolution Type", "Alerts"))
    elements.append(Paragraph(
        "This bar chart highlights the distribution of resolution types. The use of a modern dark theme with red accents "
        "makes it easy to distinguish among the different categories.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    x_vals, y_series = prepare_multiline_grouped_data(resolutions)
    elements.append(ChartImage(create_multi_line_chart, 500, 500, x_vals, y_series,
                                 "Resolution Trends Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "The multi-line chart illustrates how resolution trends evolve over time, offering insights into system responsiveness.",
        custom_styles["Normal"]
    ))
    elements.append(PageBreak())
    
    # --- Device Analysis Section ---
    elements.append(Paragraph("Device Analysis", custom_styles["Heading1"]))
    devices = athena_data['grouped_data']['device_type']
    devices_grouped = aggregate_grouped_values(devices)
    elements.append(ChartImage(create_bar_chart, 500, 400, list(devices_grouped.values()), list(devices_grouped.keys()),
                                 "Device Analysis", "Device Type", "Alerts"))
    elements.append(Paragraph(
        "This chart presents alert distributions across various device types, using sleek modern styling for clear comparison.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(devices)
    elements.append(ChartImage(create_multi_line_chart, 500, 500, x_vals, y_series,
                                 "Device Trends Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "The line chart further highlights how device-related alerts vary over the selected period.",
        custom_styles["Normal"]
    ))
    elements.append(PageBreak())
    
    # --- Sensor Analysis Section ---
    elements.append(Paragraph("Sensor Analysis", custom_styles["Heading1"]))
    sensors = athena_data['grouped_data']['sensor_type']
    sensors_grouped = aggregate_grouped_values(sensors)
    elements.append(ChartImage(create_bar_chart, 500, 450, list(sensors_grouped.values()), list(sensors_grouped.keys()),
                                 "Sensor Analysis", "Sensor Type", "Alerts"))
    elements.append(Paragraph(
        "This chart displays sensor-specific alert counts in a modern format, using shades of red to emphasize differences.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(sensors)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series,
                                 "Sensor Trends Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "The multi-line graph showcases sensor trends over time, adding further context to the data.",
        custom_styles["Normal"]
    ))
    elements.append(PageBreak())
    
    # --- Industry Analysis Section ---
    elements.append(Paragraph("Industry Analysis", custom_styles["Heading1"]))
    industry = athena_data['grouped_data']['industry']
    industry_grouped = aggregate_grouped_values(industry)
    elements.append(ChartImage(create_bar_chart, 500, 575, list(industry_grouped.values()), list(industry_grouped.keys()),
                                 "Industry Analysis", "Industry", "Alerts"))
    elements.append(Paragraph(
        "This chart segments alert data by industry, employing a modern aesthetic for enhanced clarity.",
        custom_styles["Normal"]
    ))
    x_vals, y_series = prepare_multiline_grouped_data(industry)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series,
                                 "Industry Trends Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "The line graph indicates industry-specific trends, providing valuable insight for targeted improvements.",
        custom_styles["Normal"]
    ))
    elements.append(PageBreak())
    
    # --- Event Analysis Section ---
    elements.append(Paragraph("Event Analysis", custom_styles["Heading1"]))
    event = athena_data['grouped_data']['event_type']
    event_grouped = aggregate_grouped_values(event)
    elements.append(ChartImage(create_bar_chart, 500, 500, list(event_grouped.values()), list(event_grouped.keys()),
                                 "Event Analysis", "Event Type", "Alerts"))
    elements.append(Paragraph(
        "This bar chart offers an overview of alert events, presented in a modern and sleek format.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(event)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series,
                                 "Event Trends Over Time", "Date", "Alerts"))
    elements.append(Paragraph(
        "The multi-line chart shows how event alerts change over time, supporting deeper analysis.",
        custom_styles["Normal"]
    ))
    elements.append(PageBreak())
    
    # --- Conclusion Section ---
    elements.append(Paragraph("Conclusion", custom_styles["Heading1"]))
    conclusion_text = (
        "In summary, the alert trends identified over the past year indicate several recurring patterns. "
        "The core analytics provide actionable insights while the AI-generated forecasts offer a predictive outlook. "
        "Both sections underscore the importance of proactive monitoring and continuous system improvement."
    )
    elements.append(Paragraph(conclusion_text, custom_styles["Normal"]))
    elements.append(Spacer(1, 12))
    
    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()

# End of generatepdf.py
