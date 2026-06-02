import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.request
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# ==========================================
# POBIERANIE CZCIONKI DLA POLSKICH ZNAKÓW
# ==========================================
@st.cache_resource
def pobierz_czcionke():
    font_path = "Roboto-Regular.ttf"
    if not os.path.exists(font_path):
        # Pobieranie czcionki z polskimi znakami bezpośrednio z zasobów Google
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
    return font_path

# ==========================================
# 1. INICJALIZACJA BAZY "NA SUCHO"
# ==========================================
if 'init_v6' not in st.session_state:
    st.session_state.init_v6 = True
    
    st.session_state.wz_counter = 1
    
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

# CSS
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
# MENU GŁÓWNE BOCZNE
# ==========================================
st.sidebar.title("Nawigacja")

st.sidebar.info(f"Zalogowano jako:\n**{st.session_state.aktualny_uzytkownik}**")
if st.sidebar.button("Wyloguj", use_container_width=True):
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
# ZAKŁADKA 1: PULPIT GŁÓWNY
# ------------------------------------------
if menu == "Pulpit Główny":
    st.header("Pulpit Zarządzania: GrizoThermo+")
    
    wybrany_wariant = "GrizoThermo+ (1,15m x 13mb)"
    stan_gotowych = int(st.session_state.produkty.loc[st.session_state.produkty["Wariant"] == wybrany_wariant, "Stan"].values[0])
    
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    stan_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
    stan_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

    max_rolek = min(int(stan_alu / 32.0), int(stan_bialy / 0.2), int(stan_zielony / 0.1))

    colA, colB = st.columns(2)
    with colA:
        st.markdown(f"""
        <div class="metric-card">
            <p class="big-metric-label">STAN MAGAZYNU (GOTOWE ROLKI)</p>
            <p class="big-metric" style="color: #205493;">{stan_gotowych} szt.</p>
        </div>
        """, unsafe_allow_html=True)
    with colB:
        kolor_potencjalu = "#2e7d32" if max_rolek > 0 else "#d32f2f"
        st.markdown(f"""
        <div class="metric-card">
            <p class="big-metric-label">POTENCJAŁ PRODUKCYJNY (SUROWCE)</p>
            <p class="big-metric" style="color: {kolor_potencjalu};">{max_rolek} szt.</p>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.divider()
    st.write("#### Szczegóły magazynowe")

    tab_prod, tab_komp, tab_hist = st.tabs(["Wyroby Gotowe", "Surowce i Komponenty", "Historia Operacji"])
    
    with tab_prod:
        st.dataframe(st.session_state.produkty, use_container_width=True, hide_index=True)
    with tab_komp:
        df_k = st.session_state.komponenty.copy()
        df_k["Status"] = df_k.apply(lambda row: "Niski stan" if row["Stan"] <= row["Min_Stan"] else "W normie", axis=1)
        st.dataframe(df_k.style.map(koloruj_status, subset=['Status']), use_container_width=True, hide_index=True)
    with tab_hist:
        st.dataframe(st.session_state.historia.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True)

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

    max_rolek = min(int(stan_alu / 32.0), int(stan_bialy / 0.2), int(stan_zielony / 0.1))

    with tab_kalk:
        col1, col2, col3 = st.columns(3)
        col1.metric("Zapas: Aluminium", f"{int(stan_alu / 32.0)} szt.")
        col2.metric("Zapas: Barw. biały", f"{int(stan_bialy / 0.2)} szt.")
        col3.metric("Zapas: Barw. zielony", f"{int(stan_zielony / 0.1)} szt.")
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
                    idx_komp = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == wiersz["ID_Komp"]][0]
                    st.session_state.komponenty.at[idx_komp, "Stan"] -= (wiersz["Ilosc"] * ile_produkujemy)
                    dodaj_ruch("RW", "Zlecenie Prod.", st.session_state.komponenty.at[idx_komp, "Nazwa"], (wiersz["Ilosc"] * ile_produkujemy))
                
                st.success(f"Proces zakończony. Zaksięgowano wyprodukowanie {ile_produkujemy} szt.")
                st.rerun()

# ------------------------------------------
# ZAKŁADKA 3: OPERACJE MAGAZYNOWE (GENERATOR PDF)
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
        st.subheader("Wydanie produktów do klienta i Generator WZ (PDF)")
        
        # Jeśli WZ zostało wygenerowane - pobieranie PDF
        if "wygenerowane_pdf" in st.session_state:
            st.success(f"Transakcja zaksięgowana. Dokument {st.session_state.nazwa_pliku_wz} jest gotowy do druku.")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.download_button(
                    label="📄 Pobierz dokument WZ (.pdf)",
                    data=st.session_state.wygenerowane_pdf,
                    file_name=st.session_state.nazwa_pliku_wz,
                    mime="application/pdf",
                    use_container_width=True
                )
            with col_btn2:
                if st.button("⬅️ Wyczyść formularz i wystaw kolejny dokument", use_container_width=True):
                    del st.session_state.wygenerowane_pdf
                    del st.session_state.nazwa_pliku_wz
                    st.rerun()
                    
        # Wprowadzanie danych z automatycznym numerem WZ
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            
            with st.form("wz_form"):
                nr_doc_wz = st.text_input("Numer dokumentu (Generowany automatycznie)", value=nr_wz_auto, disabled=True)
                klient = st.text_input("Nazwa firmy / Odbiorca")
                wybrany_prod = st.selectbox("Wybierz asortyment", st.session_state.produkty["Wariant"].tolist())
                
                stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
                st.caption(f"Dostępne na magazynie: {stan_obecny} szt.")
                
                ilosc_wz = st.number_input("Ilość do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
                
                if st.form_submit_button("Zatwierdź i Generuj PDF"):
                    if not klient.strip():
                        st.error("Pole 'Odbiorca' jest obowiązkowe!")
                    elif ilosc_wz <= stan_obecny:
                        # 1. Zapisanie ruchu
                        idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                        st.session_state.produkty.at[idx, "Stan"] -= ilosc_wz
                        dodaj_ruch("WZ", nr_doc_wz, wybrany_prod, ilosc_wz)
                        
                        st.session_state.wz_counter += 1
                        
                        # 2. GENEROWANIE PLIKU PDF
                        font_path = pobierz_czcionke() # Zapewnia polskie znaki
                        data_wystawienia = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        wystawil = st.session_state.aktualny_uzytkownik
                        
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.add_font("Roboto", "", font_path)
                        
                        # Nagłówek
                        pdf.set_font("Roboto", "", 18)
                        pdf.cell(0, 15, "DOKUMENT WYDANIA ZEWNĘTRZNEGO (WZ)", ln=True, align='C')
                        
                        # Dane dokumentu
                        pdf.set_font("Roboto", "", 12)
                        pdf.ln(10)
                        pdf.cell(50, 8, "NUMER DOKUMENTU:", border=0)
                        pdf.cell(0, 8, nr_doc_wz, border=0, ln=True)
                        
                        pdf.cell(50, 8, "DATA WYDANIA:", border=0)
                        pdf.cell(0, 8, data_wystawienia, border=0, ln=True)
                        
                        pdf.cell(50, 8, "WYSTAWIŁ:", border=0)
                        pdf.cell(0, 8, wystawil, border=0, ln=True)
                        
                        pdf.cell(50, 8, "ODBIORCA:", border=0)
                        pdf.cell(0, 8, klient, border=0, ln=True)
                        
                        # Tabela
                        pdf.ln(10)
                        pdf.set_font("Roboto", "", 10)
                        
                        # Nagłówki tabeli
                        pdf.cell(15, 10, "Lp.", border=1, align='C')
                        pdf.cell(115, 10, "Nazwa towaru", border=1, align='C')
                        pdf.cell(30, 10, "Ilość", border=1, align='C')
                        pdf.cell(30, 10, "Jm.", border=1, align='C', ln=True)
                        
                        # Wiersz towaru
                        pdf.cell(15, 10, "1", border=1, align='C')
                        pdf.cell(115, 10, wybrany_prod, border=1, align='L')
                        pdf.cell(30, 10, str(ilosc_wz), border=1, align='C')
                        pdf.cell(30, 10, "szt.", border=1, align='C', ln=True)
                        
                        # Miejsce na podpisy
                        pdf.ln(30)
                        pdf.cell(95, 10, ".......................................................", align='C')
                        pdf.cell(95, 10, ".......................................................", align='C', ln=True)
                        pdf.cell(95, 5, "(Podpis wystawcy)", align='C')
                        pdf.cell(95, 5, "(Podpis odbiorcy)", align='C', ln=True)
                        
                        # Zapisanie PDF do pamięci podręcznej (jako bajty)
                        pdf_bytes = bytes(pdf.output())
                        st.session_state.wygenerowane_pdf = pdf_bytes
                        
                        safe_name = nr_doc_wz.replace('/', '_')
                        st.session_state.nazwa_pliku_wz = f"{safe_name}.pdf"
                        
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
                    st.error("Wszystkie pola są wymagane!")
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

    with tab_korekt_surowce:
        zmienione_komponenty = st.data_editor(st.session_state.komponenty, key="edit_komp", hide_index=True, use_container_width=True)
        if st.button("Zapisz korektę surowców"):
            st.session_state.komponenty = zmienione_komponenty
            dodaj_ruch("KOREKTA", "Aktualizacja zbiorcza", "Wiele surowców", 0)
            st.success("Baza surowców została zaktualizowana.")
            st.rerun()

    with tab_korekt_prod:
        zmienione_produkty = st.data_editor(st.session_state.produkty, key="edit_prod", hide_index=True, use_container_width=True)
        if st.button("Zapisz korektę produktów"):
            st.session_state.produkty = zmienione_produkty
            dodaj_ruch("KOREKTA", "Aktualizacja zbiorcza", "Wiele produktów", 0)
            st.success("Baza produktów została zaktualizowana.")
            st.rerun()
