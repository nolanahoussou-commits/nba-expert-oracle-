import streamlit as st
import pandas as pd
import numpy as np
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

# --- CONFIGURATION EXPERT ---
st.set_page_config(page_title="NBA 3P Oracle Premium", layout="wide", page_icon="🏀")

@st.cache_data(ttl=3600)
def fetch_nba_stats():
    try:
        # 1. Stats Offensives (Paniers marqués)
        off = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        # 2. Stats Défensives (Paniers encaissés par l'adversaire)
        defen = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame', measure_type_detailed_defense='Opponent').get_data_frames()[0]
        # 3. Stats Avancées (Pace / Rythme)
        adv = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]

        # Nettoyage des colonnes : On uniformise les noms pour éviter les erreurs de l'API
        off = off.rename(columns=lambda x: x.replace('GP_', '') if 'FG' in x else x)
        defen = defen.rename(columns=lambda x: x.replace('GP_', '') if 'FG' in x else x)

        # Sélection et fusion chirurgicale
        off_df = off[['TEAM_ID', 'TEAM_NAME', 'FG3M']]
        def_df = defen[['TEAM_ID', 'FG3M']].rename(columns={'FG3M': 'OPP_FG3M'})
        adv_df = adv[['TEAM_ID', 'PACE']]

        final_df = off_df.merge(def_df, on='TEAM_ID').merge(adv_df, on='TEAM_ID')
        return final_df
    except Exception as e:
        st.error(f"Erreur d'acquisition : {e}")
        return pd.DataFrame()

# Chargement
df_stats = fetch_nba_stats()

# --- INTERFACE ---
st.title("🏀 NBA 3-Point Oracle Premium")
st.sidebar.header("Stratégie de Mise")
bankroll = st.sidebar.number_input("Capital total (€)", value=1000)

if df_stats.empty:
    st.error("Données NBA indisponibles. Vérifiez la connexion API.")
else:
    league_avg_pace = df_stats['PACE'].mean()

    # Récupération des matchs du jour via ScoreboardV2
    try:
        games_today = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        games_today = pd.DataFrame()

    if games_today.empty:
        st.info("Aucun match trouvé pour la date sélectionnée (Fuseau Horaire US).")
    else:
        for idx, match in games_today.iterrows():
            h_id, a_id = match.get('HOME_TEAM_ID'), match.get('VISITOR_TEAM_ID')
            
            if h_id in df_stats['TEAM_ID'].values and a_id in df_stats['TEAM_ID'].values:
                h_team = df_stats[df_stats['TEAM_ID'] == h_id].iloc[0]
                a_team = df_stats[df_stats['TEAM_ID'] == a_id].iloc[0]

                with st.expander(f"📊 ANALYSE : {a_team['TEAM_NAME']} vs {h_team['TEAM_NAME']}"):
                    # Configuration du contexte de match
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        st.write(f"**{h_team['TEAM_NAME']}**")
                        h_b2b = st.checkbox("Back-to-Back", key=f"h_b2b_{idx}")
                        h_abs = st.slider("Impact Absences (Paniers)", 0.0, 5.0, 0.0, 0.5, key=f"h_abs_{idx}")
                    with c3:
                        st.write(f"**{a_team['TEAM_NAME']}**")
                        a_b2b = st.checkbox("Back-to-Back", key=f"a_b2b_{idx}")
                        a_abs = st.slider("Impact Absences (Paniers)", 0.0, 5.0, 0.0, 0.5, key=f"a_abs_{idx}")

                    # --- ALGORITHME DE PROJECTION ---
                    match_pace = (h_team['PACE'] + a_team['PACE']) / 2
                    pace_factor = match_pace / league_avg_pace
                    
                    proj_h = ((h_team['FG3M'] + a_team['OPP_FG3M']) / 2) * pace_factor * (0.94 if h_b2b else 1.0) - h_abs
                    proj_a = ((a_team['FG3M'] + h_team['OPP_FG3M']) / 2) * pace_factor * (0.94 if a_b2b else 1.0) - a_abs
                    total_proj = proj_h + proj_a

                    # --- RÉSULTATS ---
                    st.divider()
                    res1, res2, res3 = st.columns(3)
                    res1.metric("Proj. Domicile", f"{proj_h:.2f}")
                    res2.metric("Proj. Extérieur", f"{proj_a:.2f}")
                    res3.metric("TOTAL MATCH", f"{total_proj:.2f}")

                    # --- CONSEIL DE MISE PRO ---
                    line = st.number_input("Ligne du Bookmaker", value=float(round(total_proj, 1)), step=0.5, key=f"l_{idx}")
                    edge = total_proj - line
                    
                    if abs(edge) >= 1.5:
                        confiance = min(abs(edge) * 20, 100.0)
                        mise_recommandee = (bankroll * (abs(edge) / 50)) # Gestion prudente
                        st.success(f"🎯 **SIGNAL : {'OVER' if edge > 0 else 'UNDER'}**")
                        st.write(f"Indice de confiance : **{confiance:.1f}%** | Mise suggérée : **{mise_recommandee:.2f}€**")
                    else:
                        st.info("⚖️ Écart trop faible pour une mise sécurisée.")
