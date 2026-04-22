"""
Advanced Feature Engineering for IPL Cricket Data Mining Project.

This module computes enriched player statistics (batting + bowling + all-rounder),
venue-specific performance metrics, and head-to-head team statistics from raw
match and delivery data. Outputs are saved for downstream clustering, classification,
and data warehouse ingestion.

Outputs:
    - datasets/enriched_player_stats.csv
    - datasets/enriched_match_features.csv
"""

import os
import pandas as pd
import numpy as np


def load_data():
    """Load raw match and delivery datasets."""
    matches = pd.read_csv("datasets/matches.csv")
    deliveries = pd.read_csv("datasets/deliveries.csv")
    print(f"[✓] Loaded matches: {matches.shape}, deliveries: {deliveries.shape}")
    return matches, deliveries


# ── Batting Statistics ──────────────────────────────────────────────────────────

def compute_batting_stats(deliveries):
    """
    Compute comprehensive batting stats per player from deliveries data.

    Metrics: total_runs, balls_faced, strike_rate, innings_played,
             fours, sixes, dot_ball_pct, batting_average
    """
    batting = deliveries.groupby('batter').agg(
        total_runs=('batsman_runs', 'sum'),
        balls_faced=('ball', 'count'),
        fours=('batsman_runs', lambda x: (x == 4).sum()),
        sixes=('batsman_runs', lambda x: (x == 6).sum()),
        dot_balls=('batsman_runs', lambda x: (x == 0).sum()),
        innings_played=('match_id', 'nunique'),
    ).reset_index()

    batting.rename(columns={'batter': 'player'}, inplace=True)

    # Strike rate
    batting['strike_rate'] = np.where(
        batting['balls_faced'] > 0,
        (batting['total_runs'] / batting['balls_faced']) * 100,
        0.0
    )

    # Dot ball percentage
    batting['dot_ball_pct'] = np.where(
        batting['balls_faced'] > 0,
        (batting['dot_balls'] / batting['balls_faced']) * 100,
        0.0
    )

    # Count dismissals for batting average
    if 'player_dismissed' in deliveries.columns:
        dismissals = deliveries[deliveries['player_dismissed'].notna()] \
                        .groupby('player_dismissed').size() \
                        .reset_index(name='dismissals')
        dismissals.rename(columns={'player_dismissed': 'player'}, inplace=True)
        batting = batting.merge(dismissals, on='player', how='left')
        batting['dismissals'] = batting['dismissals'].fillna(0).astype(int)
    elif 'is_wicket' in deliveries.columns:
        # fallback: attribute wicket to batter when is_wicket == 1
        dismissed = deliveries[deliveries['is_wicket'] == 1] \
                        .groupby('batter').size() \
                        .reset_index(name='dismissals')
        dismissed.rename(columns={'batter': 'player'}, inplace=True)
        batting = batting.merge(dismissed, on='player', how='left')
        batting['dismissals'] = batting['dismissals'].fillna(0).astype(int)
    else:
        batting['dismissals'] = 0

    # Batting average (runs / dismissals), inf → 0 for not-out players
    batting['batting_average'] = np.where(
        batting['dismissals'] > 0,
        batting['total_runs'] / batting['dismissals'],
        batting['total_runs'].astype(float)  # treat as not-out average
    )

    # Filter out players with minimal exposure
    batting = batting[batting['balls_faced'] > 50].copy()
    batting.drop(columns=['dot_balls'], inplace=True)

    print(f"[✓] Batting stats computed for {len(batting)} players")
    return batting


# ── Bowling Statistics ──────────────────────────────────────────────────────────

