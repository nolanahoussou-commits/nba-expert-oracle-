import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="NBA 3P Oracle Pro", layout="wide", page_icon="🏀")

# --- CHARGEMENT ET FUSION DES DONNÉES (VERSION SÉCURISÉE) ---
@st.cache_data(ttl=3600)
def load_expert_data():
    try:
        # 1. Stats Offensives (FG3M : Paniers marqués)
        off_stats = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        off_stats = off_stats[['TEAM_ID', 'TEAM_NAME', 'FG3M', 'FG3A']]

        # 2. Stats Défensives (OPP_FG3M : Paniers encaissés)
        def_stats = leaguedashteamstats.LeagueDashTeamStats(
            per_mode_detailed='PerGame', 
            measure_type_detailed_defense='Opponent'
        ).get_data_frames()[0]
        def_stats = def_stats[['TEAM_ID', 'FG3M']].rename(columns={'FG3M': 'OPP_FG3M'})

        # 3. Stats Avancées (PACE : Rythme)
        adv_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
        adv_stats = adv_stats[['TEAM_ID', 'PACE']]

        # FUSION DES TROIS SOURCES
        df = pd.merge(off_stats, def_stats, on='TEAM_ID')
        df = pd.merge(df, adv_stats, on='TEAM_ID')
        
        return df
    except Exception as e:
        st.error(f"Erreur API NBA : {e}")
        return pd.DataFrame()

# Initialisation des données
data = load_expert_data()

# --- INTERFACE UTILISATEUR ---
st.title("🏀 NBA 3-Point Expert Oracle")
st.markdown(f"**Analyse professionnelle du {datetime.now().strftime('%d/%m/%Y')}**")

if data.empty:
    st.error("Impossible de charger les statistiques. Vérifiez votre connexion ou l'état de l'API NBA.")
else:
    avg_pace_league = data['PACE'].mean()

    # --- RÉCUPÉRATION DES MATCHS ---
    try:
        # On utilise le ScoreboardV2 pour avoir les IDs des équipes du jour
        sb = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        sb = pd.DataFrame()

    if sb.empty:
        st.info("Aucun match détecté pour aujourd'hui dans l'API.")
    else:
        # Parcourir chaque match
        for index, game in sb.iterrows():
            home_id = game.get('HOME_TEAM_ID')
            away_id = game.get('VISITOR_TEAM_ID')

            # Vérification de l'existence des équipes dans nos stats
            if home_id in data['TEAM_ID'].values and away_id in data['TEAM_ID'].values:
                home_row = data[data['TEAM_ID'] == home_id].iloc[0]
                away_row = data[data['TEAM_ID'] == away_id].iloc[0]

                # Titre du match
                with st.expander(f"🔍 ANALYSE : {away_row['TEAM_NAME']} @ {home_row['TEAM_NAME']}"):
                    col_h, col_mid, col_a = st.columns([2, 1, 2])

                    with col_h:
                        st.subheader(home_row['TEAM_NAME'])
                        b2b_h = st.checkbox("Back-to-Back", key=f"b2b_h_{index}")
                        abs_h = st.multiselect("Absents", ["Star", "Shooteur", "Passeur"], key=f"abs_h_{index}")

                    with col_a:
                        st.subheader(away_row['TEAM_NAME'])
                        b2b_a = st.checkbox("Back-to-Back", key=f"b2b_a_{index}")
                        abs_a = st.multiselect("Absents", ["Star", "Shooteur", "Passeur"], key=f"abs_a_{index}")

                    # --- ALGORITHME DE PROJECTION ---
                    # Facteur Rythme (Pace)
                    match_pace = (home_row['PACE'] + away_row['PACE']) / 2
                    pace_coef = match_pace / avg_pace_league

                    # Calcul de base (Offense A vs Défense B)
                    proj_home = (home_row['FG3M'] + away_row['OPP_FG3M']) / 2
                    proj_away = (away_row['FG3M'] + home_row['OPP_FG3M']) / 2

                    # Ajustements Fatigue & Absences
                    adj_home = (proj_home * pace_coef * (0.94 if b2b_h else 1.0)) - (len(abs_h) * 1.6)
                    adj_away = (proj_away * pace_coef * (0.94 if b2b_a else 1.0)) - (len(abs_a) * 1.6)
                    total_match = adj_home + adj_away

                    # --- AFFICHAGE DES RÉSULTATS ---
                    st.divider()
                    st.write(f"📊 **Pace estimé :** {match_pace:.1f} ({'Rapide' if pace_coef > 1 else 'Lent'})")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric(f"Proj. {home_row['TEAM_NAME']}", f"{adj_home:.1f}")
                    m2.metric(f"Proj. {away_row['TEAM_NAME']}", f"{adj_away:.1f}")
                    m3.metric("TOTAL MATCH", f"{total_match:.1f}")

                    # Comparaison Bookmaker
                    bookie_line = st.number_input("Ligne du Bookmaker", value=float(round(total_match)), step=0.5, key=f"line_{index}")
                    edge = total_match - bookie_line

                    if abs(edge) >= 2.0:
                        st.success(f"🔥 **ALERTE VALUE { 'OVER' if edge > 0 else 'UNDER' }** (Edge: {edge:.2f})")
                    else:
                        st.info("⚖️ Match équilibré selon l'Oracle.")

                    # Bouton Rapport
                    if st.button("📝 Copier le Rapport Pro", key=f"btn_{index}"):
                        st.code(f"PRO-ANALYSIS: {away_row['TEAM_NAME']} @ {home_row['TEAM_NAME']}\n"
                                f"Projection: {total_match:.1f} | Ligne: {bookie_line}\n"
                                f"Signal: {'OVER' if edge > 0 else 'UNDER'} | Edge: {abs(edge):.2f}")
