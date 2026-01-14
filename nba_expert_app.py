import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

# --- CONFIGURATION PRO ---
st.set_page_config(page_title="NBA 3P Expert Oracle", layout="wide", page_icon="🏀")

# --- CHARGEMENT DES DONNÉES STATISTIQUES ---
@st.cache_data(ttl=3600)
def load_nba_data():
    try:
        # Stats de base (FG3M, OPP_FG3M)
        base = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        # Stats avancées (PACE)
        adv = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
        combined = pd.merge(base, adv[['TEAM_ID', 'PACE']], on='TEAM_ID')
        return combined
    except Exception as e:
        st.error(f"Erreur lors du chargement des statistiques : {e}")
        return pd.DataFrame()

data = load_nba_data()

# --- INTERFACE ---
st.title("🏀 NBA 3-Point Expert Oracle")
st.markdown(f"### Analyses du {datetime.now().strftime('%d/%m/%Y')}")

if data.empty:
    st.warning("Impossible de charger les statistiques NBA. Réessayez plus tard.")
else:
    avg_pace = data['PACE'].mean()

    # --- RÉCUPÉRATION DES MATCHS (VERSION ROBUSTE) ---
    try:
        # On récupère le Header du Scoreboard qui est plus stable pour les noms d'équipes
        sb = scoreboardv2.ScoreboardV2().get_data_frames()[1]
        
        # Vérification des colonnes pour éviter le KeyError
        if 'HOME_TEAM_ID' not in sb.columns:
            # Si le format est différent, on essaie de mapper via le premier tableau
            sb = scoreboardv2.ScoreboardV2().get_data_frames()[0]
            # Mapping des noms de colonnes si nécessaire
            sb = sb.rename(columns={'HOME_TEAM_ID': 'HOME_TEAM_ID', 'VISITOR_TEAM_ID': 'VISITOR_TEAM_ID'})
    except Exception as e:
        st.error("Données des matchs indisponibles pour le moment.")
        sb = pd.DataFrame()

    if sb.empty:
        st.info("Aucun match prévu ou en cours pour le moment.")
    else:
        for index, game in sb.iterrows():
            # Utilisation de .get() pour éviter le crash en cas de colonne manquante
            home_id = game.get('HOME_TEAM_ID')
            away_id = game.get('VISITOR_TEAM_ID')
            
            if not home_id or not away_id:
                continue

            # Extraction des lignes de stats
            home_stats = data[data['TEAM_ID'] == home_id]
            away_stats = data[data['TEAM_ID'] == away_id]

            if home_stats.empty or away_stats.empty:
                continue

            home_row = home_stats.iloc[0]
            away_row = away_stats.iloc[0]

            with st.expander(f"🔍 {away_row['TEAM_NAME']} @ {home_row['TEAM_NAME']}"):
                col_m1, col_m2, col_m3 = st.columns([2, 1, 2])
                
                with col_m1:
                    st.subheader(home_row['TEAM_NAME'])
                    b2b_h = st.checkbox("Back-to-Back", key=f"b2b_h_{index}")
                    abs_h = st.multiselect("Absents", ["Meneur", "Shooteur", "Pivot"], key=f"abs_h_{index}")

                with col_m3:
                    st.subheader(away_row['TEAM_NAME'])
                    b2b_a = st.checkbox("Back-to-Back", key=f"b2b_a_{index}")
                    abs_a = st.multiselect("Absents", ["Meneur", "Shooteur", "Pivot"], key=f"abs_a_{index}")

                # --- CALCULS ---
                pace_match = (home_row['PACE'] + away_row['PACE']) / 2
                pace_factor = pace_match / avg_pace
                
                proj_h = (home_row['FG3M'] + away_row['OPP_FG3M']) / 2
                proj_a = (away_row['FG3M'] + home_row['OPP_FG3M']) / 2
                
                final_h = (proj_h * pace_factor * (0.94 if b2b_h else 1.0)) - (len(abs_h) * 1.5)
                final_a = (proj_a * pace_factor * (0.94 if b2b_a else 1.0)) - (len(abs_a) * 1.5)
                total_proj = final_h + final_a

                # --- AFFICHAGE ---
                st.divider()
                r1, r2, r3 = st.columns(3)
                r1.metric("Proj. Domicile", f"{final_h:.1f}")
                r2.metric("Proj. Extérieur", f"{final_a:.1f}")
                r3.metric("TOTAL MATCH", f"{total_proj:.1f}")

                line = st.number_input("Ligne Bookmaker", value=float(round(total_proj)), step=0.5, key=f"line_{index}")
                edge = total_proj - line
                
                if abs(edge) >= 2.0:
                    st.success(f"🔥 SIGNAL FORT : {'OVER' if edge > 0 else 'UNDER'} (Edge: {edge:.2f})")
                else:
                    st.info("⚖️ Écart faible.")
