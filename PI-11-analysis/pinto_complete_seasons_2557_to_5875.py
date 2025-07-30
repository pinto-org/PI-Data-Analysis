#!/usr/bin/env python3

# Known data points from the subgraph
known_data = {
    2557: 11356148233772,
    2558: 11351076061468,
    2559: 11350577081568,
    2560: 11350578101668,
    2561: 11350579121768,
    2562: 11350580141868,
    2563: 11350581161968,
    2564: 11350582182068,
    2565: 11348372524836,
    2566: 11348373544936,
    2567: 11348374565036,
    2568: 11347315230111,
    2569: 11347316250211,
    2570: 11347214456456,
    2571: 11347215476556,
    2572: 11347216496656,
    2573: 11347217537260,
    2574: 11347218557360,
    2575: 11347219577460,
    2576: 11344957405189,
    2577: 11344958425289,
    2578: 11344959445389,
    2579: 11344960465489,
    2580: 11344961485589,
    2581: 11344962505689,
    2582: 11344963525789,
    2583: 11344964545889,
    2584: 11344965565989,
    2585: 11344966586089,
    2586: 11344916375617,
    2587: 11344917395717,
    2588: 11344918415817,
    2589: 11344919435917,
    2590: 11340165005221,
    2591: 11340166025321,
    2592: 11340167045421,
    2593: 11340168065521,
    2594: 11340169085621,
    2595: 11320170126225,
    2596: 11320171146325,
    2597: 11320172166425,
    2598: 11320173186525,
    2599: 11320174206625,
    2600: 11320175226725,
    2601: 11320176246825,
    2602: 11320177266925,
    2603: 11318178287025,
    2604: 11318179307125,
    2605: 11318180327225,
    2606: 11318181347325,
    2607: 11318182367425,
    2608: 11318183387525,
    2609: 11318184407625,
    2610: 11318185427725,
    2611: 11318186447825,
    2612: 11307627851234,
    2613: 11307628871334,
    2614: 11307629891434,
    2615: 11307630911534,
    2616: 11305997800412,
    2617: 11305998841016,
    2618: 11305999861116,
    2619: 11306000881216,
    2620: 11306001901316,
    2621: 11306002921416,
    2622: 11306003941516,
    2623: 11306004961616,
    2624: 11306005981716,
    2625: 11306007001816,
    2626: 11306008021916,
    2627: 11306009042016,
    2628: 11306010062116,
    2629: 11306011082216,
    2630: 11286012102316,
    2631: 11262340239833,
    2632: 11262341259933,
    2633: 11262342280033,
    2634: 11262343300133,
    2635: 11262344320233,
    2636: 11262345340333,
    2637: 11262346360433,
    2638: 11262347380533,
    2639: 11262348400633,
    2640: 11262349420733,
    2641: 11262350461337,
    2642: 11262351481437,
    2643: 11262352501537,
    2644: 11258132187102,
    2645: 11258133207202,
    2646: 11258134227302,
    4000: 10870428405170,
    4001: 10870096155519,
    4002: 10869709996453,
    4003: 10869272715082,
    4004: 10868873735182,
    4005: 10868712783442,
    4006: 10868496860093,
    4007: 10868226940591,
    4008: 10867900837260,
    4009: 10867515779752,
    4010: 10867116799852,
    4011: 10866955383351,
    4012: 10866738272960,
    4013: 10866465021024,
    4014: 10866134932106,
    4015: 10865748468689,
    4016: 10865349488789,
    4017: 10865187953283,
    4018: 10864969604528,
    4019: 10864694077604,
    4020: 10864358740337,
    4021: 10863965020674,
    4022: 10863566040774,
    4023: 10863405318587,
    4024: 10863188905739,
    4025: 10862916028233,
    4026: 10862617048333,
    4027: 10862458492317,
    4028: 10862245793386,
    4029: 10861972634300,
    4030: 10861973654400,
    4031: 10861808371096,
    4032: 10861587112275,
    4033: 10861313011833,
    4034: 10860984238214,
    4035: 10860594749997,
    4036: 10860145075059,
    4037: 10859639373581,
    4038: 10859075168565,
    4039: 10858816531896,
    4040: 10858654158258,
    4041: 10858436440624,
    4042: 10858162171393,
    4043: 10858163191493,
    4044: 10858001704870,
    4045: 10857784460665,
    4046: 10857510059936,
    4047: 10857511080036,
    4048: 10857348882150,
    4049: 10857129170471,
    4050: 10856851883605,
    4051: 10856852903705,
    4052: 10856688846244,
    4053: 10856467959406,
    4054: 10856193431854,
    4055: 10856194451954,
    4056: 10856033352394,
    4057: 10855817489533,
    4058: 10855546725356,
    4059: 10855547745456,
    4060: 10855394342539,
    4061: 10855187779050,
    4062: 10854924689875,
    4063: 10854925709975,
    4064: 10854774242548,
    4065: 10854565636859,
    4066: 10854303588646,
    4067: 10854304608746,
    4068: 10854149500105,
    4069: 10853937802682,
    4070: 10853670166238,
    4071: 10853353231649,
    4072: 10852995649606,
    4073: 10852848767783,
    4074: 10852647595643,
    4075: 10852395328313,
    4076: 10852108586780,
    4077: 10852109606880,
    4078: 10851976235176,
    4079: 10851792252953,
    4080: 10851562142835,
    4081: 10851281545479,
    4082: 10851182565579,
    4083: 10851049734374,
    4084: 10850867381058,
    4085: 10850633376690,
    4086: 10850349400796,
    4087: 10850250420896,
    4088: 10850120626588,
    4089: 10849944938281,
    4090: 10849714754668,
    5870: 10452591257602,
    5871: 10452421803982,
    5872: 10452372824082,
    5873: 10454549838905,
    5874: 10454544483986,
    5875: 10455287674696
}

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

