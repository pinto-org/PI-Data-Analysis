#!/bin/bash
# Pinto Protocol Convert Bonus Analysis Pipeline
#
# This script runs the complete data pipeline:
# 1. Fetch seeds per token data from PintoStalk subgraph
# 2. Fetch convert trades data from Exchange subgraph
# 3. Filter and pair LP<>LP converts
# 4. Calculate bonus based on seed differentials and convert activity
#
# Usage:
#   ./run_pipeline.sh [START_SEASON] [END_SEASON]
#
# Examples:
#   ./run_pipeline.sh 6000           # From season 6000 to latest
#   ./run_pipeline.sh 6000 7500      # From season 6000 to 7500
#   ./run_pipeline.sh                # Error: requires start season

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SEEDS_OUTPUT="csv_output/seeds_per_token_by_season.csv"
CONVERTS_OUTPUT="csv_output/converts_by_block.csv"
LP_CONVERTS_OUTPUT="csv_output/lp_converts_with_season.csv"
BONUS_OUTPUT="csv_output/bonus_calculation_details.csv"

# Parse command line arguments
START_SEASON=$1
END_SEASON=$2

if [ -z "$START_SEASON" ]; then
    echo -e "${RED}Error: START_SEASON is required${NC}"
    echo "Usage: $0 START_SEASON [END_SEASON]"
    echo "Example: $0 6000 7500"
    exit 1
fi

# Ensure csv_output directory exists
mkdir -p csv_output

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Pinto Convert Bonus Analysis Pipeline${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Start Season: ${GREEN}$START_SEASON${NC}"
if [ -n "$END_SEASON" ]; then
    echo -e "End Season: ${GREEN}$END_SEASON${NC}"
else
    echo -e "End Season: ${GREEN}latest${NC}"
fi
echo ""

# Step 1: Fetch Seeds Data
echo -e "${YELLOW}[1/4] Fetching seeds per token data...${NC}"
if [ -n "$END_SEASON" ]; then
    python3 src/fetch_seeds_per_token.py \
        --start-season "$START_SEASON" \
        --end-season "$END_SEASON" \
        --output "$SEEDS_OUTPUT"
else
    python3 src/fetch_seeds_per_token.py \
        --start-season "$START_SEASON" \
        --output "$SEEDS_OUTPUT"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Seeds data fetched successfully${NC}"
else
    echo -e "${RED}✗ Failed to fetch seeds data${NC}"
    exit 1
fi
echo ""

# Step 2: Fetch Convert Trades Data
echo -e "${YELLOW}[2/4] Fetching convert trades data...${NC}"
if [ -n "$END_SEASON" ]; then
    python3 src/fetch_converts.py \
        --start-season "$START_SEASON" \
        --end-season "$END_SEASON" \
        --output "$CONVERTS_OUTPUT"
else
    python3 src/fetch_converts.py \
        --start-season "$START_SEASON" \
        --output "$CONVERTS_OUTPUT"
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Convert trades data fetched successfully${NC}"
else
    echo -e "${RED}✗ Failed to fetch convert trades data${NC}"
    exit 1
fi
echo ""

# Step 3: Filter LP<>LP Converts
echo -e "${YELLOW}[3/4] Filtering LP<>LP converts...${NC}"
python3 src/filter_lp_converts.py \
    --input "$CONVERTS_OUTPUT" \
    --output "$LP_CONVERTS_OUTPUT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ LP<>LP converts filtered successfully${NC}"
else
    echo -e "${RED}✗ Failed to filter LP<>LP converts${NC}"
    exit 1
fi
echo ""

# Step 4: Calculate Bonus
echo -e "${YELLOW}[4/4] Calculating convert bonus...${NC}"
python3 src/calculate_bonus.py \
    --seeds "$SEEDS_OUTPUT" \
    --converts "$LP_CONVERTS_OUTPUT" \
    --output "$BONUS_OUTPUT"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Bonus calculation completed successfully${NC}"
else
    echo -e "${RED}✗ Failed to calculate bonus${NC}"
    exit 1
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Pipeline completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Output files:"
echo -e "  - Seeds data:       ${GREEN}$SEEDS_OUTPUT${NC}"
echo -e "  - Convert trades:   ${GREEN}$CONVERTS_OUTPUT${NC}"
echo -e "  - LP<>LP converts:  ${GREEN}$LP_CONVERTS_OUTPUT${NC}"
echo -e "  - Bonus details:    ${GREEN}$BONUS_OUTPUT${NC}"
echo ""
