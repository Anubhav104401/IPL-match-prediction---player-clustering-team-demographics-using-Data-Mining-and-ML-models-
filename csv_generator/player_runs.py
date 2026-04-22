import pandas as pd


deliveries = pd.read_csv("datasets/deliveries.csv")

player_runs = deliveries.groupby("batter")["batsman_runs"].sum()

player_runs = player_runs.sort_values(ascending=False)

print(player_runs.head(10))

player_runs.to_csv("player_runs.csv")