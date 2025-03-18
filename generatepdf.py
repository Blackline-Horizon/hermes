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
from datetime import date

# Load environment variables from the .env file
load_dotenv()

# 🟢 Generate Mock Data
def getAthenaData(report_data):
    ATHENA_URL = os.getenv("ATHENA_URL")
    with httpx.Client() as client:
        try:
            # had to spread the report_Data into it's own dictionary
            # since date was giving an encoding error
            # I had to turn it into isoformat
            report_dict = {
                "username": report_data.username,
                "title": report_data.title,
                "date_start": report_data.date_start.isoformat() if isinstance(report_data.date_start, date) else report_data.date_start,
                "date_end": report_data.date_start.isoformat() if isinstance(report_data.date_end, date) else report_data.date_end,
                "industry": report_data.industry,
                "continents": report_data.continents,
                "alerts": report_data.alerts,
                "devices": report_data.devices,
                "resolutions": report_data.resolutions,
                "events": report_data.events,
            }
            response = client.post(f"{ATHENA_URL}/report_data", json=report_dict)
            response.raise_for_status()
            print("RESPONSE ---------------------------------")
            response_dict = json.loads(response.text)
            print(response_dict)
        except Exception as e:
            print("ERROR ------------------------------------------------------")
            print(e)
            raise e

    return response_dict

# 🟢 Generate Bar Chart (BytesIO Buffer)
def create_bar_chart(data, labels, title, x_label, y_label):
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, data, color=['#4CAF50', '#2196F3', '#FF9800', '#E91E63', '#9C27B0'])
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.set_xticklabels(labels, rotation=90) 
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    img_buffer.seek(0)
    return img_buffer

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

# Generate PDF with Additional Paragraphs
def generate_pdf(report_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=report_data.title)
    styles = getSampleStyleSheet()
    elements = []

    # Fetch Mock Data
    data = getAthenaData(report_data)
    date_created = data['time_series_overall']['date_created'][0]

    # Title Page
    elements.append(Paragraph("Blackline Horizon Alert Analytics Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Start Date: {report_data.date_start}", styles["Normal"]))
    elements.append(Paragraph(f"End Date: {report_data.date_end}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())

    # Table of Contents (Mocked)
    elements.append(Paragraph("Table of Contents", styles["Title"]))
    toc_data = [
        ["1. Introduction"], 
        ["2. Alert Count Over Time"], 
        ["3. Past & Next Month Analysis"], 
        ["4. Resolution Reason Analysis"], 
        ["5. Device Type Analysis"], 
        ["6. Sensor Type Analysis"], 
        ["7. Industry Analysis"], 
        ["8. Event Type Analysis"], 
        ["9. Conclusion"]
    ]
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
    elements.append(Spacer(1, 6))
    # elements.append(ChartImage(create_line_chart, 400, 250, data["line_chart_data"]))
    elements.append(PageBreak())

    # Past Month & Next Month Analysis
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
    # elements.append(ChartImage(create_bar_chart, 400, 250, data["bar_chart_data"], data["bar_chart_labels"]))
    elements.append(Spacer(1, 12))

    # Next Month Forecast
    elements.append(Paragraph("Next Month Forecast", styles["Heading2"]))
    elements.append(Paragraph(
        "The predictive model projects an increase in alert counts for the next four weeks. "
        "This metric serves as an early warning indicator, helping organizations allocate "
        "resources more effectively.", styles["Normal"]
    ))
    elements.append(Spacer(1, 6))
    elements.append(Table([
        ["Expected Alerts"],
        [str(800)]
    ], style=[("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(PageBreak())

    # Resolutions Analysis
    elements.append(Paragraph("Resolutions Analysis", styles["Heading1"]))
    resolutions = data['grouped_data']['resolution_reason'][date_created]
    print(resolutions)
    elements.append(ChartImage(create_bar_chart, 500, 500, resolutions.values(), resolutions.keys(), "Resolution Analysis", "Resolution Types", "Alerts"))
    elements.append(Spacer(1, 12))
    elements.append(PageBreak())


    # Conclusion
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
