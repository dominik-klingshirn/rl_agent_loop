import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# -- project imports --
from .config import Config



def get_status_counts(
        campaign_path:str|Path, 
        model_name:str|Path, 
        num_iterations:int = 15, 
        num_seeds:int =3
        )-> pd.DataFrame:
    """
    Returns a pandas dataframe containing the distribution of semantic terminal status tags for every agent trained for every iteration
    e.g.
    
        iteration	seed	landed_centered	landed_off_centered	landed_but_slid_into_valley.....
    0	1	        0	        1.0	            0.0	            3.0	            
    1	1	        1	        5.0	            0.0	            2.0	    
    2	1	        2	        2.0	            0.0	            0.0	    
    3	2	        0	        0.0	            0.0	            0.0	   
    4	2	        1	        0.0	            0.0	            0.0	   

    """
    
    
    records = []
    for iteration in range(1,num_iterations+1):
        for seed in range(num_seeds):
            path = campaign_path / model_name /'telemetry' / f"iteration_{iteration:02d}" / f"iter{iteration:02d}_seed{seed}_eval.csv"
            
            # Check if the file exists (optional but safe)
            if not path.exists():
                print(f"Warning: {path} does not exist")
                continue
            
           
            try:
                df = pd.read_csv(path, encoding='latin1')
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding='utf-8', errors='replace')
            
            # Clean column names
            df.columns = df.columns.str.strip()
            
            # Verify 'status' column exists
            if 'status' not in df.columns:
                print(f"Warning: 'status' column missing in {path}. Columns: {df.columns.tolist()}")
                continue
            
            df_filtered = df[df['status'] != 'active']
            vc = df_filtered['status'].value_counts(normalize=False)
            vc_dict = vc.to_dict()

            record = {
                'iteration': iteration,
                'seed': seed,
                'landed_centered': vc_dict.get('landed_centered',0.0),
                'landed_off_centered': vc_dict.get('landed_off_centered',0.0),
                'landed_but_slid_into_valley': vc_dict.get('landed_but_slid_into_valley',0.0),
                'landed_off_centered_timeout':vc_dict.get("landed_off_centered_timeout",0.0),
                'hover_timeout':vc_dict.get('hover_timeout',0.0),
                'out_of_bounds':vc_dict.get('out_of_bounds',0.0),
                'crashed': vc_dict.get('crashed',0.0),
            }
            records.append(record)

    # Create final DataFrame
    results_df = pd.DataFrame(records)

    return results_df


