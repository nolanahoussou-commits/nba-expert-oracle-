import streamlit as st
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

st.set_page_config(page_title="NBA 3P Oracle Premium", layout="wide", page_icon="🏀")

# --- FONCTION DE SÉCURITÉ POUR TROUVER LA COLONNE ---
def find_col(df, target_names):
    """Trouve une colonne même si l'API change son préfixe"""
    for col in df.columns:
        if any(target in col for target in target_names):
            return col
    return None

@st.cache_data(ttl=3600)
def fetch_nba_stats():
    try:
        # 1. Appel des 3 endpoints
        raw_off = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        raw_def = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame', measure_type_detailed_defense='Opponent').get_data_frames()[0]
        raw_adv = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]

        # 2. Identification dynamique des colonnes (FG3M et PACE)
        col_fg3m_off = find_col(raw_off, ['FG3M'])
        col_fg3m_def = find_col(raw_def, ['FG3M'])
        col_pace = find_col(raw_adv, ['PACE'])
        col_team_id = find_col(raw_off, ['TEAM_ID'])
        col_team_name = find_col(raw_off, ['TEAM_NAME'])

        if not all([col_fg3m_off, col_fg3m_def, col_pace]):
            st.error("Colonnes critiques introuvables dans l'API NBA.")
            return pd.DataFrame()

        # 3. Extraction et uniformisation
        off_df = raw_off[[col_team_id, col_team_name, col_fg3m_off]].rename(columns={col_fg3m_off: 'FG3M'})
        def_df = raw_def[[col_team_id, col_fg3m_def]].rename(columns={col_fg3m_def: 'OPP_FG3M'})
        adv_df = raw_adv[[col_team_id, col_pace]].rename(columns={col_pace: 'PACE'})

        # Fusion
        final_df = off_df.merge(def_df, on=col_team_id).merge(adv_df, on=col_team_id)
        return final_df
    except Exception as e:
        st.error(f"Erreur d'acquisition : {e}")
        return pd.DataFrame()

df_stats = fetch_nba_stats()

# --- INTERFACE ---
st.title("🏀 NBA 3-Point Oracle Premium")
st.markdown(f"**Expert Analysis - {datetime.now().strftime('%d/%m/%Y')}**")

if df_stats.empty:
    st.warning("🔄 Tentative de reconnexion aux serveurs NBA... Si l'erreur persiste, l'API est en maintenance.")
    if st.button("Forcer la mise à jour"):
        st.cache_data.clear()
        st.rerun()
else:
    league_avg_pace = df_stats['PACE'].mean()

    try:
        # Récupération des matchs via ScoreboardV2 (tableau 1 pour les IDs)
        sb = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        sb = pd.DataFrame()

    if sb.empty:
        st.info("Aucun match détecté. Vérifiez le décalage horaire US (les matchs s'affichent souvent l'après-midi).")
    else:
        for idx, match in sb.iterrows():
            # Utilisation de .get pour éviter les KeyError sur le Scoreboard
            h_id = match.get('HOME_TEAM_ID')
            a_id = match.get('VISITOR_TEAM_ID')
            
            if h_id in df_stats['TEAM_ID'].values and a_id in df_stats['TEAM_ID'].values:
                h_team = df_stats[df_stats['TEAM_ID'] == h_id].iloc[0]
                a_team = df_stats[df_stats['TEAM_ID'] == a_id].iloc[0]

                with st.expander(f"🔍 {a_team['TEAM_NAME']} @ {h_team['TEAM_NAME']}"):
                    c1, c2, c3 = st.columns([2, 1, 2])
                    
                    with c1:
                        h_b2b = st.checkbox("Back-to-Back", key=f"h_b2b_{idx}")
                        h_abs = st.slider("Absences (Impact)", 0.0, 6.0, 0.0, key=f"h_abs_{idx}")
                    with c3:
                        a_b2b = st.checkbox("Back-to-Back", key=f"a_b2b_{idx}")
                        a_abs = st.slider("Absences (Impact)", 0.0, 6.0, 0.0, key=f"a_abs_{idx}")

                    # --- ALGORITHME PRO ---
                    m_pace = (h_team['PACE'] + a_team['PACE']) / 2
                    p_factor = m_pace / league_avg_pace
                    
                    # Projection croisée : (Attaque A + Défense B) / 2
                    proj_h = ((h_team['FG3M'] + a_team['OPP_FG3M']) / 2) * p_factor * (0.94 if h_b2b else 1.0) - h_abs
                    proj_a = ((a_team['FG3M'] + h_team['OPP_FG3M']) / 2) * p_factor * (0.94 if a_b2b else 1.0) - a_abs
                    total = proj_h + proj_a

                    st.divider()
                    m1, m2, m3 = st.columns(3)
                    m1.metric(f"Proj. {h_team['TEAM_NAME']}", f"{proj_h:.2f}")
                    m2.metric(f"Proj. {a_team['TEAM_NAME']}", f"{proj_a:.2f}")
                    m3.metric("TOTAL MATCH", f"{total:.2f}")

                    line = st.number_input("Ligne Bookmaker", value=float(round(total, 1)), step=0.5, key=f"l_{idx}")
                    edge = total - line
                    
                    if abs(edge) >= 2.0:
                        st.success(f"🔥 **SIGNAL FORT : {'OVER' if edge > 0 else 'UNDER'}** (Edge: {edge:.2f})")
                    else:
                        st.info("⚖️ Match équilibré.")
