"""
Interactive Streamlit Dashboard for IPL Cricket Data Mining Project.

Pages:
    1. Player Analysis   – PCA cluster scatter, filterable by label, top players table
    2. Team Analysis     – Wins bar chart, head-to-head heatmap
    3. Match Prediction  – Input match params → predict winner + confidence
    4. Data Warehouse    – OLAP query results as tables and charts

Run:
    streamlit run dashboard.py
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA

# ── Page Config ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="🏏 IPL Cricket Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid #333;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ── Data Loading Utilities ──────────────────────────────────────────────────────

@st.cache_data
def load_player_clusters():
    """Load clustered player data."""
    path = 'datasets/advanced_player_clusters.csv'
    if os.path.exists(path):
        return pd.read_csv(path)
    elif os.path.exists('datasets/enriched_player_stats.csv'):
        return pd.read_csv('datasets/enriched_player_stats.csv')
    return None


@st.cache_data
def load_enriched_matches():
    """Load enriched match features."""
    path = 'datasets/enriched_match_features.csv'
    if os.path.exists(path):
        return pd.read_csv(path)
    return None


@st.cache_data
def load_matches():
    """Load raw matches data."""
    return pd.read_csv('datasets/matches.csv')


@st.cache_data
def load_head_to_head():
    """Compute head-to-head records from matches."""
    matches = load_matches()
    winners = matches.dropna(subset=['winner'])
    h2h = winners.groupby(['team1', 'team2', 'winner']).size().reset_index(name='wins')
    return h2h


def get_warehouse_connection():
    """Connect to SQLite warehouse."""
    db_path = 'ipl_warehouse.db'
    if os.path.exists(db_path):
        return sqlite3.connect(db_path)
    return None


# ── Page 1: Player Analysis ────────────────────────────────────────────────────

def page_player_analysis():
    """Player clustering analysis with PCA visualization."""
    st.markdown('<h2>🏏 Player Analysis</h2>', unsafe_allow_html=True)

    df = load_player_clusters()
    if df is None:
        st.error("❌ No player cluster data found. Run the pipeline first.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(df))
    with col2:
        if 'cluster_label' in df.columns:
            st.metric("Clusters", df['cluster_label'].nunique())
        else:
            st.metric("Clusters", "N/A")
    with col3:
        st.metric("Avg Strike Rate", f"{df['strike_rate'].mean():.1f}" if 'strike_rate' in df.columns else "N/A")
    with col4:
        if 'all_rounder_score' in df.columns:
            st.metric("Top AR Score", f"{df['all_rounder_score'].max():.1f}")
        else:
            st.metric("Top AR Score", "N/A")

    st.markdown("---")

    # PCA Scatter Plot
    feature_cols = ['total_runs', 'strike_rate', 'batting_average', 'fours', 'sixes',
                    'dot_ball_pct', 'wickets_taken', 'economy_rate', 'all_rounder_score']
    available = [c for c in feature_cols if c in df.columns]

    if len(available) >= 2:
        X = df[available].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X_scaled)

        df_plot = df.copy()
        df_plot['PC1'] = X_pca[:, 0]
        df_plot['PC2'] = X_pca[:, 1]

        # Filter by cluster
        if 'cluster_label' in df.columns:
            labels = ['All'] + sorted(df['cluster_label'].unique().tolist())
            selected = st.selectbox("Filter by Cluster", labels, index=0)
            if selected != 'All':
                df_plot = df_plot[df_plot['cluster_label'] == selected]
            color_col = 'cluster_label'
        else:
            color_col = None

        fig = px.scatter(
            df_plot, x='PC1', y='PC2',
            color=color_col,
            hover_data=['player', 'total_runs', 'strike_rate'],
            title='Player Clusters – PCA Projection',
            template='plotly_dark',
            color_discrete_sequence=px.colors.qualitative.Set2,
            height=550
        )
        fig.update_traces(marker=dict(size=8, line=dict(width=0.5, color='white')))
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=13)
        )
        st.plotly_chart(fig, use_container_width=True)

    # Top Players Table
    st.subheader("📊 Top Players")
    sort_col = st.selectbox("Sort by", ['total_runs', 'strike_rate', 'all_rounder_score', 'wickets_taken'],
                            index=0)
    if sort_col in df.columns:
        top = df.nlargest(20, sort_col)[['player', 'total_runs', 'strike_rate',
                                          'batting_average', 'wickets_taken',
                                          'economy_rate', 'all_rounder_score',
                                          'cluster_label'] if 'cluster_label' in df.columns else
                                         ['player', 'total_runs', 'strike_rate']]
        st.dataframe(top, use_container_width=True, hide_index=True)


# ── Page 2: Team Analysis ──────────────────────────────────────────────────────

def page_team_analysis():
    """Team performance analysis with win charts and H2H heatmap."""
    st.markdown('<h2>🏆 Team Analysis</h2>', unsafe_allow_html=True)

    matches = load_matches()
    winners = matches.dropna(subset=['winner'])

    # Wins per team
    team_wins = winners['winner'].value_counts().reset_index()
    team_wins.columns = ['Team', 'Wins']

    col1, col2 = st.columns([2, 1])

    with col1:
        fig = px.bar(
            team_wins.head(15), x='Team', y='Wins',
            title='Total Wins per Team',
            template='plotly_dark',
            color='Wins',
            color_continuous_scale='Viridis',
            height=500
        )
        fig.update_layout(
            xaxis_tickangle=-45,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Win Summary")
        st.dataframe(team_wins, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Head-to-Head Heatmap
    st.subheader("🔥 Head-to-Head Win Percentage")

    # Select top teams for readable heatmap
    top_teams = team_wins.head(10)['Team'].tolist()

    relevant = winners[
        (winners['team1'].isin(top_teams)) & (winners['team2'].isin(top_teams))
    ]

    # Build H2H matrix
    h2h_matrix = pd.DataFrame(0.0, index=top_teams, columns=top_teams)
    total_matrix = pd.DataFrame(0, index=top_teams, columns=top_teams)

    for _, row in relevant.iterrows():
        t1, t2, w = row['team1'], row['team2'], row['winner']
        if t1 in top_teams and t2 in top_teams:
            total_matrix.loc[t1, t2] += 1
            total_matrix.loc[t2, t1] += 1
            if w in top_teams:
                h2h_matrix.loc[w, t1 if w != t1 else t2] += 1
                # Also add from opponent's perspective
                loser = t2 if w == t1 else t1

    # Compute win %
    h2h_pct = h2h_matrix.copy()
    for i in top_teams:
        for j in top_teams:
            if i != j and total_matrix.loc[i, j] > 0:
                # wins of i against j / total matches
                total = total_matrix.loc[i, j]
                h2h_pct.loc[i, j] = round(h2h_matrix.loc[i, j] / total * 100, 1)
            elif i == j:
                h2h_pct.loc[i, j] = None

    fig_heatmap = px.imshow(
        h2h_pct.values.astype(float),
        x=top_teams, y=top_teams,
        labels=dict(x='Opponent', y='Team', color='Win %'),
        title='Head-to-Head Win Percentage',
        template='plotly_dark',
        color_continuous_scale='RdYlGn',
        aspect='equal',
        height=600
    )
    fig_heatmap.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)


# ── Page 3: Match Prediction ───────────────────────────────────────────────────

def page_match_prediction():
    """Interactive match prediction using the trained model."""
    st.markdown('<h2>🎯 Match Prediction</h2>', unsafe_allow_html=True)

    matches = load_matches()
    enriched = load_enriched_matches()

    if enriched is None:
        st.error("❌ No enriched match features found. Run the pipeline first.")
        return

    # Get unique values for dropdowns
    all_teams = sorted(set(matches['team1'].unique()) | set(matches['team2'].unique()))
    all_venues = sorted(matches['venue'].dropna().unique())

    col1, col2 = st.columns(2)
    with col1:
        team1 = st.selectbox("🏏 Team 1", all_teams, index=0)
        toss_winner = st.selectbox("🪙 Toss Winner", all_teams, index=0)
    with col2:
        team2 = st.selectbox("🏏 Team 2", [t for t in all_teams if t != team1] if len(all_teams) > 1 else all_teams, index=0)
        toss_decision = st.selectbox("📋 Toss Decision", ['bat', 'field'])

    venue = st.selectbox("🏟️ Venue", all_venues, index=0)

    if st.button("🔮 Predict Winner", type="primary", use_container_width=True):
        with st.spinner("Training model and making prediction..."):
            try:
                result = _predict_match(enriched, team1, team2, venue, toss_winner, toss_decision)

                st.markdown("---")

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.markdown(f"""
                    <div style='text-align:center; padding:20px; background:linear-gradient(135deg, #11998e, #38ef7d);
                         border-radius:16px;'>
                        <h3 style='color:white; margin:0;'>🏆 Predicted Winner</h3>
                        <h2 style='color:white; margin:10px 0;'>{result['winner']}</h2>
                    </div>
                    """, unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"""
                    <div style='text-align:center; padding:20px; background:linear-gradient(135deg, #667eea, #764ba2);
                         border-radius:16px;'>
                        <h3 style='color:white; margin:0;'>📊 Confidence</h3>
                        <h2 style='color:white; margin:10px 0;'>{result['confidence']:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)
                with col_c:
                    st.markdown(f"""
                    <div style='text-align:center; padding:20px; background:linear-gradient(135deg, #f093fb, #f5576c);
                         border-radius:16px;'>
                        <h3 style='color:white; margin:0;'>🎯 Model Accuracy</h3>
                        <h2 style='color:white; margin:10px 0;'>{result['model_accuracy']:.1f}%</h2>
                    </div>
                    """, unsafe_allow_html=True)

                # Show probabilities for all teams
                if 'all_probs' in result and result['all_probs']:
                    st.subheader("Win Probabilities")
                    prob_df = pd.DataFrame(
                        sorted(result['all_probs'].items(), key=lambda x: x[1], reverse=True)[:5],
                        columns=['Team', 'Probability (%)']
                    )
                    fig = px.bar(prob_df, x='Team', y='Probability (%)',
                                 template='plotly_dark',
                                 color='Probability (%)',
                                 color_continuous_scale='Viridis')
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Prediction failed: {e}")


