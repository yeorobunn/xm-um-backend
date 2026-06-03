from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time

app = FastAPI()

# --- IN-MEMORY DATABASE & BEHAVIOR ANALYTICS ---
latest_reading = {
    "timestamp": "Waiting...",
    "power": 0.0,
    "voltage": 0.0,
    "current": 0.0
}

analytics = {
    "start_time": time.time(),
    "last_reading_time": time.time(),
    "total_kwh": 0.0,
    "total_readings": 0,
    "active_load_readings": 0,
    "peak_overload_events": 0,
    "phantom_virtual_hours": 0.0  # NEW: Tracks how long unnecessary devices are left on
}

TNB_RATE_RM = 0.218 
CO2_EMISSION_FACTOR = 0.39 # kg CO2 per kWh in Malaysia

class SensorData(BaseModel):
    timestamp: str
    power: float
    voltage: float
    current: float

@app.post("/sensor")
async def receive_sensor_data(data: SensorData):
    global latest_reading, analytics
    latest_reading = data.model_dump()
    
    current_time = time.time()
    real_time_diff = current_time - analytics["last_reading_time"]
    analytics["last_reading_time"] = current_time
    
    # 1 Real Second = 1 Virtual Hour (Simulation Scale)
    virtual_hours_passed = real_time_diff * 1.0 
    
    analytics["total_readings"] += 1
    
    # Active Load Tracking
    if data.current > 0.005: 
        analytics["active_load_readings"] += 1
        
    # Peak Overload Tracking
    if data.current >= 0.0145: 
        analytics["peak_overload_events"] += 1

    # NEW: Persuasive Phantom/Unnecessary Load Tracking
    # If a small appliance (like a light or TV standby) is left running alone for a long time
    if 0.001 < data.current <= 0.004:
        analytics["phantom_virtual_hours"] += virtual_hours_passed

    return {"status": "success"}

# --- HIDDEN API ROUTES FOR WEBSITES ---
@app.get("/api/data")
async def get_live_data():
    return latest_reading

@app.get("/api/behavior")
async def get_behavior_data():
    if analytics["total_readings"] > 0:
        active_ratio = (analytics["active_load_readings"] / analytics["total_readings"]) * 100
        overload_ratio = (analytics["peak_overload_events"] / analytics["total_readings"]) * 100
    else:
        active_ratio = 0
        overload_ratio = 0
        
    # Calculate Wasted Money & Carbon based on tracked phantom loads
    # Assume average phantom power is roughly 15W (0.015 kW)
    wasted_kwh = analytics["phantom_virtual_hours"] * 0.015
    wasted_rm = wasted_kwh * TNB_RATE_RM
    wasted_co2 = wasted_kwh * CO2_EMISSION_FACTOR
        
    # Determine Behavioral Persona
    if overload_ratio > 5:
        persona = "⚠️ High-Risk (Habitual Overloader)"
        insight = "User frequently runs heavy appliances simultaneously, risking grid instability."
        action = "⚡ Agentic Action: The system will automatically shed non-essential loads during peak current detection."
        color = "#c0392b" # Red
    elif analytics["phantom_virtual_hours"] > 10:
        persona = "💸 Phantom Waster"
        insight = f"You are leaving unnecessary appliances running for long periods. You have accumulated {round(analytics['phantom_virtual_hours'], 1)} virtual hours of idle waste."
        action = "💡 Agentic Action: The AI has identified idle standby devices. We recommend enabling Auto-Kill for the external hub to stop financial leakage."
        color = "#e67e22" # Orange
    elif active_ratio > 20:
        persona = "🟢 Balanced Household"
        insight = "Normal daily routines detected. Grid utilization is healthy and optimized."
        action = "💤 Agentic Action: System maintains passive NILM monitoring. Smart standby mode is actively protecting the grid."
        color = "#27ae60" # Green
    else:
        persona = "🍃 Eco-Minimalist"
        insight = "Excellent energy conservation. Minimal idle waste detected across the network."
        action = "🛡️ Agentic Action: Maintaining current baseline. Excellent eco-score achieved."
        color = "#2980b9" # Blue
        
    stability_score = max(0.0, 100.0 - (overload_ratio * 8.0) - (analytics["phantom_virtual_hours"] * 0.5))
    
    return {
        "active_ratio": round(active_ratio, 1),
        "overloads": analytics["peak_overload_events"],
        "phantom_hours": round(analytics["phantom_virtual_hours"], 1),
        "wasted_rm": f"{wasted_rm:.4f}",
        "wasted_co2": f"{wasted_co2:.4f}",
        "persona": persona,
        "insight": insight,
        "action": action,
        "color": color,
        "stability": round(stability_score, 1)
    }

