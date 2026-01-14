import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

# --- CONFIGURATION PRO ---
st.set_page_config(page_title="NBA 3P Expert Oracle", layout="wide", page_icon="🏀")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data(ttl=3600)
def load_nba_data():
    # Récupération des stats Offense, Défense et Pace
    base = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
    adv = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
    combined = pd.merge(base, adv[['TEAM_ID', 'PACE']], on='TEAM_ID')
    return combined

data = load_nba_data()
avg_pace = data['PACE'].mean()

# --- INTERFACE ---
st.title("🏀 NBA 3-Point Expert Oracle")
st.markdown(f"### Analyses du {datetime.now().strftime('%d/%m/%Y')}")

# Onglets
tab1, tab2 = st.tabs(["🎯 Analyse Live", "📊 Historique & ROI"])

with tab1:
    # 1. Récupérer les matchs du jour
    try:
        sb = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        st.error("Impossible de récupérer les matchs. Vérifiez votre connexion.")
        sb = pd.DataFrame()

    if sb.empty:
        st.info("Aucun match prévu aujourd'hui ou données indisponibles.")
    else:
        for _, game in sb.iterrows():
            home_id = game['HOME_TEAM_ID']
            away_id = game['VISITOR_TEAM_ID']
            
            home_row = data[data['TEAM_ID'] == home_id].iloc[0]
            away_row = data[data['TEAM_ID'] == away_id].iloc[0]

            with st.container():
                st.write("---")
                col_m1, col_m2, col_m3 = st.columns([2, 1, 2])
                
                with col_m1:
                    st.subheader(home_row['TEAM_NAME'])
                    b2b_h = st.checkbox("Back-to-Back (Fatigue)", key=f"b2b_h_{home_id}")
                    abs_h = st.multiselect("Absents clés", ["Meneur (Playmaker)", "Shooteur (Elite)", "Pivot (Spacing)"], key=f"abs_h_{home_id}")

                with col_m3:
                    st.subheader(away_row['TEAM_NAME'])
                    b2b_a = st.checkbox("Back-to-Back (Fatigue)", key=f"b2b_a_{away_id}")
                    abs_a = st.multiselect("Absents clés", ["Meneur (Playmaker)", "Shooteur (Elite)", "Pivot (Spacing)"], key=f"abs_a_{away_id}")

                # --- CALCULS ---
                # 1. Base (Offense + Défense adverse)
                base_h = (home_row['FG3M'] + away_row['OPP_FG3M']) / 2
                base_a = (away_row['FG3M'] + home_row['OPP_FG3M']) / 2
                
                # 2. Facteur Pace
                match_pace = (home_row['PACE'] + away_row['PACE']) / 2
                pace_factor = match_pace / avg_pace
                
                # 3. Ajustements (Fatigue & Absences)
                adj_h = 0.94 if b2b_h else 1.0
                adj_a = 0.94 if b2b_a else 1.0
                penalty_h = len(abs_h) * 1.5
                penalty_a = len(abs_a) * 1.5
                
                final_h = (base_h * pace_factor * adj_h) - penalty_h
                final_a = (base_a * pace_factor * adj_a) - penalty_a
                total_proj = final_h + final_a

                # --- AFFICHAGE RESULTATS ---
                st.info(f"Rythme de match : **{match_pace:.1f}** ({'Rapide' if pace_factor > 1 else 'Lent'})")
                
                r1, r2, r3 = st.columns(3)
                r1.metric(f"Proj. {home_row['TEAM_NAME']}", f"{final_h:.1f}")
                r2.metric(f"Proj. {away_row['TEAM_NAME']}", f"{final_a:.1f}")
                r3.metric("TOTAL MATCH", f"{total_proj:.1f}")

                # --- COMPARATEUR BOOKMAKER ---
                line = st.number_input("Ligne du Bookmaker", value=float(round(total_proj)), key=f"line_{home_id}")
                edge = total_proj - line
                
                if abs(edge) >= 2.0:
                    st.success(f"🔥 **ALERTE VALUE : {'OVER' if edge > 0 else 'UNDER'}** (Ecart : {edge:.2f})")
                else:
                    st.write("⚖️ Analyse : Match équilibré, pas d'écart majeur.")

                # Générateur de texte pro
                if st.button("📝 Générer Rapport Expert", key=f"btn_{home_id}"):
                    report = f"""
                    🏀 **RAPPORT EXPERT : {away_row['TEAM_NAME']} @ {home_row['TEAM_NAME']}**
                    ✅ **Projection : {total_proj:.1f}** | 🎰 **Ligne : {line}**
                    🚀 **Signal : {'OVER' if edge > 0 else 'UNDER'}** (Confiance : {min(int(abs(edge)*2), 10)}/10)
                    ⚠️ Absences : {', '.join(abs_h + abs_a) if (abs_h + abs_a) else 'Aucune'}
                    """
                    st.code(report)

with tab2:
    st.header("Suivi Professionnel")
    st.write("Consignez ici vos résultats pour calculer votre ROI réel.")
    # (Section à remplir manuellement pour l'instant)
