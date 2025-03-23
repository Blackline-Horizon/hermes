import io
import matplotlib
matplotlib.use("AGG")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os
import httpx
import json
from datetime import date, datetime, time
from collections import defaultdict

# Load environment variables from the .env file
load_dotenv()
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

# 🟢 Generate Mock Data
def getAthenaData(report_data) -> dict:
    ATHENA_URL = os.getenv("ATHENA_URL")
    with httpx.Client() as client:
        try:
            report_dict = formatAthenaData(report_data)
            response = client.post(f"{ATHENA_URL}/report_data", json=report_dict, timeout=60)
            response.raise_for_status()
            response_dict = json.loads(response.text)
        except Exception as e:
            print("ERROR ------------------------------------------------------")
            print(e)
            raise e

    return response_dict

def getOracleData(report_data) -> dict:
    ORACLE_URL = os.getenv("ORACLE_URL")
    with httpx.Client() as client:
        try:
            report_dict = formatOracleData(report_data)
            print("REQUEST -------------------------")
            print(report_dict)
            response = client.post(f"{ORACLE_URL}/report_data", json=report_dict, timeout=60)
            response.raise_for_status()
            print("RESPONSE ---------------------------------------")
            response_dict = json.loads(response.text)
            print(response_dict)
        except Exception as e:
            print("ERROR ------------------------------------------------------")
            print(e)
            response_dict = {}
    return response_dict


# 🟢 Generate Bar Chart (BytesIO Buffer)
def create_bar_chart(data, labels, title, x_label, y_label):
    plt.style.use("seaborn-v0_8-dark")
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, data, color=['#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0'])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    # ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.grid(visible=False)
    ax.set_xticklabels(labels, rotation=90) 
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

# import plotly.graph_objects as go
# import plotly.express as px
# from kaleido.scopes.plotly import PlotlyScope

# def create_bar_chart(data, labels, title, x_label, y_label):
#     fig = go.Figure(data=[go.Bar(
#         x=labels,
#         y=data,
#         marker_color=['#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0']
#     )])
    
#     fig.update_layout(
#         title=title,
#         xaxis_title=x_label,
#         yaxis_title=y_label,
#         template="plotly_dark",
#         paper_bgcolor='rgba(0,0,0,0)',
#         plot_bgcolor='rgba(0,0,0,0)'
#     )
    
#     # Convert to image
#     scope = PlotlyScope()
#     img_bytes = scope.transform(fig, format="png", width=500, height=300)
#     img_buffer = io.BytesIO(img_bytes)
#     return img_buffer

# 🟢 Line Graph: Multiple Dates on One Graph
def create_multi_line_chart(x_values, y_values, title, x_label, y_label):
    plt.style.use("seaborn-v0_8-dark")
    fig, ax = plt.subplots(figsize=(6, 4))

    for label, y_data in y_values.items():
        ax.plot(x_values, y_data, marker="o", linestyle="-", linewidth=2, markersize=6, label=label)

    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_xticklabels(x_values, rotation=90) 
    ax.legend()

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

def prepare_multiline_grouped_data(grouped_data_by_date):
    """
    Converts date-key-value structured data into (x_values, y_series)
    suitable for multi-line plotting.
    
    Input: {
        "2025-03-06": {"a": 1, "b": 2, "null": 5},
        "2025-03-07": {"a": 3},
        ...
    }
    
    Output:
    x_values = ["2025-03-06", "2025-03-07"]
    y_series = {"a": [1, 3], "b": [2, 0], "None": [5, 0]}
    """
    # Collect all unique keys (e.g., resolution types, device types, etc.)
    keys = set()
    for values in grouped_data_by_date.values():
        keys.update(values.keys())

    # Convert "null" keys to "None" string
    normalized_grouped_data = {}
    for date, values in grouped_data_by_date.items():
        normalized_values = {}
        for k, v in values.items():
            normalized_key = "None" if k == "null" else k
            normalized_values[normalized_key] = v
        normalized_grouped_data[date] = normalized_values

    # Update keys set to replace "null" with "None"
    if "null" in keys:
        keys.remove("null")
        keys.add("None")

    # Sort dates to use as x-axis
    x_values = sorted(normalized_grouped_data.keys())

    # Initialize output structure
    y_series = {k: [] for k in keys}

    for date in x_values:
        day_data = normalized_grouped_data.get(date, {})
        for k in keys:
            y_series[k].append(day_data.get(k, 0))  # Fill missing with 0

    return x_values, y_series

def aggregate_grouped_values(grouped_data_by_date):
    """
    Aggregates all values by key across all dates.

    Input:
    {
        "2025-03-06": {"a": 1, "b": 2},
        "2025-03-07": {"a": 3}
    }

    Output:
    {
        "a": 4,
        "b": 2
    }
    """
    aggregated = defaultdict(int)

    for day_data in grouped_data_by_date.values():
        for key, value in day_data.items():
            aggregated[key] += value

    return dict(aggregated)

