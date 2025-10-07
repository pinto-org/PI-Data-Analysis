# Pinto Protocol Convert Bonus Calculator

A Python-based data analysis toolkit for calculating convert bonus values in the Pinto Protocol based on seed differentials and LP<>LP convert activity.

## Overview

This toolkit fetches blockchain data from Pinto Protocol's GraphQL subgraphs, processes convert transactions, and calculates a bonus value that:
- **Increases** when Pinto has higher seeds than LP tokens (and no converts occur)
- **Decreases** when there is convert activity or when Pinto has lower seeds

The bonus calculation follows these rules per season:
- **No converts + positive differential**: `bonus += differential`
- **No converts + negative differential**: No change
- **Has converts + positive differential**: `bonus -= differential`
- **Has converts + negative differential**: `bonus *= 0.99` (1% decay)

**Important**: The bonus penalty is applied **once per season**, regardless of how many convert events occur in that season.

## Quick Start

### Prerequisites

```bash
# Python 3.7+ required
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### Run Full Pipeline

```bash
# Fetch all data and calculate bonus from season 6000 to latest
./run_convert_bonus_analysis.sh 6000

# Or specify an end season
./run_convert_bonus_analysis.sh 6000 7500
```

This single command will:
1. Fetch seeds per token data
2. Fetch convert trades data
3. Filter and pair LP<>LP converts
4. Calculate bonus based on seed differentials

All outputs will be saved in the `csv_output/` directory.

## Python Scripts

### 1. `fetch_seeds_per_token.py`

**Purpose**: Fetches whitelisted token seeds data from the PintoStalk subgraph.

**What it does**:
- Queries `whitelistTokenHourlySnapshots` from `https://graph.pinto.money/pintostalk`
- Retrieves `stalkEarnedPerSeason` (seeds) for each whitelisted token by season
- Outputs season-indexed seeds data for bonus calculation

**Usage**:
```bash
# Fetch from season 6000 to latest
python3 fetch_seeds_per_token.py --start-season 6000

# Fetch specific season range
python3 fetch_seeds_per_token.py --start-season 6000 --end-season 7500

# Custom output location
python3 fetch_seeds_per_token.py --start-season 6000 --output my_seeds.csv
```

**Output**: `csv_output/seeds_per_token_by_season.csv`
- Columns: `season`, `token`, `stalkEarnedPerSeason`, `bdv`, `timestamp`, `createdAt`

### 2. `fetch_converts.py`

**Purpose**: Fetches convert transaction data from the Pinto Exchange subgraph.

**What it does**:
- Queries `trades` entity with `isConvert: true` filter from `https://graph.pinto.money/exchange`
- Retrieves REMOVE_LIQUIDITY and ADD_LIQUIDITY events
- Supports both season-based and block-based queries
- Calculates season numbers from timestamps

**Usage**:
```bash
# Fetch by season (recommended)
python3 fetch_converts.py --start-season 6000

# Fetch specific season range
python3 fetch_converts.py --start-season 6000 --end-season 7500

# Fetch by block number (legacy)
python3 fetch_converts.py --start-block 21000000 --end-block 21100000

# Custom output location
python3 fetch_converts.py --start-season 6000 --output my_converts.csv
```

**Output**: `csv_output/converts_by_block.csv`
- Columns: `block_number`, `timestamp`, `well_id`, `trade_type`, `transfer_volume_usd`, `transfer_volume_reserves`, `transfer_volume_reserves_usd`, `is_convert`, `trade_id`, `datetime`

### 3. `filter_lp_converts.py`

**Purpose**: Identifies and pairs LP<>LP convert transactions from raw convert data.

**What it does**:
- Groups convert events by block number and timestamp
- Matches REMOVE_LIQUIDITY and ADD_LIQUIDITY pairs by Pinto amount
- Identifies LP<>LP converts (paired events)
- Tracks unpaired converts (LP→PINTO and PINTO→LP)
- Calculates season numbers for each convert

**Pairing Logic**:
- Events in the same block/timestamp with matching Pinto amounts (first element of `transfer_volume_reserves`)
- Tolerance of 0.01 for floating point comparison

**Usage**:
```bash
# Filter and pair LP<>LP converts (includes unpaired by default)
python3 filter_lp_converts.py --input csv_output/converts_by_block.csv

# Exclude unpaired converts from output
python3 filter_lp_converts.py --input csv_output/converts_by_block.csv --exclude-unpaired

# Custom output location
python3 filter_lp_converts.py --input converts.csv --output my_lp_converts.csv
```

**Output**: `csv_output/lp_converts_with_season.csv`
- Columns: `season`, `block_number`, `timestamp`, `convert_type`, `from_well_id`, `to_well_id`, `pinto_amount`, `from_reserves`, `to_reserves`, `from_volume_usd`, `to_volume_usd`, `total_volume_usd`, `from_trade_id`, `to_trade_id`, `datetime`
- Convert types: `LP<>LP`, `LP->PINTO`, `PINTO->LP`

### 4. `calculate_bonus.py`

**Purpose**: Calculates the convert bonus based on seed differentials and convert activity.

**What it does**:
- Loads seeds data and LP convert data
- For each season, calculates: `differential = pinto_seeds - max_lp_seeds`
- Applies bonus adjustment rules based on differential and convert activity
- **Important**: Applies penalty once per season regardless of convert count
- Tracks and reports seasons with multiple converts
- Outputs detailed season-by-season calculations

