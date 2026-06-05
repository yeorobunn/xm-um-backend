from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time

app = FastAPI()

# --- IN-MEMORY DATABASE & ANALYTICS ---
latest_reading = {
    "timestamp": "WAITING_SYNC",
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
    "phantom_virtual_hours": 0.0  
}

TNB_RATE_RM = 0.218 
CO2_EMISSION_FACTOR = 0.39 

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
    
    interval_kwh = (data.power / 1000.0) * (2.0 / 3600.0)
    analytics["total_kwh"] += interval_kwh
    analytics["total_readings"] += 1
    
    # Track behavior patterns based on incoming current
    if data.current > 0.005: 
        analytics["active_load_readings"] += 1
        
    if data.current >= 0.0145: 
        analytics["peak_overload_events"] += 1

    # Phantom/Unnecessary Load Tracking
    if 0.001 < data.current <= 0.004:
        analytics["phantom_virtual_hours"] += virtual_hours_passed

    return {"status": "success"}

# --- HIDDEN API ROUTES FOR WEBSITES ---
@app.get("/api/data")
async def get_live_data():
    return latest_reading

@app.get("/api/behavior")
async def get_behavior_data():
    elapsed_seconds = time.time() - analytics["start_time"]
    if elapsed_seconds < 1: elapsed_seconds = 1
    
    seconds_in_month = 30 * 24 * 3600
    projected_monthly_kwh = (analytics["total_kwh"] / elapsed_seconds) * seconds_in_month
    projected_monthly_rm = projected_monthly_kwh * TNB_RATE_RM
    projected_yearly_rm = projected_monthly_rm * 12

    if analytics["total_readings"] > 0:
        active_ratio = (analytics["active_load_readings"] / analytics["total_readings"]) * 100
        overload_ratio = (analytics["peak_overload_events"] / analytics["total_readings"]) * 100
    else:
        active_ratio = 0
        overload_ratio = 0
        
    wasted_kwh = analytics["phantom_virtual_hours"] * 0.015
    wasted_rm = wasted_kwh * TNB_RATE_RM
    wasted_co2 = wasted_kwh * CO2_EMISSION_FACTOR
        
    stability_score = max(0.0, 100.0 - (overload_ratio * 8.0) - (analytics["phantom_virtual_hours"] * 0.5))
    
    return {
        "active_ratio": round(active_ratio, 1),
        "overloads": analytics["peak_overload_events"],
        "phantom_hours": round(analytics["phantom_virtual_hours"], 1),
        "wasted_rm": round(wasted_rm, 2),
        "wasted_co2": round(wasted_co2, 2),
        "stability": round(stability_score, 1),
        "projected_monthly_rm": round(projected_monthly_rm, 2),
        "projected_yearly_rm": round(projected_yearly_rm, 2)
    }

