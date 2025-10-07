#!/usr/bin/env python3
"""
Fetch convert transaction data from Pinto Protocol subgraph.
Uses the trades entity with isConvert filter to get actual convert transactions.
Outputs data to CSV for convert analysis.

Usage (Season-based - Recommended):
    python fetch_converts.py --start-season 6000 --output converts.csv
    python fetch_converts.py --start-season 6000 --end-season 7000 --output converts.csv

Usage (Block-based - Legacy):
    python fetch_converts.py --start-block 21000000 --end-block 21100000 --output converts.csv

Output CSV columns:
    - block_number: Block number when convert occurred
    - timestamp: Unix timestamp of the convert
    - well_id: Well address where convert happened
    - trade_type: Type of trade (should be convert)
    - transfer_volume_usd: USD value of the convert
    - transfer_volume_reserves: Reserve volumes
    - transfer_volume_reserves_usd: USD value of reserve volumes
    - is_convert: Boolean flag confirming this is a convert (should be true)

Convert Detection Logic:
Uses the trades entity with isConvert: true filter to directly identify convert transactions
from the Pinto Protocol subgraph.
"""

import requests
import pandas as pd
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional


class ConvertDataFetcher:
    # Pinto Protocol constants for season calculation
    PINTO_START_TIMESTAMP = 1732086000  # Pinto protocol start timestamp
    SEASON_DURATION = 3600  # 1 hour per season

    def __init__(self):
        self.subgraph_url = "https://graph.pinto.money/exchange"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Pinto-Convert-Analysis/1.0'
        })

    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute GraphQL query with retry logic."""
        payload = {
            'query': query,
            'variables': variables or {}
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.post(self.subgraph_url, json=payload, timeout=30)
                response.raise_for_status()

                data = response.json()

                if 'errors' in data:
                    raise Exception(f"GraphQL errors: {data['errors']}")

                if 'data' not in data:
                    raise Exception(f"No data field in response: {data}")

                return data['data']

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to execute query after {max_retries} attempts: {e}")
                print(f"Attempt {attempt + 1} failed: {e}. Retrying in 2 seconds...")
                time.sleep(2)

    def season_to_timestamp(self, season: int) -> int:
        """Convert season number to Unix timestamp.

        Args:
            season: Season number

        Returns:
            Unix timestamp for the start of the season
        """
        return self.PINTO_START_TIMESTAMP + (season * self.SEASON_DURATION)

    def timestamp_to_season(self, timestamp: int) -> int:
        """Convert Unix timestamp to season number.

        Args:
            timestamp: Unix timestamp

        Returns:
            Season number
        """
        return int((timestamp - self.PINTO_START_TIMESTAMP) / self.SEASON_DURATION)

    def get_latest_block(self) -> int:
        """Get the latest block number from the subgraph."""
        query = """
        query GetLatestBlock {
            trades(first: 1, orderBy: blockNumber, orderDirection: desc) {
                blockNumber
            }
        }
        """

        result = self.execute_query(query)
        if not result['trades']:
            raise Exception("No trades found in subgraph")

        return int(result['trades'][0]['blockNumber'])

    def get_latest_timestamp(self) -> int:
        """Get the latest timestamp from the subgraph."""
        query = """
        query GetLatestTimestamp {
            trades(first: 1, orderBy: timestamp, orderDirection: desc) {
                timestamp
            }
        }
        """

        result = self.execute_query(query)
        if not result['trades']:
            raise Exception("No trades found in subgraph")

        return int(result['trades'][0]['timestamp'])

    def fetch_converts_by_block(self, start_block: int, end_block: Optional[int] = None,
                              batch_size: int = 1000) -> List[Dict]:
        """Fetch convert trades using the trades entity with isConvert filter."""
        if end_block is None:
            end_block = self.get_latest_block()

        print(f"Fetching convert trades from block {start_block} to {end_block}")

        query = """
        query FetchConvertTrades($startBlock: String!, $endBlock: String!, $first: Int!, $skip: Int!) {
            trades(
                first: $first
                skip: $skip
                where: {
                    isConvert: true
                    blockNumber_gte: $startBlock
                    blockNumber_lte: $endBlock
                }
                orderBy: blockNumber
                orderDirection: asc
            ) {
                id
                isConvert
                well {
                    id
                }
                transferVolumeUSD
                tradeType
                transferVolumeReserves
                transferVolumeReservesUSD
                timestamp
                blockNumber
            }
        }
        """

        all_data = []
        skip = 0

        while True:
            variables = {
                'startBlock': str(start_block),
                'endBlock': str(end_block),
                'first': batch_size,
                'skip': skip
            }

            result = self.execute_query(query, variables)
            trades = result['trades']

            if not trades:
                break

            all_data.extend(trades)
            print(f"Fetched {len(trades)} convert trades (total: {len(all_data)})")

            if len(trades) < batch_size:
                break

            skip += batch_size
            time.sleep(0.1)  # Rate limiting

        print(f"Total convert trades fetched: {len(all_data)}")
        return all_data

    def fetch_converts_by_season(self, start_season: int, end_season: Optional[int] = None,
                                batch_size: int = 1000) -> List[Dict]:
        """Fetch convert trades using season numbers (converted to timestamps).

        Args:
            start_season: Starting season number
            end_season: Ending season number (defaults to latest)
            batch_size: Number of records to fetch per request

        Returns:
            List of trade dictionaries
        """
        # Convert seasons to timestamps
        start_timestamp = self.season_to_timestamp(start_season)

        if end_season is None:
            # Get latest timestamp from subgraph
            end_timestamp = self.get_latest_timestamp()
            end_season_display = f"latest (season {self.timestamp_to_season(end_timestamp)})"
        else:
            end_timestamp = self.season_to_timestamp(end_season)
            end_season_display = str(end_season)

        print(f"Fetching convert trades from season {start_season} to {end_season_display}")
        print(f"  (timestamp {start_timestamp} to {end_timestamp})")

        query = """
        query FetchConvertTrades($startTimestamp: String!, $endTimestamp: String!, $first: Int!, $skip: Int!) {
            trades(
                first: $first
                skip: $skip
                where: {
                    isConvert: true
                    timestamp_gte: $startTimestamp
                    timestamp_lte: $endTimestamp
                }
                orderBy: timestamp
                orderDirection: asc
            ) {
                id
                isConvert
                well {
                    id
                }
                transferVolumeUSD
                tradeType
                transferVolumeReserves
                transferVolumeReservesUSD
                timestamp
                blockNumber
            }
        }
        """

        all_data = []
        skip = 0

        while True:
            variables = {
                'startTimestamp': str(start_timestamp),
                'endTimestamp': str(end_timestamp),
                'first': batch_size,
                'skip': skip
            }

            result = self.execute_query(query, variables)
            trades = result['trades']

            if not trades:
                break

            all_data.extend(trades)
            print(f"Fetched {len(trades)} convert trades (total: {len(all_data)})")

            if len(trades) < batch_size:
                break

            skip += batch_size
            time.sleep(0.1)  # Rate limiting

        print(f"Total convert trades fetched: {len(all_data)}")
        return all_data

    def process_convert_data(self, trades_data: List[Dict]) -> pd.DataFrame:
        """Process convert trades data into DataFrame format."""
        if not trades_data:
            return pd.DataFrame()

        print(f"Processing {len(trades_data)} convert trades...")

        # Convert to DataFrame
        records = []
        for trade in trades_data:
            # Handle transferVolumeReserves which might be a list
            reserves = trade['transferVolumeReserves']
            if isinstance(reserves, list):
                reserves_str = ','.join(map(str, reserves))
            else:
                reserves_str = str(reserves) if reserves else ""

            # Handle transferVolumeReservesUSD which might be a list
            reserves_usd = trade['transferVolumeReservesUSD']
            if isinstance(reserves_usd, list):
                reserves_usd_sum = sum(float(x) for x in reserves_usd if x is not None)
            else:
                reserves_usd_sum = float(reserves_usd) if reserves_usd else 0.0

            record = {
                'block_number': int(trade['blockNumber']),
                'timestamp': int(trade['timestamp']),
                'well_id': trade['well']['id'] if trade['well'] else None,
                'trade_type': trade['tradeType'],
                'transfer_volume_usd': float(trade['transferVolumeUSD']) if trade['transferVolumeUSD'] else 0.0,
                'transfer_volume_reserves': reserves_str,
                'transfer_volume_reserves_usd': reserves_usd_sum,
                'is_convert': trade['isConvert'],
                'trade_id': trade['id'],
                'datetime': pd.to_datetime(int(trade['timestamp']), unit='s')
            }
            records.append(record)

        df = pd.DataFrame(records)
        return df.sort_values(['block_number', 'timestamp']).reset_index(drop=True)

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file."""
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        print(f"Convert records: {len(df)}")
        if not df.empty:
            print(f"Block range: {df['block_number'].min()} - {df['block_number'].max()}")
            print(f"Unique wells: {df['well_id'].nunique()}")
            print(f"Total volume USD: ${df['transfer_volume_usd'].sum():,.2f}")
            print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")


