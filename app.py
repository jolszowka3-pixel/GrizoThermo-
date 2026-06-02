import streamlit as st
import pandas as pd
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# ==========================================
# 1. INICJALIZACJA BAZY "NA SUCHO"
# ==========================================
if 'init' not in st.session_state:
    st.session_state.init = True
    
    # Baza użytkowników (Zmieniony system ról)
    st.session_state.uzytkownicy = {
        "admin": {"haslo": "admin123", "rola": "Admin", "imie": "Kierownik Magazynu"},
        "jan": {"haslo": "hala123", "rola": "Pracownik", "imie": "Jan Kowalski"}
    }
    
    # Status logowania
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualna_rola = None
    
    st.session_state.komponenty = pd.DataFrame([
        {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb", "Min_Stan": 1000.0},
        {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg", "Min_Stan": 5.0},
        {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg", "Min_Stan": 3.0}
    ])
    
    st.session_state.receptury = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K01", "Ilosc": 32.0},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K02", "Ilosc": 0.2},
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "ID_Komp": "K03", "Ilosc": 0.1}
    ])
    
    st.session_state.produkty = pd.DataFrame([
        {"Wariant": "GrizoThermo+ (1,15m x 13mb)", "Stan": 0}
    ])
    
    st.session_state.historia = pd.DataFrame(columns=[
        "Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Użytkownik"
    ])

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
def dodaj_ruch(typ, dokument, nazwa, ilosc):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ,
        "Dokument": dokument,
        "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc,
        "Użytkownik": uzytkownik
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

def koloruj_status(val):
    if isinstance(val, str):
        if 'Niski stan' in val:
            return 'color: #d32f2f; font-weight: 600;' 
        elif 'W normie' in val:
            return 'color: #2e7d32; font-weight: 500;' 
    return ''

# CSS
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# EKRAN LOGOWANIA
# ==========================================
if not st.session_state.zalogowany:
    st.markdown("<h1 style='text-align: center; color: #205493;'>GrizoThermo+ | Logowanie</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("formularz_logowania"):
            login_input = st.text_input("Identyfikator użytkownika")
            haslo_input = st.text_input("Hasło", type="password")
            submit = st.form_submit_button("Zaloguj do systemu", use_container_width=True)
            
            if submit:
                # Czyszczenie białych znaków (np. spacji na końcu loginu)
                login_clean = login_input.strip()
                if login_clean in st.session_state.uzytkownicy and st.session_state.uzytkownicy[login_clean]["haslo"] == haslo_input:
                    st.session_state.zalogowany = True
                    st.session_state.aktualny_uzytkownik = st.session_state.uzytkownicy[login_clean]["imie"]
                    st.session_state.aktualna_rola = st.session_state.uzytkownicy[login_clean]["rola"]
                    st.rerun()
                else:
                    st.error("Nieprawidłowy login lub hasło.")
    
    st.stop()

# ==========================================
# MENU GŁÓWNE BOCZNE (DYNAMICZNE)
# ==========================================
st.sidebar.title("Nawigacja")

st.sidebar.info(f"Zalogowano jako:\n**{st.session_state.aktualny_uzytkownik}**\nRola: {st.session_state.aktualna_rola}")
if st.sidebar.button("🚪 Wyloguj", use_container_width=True):
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualna_rola = None
    st.rerun()

st.sidebar.divider()

# Generowanie menu w oparciu o rolę
opcje_menu = ["Pulpit Magazynowy"] # Dostępne dla każdego

rola = st.session_state.aktualna_rola

if rola in ["Admin", "Pracownik", "Produkcja"]:
    opcje_menu.append("Moduł Produkcji")

if rola in ["Admin", "Pracownik", "Magazynier"]:
    opcje_menu.append("Operacje Magazynowe (PZ/WZ)")

if rola == "Admin":
    opcje_menu.append("Panel Administracyjny")

menu = st
