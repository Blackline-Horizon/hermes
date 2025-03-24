import io
import os
import json
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use("AGG")
import matplotlib.pyplot as plt  # Retained if needed

from dotenv import load_dotenv
load_dotenv()

import httpx

# --- Plotly Imports for Modern Charts ---
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, PageBreak, NextPageTemplate, HRFlowable, Flowable)
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

# === Custom Styles (Red & White Theme) ===
custom_styles = {
    "Title": ParagraphStyle("Title", fontName="Roboto-Bold", fontSize=28, textColor=colors.HexColor("#a6192e"),
                            alignment=TA_CENTER, spaceAfter=20),
    "Heading1": ParagraphStyle("Heading1", fontName="Roboto-Bold", fontSize=24,
                               textColor=colors.HexColor("#a6192e"), spaceAfter=24),  # increased spaceAfter
    "Heading2": ParagraphStyle("Heading2", fontName="Roboto-Medium", fontSize=18,
                               textColor=colors.HexColor("#a6192e"), spaceAfter=16),  # increased spaceAfter
    "Normal": ParagraphStyle("Normal", fontName="Roboto-Light", fontSize=12,
                             textColor=colors.black, leading=16),
    "AI": ParagraphStyle("AI", fontName="Roboto-Light", fontSize=10,
                         textColor=colors.black,
                         backColor=colors.HexColor("#f0f0f0"), spaceBefore=6, spaceAfter=6,
                         leftIndent=6, rightIndent=6),
    "TOC": ParagraphStyle("TOC", fontName="Roboto-Regular", fontSize=11,
                          textColor=colors.HexColor("#a6192e"), spaceAfter=4),
}

# === Chart Generation Functions using Plotly (Red & White Theme) ===
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
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
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
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
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
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="black"),
    )
    img_bytes = pio.to_image(fig, format="png", scale=2)
    return io.BytesIO(img_bytes)

# === Custom Flowable for Charts with Adjusted Dimensions ===
class ChartImage(Image):
    def __init__(self, chart_func, width=400, height=300, *chart_args, **chart_kwargs):
        img_buffer = chart_func(*chart_args, **chart_kwargs)
        img_buffer.seek(0)
        super().__init__(img_buffer, width=width, height=height)

# === Section Cover Flowable for Separating Sections ===
class SectionCover(Flowable):
    def __init__(self, title):
        super().__init__()
        self.title = title

    def wrap(self, availWidth, availHeight):
        return availWidth, availHeight

    def draw(self):
        canvas = self.canv
        width, height = canvas._pagesize
        # White background
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, width, height, fill=1)
        # Red header rectangle at the top
        canvas.setFillColor(colors.HexColor("#a6192e"))
        canvas.rect(0, height - 50, width, 50, fill=1)
        # Draw the section title centered with a slight upward offset
        canvas.setFillColor(colors.HexColor("#a6192e"))
        canvas.setFont("Roboto-Bold", 36)
        canvas.drawCentredString(width/2, height/2 + 50, self.title)

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

# === PDF Page Layout Functions ===
def add_background(canvas, doc):
    width, height = doc.pagesize
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1)
    canvas.setFillColor(colors.HexColor("#a6192e"))
    canvas.rect(0, height - 50, width, 50, fill=1)
    canvas.setFont("Roboto-Light", 9)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(width / 2, 15, f"Page {doc.page}")