def _predict_match(enriched, team1, team2, venue, toss_winner, toss_decision):
    """Train a quick model and predict the match outcome."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split

    df = enriched.copy()

    # Filter valid winners
    winner_counts = df['winner'].value_counts()
    valid_teams = winner_counts[winner_counts >= 10].index
    df = df[df['winner'].isin(valid_teams)]

    # Features
    num_cols = ['h2h_team1_win_pct', 'avg_runs_per_match',
                'venue_win_pct_team1', 'venue_win_pct_team2',
                'form_team1', 'form_team2', 'toss_winner_won']
    num_cols = [c for c in num_cols if c in df.columns]

    cat_cols = ['team1', 'team2', 'toss_winner', 'toss_decision', 'venue']
    cat_cols = [c for c in cat_cols if c in df.columns]

    df_encoded = pd.get_dummies(df[cat_cols], columns=cat_cols)
    X = pd.concat([df[num_cols].reset_index(drop=True),
                    df_encoded.reset_index(drop=True)], axis=1).fillna(0)

    le = LabelEncoder()
    y = le.fit_transform(df['winner'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingClassifier(n_estimators=150, max_depth=5, random_state=42)
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test) * 100

    # Create input row
    input_row = pd.DataFrame(0, index=[0], columns=X.columns)
    for col in num_cols:
        if col == 'h2h_team1_win_pct':
            input_row[col] = 50.0
        elif col == 'avg_runs_per_match':
            input_row[col] = df['avg_runs_per_match'].median() if 'avg_runs_per_match' in df.columns else 300
        elif col == 'toss_winner_won':
            input_row[col] = 1 if toss_winner in [team1, team2] else 0
        else:
            input_row[col] = 50.0

    # Set one-hot encoded columns
    for prefix, value in [('team1_', team1), ('team2_', team2),
                          ('toss_winner_', toss_winner), ('toss_decision_', toss_decision),
                          ('venue_', venue)]:
        col_name = f"{prefix}{value}"
        if col_name in input_row.columns:
            input_row[col_name] = 1

    proba = model.predict_proba(input_row)[0]
    classes = le.classes_

    pred_idx = np.argmax(proba)
    predicted_winner = classes[pred_idx]
    confidence = proba[pred_idx] * 100

    all_probs = {classes[i]: round(proba[i] * 100, 2) for i in range(len(classes))}

    return {
        'winner': predicted_winner,
        'confidence': confidence,
        'model_accuracy': accuracy,
        'all_probs': all_probs
    }


# ── Page 4: Data Warehouse Queries ─────────────────────────────────────────────

def page_data_warehouse():
    """Display OLAP query results from the data warehouse."""
    st.markdown('<h2>🗄️ Data Warehouse Analytics</h2>', unsafe_allow_html=True)

    conn = get_warehouse_connection()
    if conn is None:
        st.error("❌ Data warehouse not found. Run datawarehouse.py first.")
        return

    try:
        # Table stats
        st.subheader("📊 Warehouse Overview")
        tables = ['dim_date', 'dim_team', 'dim_venue', 'dim_player', 'fact_matches']
        cols = st.columns(len(tables))
        for i, table in enumerate(tables):
            try:
                count = pd.read_sql(f"SELECT COUNT(*) as n FROM {table}", conn).iloc[0, 0]
                cols[i].metric(table, f"{count:,}")
            except:
                cols[i].metric(table, "N/A")

        st.markdown("---")

        # ── Q1: Top Venues ──
        st.subheader("🏟️ Q1: Top 5 Venues by Average Match Margin")
        q1 = pd.read_sql("""
            SELECT v.venue_name AS Venue, ROUND(AVG(f.result_margin), 2) AS Avg_Margin,
                   COUNT(*) AS Matches
            FROM fact_matches f
            JOIN dim_venue v ON f.venue_key = v.venue_key
            WHERE f.result_margin > 0
            GROUP BY v.venue_name HAVING Matches >= 5
            ORDER BY Avg_Margin DESC LIMIT 5
        """, conn)
        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(q1, use_container_width=True, hide_index=True)
        with col2:
            if not q1.empty:
                fig = px.bar(q1, x='Venue', y='Avg_Margin', template='plotly_dark',
                             color='Avg_Margin', color_continuous_scale='Plasma')
                fig.update_layout(xaxis_tickangle=-30, height=350)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Q2: Toss Decision Impact ──
        st.subheader("🪙 Q2: Win % by Toss Decision per Season")
        q2 = pd.read_sql("""
            SELECT d.season AS Season, f.toss_decision AS Decision, COUNT(*) AS Matches
            FROM fact_matches f
            JOIN dim_date d ON f.date_key = d.date_key
            WHERE f.toss_decision IS NOT NULL
            GROUP BY d.season, f.toss_decision
            ORDER BY d.season
        """, conn)
        if not q2.empty:
            fig = px.bar(q2, x='Season', y='Matches', color='Decision',
                         barmode='group', template='plotly_dark',
                         color_discrete_sequence=['#38ef7d', '#f5576c'])
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Q3: Dominant Teams ──
        st.subheader("👑 Q3: Most Dominant Team per Season")
        q3 = pd.read_sql("""
            WITH team_season AS (
                SELECT d.season, t.team_name, COUNT(*) AS wins
                FROM fact_matches f
                JOIN dim_date d ON f.date_key = d.date_key
                JOIN dim_team t ON f.winner_key = t.team_key
                GROUP BY d.season, t.team_name
            ),
            ranked AS (
                SELECT season, team_name, wins,
                       ROW_NUMBER() OVER (PARTITION BY season ORDER BY wins DESC) AS rn
                FROM team_season
            )
            SELECT season AS Season, team_name AS Team, wins AS Wins
            FROM ranked WHERE rn = 1 ORDER BY season
        """, conn)
        if not q3.empty:
            fig = px.bar(q3, x='Season', y='Wins', color='Team',
                         template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(q3, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Q4: Top All-Rounders ──
        st.subheader("⭐ Q4: Top 10 All-Rounders")
        q4 = pd.read_sql("""
            SELECT player_name AS Player, total_runs AS Runs,
                   ROUND(strike_rate, 2) AS SR, wickets AS Wickets,
                   ROUND(all_rounder_score, 2) AS AR_Score, cluster_label AS Cluster
            FROM dim_player WHERE all_rounder_score > 0
            ORDER BY all_rounder_score DESC LIMIT 10
        """, conn)
        col1, col2 = st.columns([1, 1])
        with col1:
            st.dataframe(q4, use_container_width=True, hide_index=True)
        with col2:
            if not q4.empty:
                fig = px.bar(q4, x='Player', y='AR_Score', template='plotly_dark',
                             color='AR_Score', color_continuous_scale='Viridis')
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # ── Q5: Cluster Performance ──
        st.subheader("🎯 Q5: Cluster-wise Average Performance")
        q5 = pd.read_sql("""
            SELECT cluster_label AS Cluster, COUNT(*) AS Players,
                   ROUND(AVG(total_runs), 1) AS Avg_Runs,
                   ROUND(AVG(strike_rate), 2) AS Avg_SR,
                   ROUND(AVG(wickets), 1) AS Avg_Wickets,
                   ROUND(AVG(all_rounder_score), 2) AS Avg_AR
            FROM dim_player WHERE cluster_label != 'Unknown'
            GROUP BY cluster_label ORDER BY Avg_AR DESC
        """, conn)
        if not q5.empty:
            st.dataframe(q5, use_container_width=True, hide_index=True)
            fig = px.bar(q5, x='Cluster', y=['Avg_Runs', 'Avg_Wickets', 'Avg_AR'],
                         barmode='group', template='plotly_dark',
                         title='Cluster Comparison')
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error querying warehouse: {e}")
    finally:
        conn.close()


# ── Sidebar & Navigation ───────────────────────────────────────────────────────

def main():
    """Main app entry point."""
    st.sidebar.markdown('<h1 style="text-align:center;">🏏 IPL Analytics</h1>', unsafe_allow_html=True)
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate",
        ["🏏 Player Analysis", "🏆 Team Analysis", "🎯 Match Prediction", "🗄️ Data Warehouse"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        "**IPL Cricket DWDM Project**\n\n"
        "Advanced data mining & warehousing "
        "with clustering, classification, and OLAP analytics."
    )

    # Route to page
    if page == "🏏 Player Analysis":
        page_player_analysis()
    elif page == "🏆 Team Analysis":
        page_team_analysis()
    elif page == "🎯 Match Prediction":
        page_match_prediction()
    elif page == "🗄️ Data Warehouse":
        page_data_warehouse()


if __name__ == '__main__':
    main()