def compute_bowling_stats(deliveries):
    """
    Compute bowling stats per player from deliveries data.

    Metrics: wickets_taken, balls_bowled, runs_conceded, economy_rate,
             bowling_strike_rate, bowling_innings
    """
    # Runs conceded per ball by bowler (use total_runs which includes extras)
    bowling = deliveries.groupby('bowler').agg(
        runs_conceded=('total_runs', 'sum'),
        balls_bowled=('ball', 'count'),
        bowling_innings=('match_id', 'nunique'),
    ).reset_index()

    bowling.rename(columns={'bowler': 'player'}, inplace=True)

    # Wickets taken
    if 'is_wicket' in deliveries.columns:
        wickets = deliveries[deliveries['is_wicket'] == 1] \
                    .groupby('bowler').size() \
                    .reset_index(name='wickets_taken')
        wickets.rename(columns={'bowler': 'player'}, inplace=True)
        bowling = bowling.merge(wickets, on='player', how='left')
    else:
        bowling['wickets_taken'] = 0

    bowling['wickets_taken'] = bowling['wickets_taken'].fillna(0).astype(int)

    # Overs bowled (6 balls = 1 over)
    bowling['overs_bowled'] = bowling['balls_bowled'] / 6.0

    # Economy rate (runs per over)
    bowling['economy_rate'] = np.where(
        bowling['overs_bowled'] > 0,
        bowling['runs_conceded'] / bowling['overs_bowled'],
        0.0
    )

    # Bowling strike rate (balls per wicket)
    bowling['bowling_strike_rate'] = np.where(
        bowling['wickets_taken'] > 0,
        bowling['balls_bowled'] / bowling['wickets_taken'],
        np.nan  # undefined for 0-wicket bowlers
    )

    # Filter: at least 60 balls bowled (10 overs)
    bowling = bowling[bowling['balls_bowled'] >= 60].copy()
    bowling.drop(columns=['overs_bowled'], inplace=True)

    print(f"[✓] Bowling stats computed for {len(bowling)} players")
    return bowling


# ── All-Rounder Score ───────────────────────────────────────────────────────────

def compute_allrounder_score(player_stats):
    """
    Compute a composite all-rounder score combining batting and bowling metrics.

    Score = normalized(batting_average * strike_rate) + normalized(wickets / economy)
    Players with no bowling data get bowling component = 0.
    """
    df = player_stats.copy()

    # Batting component: batting_average * strike_rate (higher is better)
    bat_raw = df['batting_average'] * df['strike_rate']
    bat_min, bat_max = bat_raw.min(), bat_raw.max()
    df['bat_component'] = (bat_raw - bat_min) / (bat_max - bat_min + 1e-9)

    # Bowling component: wickets / economy (higher is better; low economy is good)
    has_bowling = df['wickets_taken'].notna() & (df['wickets_taken'] > 0) & (df['economy_rate'] > 0)
    bowl_raw = np.where(
        has_bowling,
        df['wickets_taken'] / df['economy_rate'],
        0.0
    )
    bowl_min, bowl_max = bowl_raw.min(), bowl_raw.max()
    df['bowl_component'] = (bowl_raw - bowl_min) / (bowl_max - bowl_min + 1e-9)

    # Composite score (equal weighting)
    df['all_rounder_score'] = (df['bat_component'] + df['bowl_component']) / 2.0

    # Scale 0-100
    df['all_rounder_score'] = (df['all_rounder_score'] * 100).round(2)

    df.drop(columns=['bat_component', 'bowl_component'], inplace=True)

    print("[✓] All-rounder score computed")
    return df


# ── Venue-Specific Stats ───────────────────────────────────────────────────────

def compute_venue_stats(matches, deliveries):
    """
    Compute venue-specific statistics:
    - Average first-innings & total runs per venue
    - Win percentage per team per venue
    """
    # Average runs per venue from deliveries
    match_venue = matches[['id', 'venue']].rename(columns={'id': 'match_id'})
    merged = deliveries.merge(match_venue, on='match_id', how='left')

    venue_runs = merged.groupby('venue').agg(
        avg_runs_per_match=('total_runs', 'sum')
    ).reset_index()

    # Count matches per venue
    matches_per_venue = matches.groupby('venue').size().reset_index(name='matches_played')
    venue_runs = venue_runs.merge(matches_per_venue, on='venue', how='left')
    venue_runs['avg_runs_per_match'] = (
        venue_runs['avg_runs_per_match'] / venue_runs['matches_played']
    ).round(2)

    # Win % per team per venue
    winners = matches.dropna(subset=['winner'])
    team_venue_wins = winners.groupby(['venue', 'winner']).size().reset_index(name='wins')

    # Total matches per venue for each team (as team1 or team2)
    t1 = matches[['venue', 'team1']].rename(columns={'team1': 'team'})
    t2 = matches[['venue', 'team2']].rename(columns={'team2': 'team'})
    team_venue_matches = pd.concat([t1, t2]).groupby(['venue', 'team']).size().reset_index(name='total_matches')

    team_venue = team_venue_wins.merge(
        team_venue_matches,
        left_on=['venue', 'winner'], right_on=['venue', 'team'],
        how='left'
    )
    team_venue['venue_win_pct'] = (team_venue['wins'] / team_venue['total_matches'] * 100).round(2)
    team_venue = team_venue[['venue', 'winner', 'venue_win_pct']].rename(columns={'winner': 'team'})

    print(f"[✓] Venue stats computed for {len(venue_runs)} venues")
    return venue_runs, team_venue


