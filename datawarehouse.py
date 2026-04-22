"""
Data Warehouse Module for IPL Cricket Data Mining Project.

Implements a star schema using SQLite with fact and dimension tables.
Loads data from CSVs and enriched outputs into a normalized warehouse
and runs 5 analytical OLAP queries.

Schema:
    Fact:   fact_matches
    Dims:   dim_date, dim_team, dim_venue, dim_player

Output:
    - ipl_warehouse.db (SQLite database)
"""

import os
import sqlite3
import pandas as pd
import numpy as np


DB_PATH = 'ipl_warehouse.db'


def get_connection():
    """Create and return a SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema Creation ─────────────────────────────────────────────────────────────

def create_schema(conn):
    """
    Create the star schema: 4 dimension tables + 1 fact table.
    Drops existing tables for a clean rebuild.
    """
    cursor = conn.cursor()

    # Drop existing tables (reverse dependency order)
    cursor.execute("DROP TABLE IF EXISTS fact_matches")
    cursor.execute("DROP TABLE IF EXISTS dim_date")
    cursor.execute("DROP TABLE IF EXISTS dim_team")
    cursor.execute("DROP TABLE IF EXISTS dim_venue")
    cursor.execute("DROP TABLE IF EXISTS dim_player")

    # ── dim_date ──
    cursor.execute("""
        CREATE TABLE dim_date (
            date_key    INTEGER PRIMARY KEY AUTOINCREMENT,
            full_date   TEXT,
            year        INTEGER,
            season      TEXT,
            month       INTEGER,
            day         INTEGER
        )
    """)

    # ── dim_team ──
    cursor.execute("""
        CREATE TABLE dim_team (
            team_key      INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name     TEXT UNIQUE NOT NULL,
            cluster_label TEXT DEFAULT 'Unknown'
        )
    """)

    # ── dim_venue ──
    cursor.execute("""
        CREATE TABLE dim_venue (
            venue_key   INTEGER PRIMARY KEY AUTOINCREMENT,
            venue_name  TEXT UNIQUE NOT NULL,
            city        TEXT DEFAULT 'Unknown',
            avg_runs    REAL DEFAULT 0.0
        )
    """)

    # ── dim_player ──
    cursor.execute("""
        CREATE TABLE dim_player (
            player_key       INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name      TEXT UNIQUE NOT NULL,
            total_runs       INTEGER DEFAULT 0,
            strike_rate      REAL DEFAULT 0.0,
            wickets          INTEGER DEFAULT 0,
            all_rounder_score REAL DEFAULT 0.0,
            cluster_label    TEXT DEFAULT 'Unknown'
        )
    """)

    # ── fact_matches ──
    cursor.execute("""
        CREATE TABLE fact_matches (
            match_id      INTEGER PRIMARY KEY,
            date_key      INTEGER,
            team1_key     INTEGER,
            team2_key     INTEGER,
            venue_key     INTEGER,
            winner_key    INTEGER,
            toss_decision TEXT,
            result_margin REAL,
            FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
            FOREIGN KEY (team1_key) REFERENCES dim_team(team_key),
            FOREIGN KEY (team2_key) REFERENCES dim_team(team_key),
            FOREIGN KEY (venue_key) REFERENCES dim_venue(venue_key),
            FOREIGN KEY (winner_key) REFERENCES dim_team(team_key)
        )
    """)

    conn.commit()
    print("[✓] Star schema created (dim_date, dim_team, dim_venue, dim_player, fact_matches)")


# ── Data Loading ────────────────────────────────────────────────────────────────

def load_dim_date(conn, matches):
    """Populate dim_date from matches data."""
    # Parse date column
    if 'date' in matches.columns:
        dates = pd.to_datetime(matches['date'], errors='coerce', dayfirst=True)
    else:
        # Fallback: try 'Date' or generate from season
        date_col = [c for c in matches.columns if 'date' in c.lower()]
        if date_col:
            dates = pd.to_datetime(matches[date_col[0]], errors='coerce', dayfirst=True)
        else:
            print("[⚠] No date column found. Using placeholder dates.")
            dates = pd.Series([pd.Timestamp('2020-01-01')] * len(matches))

    date_df = pd.DataFrame({
        'full_date': dates.dt.strftime('%Y-%m-%d'),
        'year': dates.dt.year,
        'season': dates.dt.year.astype(str),  # IPL season = year
        'month': dates.dt.month,
        'day': dates.dt.day
    }).drop_duplicates(subset=['full_date']).reset_index(drop=True)

    date_df = date_df.dropna(subset=['full_date'])

    date_df.to_sql('dim_date', conn, if_exists='append', index=False)
    print(f"[✓] Loaded dim_date: {len(date_df)} unique dates")
    return date_df


def load_dim_team(conn, matches):
    """Populate dim_team from matches data + cluster labels if available."""
    all_teams = set(matches['team1'].unique()) | set(matches['team2'].unique())

    # Try to load team clustering info
    cluster_map = {}
    if os.path.exists('clustered_teams.csv'):
        tc = pd.read_csv('clustered_teams.csv')
        if 'team' in tc.columns and 'category' in tc.columns:
            cluster_map = dict(zip(tc['team'], tc['category']))

    team_df = pd.DataFrame({
        'team_name': sorted(all_teams),
    })
    team_df['cluster_label'] = team_df['team_name'].map(cluster_map).fillna('Unknown')

    team_df.to_sql('dim_team', conn, if_exists='append', index=False)
    print(f"[✓] Loaded dim_team: {len(team_df)} teams")
    return team_df


def load_dim_venue(conn, matches, deliveries):
    """Populate dim_venue from matches + venue stats."""
    venue_df = matches[['venue']].drop_duplicates().rename(columns={'venue': 'venue_name'})

    # City extraction
    if 'city' in matches.columns:
        city_map = matches.groupby('venue')['city'].first().to_dict()
        venue_df['city'] = venue_df['venue_name'].map(city_map).fillna('Unknown')
    else:
        venue_df['city'] = 'Unknown'

    # Average runs per venue
    match_venue = matches[['id', 'venue']].rename(columns={'id': 'match_id'})
    merged = deliveries.merge(match_venue, on='match_id', how='left')
    venue_runs = merged.groupby('venue')['total_runs'].sum().reset_index()
    venue_matches = matches.groupby('venue').size().reset_index(name='n_matches')
    venue_avg = venue_runs.merge(venue_matches, on='venue')
    venue_avg['avg_runs'] = (venue_avg['total_runs'] / venue_avg['n_matches']).round(2)
    avg_map = dict(zip(venue_avg['venue'], venue_avg['avg_runs']))

    venue_df['avg_runs'] = venue_df['venue_name'].map(avg_map).fillna(0.0)

    venue_df.to_sql('dim_venue', conn, if_exists='append', index=False)
    print(f"[✓] Loaded dim_venue: {len(venue_df)} venues")
    return venue_df


def load_dim_player(conn):
    """Populate dim_player from enriched player stats + cluster labels."""
    # Load enriched stats
    if os.path.exists('datasets/enriched_player_stats.csv'):
        ps = pd.read_csv('datasets/enriched_player_stats.csv')
    elif os.path.exists('datasets/player_stats.csv'):
        ps = pd.read_csv('datasets/player_stats.csv')
    else:
        print("[⚠] No player stats found. Skipping dim_player.")
        return pd.DataFrame()

    # Load cluster labels
    cluster_map = {}
    if os.path.exists('datasets/advanced_player_clusters.csv'):
        pc = pd.read_csv('datasets/advanced_player_clusters.csv')
        if 'player' in pc.columns and 'cluster_label' in pc.columns:
            cluster_map = dict(zip(pc['player'], pc['cluster_label']))

    player_df = pd.DataFrame({
        'player_name': ps['player'],
        'total_runs': ps.get('total_runs', 0),
        'strike_rate': ps.get('strike_rate', 0.0),
        'wickets': ps.get('wickets_taken', 0).astype(int) if 'wickets_taken' in ps.columns else 0,
        'all_rounder_score': ps.get('all_rounder_score', 0.0) if 'all_rounder_score' in ps.columns else 0.0,
    })
    player_df['cluster_label'] = player_df['player_name'].map(cluster_map).fillna('Unknown')

    # Remove duplicates
    player_df = player_df.drop_duplicates(subset=['player_name']).reset_index(drop=True)

    player_df.to_sql('dim_player', conn, if_exists='append', index=False)
    print(f"[✓] Loaded dim_player: {len(player_df)} players")
    return player_df


def load_fact_matches(conn, matches):
    """
    Populate fact_matches by resolving foreign keys from dimension tables.
    """
    cursor = conn.cursor()

    # Build lookup maps from dims
    teams = pd.read_sql("SELECT team_key, team_name FROM dim_team", conn)
    team_map = dict(zip(teams['team_name'], teams['team_key']))

    venues = pd.read_sql("SELECT venue_key, venue_name FROM dim_venue", conn)
    venue_map = dict(zip(venues['venue_name'], venues['venue_key']))

    dates = pd.read_sql("SELECT date_key, full_date FROM dim_date", conn)
    date_map = dict(zip(dates['full_date'], dates['date_key']))

    # Prepare facts
    records = []
    for _, row in matches.iterrows():
        match_id = row['id']

        # Date key
        if 'date' in row:
            try:
                d = pd.to_datetime(row['date'], dayfirst=True).strftime('%Y-%m-%d')
                date_key = date_map.get(d)
            except:
                date_key = None
        else:
            date_key = None

        team1_key = team_map.get(row.get('team1'))
        team2_key = team_map.get(row.get('team2'))
        venue_key = venue_map.get(row.get('venue'))
        winner_key = team_map.get(row.get('winner'))
        toss_decision = row.get('toss_decision', 'Unknown')

        # Result margin
        result_margin = row.get('result_margin', row.get('win_by_runs',
                               row.get('win_by_wickets', 0)))
        if pd.isna(result_margin):
            result_margin = 0

        records.append((match_id, date_key, team1_key, team2_key,
                        venue_key, winner_key, toss_decision, result_margin))

    cursor.executemany(
        """INSERT OR IGNORE INTO fact_matches
           (match_id, date_key, team1_key, team2_key, venue_key,
            winner_key, toss_decision, result_margin)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        records
    )
    conn.commit()
    print(f"[✓] Loaded fact_matches: {len(records)} matches")