# 🟢 Generate Line Chart (BytesIO Buffer)
def create_line_chart(data_points):
    fig, ax = plt.subplots(figsize=(5, 3))
    x_values, y_values = zip(*data_points)

    ax.plot(x_values, y_values, marker="o", linestyle="-", color="#2196F3", linewidth=2, markersize=6)
    ax.set_xlabel("X-Axis (Time)")
    ax.set_ylabel("Y-Axis (Values)")
    ax.set_title("Line Chart")
    ax.grid(True, linestyle="--", alpha=0.6)

    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

# 🟢 Custom Flowable for Charts
class ChartImage(Image):
    def __init__(self, chart_func, width=400, height=250, *chart_args, **chart_kwargs):
        img_buffer = chart_func(*chart_args, **chart_kwargs)  
        img_buffer.seek(0)
        super().__init__(img_buffer, width=width, height=height)

def generate_pdf(report_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=report_data.title)
    styles = getSampleStyleSheet()
    elements = []

    # Fetch Mock Data
    athena_data = getAthenaData(report_data)
    oracle_data = getOracleData(report_data)
    oracle_blank = not bool(oracle_data)  # Changed this line to invert the logic
    
    # Title Page
    elements.append(Paragraph("Blackline Horizon Alert Analytics Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Start Date: {report_data.date_start}", styles["Normal"]))
    elements.append(Paragraph(f"End Date: {report_data.date_end}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())

    # Table of Contents (Mocked) - conditionally include the Past & Next Month Analysis
    elements.append(Paragraph("Table of Contents", styles["Title"]))
    toc_data = [
        ["1. Introduction"], 
        ["2. Alert Count Over Time"]
    ]
    
    # Only include Past & Next Month Analysis in TOC if oracle_data exists
    if not oracle_blank:
        toc_data.append(["3. Past & Next Month Analysis"])
        # Adjust numbering for subsequent sections
        toc_data.extend([
            ["4. Resolution Reason Analysis"], 
            ["5. Device Type Analysis"], 
            ["6. Sensor Type Analysis"], 
            ["7. Industry Analysis"], 
            ["8. Event Type Analysis"], 
            ["9. Conclusion"]
        ])
    else:
        # Skip the Past & Next Month Analysis in numbering
        toc_data.extend([
            ["3. Resolution Reason Analysis"], 
            ["4. Device Type Analysis"], 
            ["5. Sensor Type Analysis"], 
            ["6. Industry Analysis"], 
            ["7. Event Type Analysis"], 
            ["8. Conclusion"]
        ])
    
    table = Table(toc_data)
    table.setStyle(TableStyle([("TEXTCOLOR", (0,0), (-1,-1), colors.black)]))
    elements.append(table)
    elements.append(PageBreak())

    # Introduction
    elements.append(Paragraph("Introduction", styles["Heading1"]))
    elements.append(Paragraph(
        "This report provides an in-depth analysis of alert data collected over the past year. "
        "It covers various aspects including system performance, AI-based predictions, and "
        "drift analysis. By identifying key trends, this analysis aims to provide actionable "
        "insights for improving response strategies and operational efficiency.", styles["Normal"]
    ))
    elements.append(Spacer(1, 12))

    # Alert Count Over Time (Line Graph)
    elements.append(Paragraph("Alert Count Over Time", styles["Heading2"]))
    elements.append(Paragraph(
        "The graph below represents the alert count over the entire date range. The data "
        "shows fluctuations that may correlate with changes in system usage, environmental conditions, "
        "or operational adjustments. Notable spikes in alerts can indicate unusual patterns that warrant further investigation.", styles["Normal"]
    ))
    # Line Graph: Alert Count Over Time (All Dates)
    dates = athena_data["time_series_overall"]["date_created"]
    alert_counts = athena_data["time_series_overall"]["alert_count"]
    
    elements.append(Paragraph("Alert Count Over Time", styles["Heading2"]))
    elements.append(ChartImage(create_multi_line_chart, 500, 350, dates, {"Alert Count": alert_counts}, 
                               "Alert Count Over Time", "Date", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())

    # Past Month & Next Month Analysis - only include if oracle_data exists
    if not oracle_blank:
        elements.append(Paragraph("Past Month & Next Month Analysis", styles["Heading1"]))
        elements.append(Paragraph(
            "A comparison of the past month's alerts versus predictive forecasts provides valuable "
            "insights into system behavior. The retrospective forecast highlights variations in "
            "actual vs. expected alert counts, aiding in refining predictive accuracy.", styles["Normal"]
        ))
        elements.append(Spacer(1, 12))

        # Past Month Bar Chart
        elements.append(Paragraph("Past Month Alert Comparison", styles["Heading2"]))
        elements.append(Spacer(1, 6))
        actual_last_4w = oracle_data['actual_last_4w']
        monthly_alerts = [actual_last_4w, oracle_data['predicted_last_4w']]
        monthly_alerts_labels = ['Actual Last 4 Weeks', 'Predicted Last 4 Weeks']
        elements.append(ChartImage(create_bar_chart, 400, 300, monthly_alerts, monthly_alerts_labels, "Past Month Alert Comparison Graph", "", "Alert Count"))
        elements.append(Spacer(1, 12))

        # Next Month Forecast
        predicted_next_4w = oracle_data['predicted_next_4w']
        elements.append(Paragraph("Next Month Forecast", styles["Heading2"]))
        trend = "increase" if predicted_next_4w > actual_last_4w else "decrease"
        elements.append(Paragraph(
            f"The predictive model projects an {trend} in alert counts for the next four weeks. "
            "This metric serves as an early warning indicator, helping organizations allocate "
            "resources more effectively.", styles["Normal"]
        ))
        elements.append(Spacer(1, 6))
        elements.append(Table([
            ["Expected Alerts"],
            [str(predicted_next_4w)]    
        ], style=[("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
        elements.append(PageBreak())

    # The rest of the code remains the same
    # Resolutions Analysis
    elements.append(Paragraph("Resolutions Analysis", styles["Heading1"]))
    resolutions = athena_data['grouped_data']['resolution_reason']
    resolutions_grouped = aggregate_grouped_values(resolutions)
    elements.append(ChartImage(create_bar_chart, 500, 500, resolutions_grouped.values(), resolutions_grouped.keys(), "Resolution Analysis", "", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())
    x_vals, y_series = prepare_multiline_grouped_data(resolutions)
    elements.append(ChartImage(create_multi_line_chart, 500, 500, x_vals, y_series, "Resolution Analysis", "", "Alerts"))

    # Device Analysis -------------------------------------------------------------------------

    elements.append(Paragraph("Device Analysis", styles["Heading1"]))
    devices = athena_data['grouped_data']['device_type']
    devices_grouped = aggregate_grouped_values(devices)
    elements.append(ChartImage(create_bar_chart, 500, 400, devices_grouped.values(), devices_grouped.keys(), "Devices Analysis", "", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(devices)
    elements.append(ChartImage(create_multi_line_chart, 500, 500, x_vals, y_series, "Devices Analysis", "", "Alerts"))
    elements.append(PageBreak())

    # Sensor Analysis -----------------------------------------------------------------------------

    elements.append(Paragraph("Sensor Analysis", styles["Heading1"]))
    sensors = athena_data['grouped_data']['sensor_type']
    sensors_grouped = aggregate_grouped_values(sensors)
    elements.append(ChartImage(create_bar_chart, 500, 450, sensors_grouped.values(), sensors_grouped.keys(), 
                            "Sensor Analysis", "", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(sensors)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series, 
                            "Sensor Trends Over Time", "Date", "Alerts"))
    elements.append(PageBreak())

    # Industry Analysis -------------------------------------------------------------------------------

    elements.append(Paragraph("Industry Analysis", styles["Heading1"]))
    industry = athena_data['grouped_data']['industry']
    industry_grouped = aggregate_grouped_values(industry)
    elements.append(ChartImage(create_bar_chart, 500, 575, industry_grouped.values(), industry_grouped.keys(), 
                            "Industry Analysis", "", "Alerts"))
    x_vals, y_series = prepare_multiline_grouped_data(industry)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series, 
                            "Industry Trends Over Time", "Date", "Alerts"))
    elements.append(PageBreak())

    # Event Analysis -------------------------------------------------------------------------------------

    elements.append(Paragraph("Event Analysis", styles["Heading1"]))
    event = athena_data['grouped_data']['event_type']
    event_grouped = aggregate_grouped_values(event)
    elements.append(ChartImage(create_bar_chart, 500, 500, event_grouped.values(), event_grouped.keys(), 
                            "Event Analysis", "", "Alerts"))
    elements.append(Spacer(1, 12))
    x_vals, y_series = prepare_multiline_grouped_data(event)
    elements.append(ChartImage(create_multi_line_chart, 500, 450, x_vals, y_series, 
                            "Event Trends Over Time", "Date", "Alerts"))
    elements.append(PageBreak())

    # Conclusion -----------------------------------------------------------------------------------------
    elements.append(Paragraph("Conclusion", styles["Heading1"]))
    elements.append(Paragraph(
        "In summary, the alert trends identified over the past year indicate several recurring patterns. "
        "The AI predictions suggest a potential increase in alerts in the near future, highlighting "
        "the importance of proactive monitoring and data-driven decision-making. "
        "Continued analysis and system improvements are recommended to enhance reliability and safety.", styles["Normal"]
    ))
    elements.append(Spacer(1, 12))

    # Build PDF
    doc.build(elements)

    # Return PDF bytes
    buffer.seek(0)
    return buffer.read()
