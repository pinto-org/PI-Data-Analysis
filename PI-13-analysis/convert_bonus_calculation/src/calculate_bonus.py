#!/usr/bin/env python3
"""
Calculate convert bonus based on Pinto token seed differentials.

This script processes seeds data and LP convert data to calculate a bonus value
that increases when Pinto has higher seeds than LP tokens, and decreases when
there is convert activity or when Pinto has lower seeds.

Usage:
    python calculate_bonus.py --seeds seeds_data.csv --converts lp_converts_with_season.csv
"""

import pandas as pd
import argparse
import sys
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict


class BonusCalculator:
    """Calculate convert bonus based on seed differentials and convert activity."""

    # Pinto token address (the reference token)
    PINTO_TOKEN = "0xb170000aeefa790fa61d6e837d1035906839a3c8"

    def __init__(self, initial_bonus: float = 0.0):
        """Initialize the bonus calculator.

        Args:
            initial_bonus: Starting bonus value (default: 0.0)
        """
        self.bonus = initial_bonus
        self.seeds_by_season: Dict[int, Dict[str, int]] = {}
        self.seasons_with_converts: Set[int] = set()
        self.convert_count_by_season: Dict[int, int] = {}  # Track number of converts per season
        self.results: List[Dict] = []

    def load_seeds_data(self, filename: str) -> None:
        """Load seeds data from CSV and group by season.

        Args:
            filename: Path to seeds_data.csv
        """
        print(f"Loading seeds data from {filename}...")

        try:
            df = pd.read_csv(filename)
        except FileNotFoundError:
            print(f"Error: File {filename} not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading seeds file: {e}")
            sys.exit(1)

        # Group by season and build dict of {token: seeds}
        for _, row in df.iterrows():
            season = int(row['season'])
            token = row['token'].lower()  # Normalize to lowercase
            seeds = int(row['stalkEarnedPerSeason'])

            if season not in self.seeds_by_season:
                self.seeds_by_season[season] = {}

            self.seeds_by_season[season][token] = seeds

        print(f"Loaded {len(df)} seed records across {len(self.seeds_by_season)} seasons")

    def load_converts_data(self, filename: str) -> None:
        """Load convert data from CSV and build set of seasons with convert activity.

        Note: Multiple converts can occur in a single season, but the bonus penalty
        is only applied ONCE per season (on the first occurrence).

        Args:
            filename: Path to lp_converts_with_season.csv
        """
        print(f"Loading convert data from {filename}...")

        try:
            df = pd.read_csv(filename)
        except FileNotFoundError:
            print(f"Error: File {filename} not found")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading converts file: {e}")
            sys.exit(1)

        # Build set of unique seasons with convert activity
        self.seasons_with_converts = set(df['season'].unique())

        # Count number of converts per season (for reporting purposes)
        convert_counts = df['season'].value_counts().to_dict()
        self.convert_count_by_season = convert_counts

        print(f"Loaded {len(df)} convert records across {len(self.seasons_with_converts)} seasons")

        # Report seasons with multiple converts
        multiple_convert_seasons = {s: c for s, c in convert_counts.items() if c > 1}
        if multiple_convert_seasons:
            print(f"Seasons with multiple converts: {len(multiple_convert_seasons)}")
            top_seasons = sorted(multiple_convert_seasons.items(), key=lambda x: x[1], reverse=True)[:5]
            for season, count in top_seasons:
                print(f"  Season {season}: {count} converts")

    def get_season_seeds(self, season: int) -> Optional[Dict[str, int]]:
        """Get seeds per token for a given season.

        Args:
            season: Season number

        Returns:
            Dict mapping token address to seeds, or None if season not found
        """
        return self.seeds_by_season.get(season)

    def calculate_differential(self, season: int) -> Tuple[Optional[float], Optional[int], Optional[int], Optional[str]]:
        """Calculate the seed differential for a season.

        Args:
            season: Season number

        Returns:
            Tuple of (differential, pinto_seeds, max_lp_seeds, max_lp_token)
            Returns (None, None, None, None) if data is missing
        """
        season_seeds = self.get_season_seeds(season)

        if not season_seeds:
            return None, None, None, None

        # Get Pinto seeds
        pinto_seeds = season_seeds.get(self.PINTO_TOKEN.lower())
        if pinto_seeds is None:
            print(f"Warning: Pinto seeds not found for season {season}")
            return None, None, None, None

        # Find max seeds among LP tokens (all tokens except Pinto)
        lp_tokens = {token: seeds for token, seeds in season_seeds.items()
                     if token != self.PINTO_TOKEN.lower()}

        if not lp_tokens:
            print(f"Warning: No LP tokens found for season {season}")
            return None, None, None, None

        max_lp_token = max(lp_tokens.items(), key=lambda x: x[1])
        max_lp_seeds = max_lp_token[1]
        max_lp_token_address = max_lp_token[0]

        differential = pinto_seeds - max_lp_seeds

        return differential, pinto_seeds, max_lp_seeds, max_lp_token_address

    def has_convert_activity(self, season: int) -> bool:
        """Check if a season has convert activity.

        Args:
            season: Season number

        Returns:
            True if season has converts, False otherwise
        """
        return season in self.seasons_with_converts

    def process_season(self, season: int) -> None:
        """Process a single season and update bonus accordingly.

        IMPORTANT: The bonus penalty is applied ONCE per season, regardless of how many
        converts occurred in that season. This prevents multiple converts in the same
        season from applying the penalty multiple times.

        Args:
            season: Season number
        """
        # Calculate differential
        differential, pinto_seeds, max_lp_seeds, max_lp_token = self.calculate_differential(season)

        if differential is None:
            # Skip this season if we can't calculate differential
            return

        # Check convert activity (binary: yes/no, regardless of count)
        has_converts = self.has_convert_activity(season)
        convert_count = self.convert_count_by_season.get(season, 0)

        # Store bonus before adjustments
        bonus_before = self.bonus

        # Apply bonus logic (ONCE per season, regardless of convert count)
        action = ""

        if not has_converts:
            # Case A: No convert activity
            if differential > 0:
                self.bonus += differential
                action = "add_differential"
            else:
                # No change
                action = "no_change"
        else:
            # Case B: Has convert activity (penalty applied ONCE regardless of count)
            if differential > 0:
                self.bonus -= differential
                action = "subtract_differential"
            else:
                # differential <= 0
                self.bonus *= 0.99
                action = "decay_1pct"

        # Clamp bonus to zero
        self.bonus = max(0.0, self.bonus)

        # Calculate change
        bonus_change = self.bonus - bonus_before

        # Record result
        result = {
            'season': season,
            'pinto_seeds': pinto_seeds,
            'max_lp_seeds': max_lp_seeds,
            'max_lp_token': max_lp_token,
            'differential': differential,
            'has_converts': has_converts,
            'convert_count': convert_count,  # Number of converts in this season
            'bonus_before': bonus_before,
            'bonus_change': bonus_change,
            'bonus_after': self.bonus,
            'action': action
        }

        self.results.append(result)

    def calculate_bonus(self, start_season: Optional[int] = None,
                       end_season: Optional[int] = None) -> float:
        """Main calculation loop through all seasons.

        Args:
            start_season: Starting season (optional, uses data min)
            end_season: Ending season (optional, uses data max)

        Returns:
            Final bonus value
        """
        # Get all seasons and sort
        all_seasons = sorted(self.seeds_by_season.keys())

        if not all_seasons:
            print("Error: No seasons found in seeds data")
            sys.exit(1)

        # Apply season filters
        if start_season is not None:
            all_seasons = [s for s in all_seasons if s >= start_season]
        if end_season is not None:
            all_seasons = [s for s in all_seasons if s <= end_season]

        if not all_seasons:
            print("Error: No seasons match the filter criteria")
            sys.exit(1)

        print(f"\nProcessing {len(all_seasons)} seasons from {all_seasons[0]} to {all_seasons[-1]}...")
        print(f"Initial bonus: {self.bonus:,.2f}\n")

        # Process each season in order
        for season in all_seasons:
            self.process_season(season)

        print(f"\nFinal bonus: {self.bonus:,.2f}")
        return self.bonus

    def save_results(self, filename: str) -> None:
        """Save detailed results to CSV.

        Args:
            filename: Output CSV filename
        """
        if not self.results:
            print("No results to save")
            return

        df = pd.DataFrame(self.results)
        df.to_csv(filename, index=False)
        print(f"\nDetailed results saved to {filename}")
        print(f"Total records: {len(df)}")

    def print_summary(self) -> None:
        """Print summary statistics."""
        if not self.results:
            print("No results to summarize")
            return

        df = pd.DataFrame(self.results)

        print("\n" + "="*70)
        print("BONUS CALCULATION SUMMARY")
        print("="*70)

        print(f"\nSeason Range: {df['season'].min()} - {df['season'].max()}")
        print(f"Total Seasons Processed: {len(df)}")
        print(f"\nFinal Bonus Value: {self.bonus:,.2f}")

        print(f"\nAction Breakdown:")
        action_counts = df['action'].value_counts()
        for action, count in action_counts.items():
            print(f"  {action}: {count}")

        print(f"\nSeasons with Converts: {df['has_converts'].sum()}")
        print(f"Seasons without Converts: {(~df['has_converts']).sum()}")

        # Show info about multiple converts per season
        seasons_with_converts = df[df['has_converts']]
        if not seasons_with_converts.empty:
            total_converts = seasons_with_converts['convert_count'].sum()
            max_converts_season = seasons_with_converts.loc[seasons_with_converts['convert_count'].idxmax()]
            print(f"\nConvert Activity Details:")
            print(f"  Total convert events: {total_converts}")
            print(f"  Season with most converts: {max_converts_season['season']} ({int(max_converts_season['convert_count'])} converts)")
            print(f"  Note: Penalty applied ONCE per season regardless of convert count")

        print(f"\nDifferential Statistics:")
        print(f"  Positive differentials: {(df['differential'] > 0).sum()}")
        print(f"  Negative/zero differentials: {(df['differential'] <= 0).sum()}")
        print(f"  Average differential: {df['differential'].mean():,.2f}")
        print(f"  Max differential: {df['differential'].max():,.2f}")
        print(f"  Min differential: {df['differential'].min():,.2f}")

        print("\n" + "="*70)