# ── Head-to-Head Stats ──────────────────────────────────────────────────────────

def compute_head_to_head(matches):
    """
    Compute historical head-to-head win percentage between every pair of teams.
    Returns a DataFrame with columns: team1, team2, h2h_win_pct (for team1).
    """
    h2h_records = []
    winners = matches.dropna(subset=['winner'])

    for _, row in winners.iterrows():
        t1, t2, winner = row['team1'], row['team2'], row['winner']
        # Normalize pair ordering alphabetically
        pair = tuple(sorted([t1, t2]))
        h2h_records.append({
            'pair_team1': pair[0],
            'pair_team2': pair[1],
            'winner': winner
        })

    h2h_df = pd.DataFrame(h2h_records)
    if h2h_df.empty:
        return pd.DataFrame(columns=['team1', 'team2', 'h2h_win_pct'])

    total = h2h_df.groupby(['pair_team1', 'pair_team2']).size().reset_index(name='total_matches')
    wins = h2h_df.groupby(['pair_team1', 'pair_team2', 'winner']).size().reset_index(name='wins')

    h2h = wins.merge(total, on=['pair_team1', 'pair_team2'])
    h2h['h2h_win_pct'] = (h2h['wins'] / h2h['total_matches'] * 100).round(2)

    # Rename for clarity
    h2h = h2h.rename(columns={
        'pair_team1': 'team1',
        'pair_team2': 'team2',
        'winner': 'team'
    })[['team1', 'team2', 'team', 'h2h_win_pct']]

    print(f"[✓] Head-to-head stats computed for {len(h2h)} matchups")
    return h2h


# ── Team Form (last N matches) ─────────────────────────────────────────────────

def compute_team_form(matches, n=5):
    """
    Compute rolling win % over the last `n` matches for each team, per match.
    Returns a column that can be merged on match_id + team.
    """
    sorted_matches = matches.sort_values('id').reset_index(drop=True)
    teams = set(sorted_matches['team1'].unique()) | set(sorted_matches['team2'].unique())

    form_records = []
    for team in teams:
        team_matches = sorted_matches[
            (sorted_matches['team1'] == team) | (sorted_matches['team2'] == team)
        ].copy()

        team_matches['team_won'] = (team_matches['winner'] == team).astype(int)
        team_matches['form_win_pct'] = (
            team_matches['team_won']
            .rolling(window=n, min_periods=1)
            .mean()
            .shift(1)  # don't include current match
            .fillna(0.5) * 100  # default 50% for first matches
        )

        for _, row in team_matches.iterrows():
            form_records.append({
                'match_id': row['id'],
                'team': team,
                'form_win_pct': round(row['form_win_pct'], 2)
            })

    form_df = pd.DataFrame(form_records)
    print(f"[✓] Team form (last {n} matches) computed")
    return form_df


# ── Build Enriched Match Features ───────────────────────────────────────────────

