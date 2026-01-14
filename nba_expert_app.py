import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leaguedashteamstats, scoreboardv2
from datetime import datetime

st.set_page_config(page_title="NBA 3P Oracle Pro", layout="wide", page_icon="🏀")

@st.cache_data(ttl=3600)
def load_expert_data():
    try:
        # 1. Stats Offensives
        raw_off = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame').get_data_frames()[0]
        # Nettoyage automatique des noms de colonnes (enlève les préfixes comme 'GP_')
        raw_off.columns = [c.replace('GP_', '') if 'FG' in c else c for c in raw_off.columns]
        off_stats = raw_off[['TEAM_ID', 'TEAM_NAME', 'FG3M']].copy()

        # 2. Stats Défensives (Opponent)
        raw_def = leaguedashteamstats.LeagueDashTeamStats(per_mode_detailed='PerGame', measure_type_detailed_defense='Opponent').get_data_frames()[0]
        raw_def.columns = [c.replace('GP_', '') if 'FG' in c else c for c in raw_def.columns]
        def_stats = raw_def[['TEAM_ID', 'FG3M']].rename(columns={'FG3M': 'OPP_FG3M'})

        # 3. Stats Avancées (Pace)
        adv_stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Advanced').get_data_frames()[0]
        adv_stats = adv_stats[['TEAM_ID', 'PACE']]

        # Fusion robuste
        df = pd.merge(off_stats, def_stats, on='TEAM_ID')
        df = pd.merge(df, adv_stats, on='TEAM_ID')
        
        return df
    except Exception as e:
        st.error(f"Détail de l'erreur technique : {e}")
        return pd.DataFrame()

data = load_expert_data()

st.title("🏀 NBA 3-Point Expert Oracle")
st.markdown(f"**Analyse professionnelle du {datetime.now().strftime('%d/%m/%Y')}**")

if data.empty:
    st.error("L'API NBA refuse la connexion ou les colonnes sont mal formatées. Tentative de reconnexion...")
    if st.button("Forcer la mise à jour"):
        st.cache_data.clear()
        st.rerun()
else:
    avg_pace_league = data['PACE'].mean()

    try:
        sb_data = scoreboardv2.ScoreboardV2().get_data_frames()[1]
    except:
        sb_data = pd.DataFrame()

    if sb_data.empty:
        st.info("Aucun match détecté. Les données du scoreboard sont peut-être en cours de mise à jour.")
    else:
        for index, game in sb_data.iterrows():
            h_id, a_id = game.get('HOME_TEAM_ID'), game.get('VISITOR_TEAM_ID')

            if h_id in data['TEAM_ID'].values and a_id in data['TEAM_ID'].values:
                h_row = data[data['TEAM_ID'] == h_id].iloc[0]
                a_row = data[data['TEAM_ID'] == a_id].iloc[0]

                with st.expander(f"🔍 {a_row['TEAM_NAME']} @ {h_row['TEAM_NAME']}"):
                    c1, c2, c3 = st.columns([2, 1, 2])
                    with c1:
                        b2b_h = st.checkbox("Back-to-Back", key=f"h_{index}")
                        abs_h = st.multiselect("Absents", ["Star", "Shooteur"], key=f"ah_{index}")
                    with c3:
                        b2b_a = st.checkbox("Back-to-Back", key=f"a_{index}")
                        abs_a = st.multiselect("Absents", ["Star", "Shooteur"], key=f"aa_{index}")

                    # Calcul avec sécurité
                    pace_fact = ((h_row['PACE'] + a_row['PACE']) / 2) / avg_pace_league
                    p_h = (h_row['FG3M'] + a_row['OPP_FG3M']) / 2
                    p_a = (a_row['FG3M'] + h_row['OPP_FG3M']) / 2

                    res_h = (p_h * pace_fact * (0.94 if b2b_h else 1.0)) - (len(abs_h) * 1.6)
                    res_a = (p_a * pace_fact * (0.94 if b2b_a else 1.0)) - (len(abs_a) * 1.6)
                    total = res_h + res_a

                    st.divider()
                    m1, m2, m3 = st.columns(3)
                    m1.metric(h_row['TEAM_NAME'], f"{res_h:.1f}")
                    m2.metric(a_row['TEAM_NAME'], f"{res_a:.1f}")
                    m3.metric("TOTAL PROJETÉ", f"{total:.1f}")
                    
                    line = st.number_input("Ligne Bookmaker", value=float(round(total)), key=f"l_{index}")
                    edge = total - line
                    if abs(edge) >= 1.8:
                        st.success(f"🔥 SIGNAL : {'OVER' if edge > 0 else 'UNDER'} (Edge: {edge:.2f})")
