"""
Advanced Player Clustering for IPL Cricket Data Mining Project.

This module performs multi-dimensional clustering on enriched player statistics
using PCA for dimensionality reduction, Elbow Method + Silhouette Score for
optimal cluster selection, and compares KMeans vs DBSCAN approaches.

Outputs:
    - datasets/advanced_player_clusters.csv
    - plots/elbow_curve.png
    - plots/player_clusters_pca.png
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend for saving plots
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score


def load_enriched_player_stats():
    """Load enriched player statistics produced by feature_engineering.py."""
    path = 'datasets/enriched_player_stats.csv'
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run feature_engineering.py first."
        )
    df = pd.read_csv(path)
    print(f"[✓] Loaded enriched player stats: {df.shape}")
    return df


def select_clustering_features(df):
    """
    Select the feature columns to use for clustering.
    Uses batting + bowling metrics for multi-dimensional analysis.
    """
    feature_cols = [
        'total_runs', 'strike_rate', 'batting_average', 'fours', 'sixes',
        'dot_ball_pct', 'innings_played', 'wickets_taken', 'economy_rate',
        'bowling_strike_rate', 'all_rounder_score'
    ]
    # Keep only columns that exist
    available = [c for c in feature_cols if c in df.columns]
    print(f"[✓] Using {len(available)} features for clustering: {available}")
    return available


def scale_and_pca(df, feature_cols, n_components=2):
    """
    Standardize features and apply PCA to reduce to 2D for visualization.

    Returns:
        X_scaled: scaled feature matrix
        X_pca: 2D PCA-transformed data
        pca: fitted PCA object
        scaler: fitted StandardScaler
    """
    X = df[feature_cols].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=n_components, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    explained = pca.explained_variance_ratio_
    print(f"[✓] PCA: Component 1 explains {explained[0]:.2%}, Component 2 explains {explained[1]:.2%}")
    print(f"    Total variance explained: {sum(explained):.2%}")

    return X_scaled, X_pca, pca, scaler


def elbow_method(X_scaled, k_range=range(2, 9)):
    """
    Apply the Elbow Method to determine optimal k for KMeans.
    Saves the elbow curve plot.

    Returns:
        inertias: list of inertia values for each k
    """
    os.makedirs('plots', exist_ok=True)

    inertias = []
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(list(k_range), inertias, 'bo-', linewidth=2, markersize=8)
    ax.set_xlabel('Number of Clusters (k)', fontsize=13)
    ax.set_ylabel('Inertia (Within-Cluster Sum of Squares)', fontsize=13)
    ax.set_title('Elbow Method – Optimal k Selection', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Annotate each point
    for i, k in enumerate(k_range):
        ax.annotate(f'k={k}', (k, inertias[i]), textcoords="offset points",
                    xytext=(0, 12), ha='center', fontsize=10)

    fig.tight_layout()
    fig.savefig('plots/elbow_curve.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("[✓] Elbow curve saved to plots/elbow_curve.png")

    return inertias


def find_optimal_k(X_scaled, k_range=range(2, 9)):
    """
    Use Silhouette Score to find the optimal k.
    Returns the k with the highest silhouette score.
    """
    scores = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        scores[k] = score
        print(f"    k={k}: Silhouette Score = {score:.4f}")

    best_k = max(scores, key=scores.get)
    print(f"[✓] Optimal k by Silhouette Score: {best_k} (score={scores[best_k]:.4f})")
    return best_k, scores


def run_kmeans(X_scaled, X_pca, k):
    """
    Run KMeans with the chosen k. Returns cluster labels.
    """
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    print(f"[✓] KMeans (k={k}): Silhouette Score = {score:.4f}")
    return labels, score


def run_dbscan(X_scaled):
    """
    Run DBSCAN clustering as an alternative to KMeans.
    Auto-tunes eps using nearest-neighbors heuristic.
    """
    from sklearn.neighbors import NearestNeighbors

    # Use k-nearest neighbors to estimate eps
    k_nn = min(5, X_scaled.shape[0] - 1)
    nn = NearestNeighbors(n_neighbors=k_nn)
    nn.fit(X_scaled)
    distances, _ = nn.kneighbors(X_scaled)
    sorted_distances = np.sort(distances[:, -1])

    # Use the "knee" as eps (90th percentile heuristic)
    eps = np.percentile(sorted_distances, 90)
    eps = max(eps, 0.5)  # minimum eps

    dbscan = DBSCAN(eps=eps, min_samples=5)
    labels = dbscan.fit_predict(X_scaled)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = (labels == -1).sum()

    if n_clusters >= 2:
        mask = labels != -1
        score = silhouette_score(X_scaled[mask], labels[mask])
    else:
        score = -1.0

    print(f"[✓] DBSCAN (eps={eps:.2f}): {n_clusters} clusters, {n_noise} noise points, "
          f"Silhouette = {score:.4f}")
    return labels, score, n_clusters


def assign_cluster_labels(df, labels, feature_cols):
    """
    Assign meaningful labels to clusters based on feature profile analysis.
    Labels: Batsman, Bowler, All-Rounder, Tail-Ender
    """
    df = df.copy()
    df['cluster'] = labels

    # Compute cluster profiles
    profiles = df.groupby('cluster')[feature_cols].mean()

    # Scoring heuristic for labeling
    label_map = {}
    used_labels = set()

    # Determine label for each cluster
    possible_labels = ['Elite All-Rounder', 'Top Batsman', 'Key Bowler', 'Tail-Ender',
                       'Impact Player', 'Specialist Batsman', 'Specialist Bowler', 'Role Player']

    for cluster_id in profiles.index:
        if cluster_id == -1:
            label_map[-1] = 'Noise/Outlier'
            continue

        p = profiles.loc[cluster_id]

        # Simple heuristic: check what the cluster is best at
        bat_score = 0
        bowl_score = 0

        if 'batting_average' in p and 'total_runs' in p:
            bat_score = (p.get('batting_average', 0) * 0.3 +
                        p.get('strike_rate', 0) * 0.2 +
                        p.get('total_runs', 0) / max(profiles['total_runs'].max(), 1) * 100 * 0.5)

        if 'wickets_taken' in p:
            bowl_score = (p.get('wickets_taken', 0) / max(profiles['wickets_taken'].max(), 1) * 100 * 0.5 +
                         max(0, 15 - p.get('economy_rate', 15)) * 5 * 0.5)

        ar_score = p.get('all_rounder_score', 0)

        # Determine label
        if ar_score > profiles['all_rounder_score'].quantile(0.7) and 'All-Rounder' not in used_labels:
            label = 'Elite All-Rounder' if ar_score > profiles['all_rounder_score'].quantile(0.85) else 'All-Rounder'
        elif bat_score > bowl_score * 1.5:
            if bat_score > profiles.apply(
                lambda x: x.get('batting_average', 0) * 0.3, axis=0
            ).quantile(0.7) if hasattr(profiles, 'apply') else True:
                label = 'Top Batsman'
            else:
                label = 'Batsman'
        elif bowl_score > bat_score * 1.5:
            label = 'Key Bowler'
        elif bat_score < profiles.apply(
            lambda _: 30, axis=0
        ).mean() if hasattr(profiles, 'apply') else bat_score < 30:
            label = 'Tail-Ender'
        else:
            label = 'Impact Player'

        # Ensure unique labels
        if label in used_labels:
            for alt in possible_labels:
                if alt not in used_labels:
                    label = alt
                    break

        label_map[cluster_id] = label
        used_labels.add(label)

    df['cluster_label'] = df['cluster'].map(label_map)
    print(f"[✓] Cluster labels assigned: {label_map}")
    return df


def plot_clusters_pca(X_pca, labels, cluster_labels_map=None, title='Player Clusters (PCA)'):
    """
    Create a scatter plot of PCA-reduced data colored by cluster assignment.
    Saves to plots/player_clusters_pca.png.
    """
    os.makedirs('plots', exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 8))

    unique_labels = sorted(set(labels))
    colors = plt.cm.Set2(np.linspace(0, 1, max(len(unique_labels), 3)))

    for i, label in enumerate(unique_labels):
        mask = labels == label
        name = cluster_labels_map.get(label, f'Cluster {label}') if cluster_labels_map else f'Cluster {label}'
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=[colors[i % len(colors)]], label=name,
                   s=60, alpha=0.7, edgecolors='white', linewidth=0.5)

    ax.set_xlabel('PCA Component 1', fontsize=13)
    ax.set_ylabel('PCA Component 2', fontsize=13)
    ax.set_title(title, fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, framealpha=0.9)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    fig.savefig('plots/player_clusters_pca.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("[✓] PCA cluster plot saved to plots/player_clusters_pca.png")


# ── Main Pipeline ───────────────────────────────────────────────────────────────

def run_clustering():
    """Run the full advanced clustering pipeline."""
    os.makedirs('plots', exist_ok=True)

    # Load data
    df = load_enriched_player_stats()
    feature_cols = select_clustering_features(df)

    # Scale + PCA
    X_scaled, X_pca, pca, scaler = scale_and_pca(df, feature_cols)

    # Elbow Method
    print("\n── Elbow Method ──")
    elbow_method(X_scaled)

    # Silhouette Score for optimal k
    print("\n── Silhouette Analysis ──")
    best_k, sil_scores = find_optimal_k(X_scaled)

    # KMeans with optimal k
    print(f"\n── KMeans Clustering (k={best_k}) ──")
    kmeans_labels, kmeans_score = run_kmeans(X_scaled, X_pca, best_k)

    # DBSCAN
    print("\n── DBSCAN Clustering ──")
    dbscan_labels, dbscan_score, dbscan_n = run_dbscan(X_scaled)

    # Compare
    print("\n── Clustering Comparison ──")
    print(f"{'Method':<15} {'Clusters':<10} {'Silhouette':<12}")
    print(f"{'─'*37}")
    print(f"{'KMeans':<15} {best_k:<10} {kmeans_score:<12.4f}")
    print(f"{'DBSCAN':<15} {dbscan_n:<10} {dbscan_score:<12.4f}")

    # Use KMeans (typically better for this data)
    chosen_labels = kmeans_labels

    # Assign meaningful labels
    df_clustered = assign_cluster_labels(df, chosen_labels, feature_cols)

    # Build label map for plotting
    label_map = dict(zip(df_clustered['cluster'], df_clustered['cluster_label']))

    # PCA plot
    plot_clusters_pca(X_pca, chosen_labels, label_map)

    # Cluster summary
    print("\n── Cluster Summary ──")
    summary_cols = ['total_runs', 'strike_rate', 'batting_average',
                    'wickets_taken', 'economy_rate', 'all_rounder_score']
    summary_cols = [c for c in summary_cols if c in df_clustered.columns]
    summary = df_clustered.groupby('cluster_label')[summary_cols].mean().round(2)
    print(summary.to_string())

    print("\n── Cluster Sizes ──")
    print(df_clustered['cluster_label'].value_counts().to_string())

    # Save
    df_clustered.to_csv('datasets/advanced_player_clusters.csv', index=False)
    print(f"\n[✓] Saved datasets/advanced_player_clusters.csv ({len(df_clustered)} players)")
    print("\n[✓] Advanced clustering complete ✅")

    return df_clustered


if __name__ == '__main__':
    run_clustering()