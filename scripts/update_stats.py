import requests
import os

def fetch_and_save_stats():
    # URL for the stats image (using the user's existing config)
    stats_url = "https://github-readme-stats.vercel.app/api?username=Raphasha27&show_icons=true&title_color=0EA5E9&icon_color=0EA5E9&text_color=cbd5e1&bg_color=0d1117&hide_border=true&include_all_commits=true"
    
    try:
        print(f"Fetching stats from: {stats_url}")
        response = requests.get(stats_url)
        response.raise_for_status()
        
        # Ensure assets directory exists
        os.makedirs("assets", exist_ok=True)
        
        # Save to file
        output_path = "assets/github_stats.svg"
        with open(output_path, "wb") as f:
            f.write(response.content)
            
        print(f"Successfully saved stats to {output_path}")
        
    except Exception as e:
        print(f"Error fetching stats: {e}")
        # We don't exit with error to avoid failing the workflow if the API is temporarily down
        # The previous image will remain.

if __name__ == "__main__":
    fetch_and_save_stats()
