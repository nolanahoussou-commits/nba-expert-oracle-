import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NBA Oracle - Basketball Head Edition", layout="wide", page_icon="🏀")

# --- MAPPING OFFICIEL (Abréviations Basketball-Reference) ---
TEAM_MAP = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BRK",
    "Charlotte Hornets": "CHO", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHO",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "CHO"
}

# Récupération des clés
try:
    RAPID_KEY = st.secrets["X_RAPIDAPI_KEY"]
    RAPID_HOST = st.secrets["X_RAPIDAPI_HOST"]
except:
    st.error("⚠️ Clés API manquantes dans Streamlit Secrets.")
    st.stop()

@st.cache_data(ttl=3600)
def get_team_data(team_name):
    abbr = TEAM_MAP.get(team_name)
    # Note : Basketball-Head utilise souvent /teams/{abbr}/2024 pour les stats de saison
    url = f"https://{RAPID_HOST}/teams/{abbr}/2024" 
    headers = {"x-rapidapi-key": RAPID_KEY, "x-rapidapi-host": RAPID_HOST}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Erreur {response.status_code} pour {abbr}"}
        
        data = response.json()
        # On extrait les stats de la réponse (souvent dans le 'body')
        body = data.get('body', {})
        
        # Valeurs par défaut basées sur les moyennes 2024 si le champ est vide
        return {
            "fg3m": float(body.get('fg3_per_game', 12.5)),
            "opp_fg3m": float(body.get('opp_fg3_per_game', 12.0)),
            "pace": float(body.get('pace', 99.2))
        }
    except Exception as e:
        return {"error": str(e)}

# --- INTERFACE ---
st.title("🏀 NBA Oracle : Basketball Head Edition")

col1, cvs, col2 = st.columns([2, 0.5, 2])
with col1:
    away_t = st.selectbox("Équipe Extérieure", list(TEAM_MAP.keys()), index=13)
with cvs:
    st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
with col2:
    home_t = st.selectbox("Équipe Domicile", list(TEAM_MAP.keys()), index=0)

with st.sidebar:
    st.header("Ajustements")
    abs_imp = st.slider("Impact Absences (3pts)", 0.0, 5.0, 0.0)
    st.info("Données sourcées via Basketball-Reference")

if st.button("🚀 ANALYSER"):
    with st.spinner("Calcul en cours..."):
        h_data = get_team_data(home_t)
        a_data = get_team_data(away_t)

        if "error" in h_data or "error" in a_data:
            st.error(f"Erreur : {h_data.get('error') or a_data.get('error')}")
            st.warning("Certaines abréviations (ex: BRK pour Brooklyn) sont spécifiques à cette API.")
        else:
            # Algorithme de projection
            pace_match = (h_data['pace'] + a_data['pace']) / 2
            pace_adj = pace_match / 99.2
            
            proj_h = ((h_data['fg3m'] + a_data['opp_fg3m']) / 2) * pace_adj
            proj_a = ((a_data['fg3m'] + h_data['opp_fg3m']) / 2) * pace_adj
            total = (proj_h + proj_a) - abs_imp

            st.divider()
            r1, r2, r3 = st.columns(3)
            r1.metric(home_t, f"{proj_h:.2f}")
            r2.metric(away_t, f"{proj_a:.2f}")
            r3.metric("TOTAL PRÉVU", f"{total:.2f}")
            
            # Message de conseil
            line = st.number_input("Ligne Bookmaker", value=float(round(total, 1)))
            diff = total - line
            if abs(diff) > 1.5:
                st.success(f"💡 SIGNAL : {'OVER' if diff > 0 else 'UNDER'} détecté.")
