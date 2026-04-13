import urllib.request
import os

def fetch_and_save_stats():
    # URL for the stats image
    stats_url = "https://github-readme-stats.vercel.app/api?username=Raphasha27&show_icons=true&title_color=0EA5E9&icon_color=0EA5E9&text_color=cbd5e1&bg_color=0d1117&hide_border=true&include_all_commits=true"
    
    try:
        print(f"Fetching stats from: {stats_url}")
        # Create request with a user agent to avoid being blocked
        req = urllib.request.Request(
            stats_url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        with urllib.request.urlopen(req) as response:
            data = response.read()
            
        # Ensure assets directory exists
        os.makedirs("assets", exist_ok=True)
        
        # Save to file
        output_path = "assets/github_stats.svg"
        with open(output_path, "wb") as f:
            f.write(data)
            
        print(f"Successfully saved stats to {output_path}")
        
    except Exception as e:
        print(f"Error fetching stats: {e}")

if __name__ == "__main__":
    fetch_and_save_stats()