# =========================================================
# ROUTE 1: LIVE TELEMETRY DASHBOARD (PAGE 1)
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def view_live_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud | Live Telemetry</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; margin: 0; padding-top: 20px; padding-bottom: 40px;}
                .navbar { background: white; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }
                .nav-btn { text-decoration: none; font-weight: bold; padding: 10px 20px; border-radius: 8px; color: #7f8c8d; transition: 0.3s; }
                .nav-active { background: #2980b9; color: white; }
                
                .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; text-align: left; min-width: 450px; max-width: 600px;}
                h1 { color: #2980b9; margin-bottom: 5px; }
                h3 { color: #7f8c8d; margin-top: 0; margin-bottom: 30px; font-weight: normal; }
                
                .data-box { background: #f8f9fa; border-left: 4px solid #2980b9; padding: 18px; margin-bottom: 20px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;}
                .title { font-size: 0.85em; color: #7f8c8d; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; }
                .big-value { font-size: 2.0em; font-family: monospace; font-weight: bold; color: #2c3e50; }
                
                .pulse { display: inline-block; width: 10px; height: 10px; background-color: #e74c3c; border-radius: 50%; margin-left: 10px; animation: blink 1s infinite alternate; }
                @keyframes blink { 0% { opacity: 1; } 100% { opacity: 0.3; } }
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-btn nav-active">📡 Live Telemetry</a>
                <a href="/analysis" class="nav-btn">🧠 AI Behavior & Energy Savings</a>
            </div>
            
            <h1>Cloud Live Telemetry</h1>
            <h3>Real-Time Global Grid Monitoring</h3>
            
            <div class="card">
                <div style="text-align:center; font-size: 0.9em; color:#7f8c8d; margin-bottom: 20px;">
                    Last Sync: <span id="timestamp" style="font-weight:bold; color:#2c3e50;">Waiting...</span> <span class="pulse"></span>
                </div>
                
                <div class="data-box">
                    <span class="title">⚡ Current</span>
                    <span class="big-value"><span id="current">0.000</span> <span style="font-size:0.5em; color:#7f8c8d;">A</span></span>
                </div>
                
                <div class="data-box" style="border-left-color: #f39c12;">
                    <span class="title">🔋 Voltage</span>
                    <span class="big-value"><span id="voltage">0.00</span> <span style="font-size:0.5em; color:#7f8c8d;">V</span></span>
                </div>
                
                <div class="data-box" style="border-left-color: #27ae60;">
                    <span class="title">📈 Power</span>
                    <span class="big-value"><span id="power">0.000</span> <span style="font-size:0.5em; color:#7f8c8d;">W</span></span>
                </div>
            </div>

            <script>
                setInterval(async () => {
                    try {
                        const response = await fetch('/api/data');
                        const data = await response.json();
                        
                        document.getElementById('timestamp').innerText = data.timestamp;
                        document.getElementById('current').innerText = data.current.toFixed(4);
                        document.getElementById('voltage').innerText = data.voltage.toFixed(2);
                        document.getElementById('power').innerText = data.power.toFixed(3);
                    } catch (err) {}
                }, 1000);
            </script>
        </body>
    </html>
    """
    return html_content

# =========================================================
# ROUTE 2: BEHAVIOR & ENERGY SAVINGS (PAGE 2)
# =========================================================
@app.get("/analysis", response_class=HTMLResponse)
async def view_user_behavior_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud | Behavior Analytics</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; margin: 0; padding-top: 20px; padding-bottom: 40px;}
                .navbar { background: white; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }
                .nav-btn { text-decoration: none; font-weight: bold; padding: 10px 20px; border-radius: 8px; color: #7f8c8d; transition: 0.3s; }
                .nav-active { background: #8e44ad; color: white; }
                
                .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; text-align: left; min-width: 450px; max-width: 600px;}
                h1 { color: #8e44ad; margin-bottom: 5px; }
                h3 { color: #7f8c8d; margin-top: 0; margin-bottom: 30px; font-weight: normal; }
                
                .data-box { background: #f8f9fa; border-left: 4px solid #27ae60; padding: 18px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.02);}
                .action-box { background: #fdfbf7; border: 1px solid #e1e8ed; padding: 18px; border-radius: 6px; margin-top: 10px;}
                .leak-box { background: #fff5f5; border: 1px dashed #e74c3c; padding: 15px; border-radius: 6px; margin-top: 15px; display: flex; justify-content: space-between; align-items: center;}
                
                .title { font-size: 0.85em; color: #7f8c8d; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; margin-bottom: 8px; display: block; }
                .big-value { font-size: 2.0em; font-family: monospace; font-weight: bold; color: #2c3e50; }
                .insight-text { font-size: 0.95em; color: #34495e; margin-top: 8px; line-height: 1.4; }
                .action-text { font-size: 0.95em; color: #8e44ad; font-weight: bold; margin-top: 5px; line-height: 1.4;}
                
                .danger-text { color: #c0392b; font-weight: bold; font-family: monospace; font-size: 1.2em;}
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-btn">📡 Live Telemetry</a>
                <a href="/analysis" class="nav-btn nav-active">🧠 AI Behavior & Savings</a>
            </div>
            
            <h1>Agentic Behavior Engine</h1>
            <h3>Long-Term User Profiling & Automated Savings</h3>
            
            <div class="card">
                <div class="data-box" id="box-persona" style="border-left-color: #2980b9;">
                    <span class="title">🧠 AI Behavioral Persona</span>
                    <div class="big-value" id="val-persona">Scanning...</div>
                    <div class="insight-text" id="val-insight">Accumulating baseline telemetry data...</div>
                    
                    <div class="action-box">
                        <span class="title" style="color:#8e44ad;">🤖 Automated System Intervention</span>
                        <div class="action-text" id="val-action">Waiting for sufficient data to generate energy saving recommendations...</div>
                    </div>
                </div>
                
                <div class="data-box" style="border-left-color: #e74c3c;">
                    <span class="title">💸 Hidden Financial Leakage (Phantom Loads)</span>
                    <div class="insight-text" style="margin-bottom: 10px;">
                        The AI has tracked <b><span id="val-phantom">0.0</span> virtual hours</b> where unnecessary appliances were left running.
                    </div>
                    
                    <div class="leak-box">
                        <div style="font-size: 0.9em; color: #7f8c8d; font-weight: bold;">💰 Wasted Cost:</div>
                        <div class="danger-text">RM <span id="val-rm">0.0000</span></div>
                    </div>
                    
                    <div class="leak-box" style="background:#f4f9f4; border-color:#27ae60;">
                        <div style="font-size: 0.9em; color: #7f8c8d; font-weight: bold;">🌍 Carbon Footprint Added:</div>
                        <div class="danger-text" style="color:#27ae60;"><span id="val-co2">0.0000</span> kg CO₂</div>
                    </div>
                </div>
                
                <div class="data-box" id="box-stability" style="border-left-color: #27ae60;">
                    <span class="title">🛡️ Grid Stability Score</span>
                    <span class="big-value"><span id="val-stability">100.0</span> <span style="font-size:0.5em; color:#7f8c8d;">/ 100</span></span>
                    <div class="insight-text" style="color: #7f8c8d; font-size: 0.85em;">
                        Peak Overloads Triggered: <b style="color:#c0392b;" id="val-overloads">0</b><br>
                        Score degrades from poor consumption habits and network overloads.
                    </div>
                </div>
                
            </div>

            <script>
                setInterval(async () => {
                    try {
                        const response = await fetch('/api/behavior');
                        const data = await response.json();
                        
                        document.getElementById('val-persona').innerText = data.persona;
                        document.getElementById('val-insight').innerText = data.insight;
                        document.getElementById('val-action').innerText = data.action;
                        document.getElementById('box-persona').style.borderLeftColor = data.color;
                        
                        // Populate the persuasive waste boxes
                        document.getElementById('val-phantom').innerText = data.phantom_hours;
                        document.getElementById('val-rm').innerText = data.wasted_rm;
                        document.getElementById('val-co2').innerText = data.wasted_co2;
                        
                        document.getElementById('val-overloads').innerText = data.overloads;
                        
                        const stabilityEl = document.getElementById('val-stability');
                        stabilityEl.innerText = data.stability;
                        
                        // Change stability color based on health
                        if (data.stability < 60) {
                            stabilityEl.style.color = "#c0392b";
                            document.getElementById('box-stability').style.borderLeftColor = "#c0392b";
                        } else if (data.stability < 90) {
                            stabilityEl.style.color = "#f39c12";
                            document.getElementById('box-stability').style.borderLeftColor = "#f39c12";
                        } else {
                            stabilityEl.style.color = "#27ae60";
                            document.getElementById('box-stability').style.borderLeftColor = "#27ae60";
                        }

                    } catch (err) {}
                }, 1000);
            </script>
        </body>
    </html>
    """
    return html_content
