import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

df = pd.read_csv("datasets/team_wins.csv")

# clean
df = df.drop(columns=['Unnamed: 0'])

# feature
X = df[['wins']]

# scale
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# clustering
kmeans = KMeans(n_clusters=3, random_state=42)
df['cluster'] = kmeans.fit_predict(X_scaled)

# dynamic labeling
cluster_means = df.groupby('cluster')['wins'].mean().sort_values()
sorted_clusters = cluster_means.index.tolist()

cluster_names = {
    sorted_clusters[0]: "Weak Team",
    sorted_clusters[1]: "Average Team",
    sorted_clusters[2]: "Strong Team"
}

df['category'] = df['cluster'].map(cluster_names)

print(df)

print("\nCluster Summary:\n")
print(df.groupby('cluster')[['wins']].mean())


df.to_csv("clustered_teams.csv", index=False)

plt.bar(df['team'], df['wins'], color='skyblue')
plt.xticks(rotation=90)
plt.xlabel("Teams")
plt.ylabel("Wins")
plt.title("Team Performance")
plt.show()