**Bonus Calculation Rules**:
```
For each season:
  differential = pinto_seeds - max(lp_seeds)

  If no converts in season:
    If differential > 0: bonus += differential
    Else: no change

  If converts in season (penalty applied ONCE):
    If differential > 0: bonus -= differential
    Else: bonus *= 0.99  (1% decay)

  bonus = max(0, bonus)  (never negative)
```

**Usage**:
```bash
# Calculate bonus with default settings
python3 calculate_bonus.py \
  --seeds csv_output/seeds_per_token_by_season.csv \
  --converts csv_output/lp_converts_with_season.csv

# Set initial bonus value
python3 calculate_bonus.py \
  --seeds csv_output/seeds_per_token_by_season.csv \
  --converts csv_output/lp_converts_with_season.csv \
  --initial-bonus 1000000.0

# Filter by season range
python3 calculate_bonus.py \
  --seeds csv_output/seeds_per_token_by_season.csv \
  --converts csv_output/lp_converts_with_season.csv \
  --start-season 6500 \
  --end-season 7000

# Custom output location
python3 calculate_bonus.py \
  --seeds seeds.csv \
  --converts lp_converts.csv \
  --output my_bonus_details.csv
```

**Output**: `csv_output/bonus_calculation_details.csv`
- Columns: `season`, `pinto_seeds`, `max_lp_seeds`, `max_lp_token`, `differential`, `has_converts`, `convert_count`, `bonus_before`, `bonus_change`, `bonus_after`, `action`
- Actions: `add_differential`, `subtract_differential`, `decay_1pct`, `no_change`

## Pipeline Script

### `run_convert_bonus_analysis.sh`

**Purpose**: Automated script that runs the complete data pipeline in the correct sequence.

**What it does**:
1. Ensures `csv_output/` directory exists
2. Fetches seeds per token data
3. Fetches convert trades data
4. Filters LP<>LP converts
5. Calculates bonus with detailed output
6. Provides color-coded progress and error reporting

**Usage**:
```bash
# Run full pipeline from season 6000 to latest
./run_convert_bonus_analysis.sh 6000

# Run full pipeline for specific season range
./run_convert_bonus_analysis.sh 6000 7500
```

**Features**:
- ✓ Error handling with clear messages
- ✓ Progress indicators for each step
- ✓ Automatic directory creation
- ✓ Summary of all output files
- ✓ Exit codes for CI/CD integration

## Protocol Constants

- **Pinto Start Timestamp**: `1732086000` (Unix timestamp)
- **Season Duration**: `3600` seconds (1 hour)
- **Pinto Token Address**: `0xb170000aeefa790fa61d6e837d1035906839a3c8`

## Season Calculation

```python
season = int((timestamp - 1732086000) / 3600)
```

## Output Files

All output files are saved in the `csv_output/` directory:

| File | Description | Generated By |
|------|-------------|--------------|
| `seeds_per_token_by_season.csv` | Seeds per token by season | `fetch_seeds_per_token.py` |
| `converts_by_block.csv` | Raw convert trades | `fetch_converts.py` |
| `lp_converts_with_season.csv` | Filtered LP<>LP convert pairs | `filter_lp_converts.py` |
| `bonus_calculation_details.csv` | Season-by-season bonus calculations | `calculate_bonus.py` |

## Data Flow

```
Season Range
     ↓
fetch_seeds_per_token.py → seeds_per_token_by_season.csv
     ↓
fetch_converts.py → converts_by_block.csv
     ↓
filter_lp_converts.py → lp_converts_with_season.csv
     ↓
calculate_bonus.py → bonus_calculation_details.csv
```

## GraphQL Endpoints

- **PintoStalk Subgraph**: `https://graph.pinto.money/pintostalk`
  - Used by: `fetch_seeds_per_token.py`
  - Entity: `whitelistTokenHourlySnapshots`

- **Exchange Subgraph**: `https://graph.pinto.money/exchange`
  - Used by: `fetch_converts.py`
  - Entity: `trades` (with `isConvert: true` filter)

## Requirements

```
pandas>=1.5.0
requests>=2.28.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Examples

### Basic Usage

```bash
# Run the full pipeline
./run_convert_bonus_analysis.sh 6000
```

### Advanced Usage

```bash
# Fetch specific season range
python3 fetch_seeds_per_token.py --start-season 6000 --end-season 6500
python3 fetch_converts.py --start-season 6000 --end-season 6500
python3 filter_lp_converts.py --input csv_output/converts_by_block.csv
python3 calculate_bonus.py \
  --seeds csv_output/seeds_per_token_by_season.csv \
  --converts csv_output/lp_converts_with_season.csv \
  --initial-bonus 500000.0
```

### Custom Batch Sizes

```bash
# Reduce batch size for rate limiting
python3 fetch_seeds_per_token.py --start-season 6000 --batch-size 500
python3 fetch_converts.py --start-season 6000 --batch-size 500
```

## Troubleshooting

### GraphQL Query Errors

If you encounter GraphQL query errors:
- Reduce batch size with `--batch-size 500`
- The scripts have built-in retry logic (3 attempts with 2s backoff)
- Check GraphQL endpoint availability

### Missing Data

If bonus calculation shows missing data:
- Ensure season ranges match across all fetched data
- Verify that Pinto token exists in seeds data for all seasons
- Check that at least one LP token exists per season

### Permission Errors

If `run_convert_bonus_analysis.sh` fails with permission denied:
```bash
chmod +x run_convert_bonus_analysis.sh
```

## License

This project is part of the Pinto Protocol data analysis toolkit.
