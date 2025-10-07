#!/usr/bin/env python3
"""
Fetch seeds (stalkEarnedPerSeason) per whitelisted token per season from Pinto Protocol subgraph.
Outputs data to CSV for convert bonus analysis.
"""

import requests
import pandas as pd
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional


class SeedDataFetcher:
    def __init__(self):
        self.subgraph_url = "https://graph.pinto.money/pintostalk"
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Pinto-Convert-Bonus-Analysis/1.0'
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

    def get_latest_season(self) -> int:
        """Get the latest season number from the subgraph."""
        query = """
        query GetLatestSeason {
            seasons(first: 1, orderBy: season, orderDirection: desc) {
                season
            }
        }
        """

        result = self.execute_query(query)
        if not result['seasons']:
            raise Exception("No seasons found in subgraph")

        return int(result['seasons'][0]['season'])

    def fetch_seeds_data(self, start_season: int, end_season: Optional[int] = None,
                        batch_size: int = 1000) -> List[Dict]:
        """Fetch whitelist token hourly snapshots with seeds data."""
        if end_season is None:
            end_season = self.get_latest_season()

        print(f"Fetching seeds data from season {start_season} to {end_season}")

        query = """
        query FetchSeeds($startSeason: Int!, $endSeason: Int!, $first: Int!, $skip: Int!) {
            whitelistTokenHourlySnapshots(
                first: $first
                skip: $skip
                where: {
                    season_gte: $startSeason
                    season_lte: $endSeason
                }
                orderBy: season
                orderDirection: asc
            ) {
                id
                season
                token
                stalkEarnedPerSeason
                bdv
                createdAt
            }
        }
        """

        all_data = []
        skip = 0

        while True:
            variables = {
                'startSeason': start_season,
                'endSeason': end_season,
                'first': batch_size,
                'skip': skip
            }

            result = self.execute_query(query, variables)
            snapshots = result['whitelistTokenHourlySnapshots']

            if not snapshots:
                break

            all_data.extend(snapshots)
            print(f"Fetched {len(snapshots)} records (total: {len(all_data)})")

            if len(snapshots) < batch_size:
                break

            skip += batch_size
            time.sleep(0.1)  # Rate limiting

        print(f"Total records fetched: {len(all_data)}")
        return all_data

    def process_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Process raw GraphQL data into clean DataFrame."""
        if not raw_data:
            return pd.DataFrame()

        df = pd.DataFrame(raw_data)

        # Extract token address from id field (format: "0xtoken-season")
        df['token'] = df['id'].str.split('-').str[0]

        # Convert data types
        df['season'] = df['season'].astype(int)
        df['stalkEarnedPerSeason'] = df['stalkEarnedPerSeason'].astype(int)
        df['bdv'] = pd.to_numeric(df['bdv'], errors='coerce')
        df['createdAt'] = pd.to_numeric(df['createdAt'], errors='coerce')

        # Convert timestamp to readable format
        df['timestamp'] = pd.to_datetime(df['createdAt'], unit='s', errors='coerce')

        # Remove duplicates (keep latest record per season/token combination)
        df = df.sort_values(['season', 'token', 'createdAt'])
        df = df.drop_duplicates(subset=['season', 'token'], keep='last')

        # Reorder columns
        df = df[['season', 'token', 'stalkEarnedPerSeason', 'bdv', 'timestamp', 'createdAt']]

        return df.sort_values(['season', 'token']).reset_index(drop=True)

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file."""
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
        print(f"Records: {len(df)}")
        print(f"Season range: {df['season'].min()} - {df['season'].max()}")
        print(f"Unique tokens: {df['token'].nunique()}")


def main():
    parser = argparse.ArgumentParser(description='Fetch seeds per token per season from Pinto subgraph')
    parser.add_argument('--start-season', type=int, required=True,
                       help='Starting season number')
    parser.add_argument('--end-season', type=int,
                       help='Ending season number (defaults to latest)')
    parser.add_argument('--output', type=str, default='csv_output/seeds_per_token_by_season.csv',
                       help='Output CSV filename')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of records to fetch per request')

    args = parser.parse_args()

    try:
        fetcher = SeedDataFetcher()

        # Fetch raw data
        raw_data = fetcher.fetch_seeds_data(
            start_season=args.start_season,
            end_season=args.end_season,
            batch_size=args.batch_size
        )

        if not raw_data:
            print("No data found for the specified season range")
            return

        # Process and save data
        df = fetcher.process_data(raw_data)
        fetcher.save_to_csv(df, args.output)

        print(f"\nSample data:")
        print(df.head(10))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())