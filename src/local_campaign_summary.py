import argparse
import subprocess
import sys
from pathlib import Path

def local_campaign_summary():
    print(f"💻 [Local-Manager] Plotting Campaign Summary")

    try:
        script_dir = Path(__file__).parent.resolve()
        plot_script = script_dir / "plot_campaign_summary.py"
        cmd = f"python3 {plot_script}"
        subprocess.run(cmd, shell=True, check=True)
        print(f"✅ Local Plotting Campaign Summary Complete.")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Critical Failure During Campaign Summary Plotting {e}")
        sys.exit(1)

if __name__ == "__main__":
    local_campaign_summary()