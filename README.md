XM.UM Agentic Grid Node - Cloud Backend 
This repository contains the cloud intelligence and analytics backend for the XM.UM Agentic Grid Node project. Built with Python and FastAPI, this server acts as the central brain of the Non-Intrusive Load Monitoring (NILM) system. It ingests real-time electrical telemetry from the ESP32 edge node, runs long-term behavioral analytics, and serves the interactive user dashboards.

Live Cloud Dashboard: https://xm-um-backend.onrender.com/

Cloud Provider: Hosted securely on Render

Core Features
1) Real-Time Data Ingestion: Processes live voltage, current, and power streams from the ESP32 hardware via secure HTTPS POST requests.

2) Agentic Behavior Engine: Analyzes long-term consumption patterns to assign AI Behavioral Personas (e.g., "Eco-Minimalist", "Phantom Waster") and prescribes automated energy-saving interventions.

3) Phantom Load Tracking: Automatically detects idle standby devices and translates wasted energy directly into Ringgit Malaysia (RM) and kg CO₂ footprint.

4) Grid Stability Scoring: A dynamic, gamified safety metric that penalizes dangerous peak overloads to protect local grid health.

5) Dual-View Dashboard: Serves clean, responsive HTML dashboards for both raw live telemetry and long-term psychological analytics.
