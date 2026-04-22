import pandas as pd

matches = pd.read_csv("datasets/matches.csv")
deliveries = pd.read_csv("datasets/deliveries.csv")

print(matches.shape)
print(deliveries.shape)
