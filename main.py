"""
Pipeline Orchestration for IPL Cricket Data Mining Project.

This script runs the entire analytical pipeline in sequence:
    1. Preprocessing  – Load and validate raw data
    2. Feature Engineering – Compute enriched player & match features
    3. Clustering – Multi-dimensional player clustering with PCA
    4. Classification – 4-model comparison for match winner prediction
    5. Data Warehouse – Build star schema + run OLAP queries

Usage:
    python main.py
"""

import os
import sys
import time
import pandas as pd


def print_banner():
    """Print an attractive startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   🏏  IPL Cricket Data Mining & Data Warehousing Pipeline  🏏    ║
║                                                                  ║
║   Advanced Analytics • Machine Learning • OLAP                   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def step_preprocessing():
    """Step 1: Load and validate datasets."""
    print("\n" + "═" * 60)
    print("  STEP 1: PREPROCESSING")
    print("═" * 60)

    matches = pd.read_csv("datasets/matches.csv")
    deliveries = pd.read_csv("datasets/deliveries.csv")

    print(f"  Matches:     {matches.shape[0]} rows × {matches.shape[1]} columns")
    print(f"  Deliveries:  {deliveries.shape[0]} rows × {deliveries.shape[1]} columns")

    # Validate columns
    required_match_cols = ['id', 'team1', 'team2', 'winner', 'venue']
    required_del_cols = ['match_id', 'batter', 'bowler', 'batsman_runs', 'total_runs']

    missing_m = [c for c in required_match_cols if c not in matches.columns]
    missing_d = [c for c in required_del_cols if c not in deliveries.columns]

    if missing_m:
        print(f"  ⚠ Missing match columns: {missing_m}")
    if missing_d:
        print(f"  ⚠ Missing delivery columns: {missing_d}")

    # Check for additional datasets
    extra_files = ['players.csv', 'player_stats.csv', 'teams.csv',
                   'team_wins.csv', 'venue_stats.csv', 'player_runs.csv']
    for f in extra_files:
        path = os.path.join('datasets', f)
        if os.path.exists(path):
            df = pd.read_csv(path)
            print(f"  {f:<25} {df.shape[0]:>6} rows × {df.shape[1]} cols")

    print("\n[✓] Preprocessing complete")
    return matches.shape, deliveries.shape


def step_feature_engineering():
    """Step 2: Run advanced feature engineering."""
    print("\n" + "═" * 60)
    print("  STEP 2: FEATURE ENGINEERING")
    print("═" * 60)

    from feature_engineering import run_feature_engineering
    player_stats, enriched_matches = run_feature_engineering()
    return len(player_stats), len(enriched_matches)


def step_clustering():
    """Step 3: Run advanced clustering."""
    print("\n" + "═" * 60)
    print("  STEP 3: CLUSTERING")
    print("═" * 60)

    from clustering import run_clustering
    df_clustered = run_clustering()
    cluster_counts = df_clustered['cluster_label'].value_counts().to_dict()
    return cluster_counts


def step_classification():
    """Step 4: Run advanced classification."""
    print("\n" + "═" * 60)
    print("  STEP 4: CLASSIFICATION")
    print("═" * 60)

    from classification import run_classification
    trained_models, cv_results, le, scaler, feature_names = run_classification()
    return cv_results


def step_datawarehouse():
    """Step 5: Build data warehouse and run OLAP queries."""
    print("\n" + "═" * 60)
    print("  STEP 5: DATA WAREHOUSE")
    print("═" * 60)

    from datawarehouse import run_datawarehouse
    results = run_datawarehouse()

    # Get table counts
    import sqlite3
    conn = sqlite3.connect('ipl_warehouse.db')
    table_counts = {}
    for table in ['dim_date', 'dim_team', 'dim_venue', 'dim_player', 'fact_matches']:
        try:
            count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn).iloc[0, 0]
            table_counts[table] = count
        except:
            table_counts[table] = 0
    conn.close()
    return table_counts


def print_final_summary(results):
    """Print the final summary report."""
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                    FINAL SUMMARY REPORT                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    # Dataset sizes
    if 'preprocessing' in results:
        m_shape, d_shape = results['preprocessing']
        print(f"\n  📊 Dataset Sizes:")
        print(f"     Matches:               {m_shape[0]:>6} rows")
        print(f"     Deliveries:            {d_shape[0]:>6} rows")

    if 'feature_engineering' in results:
        n_players, n_matches = results['feature_engineering']
        print(f"     Enriched Players:      {n_players:>6}")
        print(f"     Enriched Match Feats:  {n_matches:>6}")

    # Cluster info
    if 'clustering' in results:
        print(f"\n  🎯 Cluster Counts:")
        for label, count in results['clustering'].items():
            print(f"     {label:<25} {count:>4} players")

    # Model accuracies
    if 'classification' in results:
        print(f"\n  🤖 Model Accuracies:")
        cv = results['classification']
        for _, row in cv.iterrows():
            print(f"     {row['Model']:<25} CV: {row['CV Accuracy Mean']:.4f} "
                  f"  Test: {row['Test Accuracy']:.4f}")

    # Warehouse table counts
    if 'datawarehouse' in results:
        print(f"\n  🗄️ Data Warehouse Tables:")
        for table, count in results['datawarehouse'].items():
            print(f"     {table:<25} {count:>6} rows")

    # Output files
    print(f"\n  📁 Generated Output Files:")
    output_files = [
        'datasets/enriched_player_stats.csv',
        'datasets/enriched_match_features.csv',
        'datasets/advanced_player_clusters.csv',
        'datasets/match_predictions_advanced.csv',
        'plots/elbow_curve.png',
        'plots/player_clusters_pca.png',
        'plots/shap_feature_importance.png',
        'ipl_warehouse.db'
    ]
    for f in output_files:
        status = "✓" if os.path.exists(f) else "✗"
        size = ""
        if os.path.exists(f):
            sz = os.path.getsize(f)
            if sz > 1024 * 1024:
                size = f" ({sz / 1024 / 1024:.1f} MB)"
            elif sz > 1024:
                size = f" ({sz / 1024:.1f} KB)"
            else:
                size = f" ({sz} B)"
        print(f"     [{status}] {f}{size}")

    print(f"\n  ⏱️ Total time: {results.get('total_time', 0):.1f} seconds")
    print("\n" + "═" * 62)
    print("  🏏 Pipeline complete! Run `streamlit run dashboard.py` for the dashboard.")
    print("═" * 62 + "\n")


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    """Run the full pipeline with error handling."""
    start_time = time.time()
    print_banner()

    results = {}
    steps = [
        ('preprocessing', step_preprocessing),
        ('feature_engineering', step_feature_engineering),
        ('clustering', step_clustering),
        ('classification', step_classification),
        ('datawarehouse', step_datawarehouse),
    ]

    for step_name, step_func in steps:
        try:
            result = step_func()
            results[step_name] = result
        except Exception as e:
            print(f"\n[✗] Step '{step_name}' FAILED: {e}")
            import traceback
            traceback.print_exc()
            print(f"    Continuing to next step...\n")

    results['total_time'] = time.time() - start_time
    print_final_summary(results)


if __name__ == '__main__':
    main()
