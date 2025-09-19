import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the data
df = pd.read_csv('convert_data.csv')

# Create the plot
plt.figure(figsize=(12, 8))
plt.plot(df['season'], df['bdv_converted_this_season'] / 1e6, marker='o', linewidth=2, markersize=6)
plt.title('BDV Converted This Season by Season', fontsize=16, fontweight='bold')
plt.xlabel('Season', fontsize=12)
plt.ylabel('BDV Converted This Season (Millions)', fontsize=12)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('bdv_by_season.png', dpi=300, bbox_inches='tight')
plt.show()

print(f"Season range: {df['season'].min()} - {df['season'].max()}")
print(f"Peak BDV converted: {df['bdv_converted_this_season'].max():,.0f} in season {df.loc[df['bdv_converted_this_season'].idxmax(), 'season']}")