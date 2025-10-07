import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style for better-looking plots
plt.style.use('default')
sns.set_palette("husl")

# Read the data
df = pd.read_csv('convert_data.csv')

# Create figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle('Convert System Analysis - Season 7065-7114', fontsize=16, fontweight='bold')

# 1. Convert Capacity Growth Over Time
axes[0, 0].plot(df['step'], df['convert_capacity_factor'] / 1e6, marker='o', linewidth=2, markersize=4)
axes[0, 0].set_title('Convert Capacity Factor Growth')
axes[0, 0].set_xlabel('Step')
axes[0, 0].set_ylabel('Capacity Factor (Millions)')
axes[0, 0].grid(True, alpha=0.3)

# 2. Max Convert Capacity vs BDV Converted This Season
axes[0, 1].scatter(df['max_convert_capacity'] / 1e6, df['bdv_converted_this_season'] / 1e6, 
                   alpha=0.7, s=50, c=df['step'], cmap='viridis')
axes[0, 1].set_title('Max Capacity vs BDV Converted')
axes[0, 1].set_xlabel('Max Convert Capacity (Millions)')
axes[0, 1].set_ylabel('BDV Converted This Season (Millions)')
axes[0, 1].grid(True, alpha=0.3)

# 3. Bonus Stalk Per BDV Decay
axes[1, 0].plot(df['step'], df['bonus_stalk_per_bdv'] / 1e9, marker='s', 
                linewidth=2, markersize=4, color='orange')
axes[1, 0].set_title('Bonus Stalk Per BDV Decay')
axes[1, 0].set_xlabel('Step')
axes[1, 0].set_ylabel('Bonus Stalk per BDV (Billions)')
axes[1, 0].grid(True, alpha=0.3)

# 4. Convert Activity Heatmap (BDV Converted This vs Last Season)
axes[1, 1].scatter(df[' bdv_converted_last_season'] / 1e6, df['bdv_converted_this_season'] / 1e6,
                   alpha=0.7, s=60, c=df['season'], cmap='plasma')
axes[1, 1].plot([0, 200], [0, 200], '--', color='gray', alpha=0.5, label='Equal Convert Line')
axes[1, 1].set_title('Convert Activity: This vs Last Season')
axes[1, 1].set_xlabel('BDV Converted Last Season (Millions)')
axes[1, 1].set_ylabel('BDV Converted This Season (Millions)')
axes[1, 1].legend()
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('convert_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Additional analysis plots
fig2, axes2 = plt.subplots(1, 2, figsize=(15, 6))
fig2.suptitle('Convert System Detailed Analysis', fontsize=16, fontweight='bold')

# Convert utilization rate
utilization_rate = (df['bdv_converted_this_season'] / df['max_convert_capacity']) * 100
axes2[0].plot(df['step'], utilization_rate, marker='o', linewidth=2, color='green')
axes2[0].set_title('Convert Capacity Utilization Rate')
axes2[0].set_xlabel('Step')
axes2[0].set_ylabel('Utilization Rate (%)')
axes2[0].grid(True, alpha=0.3)

# Season progression
axes2[1].bar(range(len(df)), df['season'] - df['season'].min(), alpha=0.7, color='purple')
axes2[1].set_title('Season Progression')
axes2[1].set_xlabel('Step')
axes2[1].set_ylabel('Season Number (Relative)')
axes2[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('convert_detailed_analysis.png', dpi=300, bbox_inches='tight')
plt.show()

# Print key statistics
print("=== Convert System Analysis Summary ===")
print(f"Season Range: {df['season'].min()} - {df['season'].max()}")
print(f"Steps Analyzed: {len(df)}")
print(f"Max Convert Capacity Peak: {df['max_convert_capacity'].max():,.0f}")
print(f"Max BDV Converted in Single Season: {df['bdv_converted_this_season'].max():,.0f}")
print(f"Average Utilization Rate: {utilization_rate.mean():.1f}%")
print(f"Bonus Stalk Decay: {df['bonus_stalk_per_bdv'].iloc[0]:,.0f} → {df['bonus_stalk_per_bdv'].iloc[-1]:,.0f}")