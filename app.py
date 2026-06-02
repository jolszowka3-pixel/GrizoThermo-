import streamlit as st
import pandas as pd
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# ==========================================
# 1. INICJALIZACJA BAZY "NA SUCHO"
# ==========================================
# Zmieniono na init_v3, aby wymusić odświeżenie pamięci podręcznej!
if 'init_v3' not in st.session_state:
    st.session_state.init_v3 = True
    
    # Baza użytkowników (System Granularnych Uprawnień)
    st.session_state.uzytkownicy = {
        "admin": {
            "haslo": "admin123", 
            "imie": "Kierownik Magazynu",
            "uprawnienia": {
                "produkcja": True,
                "magazyn": True,
                "admin": True
            }
        }
    }
    
    # Status logowania
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    
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

# CSS dla profesjonalnego wyglądu
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
        .big-metric { font-size: 4rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.2; text-align: center; }
        .big-metric-label { font-size: 1.2rem; color: #6c757d; text-align: center; margin-bottom: 1rem; font-weight: 500; }
        .metric-card { background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef; }
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
                login_clean = login_input.strip()
                if login_clean in st.session_state.uzytkownicy and st.session_state.uzytkownicy[login_clean]["haslo"] == haslo_input:
                    st.session_state.zalogowany = True
                    st.session_state.aktualny_uzytkownik = st.session_state.uzytkownicy[login_clean]["imie"]
                    st.session_state.aktualne_uprawnienia = st.session_state.uzytkownicy[login_clean]["uprawnienia"]
                    st.rerun()
                else:
                    st.error("Nieprawidłowy login lub hasło.")
    
    st.stop()

# ==========================================
# MENU GŁÓWNE BOCZNE (DYNAMICZNE)
# ==========================================
st.sidebar.title("Nawigacja")

st.sidebar.info(f"Zalogowano jako:\n**{st.session_state.aktualny_uzytkownik}**")
if st.sidebar.button("🚪 Wyloguj", use_container_width=True):
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    st.rerun()

st.sidebar.divider()

opcje_menu = ["Pulpit Główny"]

uprawnienia = st.session_state.aktualne_uprawnienia

if uprawnienia.get("produkcja", False):
    opcje_menu.append("Moduł Produkcji")

if uprawnienia.get("magazyn", False):
    opcje_menu.append("Operacje Magazynowe (PZ/WZ)")

if uprawnienia.get("admin", False):
    opcje_menu.append("Panel Administracyjny")

menu = st.sidebar.radio("Wybierz moduł:", opcje_menu)

# ------------------------------------------
# ZAKŁADKA 1: PULPIT GŁÓWNY (Z WIELKIMI WSKAŹNIKAMI)
# ------------------------------------------
if menu == "Pulpit Główny":
    st.header("Pulpit Zarządzania: GrizoThermo+")
    
    # OBLICZENIA DLA WSKAŹNIKÓW
    wybrany_wariant = "GrizoThermo+ (1,15m x 13mb)"
    
    # 1. Stan wyrobów gotowych
    stan_gotowych = int(st.session_state.produkty.loc[st.session_state.produkty["Wariant"] == wybrany_wariant, "Stan"].values[0])
    
    # 2. Potencjał produkcyjny (Wąskie gardło)
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    stan_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
    stan_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

    potencjal_alu = int(stan_alu / 32.0)
    potencjal_bialy = int(stan_bialy / 0.2)
    potencjal_zielony = int(stan_zielony / 0.1)
    max_rolek = min(potencjal_alu, potencjal_bialy, potencjal_zielony)

    # WYŚWIETLANIE WIELKICH KAFELKÓW (HTML/CSS)
    colA, colB = st.columns(2)
    
    with colA:
        st.markdown(f"""
        <div class="metric-card">
            <p class="big-metric-label">📦 STAN MAGAZYNU (GOTOWE ROLKI)</p>
            <p class="big-metric" style="color: #205493;">{stan_gotowych} szt.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with colB:
        # Jeśli nie można wyprodukować niczego, kolor zmienia się na czerwony, jeśli można - na zielony
        kolor_potencjalu = "#2e7d32" if max_rolek > 0 else "#d32f2f"
        st.markdown(f"""
        <div class="metric-card">
            <p class="big-metric-label">🚀 POTENCJAŁ PRODUKCYJNY Z OBECNYCH SUROWCÓW</p>
            <p class="big-metric" style="color: {kolor_potencjalu};">{max_rolek} szt.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("") # Odstęp
    st.divider()
    st.write("#### Szczegóły magazynowe")

    # RESZTA PULPITU - TABELE
    tab_prod, tab_komp, tab_hist = st.tabs(["Wyroby Gotowe", "Surowce i Komponenty", "Historia Operacji"])
    
    with tab_prod:
        st.dataframe(
            st.session_state.produkty, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Wariant": st.column_config.TextColumn("Wariant Produktu", width="large"),
                "Stan": st.column_config.NumberColumn("Sztuk na stanie", format="%d")
            }
        )
    
    with tab_komp:
        df_k = st.session_state.komponenty.copy()
        df_k["Status"] = df_k.apply(lambda row: "Niski stan" if row["Stan"] <= row["Min_Stan"] else "W normie", axis=1)
        styled_df_k = df_k.style.map(koloruj_status, subset=['Status'])
        
        st.dataframe(
            styled_df_k, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Nazwa": st.column_config.TextColumn("Nazwa Surowca", width="medium"),
                "Stan": st.column_config.NumberColumn("Stan", format="%.2f"),
                "Min_Stan": None 
            }
        )
        
    with tab_hist:
        st.dataframe(
            st.session_state.historia.sort_values(by="Data", ascending=False), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data": st.column_config.DatetimeColumn("Data operacji", format="YYYY-MM-DD HH:mm"),
                "Typ": st.column_config.TextColumn("Typ Ruchu"),
                "Dokument": st.column_config.TextColumn("Nr Dokumentu"),
                "Ilosc": st.column_config.NumberColumn("Ilość", format="%.2f"),
                "Użytkownik": st.column_config.TextColumn("Kto wykonał")
            }
        )

