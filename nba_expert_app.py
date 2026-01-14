import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="NBA Oracle Pro + Tracker", layout="wide", page_icon="🏀")

# Initialisation de l'historique dans la session
if 'history' not in st.session_state:
    st.session_state.history = []

# Récupération sécurisée
try:
    RAPID_KEY = st.secrets["X_RAPIDAPI_KEY"]
    RAPID_HOST = st.secrets["X_RAPIDAPI_HOST"]
except:
    st.error("Erreur : Configurez vos Secrets (X_RAPIDAPI_KEY) sur Streamlit.")
    st.stop()

NBA_TEAMS = sorted([
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets", 
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets", 
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets", "Indiana Pacers", 
    "Los Angeles Clippers", "Los Angeles Lakers", "Memphis Grizzlies", "Miami Heat", 
    "Milwaukee Bucks", "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks", 
    "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers", "Phoenix Suns", 
    "Portland Trail Blazers", "Sacramento Kings", "San Antonio Spurs", "Toronto Raptors", 
    "Utah Jazz", "Washington Wizards"
])

@st.cache_data(ttl=86400)
def get_team_stats(team_display_name):
    api_slug = team_display_name.replace(" ", "-").lower()
    url = f"https://{RAPID_HOST}/teams/{api_slug}/stats"
    headers = {"x-rapidapi-key": RAPID_KEY, "x-rapidapi-host": RAPID_HOST}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        return {
            "fg3m": float(data.get('fg3_per_game', 12.0)),
            "opp_fg3m": float(data.get('opp_fg3_per_game', 12.0)),
            "pace": float(data.get('pace', 99.0))
        }
    except:
        return None

# --- INTERFACE ---
st.title("🏀 NBA Oracle : Analyse & Suivi ROI")

tab1, tab2 = st.tabs(["🎯 Analyse du Match", "📈 Historique & Performance"])

with tab1:
    c1, cvs, c2 = st.columns([2, 0.5, 2])
    with c1: away_t = st.selectbox("Équipe Extérieure", NBA_TEAMS, index=9)
    with cvs: st.markdown("<h3 style='text-align:center;'>@</h3>", unsafe_allow_html=True)
    with c2: home_t = st.selectbox("Équipe Domicile", NBA_TEAMS, index=1)

    with st.sidebar:
        st.header("⚙️ Paramètres")
        b2b_h = st.toggle("Home en B2B")
        b2b_a = st.toggle("Away en B2B")
        abs_imp = st.slider("Impact Absences", 0.0, 5.0, 0.0)
        st.divider()
        bet_amount = st.number_input("Mise (€)", value=10.0)
        odds = st.number_input("Cote (ex: 1.85)", value=1.85)

    if st.button("Calculer & Préparer le Pari"):
        h_s = get_team_stats(home_t)
        a_s = get_team_stats(away_t)
        
        if h_s and a_s:
            # Algorithme
            m_pace = (h_s['pace'] + a_s['pace']) / 2
            p_fact = m_pace / 99.2
            res_h = ((h_s['fg3m'] + a_s['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_h else 1.0)
            res_a = ((a_s['fg3m'] + h_s['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_a else 1.0)
            total = (res_h + res_a) - abs_imp

            st.metric("TOTAL PROJETÉ", f"{total:.2f} Paniers à 3pts")
            
            # Enregistrement temporaire pour le tracker
            st.session_state.current_bet = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Match": f"{away_t} @ {home_t}",
                "Projection": round(total, 2),
                "Mise": bet_amount,
                "Cote": odds
            }
            st.success("Analyse prête. Si vous pariez, cliquez sur 'Enregistrer ce pari' ci-dessous.")

    if 'current_bet' in st.session_state:
        if st.button("💾 Enregistrer ce pari dans l'historique"):
            st.session_state.history.append(st.session_state.current_bet)
            st.toast("Pari ajouté à l'historique !")

with tab2:
    st.header("Suivi de vos investissements")
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.table(df)
        
        # Calculs rapides
        total_miste = sum(d['Mise'] for d in st.session_state.history)
        st.write(f"**Total Engagé :** {total_miste:.2f}€")
        
        # Export CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger l'historique (CSV)", data=csv, file_name="nba_oracle_bets.csv", mime="text/csv")
    else:
        st.info("Aucun pari enregistré pour le moment.")
