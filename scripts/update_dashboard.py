
import os
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

def fetch_weather():
    try:
        # OpenMeteo API for Johannesburg (-26.2041, 28.0473)
        url = "https://api.open-meteo.com/v1/forecast?latitude=-26.2041&longitude=28.0473&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def generate_dashboard():
    weather_data = fetch_weather()
    
    # Time in SAST (UTC+2)
    sast_offset = timezone(timedelta(hours=2))
    now = datetime.now(sast_offset)
    current_time = "00:46"
    current_date = now.strftime("%A, %d %b %Y")
    
    # Weather Data
    temp = "N/A"
    condition = "Unknown"
    min_temp = "0"
    max_temp = "0"
    
    if weather_data:
        current = weather_data.get('current_weather', {})
        temp = f"{current.get('temperature', 0)}"
        weather_code = current.get('weathercode', 0)
        
        # Simple WMO code map
        if weather_code == 0: condition = "Clear Sky"
        elif 1 <= weather_code <= 3: condition = "Partly Cloudy"
        elif 45 <= weather_code <= 48: condition = "Foggy"
        elif 51 <= weather_code <= 67: condition = "Rainy"
        elif 71 <= weather_code <= 77: condition = "Snowy"
        elif 80 <= weather_code <= 99: condition = "Stormy"
        else: condition = "Overcast"
        
        daily = weather_data.get('daily', {})
        if daily:
            max_temp = f"{daily.get('temperature_2m_max', [0])[0]}"
            min_temp = f"{daily.get('temperature_2m_min', [0])[0]}"

    # AI "Prediction" Simulation (Cyber text)
    ai_status = "OPTIMAL"
    if "Rain" in condition or "Storm" in condition:
        prediction = "ADVISORY: Precip. detected. Network latency may vary."
        status_color = "#eab308" # Yellow
    elif float(temp) > 30:
        prediction = "ALERT: High thermal load. Cooling systems active."
        status_color = "#ef4444" # Red
    else:
        prediction = "PREDICTION: Systems nominal. Ideal extensive coding conditions."
        status_color = "#22c55e" # Green

    svg_content = f"""<svg fill="none" viewBox="0 0 800 200" width="800" height="200" xmlns="http://www.w3.org/2000/svg">
      <foreignObject width="100%" height="100%">
        <div xmlns="http://www.w3.org/1999/xhtml">
          <style>
            .container {{
              font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
              background: #0d1117;
              border: 1px solid #30363d;
              border-radius: 10px;
              width: 100%;
              height: 200px;
              display: flex;
              justify-content: space-between;
              align-items: center;
              color: #c9d1d9;
              overflow: hidden;
              position: relative;
            }}
            .glass {{
                background: rgba(22, 27, 34, 0.8);
                backdrop-filter: blur(10px);
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                z-index: 0;
            }}
            .content {{
                z-index: 1;
                display: flex;
                width: 100%;
                padding: 20px;
                justify-content: space-between;
            }}
            .left-panel {{
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            .right-panel {{
                text-align: right;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }}
            h1 {{ margin: 0; font-size: 48px; font-weight: 700; color: #38bdf8; text-shadow: 0 0 15px rgba(56, 189, 248, 0.5); }}
            h2 {{ margin: 0; font-size: 20px; color: #8b949e; letter-spacing: 1px; }}
            .weather-box {{ display: flex; align-items: center; gap: 15px; margin-top: 10px; }}
            .temp {{ font-size: 36px; font-weight: bold; color: #e2e8f0; }}
            .condition {{ font-size: 16px; color: #38bdf8; text-transform: uppercase; letter-spacing: 1px; }}
            .prediction {{ 
                margin-top: 15px; 
                font-family: 'Courier New', monospace; 
                font-size: 12px; 
                color: {status_color}; 
                background: rgba(0,0,0,0.3); 
                padding: 8px; 
                border-left: 3px solid {status_color};
            }}
            .location {{ display: flex; align-items: center; justify-content: flex-end; gap: 8px; font-size: 14px; color: #8b949e; margin-bottom: 5px; }}
            .badge {{ 
                background: #1f6feb; 
                color: white; 
                padding: 2px 8px; 
                border-radius: 12px; 
                font-size: 10px; 
                font-weight: bold;
            }}
          </style>
          <div class="container">
            <div class="glass"></div>
            <div class="content">
                <div class="left-panel">
                    <h2>SOUTH AFRICA (SAST)</h2>
                    <h1>{current_time}</h1>
                    <div class="weather-box">
                        <div class="temp">{temp}°C</div>
                        <div>
                            <div class="condition">{condition}</div>
                            <div style="font-size: 12px; color: #8b949e;">H: {max_temp}° L: {min_temp}°</div>
                        </div>
                    </div>
                </div>
                <div class="right-panel">
                    <div class="location">
                        <span>JOHANNESBURG</span>
                        <span class="badge">LIVE</span>
                    </div>
                    <div style="font-size: 14px; color: #c9d1d9; margin-bottom: 20px;">{current_date}</div>
                    <div class="prediction">
                        {prediction}
                        <br/>
                        SYSTEM STATUS: {ai_status}
                    </div>
                </div>
            </div>
          </div>
        </div>
      </foreignObject>
    </svg>
    """
    
    with open("assets/dashboard.svg", "w", encoding="utf-8") as f:
        f.write(svg_content)

if __name__ == "__main__":
    generate_dashboard()
