#!/usr/bin/env python3

import urllib.request
import urllib.error
import json
import sys
import ssl

# Create SSL context to handle certificate issues
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

SUBGRAPH_URL = "https://graph.pinto.money/pinto"

def fetch_all_seasons():
    """Fetch all available seasons from the subgraph to auto-detect range"""
    query = """
    query GetAllSeasons {
        seasons(first: 10000, orderBy: season, orderDirection: desc) {
            season
        }
    }
    """
    
    try:
        request_data = json.dumps({"query": query}).encode('utf-8')
        request = urllib.request.Request(
            SUBGRAPH_URL,
            data=request_data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(request, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        if "errors" in data:
            print(f"GraphQL errors: {data['errors']}")
            return None, None
        
        seasons = [s["season"] for s in data["data"]["seasons"]]
        return min(seasons), max(seasons)
    
    except Exception as e:
        print(f"Error getting season range: {e}")
        return 2557, 5875  # Fallback

def fetch_season_data(start_season, end_season):
    """Fetch supply data for a range of seasons from the subgraph"""
    all_data = {}
    batch_size = 10000  # GraphQL query limit
    
    print(f"Fetching seasons {start_season} to {end_season} from Pinto subgraph...")
    
    for batch_start in range(start_season, end_season + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, end_season)
        
        query = """
        query GetSeasonSupplies($gte: Int!, $lte: Int!) {
            seasons(
                where: { season_gte: $gte, season_lte: $lte }
                first: 10000
                orderBy: season
                orderDirection: asc
            ) {
                season
                beanHourlySnapshot {
                    supply
                }
            }
        }
        """
        
        variables = {"gte": batch_start, "lte": batch_end}
        
        try:
            # Prepare the request
            request_data = json.dumps({
                "query": query,
                "variables": variables
            }).encode('utf-8')
            
            request = urllib.request.Request(
                SUBGRAPH_URL,
                data=request_data,
                headers={'Content-Type': 'application/json'}
            )
            
            # Execute the request
            with urllib.request.urlopen(request, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                sys.exit(1)
            
            if "data" not in data or "seasons" not in data["data"]:
                print(f"Unexpected response structure: {json.dumps(data, indent=2)}")
                sys.exit(1)
            
            # Process response data
            for season_data in data["data"]["seasons"]:
                season = season_data["season"]
                if season_data.get("beanHourlySnapshot"):
                    supply = int(season_data["beanHourlySnapshot"]["supply"])
                    all_data[season] = supply
            
            print(f"  Fetched seasons {batch_start} to {batch_end} ({len(data['data']['seasons'])} records)")
        
        except Exception as e:
            print(f"Error fetching data from subgraph: {e}")
            sys.exit(1)
    
    return all_data

# Auto-detect season range and fetch data
print("Auto-detecting season range...")
min_season, max_season = fetch_all_seasons()
print(f"Available season range: {min_season} to {max_season}")

# Fetch data from subgraph
known_data = fetch_season_data(min_season, max_season)

def interpolate_supply(start_season, end_season, start_supply, end_supply):
    """Interpolate supply values for missing seasons"""
    seasons = list(range(start_season, end_season + 1))
    if len(seasons) == 1:
        return {start_season: start_supply}
    
    # For missing seasons, add 1 for each missing season
    result = {}
    for i, season in enumerate(seasons):
        if i == 0:
            result[season] = start_supply
        elif season == end_season:
            result[season] = end_supply
        else:
            # Add 1,000,000 for each missing season
            result[season] = start_supply + (i * 1000000)
    
    return result

def detect_gaps(seasons, min_gap_size=50):
    """Detect gaps in season data where there are large jumps"""
    gaps = []
    sorted_seasons = sorted(seasons)
    
    for i in range(len(sorted_seasons) - 1):
        current = sorted_seasons[i]
        next_season = sorted_seasons[i + 1]
        gap_size = next_season - current - 1
        
        if gap_size >= min_gap_size:
            gaps.append({
                'start': current,
                'end': next_season,
                'gap_start': current + 1,
                'gap_end': next_season - 1,
                'gap_size': gap_size
            })
    
    return gaps

# Generate complete dataset
complete_data = {}

# Sort known seasons and detect gaps
known_seasons = sorted(known_data.keys())
first_season = 2558
last_season = 5875

print(f"Data range: seasons {first_season} to {last_season}")

# Detect gaps automatically
gaps = detect_gaps(known_seasons)
print(f"Detected {len(gaps)} gaps:")
for gap in gaps:
    print(f"  Gap: seasons {gap['gap_start']} to {gap['gap_end']} ({gap['gap_size']} missing seasons)")

# Fill in data between known points
for i in range(len(known_seasons) - 1):
    current_season = known_seasons[i]
    next_season = known_seasons[i + 1]
    current_supply = known_data[current_season]
    
    # Add known data point
    complete_data[current_season] = current_supply
    
    # Check if this is a small gap (interpolate) or large gap (use fixed increment)
    gap_size = next_season - current_season - 1
    if gap_size > 0:
        if gap_size < 50:  # Small gap - interpolate
            next_supply = known_data[next_season]
            for missing_season in range(current_season + 1, next_season):
                # Linear interpolation
                progress = (missing_season - current_season) / (next_season - current_season)
                interpolated_supply = current_supply + (next_supply - current_supply) * progress
                complete_data[missing_season] = int(interpolated_supply)
        else:  # Large gap - use fixed increment
            for missing_season in range(current_season + 1, next_season):
                # Add 1,000,000 for each missing season
                complete_data[missing_season] = current_supply + ((missing_season - current_season) * 1000000)

# Add the last known data point
complete_data[known_seasons[-1]] = known_data[known_seasons[-1]]

# Create CSV content
csv_lines = ["season,supply_formatted,calculated_value,cumulative_sum"]
cumulative_sum = 0.0

for season in range(first_season, last_season + 1):
    supply_unformatted = complete_data[season]
    supply_formatted = supply_unformatted / 1000000  # Convert to millions for readability
    calculated_value = supply_formatted * 416666666666667 / 1e18
    cumulative_sum += calculated_value

    print(f"Season {season}: {supply_formatted:.6f} {calculated_value:.6f} {cumulative_sum:.6f}")
    
    csv_lines.append(f"{season},{supply_formatted:.6f},{calculated_value:.6f},{cumulative_sum:.6f}")

# Write to file
output_filename = f'pinto_complete_seasons_{first_season}_to_{last_season}.csv'
with open(output_filename, 'w') as f:
    f.write('\n'.join(csv_lines))

print(f"Generated complete dataset with {len(csv_lines)-1} seasons")
print(f"From season {first_season} to {last_season}")
print(f"Output file: {output_filename}")
print(f"Final cumulative sum: {cumulative_sum:.6f}")