# Generate complete dataset
complete_data = {}

# Sort known seasons
known_seasons = sorted(known_data.keys())

# Handle seasons before first known season (shouldn't happen in this case)
first_season = 2557
last_season = 5875

# Fill in data between known points
for i in range(len(known_seasons) - 1):
    current_season = known_seasons[i]
    next_season = known_seasons[i + 1]
    current_supply = known_data[current_season]
    next_supply = known_data[next_season]
    
    # Add known data point
    complete_data[current_season] = current_supply
    
    # Interpolate missing seasons
    if next_season - current_season > 1:
        for missing_season in range(current_season + 1, next_season):
            # Add 1,000,000 for each missing season
            complete_data[missing_season] = current_supply + ((missing_season - current_season) * 1000000)

# Add the last known data point
complete_data[known_seasons[-1]] = known_data[known_seasons[-1]]

# Fill in any remaining gaps at the beginning or end
all_seasons = set(range(first_season, last_season + 1))
filled_seasons = set(complete_data.keys())
missing_seasons = all_seasons - filled_seasons

# Handle missing seasons at the end (after 4090, before 5870)
if missing_seasons:
    missing_list = sorted(missing_seasons)
    
    # Find the gap between 4090 and 5870
    gap_start = 4091
    gap_end = 5869
    gap_start_supply = known_data[4090]
    gap_end_supply = known_data[5870]
    
    for season in range(gap_start, gap_end + 1):
        # Add 1,000,000 for each season in the gap
        complete_data[season] = gap_start_supply + ((season - 4090) * 1000000)

# Create CSV content
csv_lines = ["season,supply,supply_formatted,calculated_value,cumulative_sum"]
cumulative_sum = 0.0

for season in range(first_season, last_season + 1):
    supply = complete_data[season]
    supply_formatted = supply / 1000000  # Convert to millions for readability
    calculated_value = supply * 416666666666667 / 1e18
    cumulative_sum += calculated_value
    
    csv_lines.append(f"{season},{supply},{supply_formatted:.6f},{calculated_value:.6f},{cumulative_sum:.6f}")

# Write to file
with open('/Users/brian/dev/pinto_complete_seasons_2557_to_5875.csv', 'w') as f:
    f.write('\n'.join(csv_lines))

print(f"Generated complete dataset with {len(csv_lines)-1} seasons")
print(f"From season {first_season} to {last_season}")
print(f"Final cumulative sum: {cumulative_sum:.6f}")