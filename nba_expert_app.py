import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="NBA Oracle Pro v4", layout="wide", page_icon="🏀")

# --- MAPPING OFFICIEL BASKETBALL-HEAD ---
# Ce dictionnaire fait le lien entre le nom affiché et l'identifiant API
TEAM_MAP = {
    "Atlanta Hawks": "hawks", "Boston Celtics": "celtics", "Brooklyn Nets": "nets",
    "Charlotte Hornets": "hornets", "Chicago Bulls": "bulls", "Cleveland Cavaliers": "cavaliers",
    "Dallas Mavericks": "mavericks", "Denver Nuggets": "nuggets", "Detroit Pistons": "pistons",
    "Golden State Warriors": "warriors", "Houston Rockets": "rockets", "Indiana Pacers": "pacers",
    "Los Angeles Clippers": "clippers", "Los Angeles Lakers": "lakers", "Memphis Grizzlies": "grizzlies",
    "Miami Heat": "heat", "Milwaukee Bucks": "bucks", "Minnesota Timberwolves": "timberwolves",
    "New Orleans Pelicans": "pelicans", "New York Knicks": "knicks", "Oklahoma City Thunder": "thunder",
    "Orlando Magic": "magic", "Philadelphia 76ers": "76ers", "Phoenix Suns": "suns",
    "Portland Trail Blazers": "blazers", "Sacramento Kings": "kings", "San Antonio Spurs": "spurs",
    "Toronto Raptors": "raptors", "Utah Jazz": "jazz", "Washington Wizards": "wizards"
}

try:
    RAPID_KEY = st.secrets["X_RAPIDAPI_KEY"]
    RAPID_HOST = st.secrets["X_RAPIDAPI_HOST"]
except:
    st.error("⚠️ Clés API absentes des Secrets Streamlit")
    st.stop()

@st.cache_data(ttl=3600)
def get_nba_data(team_display_name):
    slug = TEAM_MAP.get(team_display_name)
    url = f"https://{RAPID_HOST}/teams/{slug}/stats"
    headers = {"x-rapidapi-key": RAPID_KEY, "x-rapidapi-host": RAPID_HOST}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return {"error": f"L'équipe '{slug}' n'a pas été trouvée (404)."}
        if response.status_code != 200:
            return {"error": f"Erreur {response.status_code}"}
        
        data = response.json()
        # On vérifie si les données sont dans une liste ou un dictionnaire
        stats = data[0] if isinstance(data, list) else data
        
        # Extraction des stats avec noms de colonnes alternatifs
        fg3 = stats.get('fg3_per_game') or stats.get('three_pointers_made')
        opp_fg3 = stats.get('opp_fg3_per_game') or stats.get('opp_three_pointers_made')
        pace = stats.get('pace')

        if fg3 is None:
            return {"error": "Champs statistiques manquants dans la réponse API.", "debug": data}
            
        return {"fg3m": float(fg3), "opp_fg3m": float(opp_fg3) if opp_fg3 else 11.5, "pace": float(pace) if pace else 99.0}
    except Exception as e:
        return {"error": str(e)}

# --- INTERFACE ---
st.title("🏀 NBA Oracle : Version Infaillible")

c1, cvs, c2 = st.columns([2, 0.5, 2])
with c1: away_t = st.selectbox("✈️ Équipe Extérieure", list(TEAM_MAP.keys()), index=13)
with cvs: st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
with c2: home_t = st.selectbox("🏠 Équipe Domicile", list(TEAM_MAP.keys()), index=23)

with st.sidebar:
    st.header("⚙️ Paramètres")
    b2b_h = st.toggle("Home B2B")
    b2b_a = st.toggle("Away B2B")
    abs_imp = st.slider("Impact Absences", 0.0, 6.0, 0.0, 0.5)

if st.button("🚀 ANALYSER LE MATCH"):
    h_res = get_nba_data(home_t)
    a_res = get_nba_data(away_t)

    if "error" in h_res or "error" in a_res:
        st.error(h_res.get('error') or a_res.get('error'))
        if "debug" in h_res: st.json(h_res["debug"])
    else:
        # Algorithme
        m_pace = (h_res['pace'] + a_res['pace']) / 2
        p_fact = m_pace / 99.5
        proj_h = ((h_res['fg3m'] + a_res['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_h else 1.0)
        proj_a = ((a_res['fg3m'] + h_res['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_a else 1.0)
        total = (proj_h + proj_a) - abs_imp

        st.divider()
        res1, res2, res3 = st.columns(3)
        res1.metric(home_t, f"{proj_h:.2f}")
        res2.metric(away_t, f"{proj_a:.2f}")
        res3.metric("TOTAL MATCH", f"{total:.2f}")
        st.balloons()