# ------------------------------------------
# ZAKŁADKA 2: PRODUKCJA 
# ------------------------------------------
elif menu == "Moduł Produkcji":
    st.header("Zarządzanie Produkcją: GrizoThermo+")
    
    tab_kalk, tab_zlecenie = st.tabs(["Kalkulator Potencjału", "Zlecenie Produkcji"])
    
    wybrany_wariant = "GrizoThermo+ (1,15m x 13mb)"
    
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    stan_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
    stan_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

    potencjal_alu = int(stan_alu / 32.0)
    potencjal_bialy = int(stan_bialy / 0.2)
    potencjal_zielony = int(stan_zielony / 0.1)

    max_rolek = min(potencjal_alu, potencjal_bialy, potencjal_zielony)

    with tab_kalk:
        st.write("#### Szczegółowe zapotrzebowanie surowcowe")
        col1, col2, col3 = st.columns(3)
        col1.metric("Zapas: Aluminium", f"{potencjal_alu} szt.")
        col2.metric("Zapas: Barw. biały", f"{potencjal_bialy} szt.")
        col3.metric("Zapas: Barw. zielony", f"{potencjal_zielony} szt.")
        
        st.divider()
        if max_rolek > 0:
            st.info(f"Maksymalny możliwy wolumen produkcji: {max_rolek} szt.")
        else:
            st.warning("Brak wystarczającej ilości surowców do uruchomienia partii.")

    with tab_zlecenie:
        st.subheader("Rejestracja wykonanej produkcji")
        with st.form("produkcja_form"):
            ile_produkujemy = st.number_input("Wprowadź ilość wyprodukowanych rolek", min_value=1, max_value=max_rolek if max_rolek > 0 else 1, value=1 if max_rolek > 0 else 0)
            
            if st.form_submit_button("Zatwierdź i zaksięguj produkcję", disabled=(max_rolek == 0)):
                idx_prod = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_wariant][0]
                st.session_state.produkty.at[idx_prod, "Stan"] += ile_produkujemy
                dodaj_ruch("PW", "Zlecenie Prod.", wybrany_wariant, ile_produkujemy)
                
                receptura = st.session_state.receptury[st.session_state.receptury["Wariant"] == wybrany_wariant]
                for _, wiersz in receptura.iterrows():
                    id_komp = wiersz["ID_Komp"]
                    zuzycie_laczne = wiersz["Ilosc"] * ile_produkujemy
                    
                    idx_komp = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == id_komp][0]
                    st.session_state.komponenty.at[idx_komp, "Stan"] -= zuzycie_laczne
                    nazwa_komp = st.session_state.komponenty.at[idx_komp, "Nazwa"]
                    dodaj_ruch("RW", "Zlecenie Prod.", nazwa_komp, zuzycie_laczne)
                
                st.success(f"Proces zakończony. Zaksięgowano wyprodukowanie {ile_produkujemy} szt.")
                st.rerun()

