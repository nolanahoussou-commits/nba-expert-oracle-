import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

st.set_page_config(page_title="NBA 3P Oracle Pro", layout="wide", page_icon="🏀")

@st.cache_data(ttl=3600)
def load_expert_data():
    try:
        # Chargement des 3 sources de données
        raw_off = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        raw_def = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame', measure_type_detailed_defense='Opponent').get_data_frames()[0]
        raw_adv = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]

        # Nettoyage automatique des noms de colonnes pour supprimer les préfixes "GP_" ou "TEAM_"
        for df in [raw_off, raw_def]:
            df.columns = [c.split('_')[-1] if 'FG' in c else c for c in df.columns]

        # On s'assure d'extraire les bonnes données même si l'ordre change
        off_df = raw_off[['TEAM_ID', 'TEAM_NAME', 'FG3M']].copy()
        def_df = raw_def[['TEAM_ID', 'FG3M']].rename(columns={'FG3M': 'OPP_FG3M'})
        adv_df = raw_adv[['TEAM_ID', 'PACE']]

        # Fusion finale
        final_df = off_df.merge(def_df, on='TEAM_ID').merge(adv_df, on='TEAM_ID')
        return final_df
    except Exception as e:
        st.error(f"Erreur d'acquisition de données : {e}")
        return pd.DataFrame()

data = load_expert_data()

# --- HEADER ---
st.title("🏀 NBA 3-Point Expert Oracle")
st.markdown(f"**Analyse professionnelle du {datetime.now().strftime('%d/%m/%Y')}**")

if data.empty:
    st.error("L'API NBA est momentanément indisponible ou a changé sa structure.")
    if st.button("Réessayer la connexion"):
        st.rerun()
else:
    avg_pace = data['PACE'].mean()

    # --- MATCHS DU JOUR ---
    try:
        # ScoreboardV2 est le plus fiable pour les matchs à venir
        games = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        games = pd.DataFrame()

    if games.empty:
        st.info("Aucun match trouvé pour le moment. Vérifiez l'heure des matchs (Fuseau US).")
    else:
        for idx, row in games.iterrows():
            h_id, a_id = row.get('HOME_TEAM_ID'), row.get('VISITOR_TEAM_ID')
            
            # On vérifie si les IDs existent dans notre base de stats
            if h_id in data['TEAM_ID'].values and a_id in data['TEAM_ID'].values:
                h_stats = data[data['TEAM_ID'] == h_id].iloc[0]
                a_stats = data[data['TEAM_ID'] == a_id].iloc[0]

                with st.expander(f"🔍 {a_stats['TEAM_NAME']} @ {h_stats['TEAM_NAME']}"):
                    # Interface de réglage
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        b2b_h = st.checkbox("Back-to-Back", key=f"b2b_h_{idx}")
                        abs_h = st.multiselect("Absents majeurs", ["Star", "Shooteur", "Meneur"], key=f"abs_h_{idx}")
                    with c3:
                        b2b_a = st.checkbox("Back-to-Back", key=f"b2b_a_{idx}")
                        abs_a = st.multiselect("Absents majeurs", ["Star", "Shooteur", "Meneur"], key=f"abs_a_{idx}")

                    # --- CALCULS ---
                    pace_match = (h_stats['PACE'] + a_stats['PACE']) / 2
                    pace_adj = pace_match / avg_pace
                    
                    # Logique de projection croisée
                    base_h = (h_stats['FG3M'] + a_stats['OPP_FG3M']) / 2
                    base_a = (a_stats['FG3M'] + h_stats['OPP_FG3M']) / 2

                    # Application des facteurs de fatigue et absences
                    final_h = (base_h * pace_adj * (0.94 if b2b_h else 1.0)) - (len(abs_h) * 1.6)
                    final_a = (base_a * pace_adj * (0.94 if b2b_a else 1.0)) - (len(abs_a) * 1.6)
                    total = final_h + final_a

                    # --- AFFICHAGE ---
                    st.divider()
                    st.write(f"📈 Rythme de jeu : **{pace_match:.1f}**")
                    v1, v2, v3 = st.columns(3)
                    v1.metric(h_stats['TEAM_NAME'], f"{final_h:.1f}")
                    v2.metric(a_stats['TEAM_NAME'], f"{final_a:.1f}")
                    v3.metric("TOTAL PROJETÉ", f"{total:.1f}")

                    # Comparateur
                    line = st.number_input("Cote Bookmaker", value=float(round(total)), step=0.5, key=f"line_{idx}")
                    edge = total - line
                    
                    if abs(edge) >= 2.0:
                        st.success(f"🔥 SIGNAL FORT : **{'OVER' if edge > 0 else 'UNDER'}** (Edge: {edge:.2f})")
                    else:
                        st.info("⚖️ Match neutre statistique.")