# ── OLAP Queries ────────────────────────────────────────────────────────────────

def run_olap_queries(conn):
    """
    Run 5 analytical OLAP queries and print results.
    """
    print("\n" + "═" * 70)
    print("  OLAP ANALYTICAL QUERIES")
    print("═" * 70)

    # ── Query 1: Top 5 venues by average match margin ──
    print("\n── Q1: Top 5 Venues by Average Match Margin ──")
    q1 = pd.read_sql("""
        SELECT v.venue_name, ROUND(AVG(f.result_margin), 2) AS avg_margin,
               COUNT(*) AS total_matches
        FROM fact_matches f
        JOIN dim_venue v ON f.venue_key = v.venue_key
        WHERE f.result_margin > 0
        GROUP BY v.venue_name
        HAVING total_matches >= 5
        ORDER BY avg_margin DESC
        LIMIT 5
    """, conn)
    print(q1.to_string(index=False))

    # ── Query 2: Win % by toss decision per season ──
    print("\n── Q2: Win % by Toss Decision (Bat vs Field) per Season ──")
    q2 = pd.read_sql("""
        SELECT d.season, f.toss_decision,
               COUNT(*) AS matches,
               SUM(CASE WHEN f.winner_key IS NOT NULL THEN 1 ELSE 0 END) AS decided,
               ROUND(
                   SUM(CASE WHEN f.winner_key = f.team1_key
                            OR f.winner_key = f.team2_key THEN 1 ELSE 0 END)
                   * 100.0 / COUNT(*), 2
               ) AS win_pct
        FROM fact_matches f
        JOIN dim_date d ON f.date_key = d.date_key
        WHERE f.toss_decision IS NOT NULL
        GROUP BY d.season, f.toss_decision
        ORDER BY d.season, f.toss_decision
    """, conn)
    # Show last 5 seasons to keep it readable
    recent = q2[q2['season'].notna()].tail(10)
    print(recent.to_string(index=False))

    # ── Query 3: Most dominant team per season ──
    print("\n── Q3: Most Dominant Team per Season (Win %) ──")
    q3 = pd.read_sql("""
        WITH team_season AS (
            SELECT d.season, t.team_name,
                   COUNT(*) AS wins
            FROM fact_matches f
            JOIN dim_date d ON f.date_key = d.date_key
            JOIN dim_team t ON f.winner_key = t.team_key
            GROUP BY d.season, t.team_name
        ),
        season_total AS (
            SELECT d.season, COUNT(*) AS total_matches
            FROM fact_matches f
            JOIN dim_date d ON f.date_key = d.date_key
            GROUP BY d.season
        ),
        ranked AS (
            SELECT ts.season, ts.team_name, ts.wins,
                   ROUND(ts.wins * 100.0 / st.total_matches, 2) AS win_pct,
                   ROW_NUMBER() OVER (PARTITION BY ts.season ORDER BY ts.wins DESC) AS rn
            FROM team_season ts
            JOIN season_total st ON ts.season = st.season
        )
        SELECT season, team_name, wins, win_pct
        FROM ranked
        WHERE rn = 1
        ORDER BY season
    """, conn)
    print(q3.to_string(index=False))

    # ── Query 4: Top 10 players by all-rounder score ──
    print("\n── Q4: Top 10 Players by All-Rounder Score ──")
    q4 = pd.read_sql("""
        SELECT player_name, total_runs, ROUND(strike_rate, 2) AS strike_rate,
               wickets, ROUND(all_rounder_score, 2) AS all_rounder_score,
               cluster_label
        FROM dim_player
        WHERE all_rounder_score > 0
        ORDER BY all_rounder_score DESC
        LIMIT 10
    """, conn)
    print(q4.to_string(index=False))

    # ── Query 5: Cluster-wise average performance ──
    print("\n── Q5: Cluster-wise Average Performance ──")
    q5 = pd.read_sql("""
        SELECT cluster_label,
               COUNT(*) AS player_count,
               ROUND(AVG(total_runs), 1) AS avg_runs,
               ROUND(AVG(strike_rate), 2) AS avg_strike_rate,
               ROUND(AVG(wickets), 1) AS avg_wickets,
               ROUND(AVG(all_rounder_score), 2) AS avg_ar_score
        FROM dim_player
        WHERE cluster_label != 'Unknown'
        GROUP BY cluster_label
        ORDER BY avg_ar_score DESC
    """, conn)
    print(q5.to_string(index=False))

    print("\n" + "═" * 70)
    return q1, q2, q3, q4, q5


