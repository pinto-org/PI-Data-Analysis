#!/usr/bin/env python3
"""
Filter and combine LP<>LP converts from raw convert data.

LP<>LP converts are pairs of REMOVE_LIQUIDITY (well→pinto) and ADD_LIQUIDITY (pinto→well)
events that occur in the same block/timestamp with matching Pinto amounts.

Usage:
    python filter_lp_converts.py --input converts.csv --output lp_converts.csv

Output CSV columns:
    - season: Pinto season number when convert occurred
    - block_number: Block number when LP<>LP convert occurred
    - timestamp: Unix timestamp of the convert
    - convert_type: "LP<>LP" for matched pairs, "LP->PINTO" or "PINTO->LP" for unpaired
    - from_well_id: Source well address (REMOVE_LIQUIDITY)
    - to_well_id: Destination well address (ADD_LIQUIDITY)
    - pinto_amount: Amount of Pinto tokens involved (first reserve element)
    - from_reserves: Reserve amounts from source well
    - to_reserves: Reserve amounts from destination well
    - from_volume_usd: USD volume of REMOVE_LIQUIDITY
    - to_volume_usd: USD volume of ADD_LIQUIDITY
    - total_volume_usd: Combined USD volume
    - from_trade_id: Trade ID of REMOVE_LIQUIDITY event
    - to_trade_id: Trade ID of ADD_LIQUIDITY event
    - datetime: Human-readable timestamp

LP<>LP Detection Logic:
Identifies LP<>LP converts by finding REMOVE_LIQUIDITY and ADD_LIQUIDITY events
in the same block/timestamp where the first element of transfer_volume_reserves
(Pinto amount) matches between the two events.
"""

