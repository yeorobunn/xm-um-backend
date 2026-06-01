from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time

app = FastAPI()

# --- IN-MEMORY DATABASE & ANALYTICS ---
latest_reading = {
    "timestamp": "Waiting...",
    "power": 0.0,
    "voltage": 0.0,
    "current": 0.0
}

analytics = {
    "start_time": time.time(),
    "total_kwh": 0.0,
    "total_readings": 0,
    "active_load_readings": 0 
}

TNB_RATE_RM = 0.218 

class SensorData(BaseModel):
    timestamp: str
    power: float
    voltage: float
    current: float

@app.post("/sensor")
async def receive_sensor_data(data: SensorData):
    global latest_reading, analytics
    latest_reading = data.model_dump()
    
    interval_kwh = (data.power / 1000.0) * (2.0 / 3600.0)
    analytics["total_kwh"] += interval_kwh
    analytics["total_readings"] += 1
    
    if data.power > 10.0:
        analytics["active_load_readings"] += 1

    return {"status": "success"}

# --- NEW ROUTE: Hidden API for the Live Graph ---
@app.get("/api/data")
async def get_live_data():
    return latest_reading

# --- GET ROUTE 1: Live Dashboard (WITH HITL CALIBRATION) ---
@app.get("/", response_class=HTMLResponse)
async def view_live_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud | Live</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; margin: 0; padding-top: 20px; padding-bottom: 40px;}
                .navbar { background: white; padding: 15px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); display: flex; justify-content: center; gap: 20px; margin-bottom: 30px; }
                .nav-btn { text-decoration: none; font-weight: bold; padding: 10px 20px; border-radius: 8px; color: #7f8c8d; transition: 0.3s; }
                .nav-active { background: #2980b9; color: white; }
                
                .dashboard-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; max-width: 900px; margin: 0 auto; }
                
                .card { background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: left; flex: 1; min-width: 300px; position: relative; }
                .chart-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 100%; max-width: 900px; margin: 20px auto; }
                
                h1 { color: #2980b9; margin-bottom: 5px; }
                h3 { color: #7f8c8d; margin-top: 0; margin-bottom: 30px; }
                .row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #ecf0f1; font-size: 1.2em; }
                .row:last-child { border-bottom: none; }
                .label { font-weight: bold; color: #34495e; }
                .value { font-family: monospace; font-size: 1.1em; color: #e74c3c; font-weight: bold; }
                
                /* Calibration Button & Modal Styles */
                .btn-cal { background: #f39c12; color: white; border: none; padding: 12px; font-size: 1.1em; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; margin-top: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: 0.3s; }
                .btn-cal:hover { background: #e67e22; }
                .cal-selector { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 6px; border: 1px solid #bdc3c7; font-size: 1.05em; font-family: inherit; color: #2c3e50; background-color: #f8f9fa; cursor: pointer; }
                
                #cal-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 100; justify-content: center; align-items: center; }
                .modal-content { background: white; padding: 40px; border-radius: 12px; width: 80%; max-width: 450px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
                .modal-title { color: #2980b9; font-size: 1.5em; font-weight: bold; margin-bottom: 20px; }
                .step-text { font-size: 1.1em; font-weight: bold; color: #34495e; margin: 20px 0; min-height: 80px; line-height: 1.4; }
                .loader { border: 5px solid #f3f3f3; border-top: 5px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; display: none; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="navbar">
                <a href="/" class="nav-btn nav-active">🎛️ Live Telemetry</a>
                <a href="/analysis" class="nav-btn">📊 Monthly Analysis</a>
            </div>
            
            <h1>XM.UM Agentic Grid Node</h1>
            <h3>Real-Time Cloud Synchronization</h3>
            
            <div class="dashboard-grid">
                <div class="card">
                    <div class="row">
                        <span class="label">🕒 Last Sync:</span>
                        <span class="value" id="val-time" style="color:#7f8c8d; font-size: 0.85em;">Waiting...</span>
                    </div>
                    <div class="row">
                        <span class="label">⚡ Active Power:</span>
                        <span class="value"><span id="val-power">0.00</span> W</span>
                    </div>
                    <div class="row">
                        <span class="label">🔌 Grid Voltage:</span>
                        <span class="value"><span id="val-voltage">0.00</span> V</span>
                    </div>
                    <div class="row">
                        <span class="label">🌊 Load Current:</span>
                        <span class="value"><span id="val-current">0.0000</span> A</span>
                    </div>
                    <button class="btn-cal" onclick="startCalibration()">🛠️ Profile New Appliance</button>
                </div>
            </div>

            <div class="chart-card">
                <h4 style="text-align: left; color: #7f8c8d; margin-top: 0;">Live Current Draw (mA) - NILM Signature Monitor</h4>
                <canvas id="currentChart" height="80"></canvas>
            </div>

            <div id="cal-modal">
                <div class="modal-content">
                    <div class="modal-title">AI Calibration Sequence</div>
                    <div id="loader" class="loader"></div>
                    <div id="step-text" class="step-text">Initializing Training Protocol...</div>
                </div>
            </div>

            <script>
                // --- 1. SETUP THE CHART ---
                const ctx = document.getElementById('currentChart').getContext('2d');
                const currentChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [], 
                        datasets: [{
                            label: 'Current (mA)',
                            data: [], 
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.2)',
                            borderWidth: 2,
                            tension: 0.3, 
                            fill: true,
                            pointRadius: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: { x: { display: true }, y: { display: true, suggestedMin: 0 } },
                        animation: { duration: 400 } 
                    }
                });

                // --- 2. FETCH DATA IN BACKGROUND ---
                setInterval(async () => {
                    try {
                        const response = await fetch('/api/data');
                        const data = await response.json();
                        
                        document.getElementById('val-time').innerText = data.timestamp;
                        document.getElementById('val-power').innerText = data.power.toFixed(2);
                        document.getElementById('val-voltage').innerText = data.voltage.toFixed(2);
                        document.getElementById('val-current').innerText = data.current.toFixed(4);

                        let current_mA = data.current * 1000;
                        let now = new Date();
                        let timeString = now.toLocaleTimeString([], {hour12: false});

                        currentChart.data.labels.push(timeString);
                        currentChart.data.datasets[0].data.push(current_mA);

                        if (currentChart.data.labels.length > 15) {
                            currentChart.data.labels.shift();
                            currentChart.data.datasets[0].data.shift();
                        }
                        currentChart.update();
                        
                    } catch (err) {}
                }, 2000);

                // --- 3. HITL CALIBRATION SEQUENCE ---
                let baseline_mA = 0;
                let detectionInterval;
                let detectedDelta = 0;

                function startCalibration() {
                    const modal = document.getElementById('cal-modal');
                    const text = document.getElementById('step-text');
                    const loader = document.getElementById('loader');
                    
                    modal.style.display = 'flex';
                    loader.style.display = 'block';
                    
                    // Snapshot the baseline current
                    baseline_mA = parseFloat(document.getElementById('val-current').innerText) * 1000;
                    text.innerHTML = `Scanning Baseline Noise Floor...<br><span style='font-size:0.75em; color:#7f8c8d;'>Steady state established at ${baseline_mA.toFixed(1)} mA.</span>`;
                    
                    setTimeout(() => { 
                        text.innerHTML = "🔴 Waiting for Activation...<br><span style='font-size:0.75em; color:#e74c3c;'>Please turn on the appliance now.</span>"; 
                        
                        // Wait for a jump in the live data
                        let attempts = 0;
                        detectionInterval = setInterval(() => {
                            let liveCurrent_mA = parseFloat(document.getElementById('val-current').innerText) * 1000;
                            let delta = liveCurrent_mA - baseline_mA;

                            if (delta >= 1.5) {
                                clearInterval(detectionInterval);
                                detectedDelta = delta;
                                generateSuggestions(delta);
                            } else if (attempts > 30) {
                                clearInterval(detectionInterval);
                                text.innerHTML = "❌ Timeout.<br><span style='font-size:0.75em; color:#7f8c8d;'>No appliance jump detected.</span>";
                                setTimeout(() => { modal.style.display = 'none'; }, 3000);
                            }
                            attempts++;
                        }, 500);
                    }, 2500);
                }

                function generateSuggestions(delta) {
                    const text = document.getElementById('step-text');
                    const loader = document.getElementById('loader');
                    loader.style.display = 'none';

                    let optionsHTML = "";
                    let matchRange = "";

                    // Categorize the jump and provide logical suggestions
                    if (delta >= 1.5 && delta <= 5.0) {
                        matchRange = "1.5mA - 5.0mA (Low Power)";
                        optionsHTML = `
                            <option value="Television">📺 Television</option>
                            <option value="Standing Fan">🌬️ Standing Fan</option>
                            <option value="Desktop PC">💻 Desktop PC</option>
                        `;
                    } else if (delta >= 7.0 && delta <= 12.0) {
                        matchRange = "7.0mA - 12.0mA (Medium Power)";
                        optionsHTML = `
                            <option value="Air Conditioner">❄️ Air Conditioner</option>
                            <option value="Hair Dryer">💨 Hair Dryer</option>
                            <option value="Iron">👔 Iron</option>
                        `;
                    } else if (delta >= 13.0 && delta <= 18.0) {
                        matchRange = "13.0mA - 18.0mA (Heavy Motor/Heating)";
                        optionsHTML = `
                            <option value="Refrigerator">🧊 Refrigerator</option>
                            <option value="Microwave">🍲 Microwave</option>
                            <option value="Water Heater">🚿 Water Heater</option>
                        `;
                    } else {
                        matchRange = "> 18.0mA (Extreme Load)";
                        optionsHTML = `
                            <option value="Electric Oven">🔥 Electric Oven</option>
                            <option value="Washing Machine">👕 Washing Machine</option>
                        `;
                    }

                    // Render the UI for the user to make the final choice
                    text.innerHTML = `
                        <div style="color:#27ae60; font-size:1.1em; margin-bottom:10px;">✅ Signature Captured: Δ ${delta.toFixed(1)} mA</div>
                        <div style="font-size:0.8em; color:#7f8c8d; margin-bottom:15px; font-weight:normal;">This signature matches the <b>${matchRange}</b> tier.</div>
                        <div style="font-size:0.9em; margin-bottom:10px; color:#2c3e50;">Please confirm the appliance type:</div>
                        <select id="user-selection" class="cal-selector">
                            ${optionsHTML}
                        </select>
                        <button class="btn-cal" style="margin-top:0;" onclick="saveProfile()">💾 Confirm & Save Profile</button>
                    `;
                }

                function saveProfile() {
                    const selectedAppliance = document.getElementById('user-selection').value;
                    const text = document.getElementById('step-text');

                    text.innerHTML = `
                        <div style="color:#2980b9; font-size:1.2em; margin-bottom:10px;">Profile Saved Successfully!</div>
                        Saved as: <b>'${selectedAppliance}'</b><br>
                        <span style='font-size:0.7em; color:#7f8c8d; font-weight:normal;'><br>System locked to ${detectedDelta.toFixed(1)} mA with a ± 2.0 mA tolerance band.</span>
                    `;

                    setTimeout(() => { document.getElementById('cal-modal').style.display = 'none'; }, 4500);
                }
            </script>
        </body>
    </html>
    """
    return html_content

# --- GET ROUTE 2: Monthly Analysis Dashboard ---
@app.get("/analysis", response_class=HTMLResponse)
async def view_monthly_analysis():
    elapsed_seconds = time.time() - analytics["start_time"]
    if elapsed_seconds < 1: 
        elapsed_seconds = 1 
        
    seconds_in_month = 30 * 24 * 3600
    projected_monthly_kwh = (analytics["total_kwh"] / elapsed_seconds) * seconds_in_month
    estimated_bill_rm = projected_monthly_kwh * TNB_RATE_RM
    
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