# ── Main Pipeline ───────────────────────────────────────────────────────────────

def run_datawarehouse():
    """Run the full data warehouse pipeline: create schema, load data, run queries."""
    # Load raw data
    matches = pd.read_csv('datasets/matches.csv')
    deliveries = pd.read_csv('datasets/deliveries.csv')
    print(f"[✓] Raw data loaded: matches={matches.shape}, deliveries={deliveries.shape}")

    # Create / connect to database
    conn = get_connection()

    # Create schema
    create_schema(conn)

    # Load dimensions
    load_dim_date(conn, matches)
    load_dim_team(conn, matches)
    load_dim_venue(conn, matches, deliveries)
    load_dim_player(conn)

    # Load facts
    load_fact_matches(conn, matches)

    # Print table row counts
    print("\n── Data Warehouse Table Sizes ──")
    for table in ['dim_date', 'dim_team', 'dim_venue', 'dim_player', 'fact_matches']:
        count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn).iloc[0, 0]
        print(f"  {table:<20} {count:>6} rows")

    # Run OLAP queries
    results = run_olap_queries(conn)

    conn.close()
    print(f"\n[✓] Data warehouse built: {DB_PATH}")
    print("[✓] Data warehouse complete ✅")
    return results


if __name__ == '__main__':
    run_datawarehouse()