def plot_landing_distribution(
        status_counts_dataframe:pd.DataFrame,
        campaign_path:str|Path,
        init_func:str,
        model_name:str,
        save_file:bool=False):

    # Lists of the different semantic terminal status tags
    all_statuses = ['landed_off_centered', 'landed_centered', 'landed_but_slid_into_valley',\
                    'landed_off_centered_timeout','hover_timeout' ,'out_of_bounds','crashed' ]
    no_land_statuses= ['hover_timeout','out_of_bounds','crashed']

    land_statuses=['landed_off_centered', 'landed_centered', 'landed_but_slid_into_valley','landed_off_centered_timeout']

    off_land_statuses=['landed_off_centered', 'landed_but_slid_into_valley','landed_off_centered_timeout']

    other_statuses=['hover_timeout','out_of_bounds']

    sc_df = status_counts_dataframe.copy()

    groupby_df = sc_df.groupby('iteration')[all_statuses].sum()
    groupby_df['imperfect_landings'] = groupby_df['landed_off_centered'] + groupby_df['landed_off_centered_timeout'] + groupby_df['landed_but_slid_into_valley']
    groupby_df['other_fails'] = groupby_df['hover_timeout'] + groupby_df['out_of_bounds']
    groupby_df['landing_rate'] = groupby_df[land_statuses].sum(axis=1) / groupby_df[all_statuses].sum(axis=1)

    df = pd.DataFrame({
    'Iteration':           groupby_df.index.to_list(),
    'Centered Landing':    groupby_df['landed_centered'],
    'Off-Center Landing':  groupby_df['imperfect_landings'],
    'Hover Timeout':       groupby_df['hover_timeout'],
    'Out of Bounds':       groupby_df['out_of_bounds'],
    'Crash':               groupby_df['crashed']
})
    iterations = df['Iteration'].to_list()
    df.set_index('Iteration', inplace=True)

    # --- 2. COLOR PALETTE FOR POSTER ---
    # Strategic colors: Success = Blues/Teals, Fails = Reds, Timeouts = Grays
    colors = {
        'Centered Landing':  '#2ca02c',   # Green   — success
        'Off-Center Landing':'#1f77b4',   # Blue    — partial success
        'Hover Timeout':     '#ff7f0e',   # Orange  — agent passive/paralyzed
        'Out of Bounds':     '#9467bd',   # Purple  — agent unconstrained/escaping
        'Crash':             '#d62728',   # Red     — catastrophic failure
    }

    # --- 3. FIGURE SETUP ---
    # Create 2 subplots, stacked vertically, sharing the X-axis
    fig, (ax1, ax2) = plt.subplots(nrows=2, ncols=1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1.5]})
    plt.subplots_adjust(hspace=0.1) # Bring plots closer together

    # --- 4. TOP PLOT: STACKED BAR CHART ---
    df.plot(kind='bar', stacked=True, ax=ax1, color=[colors[col] for col in df.columns], width=0.7)
    ax1.set_ylabel('Number of Episodes', fontsize=12, fontweight='bold')
    ax1.set_title(f'Autonomous Correction | {init_func} | {model_name}', fontsize=16, pad=15)
    ax1.legend(loc='upper right', bbox_to_anchor=(1.22, 1), fontsize=10) # Move legend outside
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # --- 5. BOTTOM PLOT: LINE CHART ---
    ax2.plot(df.index-1, groupby_df['landing_rate'], color='#1f77b4', linewidth=3, marker='o', markersize=6)
    ax2.set_ylabel('Landing Rate', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Autonomous Pipeline Iteration', fontsize=12, fontweight='bold')
    ax2.set_ylim(-0.05, 1.05)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)

    # Ensure x-axis ticks match iterations perfectly
    ax2.set_xticks(range(len(iterations)))
    ax2.set_xticklabels(iterations, rotation=0)

    #fig.suptitle('Autonomous Correction', fontsize=20)
    # --- 6. ANNOTATIONS & CALLOUTS (The "Data Story") ---
    # Draw a vertical line denoting the pivot
    #max_idx = groupby_df['landing_rate'].idxmax()
    #ax2.axvline(x=5.5, color='black', linestyle='--', linewidth=2, alpha=0.7) # x=2.5 because index is 0-based in bar charts

    """# Annotation 1: The Fix
    ax2.annotate('Max. Learning Rate', 
                xy=(max_idx, 0.63), xycoords='data',
                xytext=(4.5, 0.2), textcoords='data',
                arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="black", lw=1),
                fontsize=10, fontweight='bold', ha='center')

    # Annotation 2: The Peak
    ax2.annotate('Local Optimum Reached\n93% Success Rate', 
                xy=(8, 0.93), xycoords='data',
                xytext=(8, 0.5), textcoords='data',
                arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="black", lw=1),
                fontsize=10, fontweight='bold', ha='center')

    # Annotation 3: Regression & Recovery
    ax2.annotate('System Resilience\nValidator detects regression,\nrolls back constraints.', 
                xy=(9.5, 0.53), xycoords='data',
                xytext=(11.5, 0.2), textcoords='data',
                arrowprops=dict(facecolor='black', shrink=0.05, width=1.5, headwidth=8),
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="black", lw=1),
                fontsize=10, fontweight='bold', ha='center')"""



    if save_file:
        save_path = campaign_path / model_name/ f'all_iterations_{model_name}.png'
        #plt.savefig(save_path, format='svg', bbox_inches='tight')
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Campaign Summary Plot Saved at: {save_path} ")
 

def main():
    campaign_path = Path("experiments") / Config.CAMPAIGN_TAG 
    num_iterations = Config.TOTAL_ITERATIONS
    init_func = Config.INITIAL_FUNC
    model_name=Config.LLM_MODEL.replace(":", "-")
   

    status_counts_df = get_status_counts(
        campaign_path=campaign_path,
        model_name=model_name,
        num_iterations=num_iterations
    )
    if status_counts_df.empty:
        print("❌ No telemetry CSVs found. Check campaign path and iteration count.")
        print(f"   Looked in: {campaign_path / model_name / 'telemetry'}")
        sys.exit(1)

    plot_landing_distribution(
        status_counts_dataframe=status_counts_df,
        campaign_path=campaign_path,
        init_func=init_func,
        model_name=model_name,
        save_file=True
    )
    

if __name__ == "__main__":
    main()