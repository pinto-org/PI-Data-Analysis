import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the data
df = pd.read_csv('convert_data.csv')

# Filter to only season 7300 and below
df = df[df['season'] <= 7300]

# Create figure with 6 subplots (2 rows, 3 columns)
fig, axes = plt.subplots(2, 3, figsize=(18, 12))
fig.suptitle('Convert System Parameters by Season', fontsize=16, fontweight='bold')

# 1. Convert Capacity Factor
axes[0, 0].plot(df['season'], df['convert_capacity_factor'] / 1e6, marker='o', linewidth=2, markersize=4, color='blue')
axes[0, 0].set_title('Convert Capacity Factor')
axes[0, 0].set_xlabel('Season')
axes[0, 0].set_ylabel('Capacity Factor (Millions)')
axes[0, 0].grid(True, alpha=0.3)

# 2. Max Convert Capacity
axes[0, 1].plot(df['season'], df['max_convert_capacity'] / 1e6, marker='o', linewidth=2, markersize=4, color='green')
axes[0, 1].set_title('Max Convert Capacity')
axes[0, 1].set_xlabel('Season')
axes[0, 1].set_ylabel('Max Capacity (Millions)')
axes[0, 1].grid(True, alpha=0.3)

# 3. Bonus Stalk Per BDV
axes[0, 2].plot(df['season'], df['bonus_stalk_per_bdv'] / 1e9, marker='o', linewidth=2, markersize=4, color='orange')
axes[0, 2].set_title('Bonus Stalk Per BDV')
axes[0, 2].set_xlabel('Season')
axes[0, 2].set_ylabel('Bonus Stalk per BDV (Billions)')
axes[0, 2].grid(True, alpha=0.3)

# 4. BDV Converted This Season
axes[1, 0].plot(df['season'], df['bdv_converted_this_season'] / 1e6, marker='o', linewidth=2, markersize=4, color='red')
axes[1, 0].set_title('BDV Converted This Season')
axes[1, 0].set_xlabel('Season')
axes[1, 0].set_ylabel('BDV Converted (Millions)')
axes[1, 0].grid(True, alpha=0.3)

# 5. BDV Converted Last Season
axes[1, 1].plot(df['season'], df[' bdv_converted_last_season'] / 1e6, marker='o', linewidth=2, markersize=4, color='purple')
axes[1, 1].set_title('BDV Converted Last Season')
axes[1, 1].set_xlabel('Season')
axes[1, 1].set_ylabel('BDV Converted (Millions)')
axes[1, 1].grid(True, alpha=0.3)

# 6. Last Convert Bonus Taken (omit zeros)
bonus_non_zero = df[df[' last_convert_bonus_taken'] > 0]
axes[1, 2].plot(bonus_non_zero['season'], bonus_non_zero[' last_convert_bonus_taken'] / 1e9, marker='o', linewidth=2, markersize=4, color='brown')
axes[1, 2].set_title('Last Convert Bonus Taken (Non-Zero)')
axes[1, 2].set_xlabel('Season')
axes[1, 2].set_ylabel('Bonus Taken (Billions)')
axes[1, 2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('all_params_by_season.png', dpi=300, bbox_inches='tight')
plt.show()

# Print summary statistics
print("=== Parameter Summary by Season ===")
print(f"Season Range: {df['season'].min()} - {df['season'].max()}")
print(f"Total Seasons: {len(df)}")
print(f"\nPeak Values:")
print(f"Convert Capacity Factor: {df['convert_capacity_factor'].max():,.0f}")
print(f"Max Convert Capacity: {df['max_convert_capacity'].max():,.0f}")
print(f"BDV Converted This Season: {df['bdv_converted_this_season'].max():,.0f}")
print(f"Last Convert Bonus: {df[' last_convert_bonus_taken'].max():,.0f}")