def draw_cover(canvas, doc, report_data):
    width, height = doc.pagesize
    # White background cover page with red header
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1)
    canvas.setFillColor(colors.HexColor("#a6192e"))
    canvas.rect(0, height - 50, width, 50, fill=1)
    logo_path = "./assets/blackline-horizon.png"
    canvas.drawImage(logo_path, width/2 - 150, height - 250, width=300, height=80, mask='auto')
    # Removed "Blackline Horizon" text since the logo suffices
    canvas.setFont("Roboto-Light", 18)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(width/2, height - 320, "Automated Alert Analytics Report")
    canvas.setFont("Roboto-Light", 12)
    generated_on = datetime.now().strftime("%B %d, %Y")
    canvas.drawCentredString(width/2, height - 350, f"Generated: {generated_on}")

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
    
    # --- TOC Setup ---
    toc = TableOfContents()
    toc.levelStyles = [custom_styles["TOC"]]
    
    elements = []
    # Start with cover page then switch to Body template:
    elements.append(NextPageTemplate("Body"))
    elements.append(PageBreak())
    
    # Table of Contents
    elements.append(Paragraph("Table of Contents", custom_styles["Heading1"]))
    elements.append(toc)
    elements.append(PageBreak())
    
    # --- Add Section Cover for Analytics (centered) ---
    elements.append(SectionCover("Analytics Section"))
    elements.append(PageBreak())
    
    # --- Introduction Section with Increased Spacing ---
    elements.append(Paragraph("Introduction", custom_styles["Heading1"]))
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "This report provides an in-depth analysis of alert data collected over the past year. "
        "It examines system performance, identifies trends, and highlights areas for improvement. "
        "The following sections break down the data from various angles and provide insights to guide future actions.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 24))
    
    # --- Alert Count Over Time ---
    # Fetch Athena and Oracle data first:
    athena_data = getAthenaData(report_data)
    oracle_data = getOracleData(report_data)
    oracle_blank = not bool(oracle_data)
    
    dates = athena_data.get("time_series_overall", {}).get("date_created", [])
    alert_counts = athena_data.get("time_series_overall", {}).get("alert_count", [])
    
    elements.append(Paragraph("Alert Count Over Time", custom_styles["Heading2"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "The line graph below highlights fluctuations in alert volume over time, helping to quickly identify periods of high activity that may warrant further investigation.",
        custom_styles["Normal"]
    ))
    elements.append(ChartImage(create_multi_line_chart, 400, 250, dates, {"Alert Count": alert_counts},
                                 "Alert Count Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Resolutions Analysis Section ---
    elements.append(Paragraph("Resolutions Analysis", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "This section breaks down the types of resolutions applied to alerts. The charts below display aggregate counts and trends over time, helping assess the effectiveness of various resolution strategies.",
        custom_styles["Normal"]
    ))
    resolutions = athena_data['grouped_data']['resolution_reason']
    resolutions_grouped = aggregate_grouped_values(resolutions)
    elements.append(ChartImage(create_bar_chart, 400, 400, list(resolutions_grouped.values()), list(resolutions_grouped.keys()),
                                 "Resolution Analysis", "Resolution Type", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(resolutions)
    elements.append(ChartImage(create_multi_line_chart, 400, 400, x_vals, y_series,
                                 "Resolution Trends Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Device Analysis Section ---
    elements.append(Paragraph("Device Analysis", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "This section examines alert distributions across different device types, helping identify areas where targeted maintenance or optimization may be needed.",
        custom_styles["Normal"]
    ))
    devices = athena_data['grouped_data']['device_type']
    devices_grouped = aggregate_grouped_values(devices)
    elements.append(ChartImage(create_bar_chart, 400, 350, list(devices_grouped.values()), list(devices_grouped.keys()),
                                 "Device Analysis", "Device Type", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(devices)
    elements.append(ChartImage(create_multi_line_chart, 400, 400, x_vals, y_series,
                                 "Device Trends Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Sensor Analysis Section ---
    elements.append(Paragraph("Sensor Analysis", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Sensor data is critical for understanding alert generation. The charts below display sensor-specific alert counts and their trends over time.",
        custom_styles["Normal"]
    ))
    sensors = athena_data['grouped_data']['sensor_type']
    sensors_grouped = aggregate_grouped_values(sensors)
    elements.append(ChartImage(create_bar_chart, 400, 350, list(sensors_grouped.values()), list(sensors_grouped.keys()),
                                 "Sensor Analysis", "Sensor Type", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(sensors)
    elements.append(ChartImage(create_multi_line_chart, 400, 350, x_vals, y_series,
                                 "Sensor Trends Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Industry Analysis Section ---
    elements.append(Paragraph("Industry Analysis", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "This section segments alert data by industry, revealing trends that may highlight market-specific challenges and opportunities.",
        custom_styles["Normal"]
    ))
    industry = athena_data['grouped_data']['industry']
    industry_grouped = aggregate_grouped_values(industry)
    elements.append(ChartImage(create_bar_chart, 400, 450, list(industry_grouped.values()), list(industry_grouped.keys()),
                                 "Industry Analysis", "Industry", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(industry)
    elements.append(ChartImage(create_multi_line_chart, 400, 350, x_vals, y_series,
                                 "Industry Trends Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Event Analysis Section ---
    elements.append(Paragraph("Event Analysis", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Events can have a significant impact on alert patterns. This section breaks down alerts by event type and examines their trends over time.",
        custom_styles["Normal"]
    ))
    event = athena_data['grouped_data']['event_type']
    event_grouped = aggregate_grouped_values(event)
    elements.append(ChartImage(create_bar_chart, 400, 400, list(event_grouped.values()), list(event_grouped.keys()),
                                 "Event Analysis", "Event Type", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(event)
    elements.append(ChartImage(create_multi_line_chart, 400, 350, x_vals, y_series,
                                 "Event Trends Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    
    # --- Conclusion Section ---
    elements.append(Paragraph("Conclusion", custom_styles["Heading1"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "In summary, the analysis above reveals key trends in alert data across multiple dimensions. "
        "The detailed breakdown—from overall trends to device, sensor, industry, and event insights—provides a comprehensive view of system performance, enabling proactive adjustments and strategic planning.",
        custom_styles["Normal"]
    ))
    elements.append(Spacer(1, 12))
    
    # --- AI Insights or Predictive Analytics Section ---
    if not oracle_blank:
        # Existing AI Insights section:
        elements.append(PageBreak())
        elements.append(SectionCover("AI Insights"))
        elements.append(PageBreak())
        
        elements.append(Paragraph("Past Month & Next Month Analysis", custom_styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(
            "This section compares actual alert data from the past month with AI-generated forecasts. "
            "The analysis identifies discrepancies between observed data and predictions, refining future forecasts.",
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Past Month Alert Comparison", custom_styles["Heading2"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(
            "The bar chart below contrasts the actual alert counts from the past 4 weeks with AI predictions, helping evaluate forecasting accuracy.",
            custom_styles["Normal"]
        ))
        actual_last_4w = oracle_data['actual_last_4w']
        monthly_alerts = [actual_last_4w, oracle_data['predicted_last_4w']]
        monthly_alerts_labels = ['Actual Last 4 Weeks', 'Predicted Last 4 Weeks']
        elements.append(ChartImage(create_bar_chart, 350, 250, monthly_alerts, monthly_alerts_labels,
                                     "Past Month Alert Comparison", "Category", "Alert Count"))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph("Next Month Forecast", custom_styles["Heading2"]))
        elements.append(Spacer(1, 12))
        trend = "increase" if oracle_data['predicted_next_4w'] > actual_last_4w else "decrease"
        elements.append(Paragraph(
            f"Based on the AI model, an {trend} in alert counts is forecasted for the next four weeks. This predictive insight enables early resource allocation to address potential challenges.",
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 12))
        forecast_table = Table([
            ["Expected Alerts"],
            [str(oracle_data['predicted_next_4w'])]
        ], style=[("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                  ("ALIGN", (0,0), (-1,-1), "CENTER")])
        elements.append(forecast_table)
        elements.append(Spacer(1, 12))
        elements.append(PageBreak())
    else:
        # Add this new section
        elements.append(PageBreak())
        elements.append(Paragraph("Predictive Analytics", custom_styles["Heading1"]))
        elements.append(Paragraph(
            "There is not enough historical data to generate reliable predictions at this time. "
            "As more alert data is collected, predictive forecasting will become available in future reports.", 
            custom_styles["Normal"]
        ))
        elements.append(Spacer(1, 12))
        elements.append(PageBreak())
    
    # --- Add TOC Callback ---
    def after_flowable(flowable):
        if hasattr(flowable, "style") and flowable.style.name in ["Heading1", "Heading2"]:
            level = 0 if flowable.style.name == "Heading1" else 1
            text = flowable.getPlainText()
            # Notify the TOC about this entry
            doc.notify('TOCEntry', (level, text, doc.page))
    
    doc.afterFlowable = after_flowable
    
    # Build the PDF document
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
