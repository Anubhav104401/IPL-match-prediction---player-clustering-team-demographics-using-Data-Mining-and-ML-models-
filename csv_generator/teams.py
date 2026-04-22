import pandas as pd

matches = pd.read_csv("datasets/matches.csv")

teams = pd.concat([matches['team1'], matches['team2']]).unique()

teams_df = pd.DataFrame(teams, columns=["team_name"])

print(teams_df)

teams_df.to_csv("teams.csv", index=False)