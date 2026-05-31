from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# 1. Global variable to store the latest reading from the ESP32
latest_reading = {
    "timestamp": "Waiting for ESP32 connection...",
    "power": 0.0,
    "voltage": 0.0,
    "current": 0.0
}

# 2. Define the exact shape of the data the ESP32 is sending
class SensorData(BaseModel):
    timestamp: str
    power: float
    voltage: float
    current: float

# 3. The POST route: The ESP32 silently sends data here every 2 seconds
@app.post("/sensor")
async def receive_sensor_data(data: SensorData):
    global latest_reading
    # Update our global dictionary with the fresh data
    latest_reading = {
        "timestamp": data.timestamp,
        "power": data.power,
        "voltage": data.voltage,
        "current": data.current
    }
    print(f"[Cloud Log] Updated: {latest_reading['power']} W")
    return {"status": "success"}

# 4. The GET route: This is what YOU see when you open the URL in a browser
@app.get("/", response_class=HTMLResponse)
async def view_dashboard():
    # A clean, professional HTML/CSS layout that automatically refreshes
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>XM.UM Cloud Monitor</title>
            <meta http-equiv="refresh" content="2">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; color: #2c3e50; text-align: center; padding-top: 50px; }}
                .card {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; text-align: left; min-width: 300px; }}
                h1 {{ color: #2980b9; margin-bottom: 5px; }}
                h3 {{ color: #7f8c8d; margin-top: 0; margin-bottom: 30px; }}
                .row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #ecf0f1; font-size: 1.2em; }}
                .row:last-child {{ border-bottom: none; }}
                .label {{ font-weight: bold; color: #34495e; }}
                .value {{ font-family: monospace; font-size: 1.1em; color: #e74c3c; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>XM.UM Agentic Grid Node</h1>
            <h3>Live Cloud Telemetry</h3>
            
            <div class="card">
                <div class="row">
                    <span class="label">🕒 Timestamp:</span>
                    <span class="value" style="color:#7f8c8d; font-size: 0.9em;">{latest_reading['timestamp']}</span>
                </div>
                <div class="row">
                    <span class="label">⚡ Active Power:</span>
                    <span class="value">{latest_reading['power']} W</span>
                </div>
                <div class="row">
                    <span class="label">🔌 Grid Voltage:</span>
                    <span class="value">{latest_reading['voltage']} V</span>
                </div>
                <div class="row">
                    <span class="label">🌊 Load Current:</span>
                    <span class="value">{latest_reading['current']} A</span>
                </div>
            </div>
        </body>
    </html>
    """
    return html_content