# ------------------------------------------
# ZAKŁADKA 3: OPERACJE MAGAZYNOWE (PZ / WZ)
# ------------------------------------------
elif menu == "Operacje Magazynowe (PZ/WZ)":
    st.header("Zarządzanie Zapasami (PZ/WZ)")
    
    tab_pz, tab_wz = st.tabs(["Przyjęcie Zewnętrzne (PZ)", "Wydanie Zewnętrzne (WZ)"])
    
    with tab_pz:
        st.subheader("Rejestracja nowej dostawy surowców")
        with st.form("pz_form"):
            nr_doc = st.text_input("Numer dokumentu (np. nr faktury, WZ dostawcy)")
            wybrany_komp = st.selectbox("Wybierz przyjmowany surowiec", st.session_state.komponenty["Nazwa"].tolist())
            ilosc = st.number_input("Ilość przyjmowana (zgodnie z jm.)", min_value=0.1, value=100.0)
            
            if st.form_submit_button("Zatwierdź dokument PZ"):
                idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == wybrany_komp][0]
                st.session_state.komponenty.at[idx, "Stan"] += ilosc
                dodaj_ruch("PZ", nr_doc, wybrany_komp, ilosc)
                st.success("Dokument PZ został pomyślnie zapisany w systemie.")
                st.rerun()

    with tab_wz:
        st.subheader("Wydanie produktów do klienta")
        with st.form("wz_form"):
            nr_doc_wz = st.text_input("Numer dokumentu (np. nr zamówienia, WZ)", key="wz_doc")
            wybrany_prod = st.selectbox("Wybierz asortyment", st.session_state.produkty["Wariant"].tolist())
            
            stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
            st.caption(f"Dostępne na magazynie: {stan_obecny} szt.")
            
            ilosc_wz = st.number_input("Ilość do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
            
            if st.form_submit_button("Zatwierdź dokument WZ"):
                if ilosc_wz <= stan_obecny:
                    idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                    st.session_state.produkty.at[idx, "Stan"] -= ilosc_wz
                    dodaj_ruch("WZ", nr_doc_wz, wybrany_prod, ilosc_wz)
                    st.success("Dokument WZ został pomyślnie zapisany w systemie.")
                    st.rerun()
                else:
                    st.error("Odrzucono: Niewystarczająca ilość asortymentu na magazynie.")

# ------------------------------------------
# ZAKŁADKA 4: PANEL ADMINA
# ------------------------------------------
elif menu == "Panel Administracyjny" and st.session_state.aktualne_uprawnienia.get("admin", False):
    st.header("Narzędzia Administracyjne")
    
    tab_uzytkownicy, tab_korekt_surowce, tab_korekt_prod = st.tabs([
        "Konta Użytkowników", "Korekta Surowców", "Korekta Wyrobów Gotowych"
    ])
    
    # --- ZARZĄDZANIE KONTAMI ---
    with tab_uzytkownicy:
        st.subheader("Zarządzanie Dostępem i Uprawnieniami")
        
        lista_uzytkownikow = []
        for l, dane in st.session_state.uzytkownicy.items():
            lista_uzytkownikow.append({
                "Login": l,
                "Imię i Nazwisko": dane["imie"],
                "Dostęp: Produkcja": "Tak" if dane["uprawnienia"].get("produkcja") else "Nie",
                "Dostęp: PZ/WZ": "Tak" if dane["uprawnienia"].get("magazyn") else "Nie",
                "Dostęp: Admin": "Tak" if dane["uprawnienia"].get("admin") else "Nie"
            })
            
        st.write("**Aktywne konta w systemie:**")
        st.dataframe(pd.DataFrame(lista_uzytkownikow), use_container_width=True, hide_index=True)
        
        st.divider()
        st.write("**Utwórz nowe konto użytkownika:**")
        with st.form("dodaj_uzytkownika"):
            colA, colB = st.columns(2)
            with colA:
                nowy_login = st.text_input("Login (Identyfikator)")
                nowe_imie = st.text_input("Imię i Nazwisko")
                nowe_haslo = st.text_input("Hasło startowe", type="password")
            with colB:
                st.write("Wybierz uprawnienia dla konta:")
                upr_produkcja = st.checkbox("Dostęp do Modułu Produkcji")
                upr_magazyn = st.checkbox("Dostęp do Operacji Magazynowych (PZ/WZ)")
                upr_admin = st.checkbox("Dostęp do Panelu Administracyjnego")
                
            if st.form_submit_button("Utwórz konto"):
                nowy_login = nowy_login.strip()
                if not nowy_login or not nowe_haslo or not nowe_imie:
                    st.error("Wszystkie pola (Login, Imię, Hasło) są wymagane!")
                elif nowy_login in st.session_state.uzytkownicy:
                    st.error("Konto o takim loginie już istnieje!")
                else:
                    st.session_state.uzytkownicy[nowy_login] = {
                        "haslo": nowe_haslo,
                        "imie": nowe_imie,
                        "uprawnienia": {
                            "produkcja": upr_produkcja,
                            "magazyn": upr_magazyn,
                            "admin": upr_admin
                        }
                    }
                    st.success(f"Pomyślnie utworzono nowe konto dla: {nowe_imie}!")
                    st.rerun()

    # --- KOREKTA SUROWCÓW ---
    with tab_korekt_surowce:
        st.caption("Instrukcja: Kliknij dwukrotnie wartość w kolumnie 'Stan Aktualny', wpisz poprawną i zatwierdź przyciskiem na dole tabeli.")
        zmienione_komponenty = st.data_editor(
            st.session_state.komponenty, 
            key="edit_komp", 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", disabled=True),
                "Nazwa": st.column_config.TextColumn("Nazwa Surowca", disabled=True),
                "Jednostka": st.column_config.TextColumn("Jm.", disabled=True),
                "Min_Stan": st.column_config.NumberColumn("Min. Stan (Alarm)", disabled=True),
                "Stan": st.column_config.NumberColumn("Stan Aktualny", format="%.2f", required=True)
            }
        )
        
        if st.button("Zapisz korektę surowców"):
            st.session_state.komponenty = zmienione_komponenty
            dodaj_ruch("KOREKTA", "Aktualizacja zbiorcza", "Wiele surowców", 0)
            st.success("Baza surowców została zaktualizowana.")
            st.rerun()

    # --- KOREKTA PRODUKTÓW ---
    with tab_korekt_prod:
        st.caption("Instrukcja: Kliknij dwukrotnie wartość w kolumnie 'Stan Aktualny', wpisz poprawną i zatwierdź przyciskiem na dole tabeli.")
        zmienione_produkty = st.data_editor(
            st.session_state.produkty, 
            key="edit_prod", 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Wariant": st.column_config.TextColumn("Wariant Maty", disabled=True),
                "Stan": st.column_config.NumberColumn("Stan Aktualny", required=True, step=1)
            }
        )
        
        if st.button("Zapisz korektę produktów"):
            st.session_state.produkty = zmienione_produkty
            dodaj_ruch("KOREKTA", "Aktualizacja zbiorcza", "Wiele produktów", 0)
            st.success("Baza produktów została zaktualizowana.")
            st.rerun()
