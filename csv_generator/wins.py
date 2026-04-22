import pandas as pd


matches = pd.read_csv("datasets/matches.csv")

team_wins = matches['winner'].value_counts()

team_wins_df = team_wins.reset_index()

team_wins_df.columns = ["team","wins"]

print(team_wins_df)

team_wins_df.to_csv("team_wins.csv")
