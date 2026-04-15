import base64
import requests
import os

logos = {
    "google": "https://raw.githubusercontent.com/devicons/devicon/master/icons/google/google-original.svg",
    "ibm": "https://raw.githubusercontent.com/devicons/devicon/master/icons/ibm/ibm-original.svg",
    "michigan": "https://upload.wikimedia.org/wikipedia/commons/9/93/University_of_Michigan_Official_Logo.svg",
    "cisco": "https://raw.githubusercontent.com/devicons/devicon/master/icons/cisco/cisco-original.svg",
    "azure": "https://raw.githubusercontent.com/devicons/devicon/master/icons/azure/azure-original.svg"
}

def get_base64_svg(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # If it's an SVG, we can just embed it or convert to base64
            encoded = base64.b64encode(response.content).decode('utf-8')
            return f"data:image/svg+xml;base64,{encoded}"
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return ""

# Map of logo names to their data URIs
data_uris = {}
for name, url in logos.items():
    print(f"Fetching {name}...")
    data_uris[name] = get_base64_svg(url)

svg_template = f"""<svg fill="none" viewBox="0 0 1000 600" width="1000" height="600" xmlns="http://www.w3.org/2000/svg">
  <rect width="1000" height="600" rx="16" fill="#0d1117"/>
  <foreignObject width="1000" height="600">
    <div xmlns="http://www.w3.org/1999/xhtml">
      <style>
        .container {{
          width: 1000px;
          height: 600px;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          grid-template-rows: repeat(3, 1fr);
          gap: 20px;
          padding: 20px;
          box-sizing: border-box;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        }}
        .card {{
          background: #161b22;
          border: 1px solid #30363d;
          border-radius: 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 15px;
        }}
        .logo-box {{
          background: #0d1117;
          width: 180px;
          height: 70px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 12px;
          padding: 10px;
        }}
        .title {{ color: #f0f6fc; font-size: 16px; font-weight: 700; margin-bottom: 4px; text-align: center; }}
        .subtitle {{ color: #8b949e; font-size: 12px; text-align: center; }}
        .logo-img {{ max-width: 100%; max-height: 100%; }}
        .white-filter {{ filter: brightness(0) invert(1); }}
      </style>
      <div class="container">
        <div class="card">
          <div class="logo-box"><img class="logo-img" src="{data_uris['google']}"/></div>
          <div class="title">Data Analytics</div>
          <div class="subtitle">Google Professional</div>
        </div>
        <div class="card">
          <div class="logo-box"><img class="logo-img" src="{data_uris['google']}"/></div>
          <div class="title">UX Design</div>
          <div class="subtitle">Google Professional</div>
        </div>
        <div class="card">
          <div class="logo-box"><img class="logo-img white-filter" src="{data_uris['ibm']}"/></div>
          <div class="title">AI Engineering</div>
          <div class="subtitle">IBM Professional</div>
        </div>
        <div class="card">
          <div class="logo-box"><div style="color:white; font-weight:bold; font-size:16px;">YES4Youth / CapaCiTi</div></div>
          <div class="title">Professional Development</div>
          <div class="subtitle">Enterprise Track</div>
        </div>
        <div class="card">
          <div class="logo-box"><img class="logo-img" src="{data_uris['michigan']}"/></div>
          <div class="title">Python for Everybody</div>
          <div class="subtitle">University of Michigan</div>
        </div>
        <div class="card">
          <div class="logo-box"><div style="color:#FF9D00; font-weight:bold; font-size:18px;">DeepLearning.AI</div></div>
          <div class="title">Machine Learning</div>
          <div class="subtitle">DeepLearning.AI</div>
        </div>
        <div class="card">
          <div class="logo-box"><div style="color:#58a6ff; font-weight:bold; font-size:24px;">Ai</div></div>
          <div class="title">Generative AI Specialist</div>
          <div class="subtitle">Applied Intelligence</div>
        </div>
        <div class="card">
          <div class="logo-box"><img class="logo-img white-filter" src="{data_uris['cisco']}"/></div>
          <div class="title">Cybersecurity Specialist</div>
          <div class="subtitle">Cisco Academy</div>
        </div>
        <div class="card">
          <div class="logo-box"><img class="logo-img" src="{data_uris['azure']}"/><span style="color:white; margin-left:8px; font-weight:bold;">Azure</span></div>
          <div class="title">Cloud Infrastructure</div>
          <div class="subtitle">Azure Solution Associate</div>
        </div>
      </div>
    </div>
  </foreignObject>
</svg>"""

with open("assets/specialized_learning.svg", "w", encoding="utf-8") as f:
    f.write(svg_template)

print("Created assets/specialized_learning.svg with embedded logos.")
