# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a Python-based data analysis toolkit for the Pinto Protocol convert bonus system. It fetches blockchain data from Pinto's GraphQL subgraphs, processes convert transactions, and analyzes LP<>LP convert patterns for bonus calculations.

**Directory Structure**:
- `src/`: Python source files (data fetching, filtering, and analysis scripts)
- `csv_output/`: All generated CSV output files from the pipeline
- `run_convert_bonus_analysis.sh`: Main pipeline orchestration script

## Core Architecture

### Three-Stage Data Pipeline

1. **Data Fetching** (`fetch_*.py` scripts)
   - Fetch raw data from Pinto Protocol subgraphs
   - Two primary subgraph endpoints:
     - Exchange subgraph: `https://graph.pinto.money/exchange` (convert trades)
     - PintoStalk subgraph: `https://graph.pinto.money/pintostalk` (seeds/stalk data)

2. **Data Processing** (`filter_lp_converts.py`)
   - Identifies LP<>LP convert pairs from raw convert events
   - Matches REMOVE_LIQUIDITY and ADD_LIQUIDITY events by:
     - Same block number and timestamp
     - Matching Pinto amounts (first element of transfer_volume_reserves)

3. **Data Analysis** (parent directory: `visualize_convert_data.py`)
   - Generates visualizations of convert system metrics
   - Analyzes convert capacity, bonus stalk decay, and utilization rates

### Key Data Structures

**Convert Event (raw)**:
- `block_number`, `timestamp`: When convert occurred
- `well_id`: Well contract address
- `trade_type`: REMOVE_LIQUIDITY or ADD_LIQUIDITY
- `transfer_volume_reserves`: Array of reserve amounts (first element = Pinto amount)
- `transfer_volume_usd`: USD value of the convert
- `is_convert`: Boolean flag (should be true)

**LP<>LP Convert (processed)**:
- `season`: Calculated from timestamp (`(timestamp - 1732086000) / 3600`)
- `convert_type`: "LP<>LP", "LP->PINTO", or "PINTO->LP"
- `from_well_id`, `to_well_id`: Source and destination wells
- `pinto_amount`: Amount of Pinto tokens involved (matched between REMOVE/ADD)
- `from_reserves`, `to_reserves`: Reserve amounts from both sides

**Seeds Data**:
- `season`, `token`: Season number and whitelisted token address
- `stalkEarnedPerSeason`: Seeds (stalk earning rate) for that token
- `bdv`: Bean Denominated Value

## Common Development Commands

### Setup

```bash
# Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### Fetch Convert Data

```bash
# Fetch convert transactions using season numbers (RECOMMENDED)
python src/fetch_converts.py --start-season 6000 --output converts.csv
python src/fetch_converts.py --start-season 6000 --end-season 7000 --output converts.csv

# Fetch convert transactions using block numbers (LEGACY)
python src/fetch_converts.py --start-block 21000000 --end-block 21100000 --output converts.csv
python src/fetch_converts.py --start-block 21000000 --output converts.csv

# Customize batch size for API efficiency
python src/fetch_converts.py --start-season 6000 --batch-size 500 --output converts.csv
```

### Fetch Seeds Data

```bash
# Fetch seeds per token from specific season range
python src/fetch_seeds_per_token.py --start-season 7000 --end-season 7100 --output seeds.csv

# Fetch seeds data to latest season
python src/fetch_seeds_per_token.py --start-season 7000 --output seeds.csv
```

### Filter LP<>LP Converts

```bash
# Filter and pair LP<>LP converts (includes unpaired by default)
python src/filter_lp_converts.py --input converts.csv --output lp_converts.csv

# Exclude unpaired converts (LP->PINTO and PINTO->LP)
python src/filter_lp_converts.py --input converts.csv --output lp_converts.csv --exclude-unpaired
```

### Calculate Bonus

```bash
# Calculate bonus based on seed differentials and convert activity
python src/calculate_bonus.py \
  --seeds seeds_data.csv \
  --converts lp_converts_with_season.csv \
  --output bonus_calculation_details.csv

# With custom starting bonus and season range
python src/calculate_bonus.py \
  --seeds seeds_data.csv \
  --converts lp_converts_with_season.csv \
  --initial-bonus 0.0 \
  --start-season 6000 \
  --end-season 7500 \
  --output bonus_details.csv
```

**Important**: The bonus penalty is applied **ONCE per season**, regardless of how many convert events occurred in that season. For example, if season 7225 has 16 convert events, the penalty is still only applied once. This is tracked using a set of unique seasons with convert activity.

### Data Analysis

```bash
# Generate visualization (run from parent directory)
cd ..
python visualize_convert_data.py
# Outputs: convert_analysis.png, convert_detailed_analysis.png
```

## Protocol Constants

- **Pinto Start Timestamp**: `1732086000` (Unix timestamp)
- **Season Duration**: 3600 seconds (1 hour)
- **Bean Token Address**: `0xb170000aeefa790fa61d6e837d1035906839a3c8`

## Data Flow Example

```
Season Range → src/fetch_converts.py → csv_output/converts.csv (raw events)
                    ↓
              src/filter_lp_converts.py → csv_output/lp_converts.csv (paired LP<>LP)
                    ↓
Season Range → src/fetch_seeds_per_token.py → csv_output/seeds.csv (seeds/token/season)
                    ↓
              src/calculate_bonus.py → csv_output/bonus_calculation_details.csv
```

**Note**: Both `fetch_converts.py` and `fetch_seeds_per_token.py` now accept season numbers, making the pipeline consistent and user-friendly.

## Important Implementation Details

### LP<>LP Pairing Logic
The system pairs REMOVE_LIQUIDITY and ADD_LIQUIDITY events by:
1. Grouping events by (block_number, timestamp)
2. Extracting Pinto amount from `transfer_volume_reserves[0]`
3. Matching pairs where Pinto amounts are within 0.01 tolerance
4. Creating combined LP<>LP record with both well addresses

### Season Calculation
```python
# Convert timestamp to season number
season = int((timestamp - 1732086000) / 3600)

# Convert season to timestamp
timestamp = 1732086000 + (season * 3600)
```

**Season-Block Conversion**: `fetch_converts.py` now supports both season-based and block-based queries. Season-based queries are recommended as they align with `fetch_seeds_per_token.py` and provide a consistent interface across all data fetching scripts.

### GraphQL Query Patterns
- Both fetchers use pagination with configurable batch sizes (default 1000)
- Retry logic with max 3 attempts and 2-second backoff
- Rate limiting with 0.1s sleep between batches

## CSV Output Schemas

### converts.csv (from fetch_converts.py)
`block_number,timestamp,well_id,trade_type,transfer_volume_usd,transfer_volume_reserves,transfer_volume_reserves_usd,is_convert,trade_id,datetime`

### lp_converts.csv (from filter_lp_converts.py)
`season,block_number,timestamp,convert_type,from_well_id,to_well_id,pinto_amount,from_reserves,to_reserves,from_volume_usd,to_volume_usd,total_volume_usd,from_trade_id,to_trade_id,datetime`

### seeds_data.csv (from fetch_seeds_per_token.py)
`season,token,stalkEarnedPerSeason,bdv,timestamp,createdAt`