import pandas as pd
import argparse
import sys
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class LPConvertFilter:
    def __init__(self):
        self.lp_converts = []
        self.unpaired_converts = []
        self.pinto_start_timestamp = 1732086000  # Pinto protocol start timestamp

    def calculate_season(self, timestamp: int) -> int:
        """Calculate the season number from a timestamp."""
        return int((timestamp - self.pinto_start_timestamp) / 3600)

    def parse_reserves(self, reserves_str: str) -> List[float]:
        """Parse the comma-separated reserves string into a list of floats."""
        if not reserves_str or reserves_str == "":
            return []

        try:
            # Split by comma and convert to float
            reserves = []
            for item in reserves_str.split(','):
                reserves.append(float(item.strip()))
            return reserves
        except (ValueError, AttributeError) as e:
            print(f"Warning: Could not parse reserves '{reserves_str}': {e}")
            return []

    def get_pinto_amount(self, reserves_str: str) -> Optional[float]:
        """Extract the first element (Pinto amount) from reserves."""
        reserves = self.parse_reserves(reserves_str)
        return reserves[0] if reserves else None

    def group_converts_by_block_timestamp(self, df: pd.DataFrame) -> Dict[Tuple[int, int], List[Dict]]:
        """Group converts by (block_number, timestamp) tuple."""
        groups = {}

        for _, row in df.iterrows():
            key = (row['block_number'], row['timestamp'])
            if key not in groups:
                groups[key] = []
            groups[key].append(row.to_dict())

        return groups

    def find_lp_pairs(self, converts: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Find LP<>LP pairs within a group of converts from same block/timestamp.
        Returns (paired_converts, unpaired_converts).
        """
        remove_liquidity = []
        add_liquidity = []

        # Separate by trade type
        for convert in converts:
            if convert['trade_type'] == 'REMOVE_LIQUIDITY':
                remove_liquidity.append(convert)
            elif convert['trade_type'] == 'ADD_LIQUIDITY':
                add_liquidity.append(convert)

        paired = []
        used_remove = set()
        used_add = set()

        # Try to match REMOVE and ADD events by Pinto amount
        for i, remove_event in enumerate(remove_liquidity):
            if i in used_remove:
                continue

            remove_pinto = self.get_pinto_amount(remove_event['transfer_volume_reserves'])
            if remove_pinto is None:
                continue

            # Look for matching ADD event
            for j, add_event in enumerate(add_liquidity):
                if j in used_add:
                    continue

                add_pinto = self.get_pinto_amount(add_event['transfer_volume_reserves'])
                if add_pinto is None:
                    continue

                # Check if Pinto amounts match (with small tolerance for floating point)
                if abs(remove_pinto - add_pinto) < 0.01:
                    # Found a pair!
                    paired_convert = self.combine_lp_pair(remove_event, add_event, remove_pinto)
                    paired.append(paired_convert)
                    used_remove.add(i)
                    used_add.add(j)
                    break

        # Collect unpaired events
        unpaired = []
        for i, event in enumerate(remove_liquidity):
            if i not in used_remove:
                unpaired.append(event)
        for i, event in enumerate(add_liquidity):
            if i not in used_add:
                unpaired.append(event)

        return paired, unpaired

    def combine_lp_pair(self, remove_event: Dict, add_event: Dict, pinto_amount: float) -> Dict:
        """Combine REMOVE and ADD events into a single LP<>LP convert record."""
        timestamp = remove_event['timestamp']
        return {
            'season': self.calculate_season(timestamp),
            'block_number': remove_event['block_number'],
            'timestamp': timestamp,
            'convert_type': 'LP<>LP',
            'from_well_id': remove_event['well_id'],
            'to_well_id': add_event['well_id'],
            'pinto_amount': pinto_amount,
            'from_reserves': remove_event['transfer_volume_reserves'],
            'to_reserves': add_event['transfer_volume_reserves'],
            'from_volume_usd': remove_event['transfer_volume_usd'],
            'to_volume_usd': add_event['transfer_volume_usd'],
            'total_volume_usd': remove_event['transfer_volume_usd'] + add_event['transfer_volume_usd'],
            'from_trade_id': remove_event['trade_id'],
            'to_trade_id': add_event['trade_id'],
            'datetime': remove_event['datetime']
        }

    def create_unpaired_record(self, event: Dict) -> Dict:
        """Create a record for an unpaired convert event."""
        pinto_amount = self.get_pinto_amount(event['transfer_volume_reserves'])
        timestamp = event['timestamp']

        # Determine convert type based on trade type
        if event['trade_type'] == 'REMOVE_LIQUIDITY':
            convert_type = 'LP->PINTO'  # LP to Pinto convert
        elif event['trade_type'] == 'ADD_LIQUIDITY':
            convert_type = 'PINTO->LP'  # Pinto to LP convert
        else:
            convert_type = 'UNKNOWN'

        return {
            'season': self.calculate_season(timestamp),
            'block_number': event['block_number'],
            'timestamp': timestamp,
            'convert_type': convert_type,
            'from_well_id': event['well_id'] if event['trade_type'] == 'REMOVE_LIQUIDITY' else None,
            'to_well_id': event['well_id'] if event['trade_type'] == 'ADD_LIQUIDITY' else None,
            'pinto_amount': pinto_amount,
            'from_reserves': event['transfer_volume_reserves'] if event['trade_type'] == 'REMOVE_LIQUIDITY' else None,
            'to_reserves': event['transfer_volume_reserves'] if event['trade_type'] == 'ADD_LIQUIDITY' else None,
            'from_volume_usd': event['transfer_volume_usd'] if event['trade_type'] == 'REMOVE_LIQUIDITY' else None,
            'to_volume_usd': event['transfer_volume_usd'] if event['trade_type'] == 'ADD_LIQUIDITY' else None,
            'total_volume_usd': event['transfer_volume_usd'],
            'from_trade_id': event['trade_id'] if event['trade_type'] == 'REMOVE_LIQUIDITY' else None,
            'to_trade_id': event['trade_id'] if event['trade_type'] == 'ADD_LIQUIDITY' else None,
            'datetime': event['datetime']
        }

    def process_converts(self, input_file: str, include_unpaired: bool = False) -> pd.DataFrame:
        """Process the raw converts CSV and identify LP<>LP pairs."""
        print(f"Reading converts from {input_file}...")

        try:
            df = pd.read_csv(input_file)
        except FileNotFoundError:
            print(f"Error: Input file {input_file} not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)

        print(f"Loaded {len(df)} convert events")

        # Group by block and timestamp
        groups = self.group_converts_by_block_timestamp(df)
        print(f"Found {len(groups)} unique block/timestamp combinations")

        all_lp_converts = []
        all_unpaired = []

        # Process each group
        for (block, timestamp), converts in groups.items():
            if len(converts) < 2:
                # Single convert, can't be LP<>LP
                for convert in converts:
                    all_unpaired.append(self.create_unpaired_record(convert))
                continue

            paired, unpaired = self.find_lp_pairs(converts)
            all_lp_converts.extend(paired)

            # Convert unpaired to records
            for convert in unpaired:
                all_unpaired.append(self.create_unpaired_record(convert))

        print(f"Found {len(all_lp_converts)} LP<>LP convert pairs")
        print(f"Found {len(all_unpaired)} unpaired convert events")

        # Combine results
        results = all_lp_converts.copy()
        if include_unpaired:
            results.extend(all_unpaired)
            print(f"Including unpaired converts in output")

        if not results:
            print("No converts found to output")
            return pd.DataFrame()

        return pd.DataFrame(results).sort_values(['season', 'block_number', 'timestamp']).reset_index(drop=True)

    def save_to_csv(self, df: pd.DataFrame, output_file: str):
        """Save filtered converts to CSV."""
        if df.empty:
            print("No data to save")
            return

        df.to_csv(output_file, index=False)
        print(f"Saved {len(df)} records to {output_file}")

        # Print summary statistics
        if not df.empty:
            lp_converts = df[df['convert_type'] == 'LP<>LP']
            lp_to_pinto = df[df['convert_type'] == 'LP->PINTO']
            pinto_to_lp = df[df['convert_type'] == 'PINTO->LP']

            print(f"LP<>LP converts: {len(lp_converts)}")
            print(f"LP->PINTO converts: {len(lp_to_pinto)}")
            print(f"PINTO->LP converts: {len(pinto_to_lp)}")

            if len(lp_converts) > 0:
                print(f"Total LP<>LP volume: ${lp_converts['total_volume_usd'].sum():,.2f}")
                print(f"Unique wells involved: {pd.concat([lp_converts['from_well_id'], lp_converts['to_well_id']]).nunique()}")

            if len(lp_to_pinto) > 0:
                print(f"Total LP->PINTO volume: ${lp_to_pinto['total_volume_usd'].sum():,.2f}")

            if len(pinto_to_lp) > 0:
                print(f"Total PINTO->LP volume: ${pinto_to_lp['total_volume_usd'].sum():,.2f}")


def main():
    parser = argparse.ArgumentParser(description='Filter LP<>LP converts from raw convert data')
    parser.add_argument('--input', type=str, required=True,
                       help='Input CSV file with raw convert data')
    parser.add_argument('--output', type=str, default='csv_output/lp_converts.csv',
                       help='Output CSV filename for filtered LP<>LP converts')
    parser.add_argument('--exclude-unpaired', action='store_true',
                       help='Exclude unpaired (single) converts from output')

    args = parser.parse_args()

    try:
        filter = LPConvertFilter()

        # Process the converts (include unpaired by default unless excluded)
        include_unpaired = not args.exclude_unpaired
        df = filter.process_converts(args.input, include_unpaired)

        if df.empty:
            print("No LP<>LP converts found")
            return

        # Save results
        filter.save_to_csv(df, args.output)

        # Show sample data
        print(f"\nSample data:")
        print(df.head(10))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())