def build_enriched_match_features(matches, h2h, venue_stats, team_venue, team_form):
    """
    Build enriched match-level feature set for classification.
    Adds: h2h_win_pct, venue_avg_runs, venue_win_pct (for each team),
          team_form for each team, toss_impact.
    """
    df = matches[['id', 'team1', 'team2', 'toss_winner', 'toss_decision', 'venue', 'winner']].copy()
    df = df.dropna(subset=['winner'])
    df.rename(columns={'id': 'match_id'}, inplace=True)

    # ── Head-to-head win % for team1 ──
    def get_h2h_pct(row):
        pair = tuple(sorted([row['team1'], row['team2']]))
        subset = h2h[(h2h['team1'] == pair[0]) & (h2h['team2'] == pair[1]) & (h2h['team'] == row['team1'])]
        if not subset.empty:
            return subset['h2h_win_pct'].values[0]
        return 50.0  # default

    df['h2h_team1_win_pct'] = df.apply(get_h2h_pct, axis=1)

    # ── Venue average runs ──
    df = df.merge(venue_stats[['venue', 'avg_runs_per_match']], on='venue', how='left')
    df['avg_runs_per_match'] = df['avg_runs_per_match'].fillna(df['avg_runs_per_match'].median())

    # ── Venue win % for team1 and team2 ──
    tv1 = team_venue.rename(columns={'team': 'team1', 'venue_win_pct': 'venue_win_pct_team1'})
    tv2 = team_venue.rename(columns={'team': 'team2', 'venue_win_pct': 'venue_win_pct_team2'})
    df = df.merge(tv1[['venue', 'team1', 'venue_win_pct_team1']], on=['venue', 'team1'], how='left')
    df = df.merge(tv2[['venue', 'team2', 'venue_win_pct_team2']], on=['venue', 'team2'], how='left')
    df['venue_win_pct_team1'] = df['venue_win_pct_team1'].fillna(50.0)
    df['venue_win_pct_team2'] = df['venue_win_pct_team2'].fillna(50.0)

    # ── Team form ──
    form1 = team_form.rename(columns={'team': 'team1', 'form_win_pct': 'form_team1'})
    form2 = team_form.rename(columns={'team': 'team2', 'form_win_pct': 'form_team2'})
    df = df.merge(form1, on=['match_id', 'team1'], how='left')
    df = df.merge(form2, on=['match_id', 'team2'], how='left')
    df['form_team1'] = df['form_team1'].fillna(50.0)
    df['form_team2'] = df['form_team2'].fillna(50.0)

    # ── Toss impact: did toss winner win the match? ──
    df['toss_winner_won'] = (df['toss_winner'] == df['winner']).astype(int)

    print(f"[✓] Enriched match features built: {df.shape}")
    return df


# ── Main Pipeline ───────────────────────────────────────────────────────────────

def run_feature_engineering():
    """Run the full feature engineering pipeline and save outputs."""
    os.makedirs('datasets', exist_ok=True)

    matches, deliveries = load_data()

    # Player stats
    batting = compute_batting_stats(deliveries)
    bowling = compute_bowling_stats(deliveries)

    # Merge batting + bowling
    player_stats = batting.merge(bowling, on='player', how='left')

    # Fill missing bowling stats for pure batsmen
    bowl_cols = ['runs_conceded', 'balls_bowled', 'bowling_innings',
                 'wickets_taken', 'economy_rate', 'bowling_strike_rate']
    for col in bowl_cols:
        player_stats[col] = player_stats[col].fillna(0)

    # All-rounder score
    player_stats = compute_allrounder_score(player_stats)

    # Save enriched player stats
    player_stats.to_csv('datasets/enriched_player_stats.csv', index=False)
    print(f"[✓] Saved datasets/enriched_player_stats.csv ({len(player_stats)} players)")

    # Match-level features
    venue_stats, team_venue = compute_venue_stats(matches, deliveries)
    h2h = compute_head_to_head(matches)
    team_form = compute_team_form(matches, n=5)

    enriched_matches = build_enriched_match_features(
        matches, h2h, venue_stats, team_venue, team_form
    )

    enriched_matches.to_csv('datasets/enriched_match_features.csv', index=False)
    print(f"[✓] Saved datasets/enriched_match_features.csv ({len(enriched_matches)} rows)")

    print("\n[✓] Feature engineering complete ✅")
    return player_stats, enriched_matches


if __name__ == '__main__':
    run_feature_engineering()