# =========================================================
# ROUTE 1: LIVE TELEMETRY DASHBOARD
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def view_live_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM | Telemetry Interface</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                :root { --bg: #05070a; --card: #0d1117; --border: #1f2937; --text: #e5e7eb; --text-muted: #9ca3af; --accent: #00f3ff; --accent-glow: rgba(0, 243, 255, 0.2); --danger: #ff003c; --success: #00ffa3; }
                body { font-family: 'Inter', -apple-system, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding-bottom: 40px; }
                
                .navbar { background: var(--card); padding: 15px 30px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
                .nav-brand { font-weight: 800; letter-spacing: 2px; color: var(--text); font-size: 1.2em; }
                .nav-brand span { color: var(--accent); }
                .nav-links { display: flex; gap: 15px; }
                .nav-btn { text-decoration: none; font-weight: 600; font-size: 0.9em; padding: 8px 16px; border-radius: 4px; color: var(--text-muted); transition: all 0.2s; border: 1px solid transparent; }
                .nav-active { color: var(--accent); border: 1px solid var(--accent); background: var(--accent-glow); }
                .nav-btn:hover:not(.nav-active) { color: var(--text); border: 1px solid var(--border); }
                
                .container { max-width: 1000px; margin: 0 auto; padding: 0 20px; }
                .header-title { font-size: 1.8em; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
                .header-sub { color: var(--text-muted); font-size: 0.9em; margin-bottom: 30px; letter-spacing: 0.5px; text-transform: uppercase; }
                
                .grid-panel { display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }
                .card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 25px; flex: 1; min-width: 300px; position: relative; }
                .chart-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 25px; width: 100%; box-sizing: border-box; }
                
                .data-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #1f2937; }
                .data-row:last-of-type { border-bottom: none; }
                .label { font-size: 0.85em; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
                .value { font-family: 'Courier New', monospace; font-size: 1.2em; color: var(--accent); font-weight: bold; }
                
                .btn-primary { background: transparent; color: var(--text); border: 1px solid var(--accent); padding: 12px; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; border-radius: 4px; cursor: pointer; width: 100%; margin-top: 20px; transition: all 0.2s; box-shadow: 0 0 10px var(--accent-glow); }
                .btn-primary:hover { background: var(--accent); color: #000; }
                
                .cal-selector { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 4px; border: 1px solid var(--border); font-size: 0.95em; color: var(--text); background-color: #0d1117; cursor: pointer; outline: none; }
                
                #cal-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(5px); z-index: 100; justify-content: center; align-items: center; }
                .modal-content { background: var(--card); border: 1px solid var(--border); padding: 40px; border-radius: 8px; width: 90%; max-width: 450px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.5); }
                .modal-title { color: var(--text); font-size: 1.2em; text-transform: uppercase; letter-spacing: 2px; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
                .step-text { font-size: 0.95em; color: var(--text-muted); margin: 20px 0; min-height: 80px; line-height: 1.6; }
                .loader { border: 2px solid var(--border); border-top: 2px solid var(--accent); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto; display: none; }
                @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
        </head>
        <body>
            <div class="navbar">
                <div class="nav-brand">XM.UM <span>GRID NODE</span></div>
                <div class="nav-links">
                    <a href="/" class="nav-btn nav-active">TELEMETRY</a>
                    <a href="/analysis" class="nav-btn">ROI SIMULATOR</a>
                </div>
            </div>
            
            <div class="container">
                <div class="header-title">Live Telemetry Data</div>
                <div class="header-sub">System Status: Active Monitoring</div>
                
                <div class="grid-panel">
                    <div class="card">
                        <div class="data-row">
                            <span class="label">Last Sync</span>
                            <span class="value" id="val-time" style="color:var(--text-muted); font-size:0.9em;">--:--:--</span>
                        </div>
                        <div class="data-row">
                            <span class="label">Active Power</span>
                            <span class="value"><span id="val-power">0.00</span> W</span>
                        </div>
                        <div class="data-row">
                            <span class="label">Grid Voltage</span>
                            <span class="value"><span id="val-voltage">0.00</span> V</span>
                        </div>
                        <div class="data-row">
                            <span class="label">Load Current</span>
                            <span class="value" style="color:var(--danger);"><span id="val-current">0.0000</span> A</span>
                        </div>
                        <button class="btn-primary" onclick="startCalibration()">Initialize Profiling</button>
                    </div>
                </div>

                <div class="chart-card">
                    <div class="label" style="margin-bottom: 15px;">NILM Current Signature Monitor (mA)</div>
                    <canvas id="currentChart" height="80"></canvas>
                </div>
            </div>

            <div id="cal-modal">
                <div class="modal-content">
                    <div class="modal-title">System Calibration</div>
                    <div id="loader" class="loader"></div>
                    <div id="step-text" class="step-text">Awaiting command...</div>
                </div>
            </div>

            <script>
                Chart.defaults.color = '#9ca3af';
                Chart.defaults.font.family = "'Courier New', monospace";
                
                const ctx = document.getElementById('currentChart').getContext('2d');
                const currentChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [], 
                        datasets: [{
                            label: 'CURRENT (mA)',
                            data: [], 
                            borderColor: '#00f3ff',
                            backgroundColor: 'rgba(0, 243, 255, 0.05)',
                            borderWidth: 2,
                            tension: 0.1, 
                            fill: true,
                            pointRadius: 2,
                            pointBackgroundColor: '#00f3ff'
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: { 
                            x: { grid: { color: '#1f2937' } }, 
                            y: { grid: { color: '#1f2937' }, suggestedMin: 0 } 
                        },
                        animation: { duration: 200 } 
                    }
                });

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/data');
                        const data = await response.json();
                        
                        document.getElementById('val-time').innerText = data.timestamp.split('T')[1]?.split('+')[0] || data.timestamp;
                        document.getElementById('val-power').innerText = data.power.toFixed(2);
                        document.getElementById('val-voltage').innerText = data.voltage.toFixed(2);
                        document.getElementById('val-current').innerText = data.current.toFixed(4);

                        let current_mA = data.current * 1000;
                        let now = new Date();
                        let timeString = now.toLocaleTimeString([], {hour12: false});

                        currentChart.data.labels.push(timeString);
                        currentChart.data.datasets[0].data.push(current_mA);

                        if (currentChart.data.labels.length > 20) {
                            currentChart.data.labels.shift();
                            currentChart.data.datasets[0].data.shift();
                        }
                        currentChart.update();
                    } catch (err) {}
                }, 2000);

                let baseline_mA = 0;
                let detectionInterval;
                let detectedDelta = 0;

                function startCalibration() {
                    const modal = document.getElementById('cal-modal');
                    const text = document.getElementById('step-text');
                    const loader = document.getElementById('loader');
                    
                    modal.style.display = 'flex';
                    loader.style.display = 'block';
                    
                    baseline_mA = parseFloat(document.getElementById('val-current').innerText) * 1000;
                    text.innerHTML = `CALIBRATING NOISE FLOOR...<br><span style='font-size:0.85em; color:var(--text-muted);'>Baseline locked at ${baseline_mA.toFixed(1)} mA.</span>`;
                    
                    setTimeout(() => { 
                        text.innerHTML = "<span style='color:var(--danger); font-weight:bold;'>AWAITING ACTIVATION</span><br><span style='font-size:0.85em;'>Engage target appliance now.</span>"; 
                        
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
                                text.innerHTML = "<span style='color:var(--text-muted);'>TIMEOUT.</span><br><span style='font-size:0.85em;'>No signature detected.</span>";
                                setTimeout(() => { modal.style.display = 'none'; }, 2000);
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

                    if (delta >= 1.5 && delta <= 5.0) {
                        matchRange = "LOW POWER TIER";
                        optionsHTML = `<option value="TELEVISION">TELEVISION</option><option value="STANDING FAN">STANDING FAN</option>`;
                    } else if (delta >= 7.0 && delta <= 12.0) {
                        matchRange = "MID POWER TIER";
                        optionsHTML = `<option value="AIR CONDITIONER">AIR CONDITIONER</option><option value="IRON">IRON</option>`;
                    } else {
                        matchRange = "HIGH POWER TIER";
                        optionsHTML = `<option value="REFRIGERATOR">REFRIGERATOR</option><option value="WASHING MACHINE">WASHING MACHINE</option>`;
                    }

                    text.innerHTML = `
                        <div style="color:var(--success); margin-bottom:10px; font-weight:bold;">SIGNATURE CAPTURED: Δ ${delta.toFixed(1)} mA</div>
                        <div style="font-size:0.85em; color:var(--text-muted); margin-bottom:15px;">Classification: [ ${matchRange} ]</div>
                        <select id="user-selection" class="cal-selector">${optionsHTML}</select>
                        <button class="btn-primary" style="margin-top:0;" onclick="saveProfile()">CONFIRM PROFILE</button>
                    `;
                }

                function saveProfile() {
                    const selectedAppliance = document.getElementById('user-selection').value;
                    const text = document.getElementById('step-text');

                    text.innerHTML = `
                        <div style="color:var(--accent); font-weight:bold; margin-bottom:10px;">PROFILE WRITTEN TO MEMORY</div>
                        ID: [ ${selectedAppliance} ]<br>
                        <span style='font-size:0.8em; color:var(--text-muted);'>Tolerance band set to ${detectedDelta.toFixed(1)} mA.</span>
                    `;

                    setTimeout(() => { document.getElementById('cal-modal').style.display = 'none'; }, 3000);
                }
            </script>
        </body>
    </html>
    """
    return html_content

# =========================================================
# ROUTE 2: SMART ROI SIMULATOR
# =========================================================
@app.get("/analysis", response_class=HTMLResponse)
async def view_user_behavior_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM | Predictive ROI</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                :root { --bg: #05070a; --card: #0d1117; --border: #1f2937; --text: #e5e7eb; --text-muted: #9ca3af; --accent: #00f3ff; --accent-glow: rgba(0, 243, 255, 0.2); --success: #00ffa3; --danger: #ff003c; --warning: #ffb800;}
                body { font-family: 'Inter', -apple-system, sans-serif; background-color: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }
                
                .navbar { background: var(--card); padding: 15px 30px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
                .nav-brand { font-weight: 800; letter-spacing: 2px; color: var(--text); font-size: 1.2em; }
                .nav-brand span { color: var(--accent); }
                .nav-links { display: flex; gap: 15px; }
                .nav-btn { text-decoration: none; font-weight: 600; font-size: 0.9em; padding: 8px 16px; border-radius: 4px; color: var(--text-muted); transition: all 0.2s; border: 1px solid transparent; }
                .nav-active { color: var(--accent); border: 1px solid var(--accent); background: var(--accent-glow); }
                .nav-btn:hover:not(.nav-active) { color: var(--text); border: 1px solid var(--border); }
                
                .container { max-width: 1000px; margin: 0 auto; padding: 0 20px; }
                .header-title { font-size: 1.8em; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }
                .header-sub { color: var(--text-muted); font-size: 0.9em; margin-bottom: 30px; letter-spacing: 0.5px; text-transform: uppercase; }
                
                .grid-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;}
                @media (max-width: 768px) { .grid-layout { grid-template-columns: 1fr; } }
                
                .glass-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 30px; position: relative; overflow: hidden; }
                .glass-card::before { content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px; background: linear-gradient(90deg, transparent, var(--border), transparent); }
                
                .card-title { font-size: 0.85em; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-muted); font-weight: 600; margin-bottom: 15px; display: block;}
                .big-money { font-size: 3em; font-weight: 700; color: var(--text); margin: 10px 0; font-family: 'Courier New', monospace; letter-spacing: -1px;}
                
                .divider { height: 1px; background: var(--border); margin: 25px 0; }
                
                .slider-container { margin: 30px 0; }
                .slider-label { display: flex; justify-content: space-between; margin-bottom: 15px; font-weight: 600; font-size: 0.9em; color: var(--text); text-transform: uppercase; letter-spacing: 1px;}
                input[type=range] { -webkit-appearance: none; width: 100%; background: transparent; }
                input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; height: 16px; width: 16px; border: 2px solid var(--accent); background: var(--bg); cursor: pointer; margin-top: -6px; box-shadow: 0 0 10px var(--accent-glow); border-radius: 0; transform: rotate(45deg);}
                input[type=range]::-webkit-slider-runnable-track { width: 100%; height: 2px; cursor: pointer; background: var(--border); }
                
                .roi-item { background: #05070a; border: 1px solid var(--border); padding: 20px; border-radius: 4px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid var(--accent); }
                .roi-info h4 { margin: 0 0 8px 0; color: var(--text); font-size: 1em; text-transform: uppercase; letter-spacing: 1px;}
                .roi-info p { margin: 0; color: var(--text-muted); font-size: 0.85em; line-height: 1.4;}
                .roi-badge { background: var(--card); border: 1px solid var(--border); color: var(--accent); padding: 10px 15px; font-weight: 600; text-align: right; font-family: 'Courier New', monospace; font-size: 0.9em;}
            </style>
        </head>
        <body>
            <div class="navbar">
                <div class="nav-brand">XM.UM <span>GRID NODE</span></div>
                <div class="nav-links">
                    <a href="/" class="nav-btn">TELEMETRY</a>
                    <a href="/analysis" class="nav-btn nav-active">ROI SIMULATOR</a>
                </div>
            </div>
            
            <div class="container">
                <div class="header-title">Predictive ROI Intelligence</div>
                <div class="header-sub">Financial Forecasting Engine</div>
                
                <div class="grid-layout">
                    <!-- Base Cost Extrapolation -->
                    <div class="glass-card">
                        <span class="card-title">PROJECTED YEARLY METRICS</span>
                        <div class="big-money" style="color: var(--text);">RM <span id="val-yearly-cost">0.00</span></div>
                        <p style="color: var(--text-muted); margin:0; font-size: 0.85em; text-transform: uppercase;">Based on live active load tracking.</p>
                        
                        <div class="divider"></div>
                        
                        <span class="card-title" style="color: var(--warning);">IDENTIFIED PHANTOM LEAKAGE</span>
                        <div style="font-size: 1.5em; font-family: 'Courier New', monospace; font-weight:bold; color: var(--warning);">RM <span id="val-wasted">0.00</span> / YR</div>
                    </div>
                    
                    <!-- Interactive What-If Simulator -->
                    <div class="glass-card" style="border-top: 2px solid var(--accent);">
                        <span class="card-title" style="color: var(--accent);">WHAT-IF SAVINGS SIMULATOR</span>
                        <p style="color: var(--text-muted); font-size: 0.85em; margin-bottom: 25px; line-height: 1.5;">Simulate financial impact of automated load shedding and off-peak shifting.</p>
                        
                        <div class="slider-container">
                            <div class="slider-label">
                                <span>TARGET REDUCTION</span>
                                <span id="slider-val-display" style="color: var(--accent);">0%</span>
                            </div>
                            <input type="range" id="savings-slider" min="0" max="40" value="0" step="5">
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 35px;">
                            <div>
                                <span style="font-size: 0.75em; color:var(--text-muted); text-transform:uppercase; font-weight:bold; letter-spacing: 1px;">OPTIMIZED FORECAST</span><br>
                                <span style="font-size: 1.8em; font-weight: 700; color: var(--text); font-family:'Courier New', monospace;">RM <span id="optimized-bill">0.00</span></span>
                            </div>
                            <div style="text-align: right;">
                                <span style="font-size: 0.75em; color:var(--text-muted); text-transform:uppercase; font-weight:bold; letter-spacing: 1px;">NET SAVINGS</span><br>
                                <span style="font-size: 1.5em; font-weight: 700; color: var(--success); font-family:'Courier New', monospace;">+RM <span id="slider-savings">0.00</span></span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Smart Hardware Upgrades ROI -->
                <div class="glass-card">
                    <span class="card-title">HARDWARE UPGRADE ANALYSIS</span>
                    <p style="color: var(--text-muted); margin-bottom: 25px; font-size: 0.9em;">Payback periods calculated using user-specific NILM signatures and tariff rates.</p>
                    
                    <div class="roi-item">
                        <div class="roi-info">
                            <h4>DEPLOY XM.UM SMART RELAY</h4>
                            <p>CAPEX: RM 45.00<br>Automated phantom load elimination.</p>
                        </div>
                        <div class="roi-badge">
                            PAYBACK<br>
                            <span style="font-size: 1.4em; color: var(--text);" id="roi-relay">CALC...</span>
                        </div>
                    </div>
                    
                    <div class="roi-item" style="border-left-color: #374151;">
                        <div class="roi-info">
                            <h4>HVAC INVERTER UPGRADE</h4>
                            <p>CAPEX: RM 1,800.00<br>Based on detected high-tier thermal loads.</p>
                        </div>
                        <div class="roi-badge" style="color: var(--text-muted);">
                            PAYBACK<br>
                            <span style="font-size: 1.4em; color: var(--text);">14 MO</span>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                let baseYearlyCost = 0.0;
                let phantomWastedYearly = 0.0;

                const elYearlyCost = document.getElementById('val-yearly-cost');
                const elWasted = document.getElementById('val-wasted');
                const slider = document.getElementById('savings-slider');
                const elSliderVal = document.getElementById('slider-val-display');
                const elOptimized = document.getElementById('optimized-bill');
                const elSavings = document.getElementById('slider-savings');
                const elRoiRelay = document.getElementById('roi-relay');

                function updateSimulatorUI() {
                    const reductionPercent = parseInt(slider.value);
                    elSliderVal.innerText = reductionPercent + '%';
                    
                    const savingsAmount = baseYearlyCost * (reductionPercent / 100.0);
                    const newBill = baseYearlyCost - savingsAmount;
                    
                    elOptimized.innerText = newBill.toFixed(2);
                    elSavings.innerText = savingsAmount.toFixed(2);
                }

                slider.addEventListener('input', updateSimulatorUI);

                setInterval(async () => {
                    try {
                        const response = await fetch('/api/behavior');
                        const data = await response.json();
                        
                        if(data.projected_yearly_rm > 0) {
                            baseYearlyCost = data.projected_yearly_rm;
                            phantomWastedYearly = (data.wasted_rm * 365); 
                            
                            elYearlyCost.innerText = baseYearlyCost.toFixed(2);
                            elWasted.innerText = phantomWastedYearly.toFixed(2);
                            
                            if(phantomWastedYearly > 0.5) {
                                let monthsToPayoff = (45.0 / (phantomWastedYearly / 12.0));
                                elRoiRelay.innerText = monthsToPayoff.toFixed(1) + " MO";
                            } else {
                                elRoiRelay.innerText = "N/A";
                            }
                            
                            updateSimulatorUI();
                        }
                    } catch (err) {}
                }, 2000);
            </script>
        </body>
    </html>
    """
    return html_content
