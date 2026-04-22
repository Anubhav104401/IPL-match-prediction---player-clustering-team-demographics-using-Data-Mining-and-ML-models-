import pandas as pd


matches = pd.read_csv("datasets/matches.csv")

venue_stats = matches['venue'].value_counts()

print(venue_stats)

venue_stats.to_csv("venue_stats.csv")