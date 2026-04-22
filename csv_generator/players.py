import pandas as pd


deliveries = pd.read_csv("datasets/deliveries.csv")

players = pd.concat([
    deliveries['batter'],
    deliveries['bowler'],
    deliveries['non_striker']
]).unique()

players_df = pd.DataFrame(players, columns=["player_name"])

players_df.to_csv("players.csv", index=False)
