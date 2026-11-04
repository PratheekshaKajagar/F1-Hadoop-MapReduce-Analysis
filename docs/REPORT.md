# Project Report - Results & Insights (all numbers from the Hadoop outputs)

## 1. Why Hadoop / HDFS / MapReduce
Lap-level data is the largest table (189,105 laps over 173 races, 5,941 pit stops). It is stored in HDFS (`/f1/laps` ...) and aggregated by MapReduce jobs that run mapper -> shuffle/sort -> reducer, so the same scripts scale to multi-GB data by adding nodes. Honest note: this dataset is small; the value here is the architecture, not volume.

## 2. Findings
**Drivers.** Best average finish (min 50 starts): Verstappen 4.19, Hamilton 4.94, Piastri 6.63, Norris 7.28, Leclerc 7.45 (retirements included). Fastest race pace vs field: Verstappen -1.326%, Hamilton -1.106%, Piastri -0.754%. Consistency (within-race lap variation, lower is better): Charles Leclerc 1.26% best; the whole field only spans 1.26-1.465%, and pace vs consistency correlation is 0.252 - i.e. consistency barely separates drivers, pace and results do. Laps led: Verstappen 3,697 (35.7% of all 10,367), Hamilton 1,971 (19.0%), Leclerc 878.

**Constructors.** Points 2018-2025 (GP+sprint): Mercedes 4,441.5, Red Bull 4,399.5, Ferrari 3,539.5, McLaren 2,644.0. Wins: Red Bull 75, Mercedes 55, McLaren 21, Ferrari 19. Champions: 2018 Mercedes, 2019 Mercedes, 2020 Mercedes, 2021 Mercedes, 2022 Red Bull, 2023 Red Bull, 2024 McLaren, 2025 McLaren. Mercedes edges Red Bull on total points while Red Bull wins more races. Ferrari had 109 podiums but only 19 wins.

**Qualifying vs race.** Grid slot and finish correlate r = 0.738. Pole converts to a win 52.3% of the time. Overall 52.8% of classified starts gain places, 29.8% lose, 17.4% hold. Biggest average gainers: Lance Stroll (+2.26), Nicholas Latifi (+1.84), Esteban Ocon (+1.79) - gains are largest for drivers starting mid/back (regression to the mean and strategy), so front-runners cannot gain much. Grid matters most at Monaco (r=0.879) and least at Interlagos (r=0.628).

**Circuits.** Highest fastest-lap speeds: Monza 246.0 km/h, Jeddah 238.7 km/h, Albert Park 232.9 km/h; slowest: Monaco 156.9, Marina Bay (pre-2023 layout) 169.2, Marina Bay 182.7. Shortest lap times: Red Bull Ring 70.35s, Interlagos 76.34s, Zandvoort 76.42s (track length effect). Largest pace spread between drivers: Barcelona (pre-2023) 1.22%, Montreal 1.16%, Sochi 1.15%.

**Pit stops** (pit-lane time, 5,565 valid of 5,941; field mean 24.69s, median 23.57s). Fastest teams on average: Red Bull 23.96s, Mercedes 24.07s, Ferrari 24.2s; slowest: Sauber (Alfa Romeo) 25.46s, Haas 25.55s. The whole spread is ~1.6 s and std-devs are 4-6 s (driven by occasional slow stops), so differences are small relative to variability - interpret rankings cautiously (error bars in Fig 9).

**Historical trend.** Like-for-like race-pace index (2018=100): 2018: 100.0, 2019: 100.12, 2020: 99.28, 2021: 100.25, 2022: 101.84, 2023: 101.01, 2024: 100.26, 2025: 99.74. Pace was slowest in 2022 (new regulations) and has since returned to 2018 levels; no strong monotonic trend. Champion team's share of all points: 2018: 31.8%, 2019: 34.5%, 2020: 33.3%, 2021: 27.8%, 2022: 32.3%, 2023: 35.0%, 2024: 25.0%, 2025: 31.6%. Eras: Mercedes 2018-21, Red Bull 2022-23, McLaren 2024-25. Driver champions: 2019 Lewis Hamilton, 2020 Lewis Hamilton, 2022 Max Verstappen, 2024 Max Verstappen, 2025 Lando Norris, 2018 Lewis Hamilton, 2021 Max Verstappen, 2023 Max Verstappen.

## 3. K-Means (descriptive clustering, no prediction)
25 drivers with >=40 starts, 8 features, standardised. Silhouette by k: 2:0.37, 3:0.34, 4:0.30, 5:0.28, 6:0.24, 7:0.24, 8:0.25. k=2 scores highest but only splits front vs midfield; k=3 (best silhouette for k>=3, and visible elbow) was used. Clusters: (1) Hamilton & Verstappen - elite: ~32% win rate, avg finish 4.6; (2) front/upper-midfield winners and podium finishers (Leclerc, Norris, Piastri, Russell, Sainz, Bottas, Perez, Vettel); (3) midfield/backmarkers. Caveat: results depend on car quality as much as driver skill, and only 2 drivers sit in cluster 1.

## 4. Limitations
Car performance is confounded with driver performance; Ergast pit time is lane time; 2018-2025 only; small data volume; local-mode Hadoop in the build environment (see README).
