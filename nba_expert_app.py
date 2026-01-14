import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="NBA Oracle Pro v3", layout="wide", page_icon="🏀")

# Initialisation de l'historique
if 'history' not in st.session_state:
    st.session_state.history = []

# Récupération sécurisée des clés
try:
    RAPID_KEY = st.secrets["X_RAPIDAPI_KEY"]
    RAPID_HOST = st.secrets["X_RAPIDAPI_HOST"]
except:
    st.error("⚠️ Clés API absentes des Secrets Streamlit (X_RAPIDAPI_KEY / X_RAPIDAPI_HOST)")
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

# --- MOTEUR D'ACQUISITION ---
@st.cache_data(ttl=3600)
def get_nba_data(team_name):
    """Récupère les données réelles et gère les erreurs de structure JSON"""
    # L'API Basketball-Head utilise souvent le nom de l'équipe en minuscule (ex: lakers)
    slug = team_name.split(" ")[-1].lower() 
    url = f"https://{RAPID_HOST}/teams/{slug}/stats"
    headers = {"x-rapidapi-key": RAPID_KEY, "x-rapidapi-host": RAPID_HOST}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Erreur API: {response.status_code}"}
        
        data = response.json()
        
        # Extraction dynamique selon plusieurs structures possibles de l'API
        stats = data.get('body', data) # Cherche dans 'body' ou à la racine
        if isinstance(stats, list) and len(stats) > 0: stats = stats[0]

        # On cherche les valeurs sans fallback automatique pour détecter les pannes
        fg3 = stats.get('fg3_per_game') or stats.get('three_pointers_made')
        opp_fg3 = stats.get('opp_fg3_per_game') or stats.get('opp_three_pointers_made')
        pace = stats.get('pace')

        if fg3 is None:
            return {"error": f"Données non trouvées pour {team_name}", "debug": data}
            
        return {
            "fg3m": float(fg3),
            "opp_fg3m": float(opp_fg3) if opp_fg3 else 11.5,
            "pace": float(pace) if pace else 99.0
        }
    except Exception as e:
        return {"error": str(e)}

# --- INTERFACE ---
st.title("🏀 NBA Oracle Premium : Analyse Corrigée")

# Barre latérale pour le Debug et Paramètres
with st.sidebar:
    st.header("🛠️ Options")
    debug_mode = st.checkbox("Afficher les données brutes (Debug)")
    st.divider()
    b2b_h = st.toggle("Home en B2B")
    b2b_a = st.toggle("Away en B2B")
    abs_imp = st.slider("Impact Absences (Paniers)", 0.0, 6.0, 0.0, 0.5)
    st.divider()
    bet_val = st.number_input("Mise (€)", 10.0)
    odd_val = st.number_input("Cote", 1.85)

tab1, tab2 = st.tabs(["🎯 Analyse", "📈 Historique ROI"])

with tab1:
    c1, cvs, c2 = st.columns([2, 0.5, 2])
    with c1: away_t = st.selectbox("✈️ Équipe Extérieure", NBA_TEAMS, index=13)
    with cvs: st.markdown("<h3 style='text-align:center;'>VS</h3>", unsafe_allow_html=True)
    with c2: home_t = st.selectbox("🏠 Équipe Domicile", NBA_TEAMS, index=23)

    if st.button("🚀 LANCER L'ANALYSE"):
        h_res = get_nba_data(home_t)
        a_res = get_nba_data(away_t)

        if debug_mode:
            st.write("Debug Home:", h_res)
            st.write("Debug Away:", a_res)

        if "error" in h_res or "error" in a_res:
            st.error(f"Impossible de calculer : {h_res.get('error') or a_res.get('error')}")
            st.info("💡 Conseil : Si l'erreur est 'Données non trouvées', essayez d'effacer le cache dans le menu en haut à droite.")
        else:
            # --- ALGORITHME ---
            m_pace = (h_res['pace'] + a_res['pace']) / 2
            p_fact = m_pace / 99.5
            
            proj_h = ((h_res['fg3m'] + a_res['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_h else 1.0)
            proj_a = ((a_res['fg3m'] + h_res['opp_fg3m']) / 2) * p_fact * (0.94 if b2b_a else 1.0)
            total = (proj_h + proj_a) - abs_imp

            st.divider()
            r1, r2, r3 = st.columns(3)
            r1.metric(home_t, f"{proj_h:.2f}")
            r2.metric(away_t, f"{proj_a:.2f}")
            r3.metric("TOTAL MATCH", f"{total:.2f}")

            st.session_state.last_calc = {
                "Date": datetime.now().strftime("%d/%m/%Y"),
                "Match": f"{away_t} @ {home_t}",
                "Projection": round(total, 2),
                "Mise": bet_val, "Cote": odd_val
            }

    if 'last_calc' in st.session_state:
        if st.button("💾 Enregistrer ce pari"):
            st.session_state.history.append(st.session_state.last_calc)
            st.success("Pari archivé !")

with tab2:
    if st.session_state.history:
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)
        total_bets = sum(i['Mise'] for i in st.session_state.history)
        st.metric("Total Engagé", f"{total_bets:.2f} €")
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger Excel/CSV", data=csv, file_name="nba_tracker.csv")
    else:
        st.info("Aucun historique pour cette session.")