def main():
    """Main entry point for the bonus calculator."""
    parser = argparse.ArgumentParser(
        description='Calculate convert bonus based on seed differentials'
    )
    parser.add_argument('--seeds', type=str, required=True,
                       help='Path to seeds data CSV file')
    parser.add_argument('--converts', type=str, required=True,
                       help='Path to LP converts CSV file')
    parser.add_argument('--output', type=str, default='csv_output/bonus_calculation_details.csv',
                       help='Output CSV filename (default: csv_output/bonus_calculation_details.csv)')
    parser.add_argument('--initial-bonus', type=float, default=0.0,
                       help='Starting bonus value (default: 0.0)')
    parser.add_argument('--start-season', type=int,
                       help='Starting season filter (optional)')
    parser.add_argument('--end-season', type=int,
                       help='Ending season filter (optional)')

    args = parser.parse_args()

    try:
        # Initialize calculator
        calculator = BonusCalculator(initial_bonus=args.initial_bonus)

        # Load data
        calculator.load_seeds_data(args.seeds)
        calculator.load_converts_data(args.converts)

        # Calculate bonus
        final_bonus = calculator.calculate_bonus(
            start_season=args.start_season,
            end_season=args.end_season
        )

        # Save results
        calculator.save_results(args.output)

        # Print summary
        calculator.print_summary()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
