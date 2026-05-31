from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time
from datetime import datetime

app = FastAPI()

# --- IN-MEMORY DATABASE & ANALYTICS ---
latest_reading = {
    "timestamp": "Waiting for ESP32...",
    "power": 0.0,
    "voltage": 0.0,
    "current": 0.0
}

# Analytics engine variables
analytics = {
    "start_time": time.time(),
    "total_kwh": 0.0,
    "total_readings": 0,
    "active_load_readings": 0 # Tracks when heavy appliances are ON
}

TNB_RATE_RM = 0.218 # RM per kWh (Tier 1)

class SensorData(BaseModel):
    timestamp: str
    power: float
    voltage: float
    current: float

# --- POST ROUTE: Receive Data from ESP32 ---
@app.post("/sensor")
async def receive_sensor_data(data: SensorData):
    global latest_reading, analytics
    latest_reading = data.model_dump()
    
    # 1. Calculate energy consumed in this 2-second interval
    # Convert Watts to kW (/1000) and 2 seconds to hours (2/3600)
    interval_kwh = (data.power / 1000.0) * (2.0 / 3600.0)
    analytics["total_kwh"] += interval_kwh
    analytics["total_readings"] += 1
    
    # 2. Track User Behavior (If power > 10W, appliances are actively running)
    if data.power > 10.0:
        analytics["active_load_readings"] += 1

    return {"status": "success"}

# --- GET ROUTE 1: Live Dashboard ---
@app.get("/", response_class=HTMLResponse)
async def view_live_dashboard():
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud | Live</title>
            <meta http-equiv="refresh" content="2">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; margin: 0; padding-top: 20px; }}
                .navbar {{ background: white; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }}
                .nav-btn {{ text-decoration: none; font-weight: bold; padding: 10px 20px; border-radius: 8px; color: #7f8c8d; transition: 0.3s; }}
                .nav-active {{ background: #2980b9; color: white; }}
                .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; text-align: left; min-width: 350px; }}
                h1 {{ color: #2980b9; margin-bottom: 5px; }}
                h3 {{ color: #7f8c8d; margin-top: 0; margin-bottom: 30px; }}
                .row {{ display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #ecf0f1; font-size: 1.2em; }}
                .row:last-child {{ border-bottom: none; }}
                .label {{ font-weight: bold; color: #34495e; }}
                .value {{ font-family: monospace; font-size: 1.1em; color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-btn nav-active">🎛️ Live Telemetry</a>
                <a href="/analysis" class="nav-btn">📊 Monthly Analysis</a>
            </div>
            
            <h1>XM.UM Agentic Grid Node</h1>
            <h3>Real-Time Cloud Synchronization</h3>
            
            <div class="card">
                <div class="row">
                    <span class="label">🕒 Last Sync:</span>
                    <span class="value" style="color:#7f8c8d; font-size: 0.85em;">{latest_reading['timestamp']}</span>
                </div>
                <div class="row">
                    <span class="label">⚡ Active Power:</span>
                    <span class="value">{latest_reading['power']:.2f} W</span>
                </div>
                <div class="row">
                    <span class="label">🔌 Grid Voltage:</span>
                    <span class="value">{latest_reading['voltage']:.2f} V</span>
                </div>
                <div class="row">
                    <span class="label">🌊 Load Current:</span>
                    <span class="value">{latest_reading['current']:.4f} A</span>
                </div>
            </div>
        </body>
    </html>
    """
    return html_content

# --- GET ROUTE 2: Monthly Analysis Dashboard ---
@app.get("/analysis", response_class=HTMLResponse)
async def view_monthly_analysis():
    # 1. Calculate time elapsed since server started
    elapsed_seconds = time.time() - analytics["start_time"]
    if elapsed_seconds < 1: 
        elapsed_seconds = 1 # Prevent division by zero errors
        
    # 2. Predictive Math (Project current usage out to 30 days)
    seconds_in_month = 30 * 24 * 3600
    projected_monthly_kwh = (analytics["total_kwh"] / elapsed_seconds) * seconds_in_month
    estimated_bill_rm = projected_monthly_kwh * TNB_RATE_RM
    
    # 3. Behavioral Analysis Logic
    if analytics["total_readings"] > 0:
        active_ratio = (analytics["active_load_readings"] / analytics["total_readings"]) * 100
    else:
        active_ratio = 0
        
    if active_ratio > 60:
        behavior_insight = "🔴 High Activity (Appliances constantly running)"
    elif active_ratio > 20:
        behavior_insight = "🟡 Moderate Usage (Normal household behavior)"
    else:
        behavior_insight = "🟢 Eco-Mode (Mostly standby / unused appliances)"

    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud | Analysis</title>
            <meta http-equiv="refresh" content="3">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; margin: 0; padding-top: 20px; }}
                .navbar {{ background: white; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }}
                .nav-btn {{ text-decoration: none; font-weight: bold; padding: 10px 20px; border-radius: 8px; color: #7f8c8d; transition: 0.3s; }}
                .nav-active {{ background: #27ae60; color: white; }}
                .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; text-align: left; min-width: 400px; }}
                h1 {{ color: #27ae60; margin-bottom: 5px; }}
                h3 {{ color: #7f8c8d; margin-top: 0; margin-bottom: 30px; }}
                .data-box {{ background: #f8f9fa; border-left: 4px solid #27ae60; padding: 15px; margin-bottom: 15px; border-radius: 4px; }}
                .title {{ font-size: 0.9em; color: #7f8c8d; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; margin-bottom: 5px; display: block; }}
                .big-value {{ font-size: 2.2em; font-family: monospace; font-weight: bold; color: #2c3e50; }}
                .highlight {{ color: #c0392b; }}
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-btn">🎛️ Live Telemetry</a>
                <a href="/analysis" class="nav-btn nav-active">📊 Monthly Analysis</a>
            </div>
            
            <h1>AI Predictive Analytics</h1>
            <h3>30-Day Automated Forecasting</h3>
            
            <div class="card">
                <div class="data-box">
                    <span class="title">📈 Monthly Projected Usage</span>
                    <span class="big-value">{projected_monthly_kwh:.2f} <span style="font-size:0.5em; color:#7f8c8d;">kWh</span></span>
                </div>
                
                <div class="data-box" style="border-left-color: #c0392b;">
                    <span class="title">💰 Estimated Monthly Bill (TNB)</span>
                    <span class="big-value highlight">RM {estimated_bill_rm:.2f}</span>
                </div>
                
                <div class="data-box" style="border-left-color: #f39c12;">
                    <span class="title">🧠 User Behavior Profile</span>
                    <div style="font-weight: bold; color: #2c3e50; margin-top: 5px; font-size: 1.1em;">
                        {behavior_insight}
                    </div>
                    <div style="font-size: 0.85em; color: #7f8c8d; margin-top: 5px;">
                        Active Load Ratio: {active_ratio:.1f}% of total grid uptime.
                    </div>
                </div>
                
                <div style="text-align:center; margin-top: 20px; font-size: 0.8em; color: #bdc3c7;">
                    Projections are calculated dynamically based on real-time hardware telemetry streams.
                </div>
            </div>
        </body>
    </html>
    """
    return html_content