def main():
    parser = argparse.ArgumentParser(description='Fetch convert data from Pinto subgraph using trades entity')
    parser.add_argument('--start-block', type=int,
                       help='Starting block number (use --start-season for season-based queries)')
    parser.add_argument('--end-block', type=int,
                       help='Ending block number (optional, defaults to latest)')
    parser.add_argument('--start-season', type=int,
                       help='Starting season number (alternative to --start-block)')
    parser.add_argument('--end-season', type=int,
                       help='Ending season number (optional, defaults to latest)')
    parser.add_argument('--output', type=str, default='csv_output/converts_by_block.csv',
                       help='Output CSV filename')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of records to fetch per request')

    args = parser.parse_args()

    try:
        # Validate arguments
        if args.start_season and args.start_block:
            print("Error: Cannot specify both --start-season and --start-block")
            print("Use --start-season for season-based queries or --start-block for block-based queries")
            return 1

        if not args.start_season and not args.start_block:
            print("Error: Must specify either --start-season or --start-block")
            print("Use --start-season SEASON_NUMBER for season-based queries")
            print("Use --start-block BLOCK_NUMBER for block-based queries")
            return 1

        if args.end_season and not args.start_season:
            print("Error: --end-season can only be used with --start-season")
            return 1

        if args.end_block and not args.start_block:
            print("Error: --end-block can only be used with --start-block")
            return 1

        fetcher = ConvertDataFetcher()

        # Fetch convert trades data using appropriate method
        if args.start_season:
            trades_data = fetcher.fetch_converts_by_season(
                start_season=args.start_season,
                end_season=args.end_season,
                batch_size=args.batch_size
            )
            range_description = f"season range {args.start_season} to {args.end_season or 'latest'}"
        else:
            trades_data = fetcher.fetch_converts_by_block(
                start_block=args.start_block,
                end_block=args.end_block,
                batch_size=args.batch_size
            )
            range_description = f"block range {args.start_block} to {args.end_block or 'latest'}"

        if not trades_data:
            print(f"No convert trades found for the specified {range_description}")
            return

        # Process data
        df = fetcher.process_convert_data(trades_data)

        if df.empty:
            print("No convert data found for processing")
            return

        # Save results
        fetcher.save_to_csv(df, args.output)

        print(f"\nSample data:")
        print(df.head(10))

        print(f"\nConvert fetching completed!")
        print(f"Converts retrieved using trades entity with isConvert: true filter.")
        print(f"Each record represents an actual convert transaction with volume data.")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())