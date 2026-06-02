import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.request
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# ==========================================
# DANE TWOJEJ FIRMY (WYSTAWCY DOKUMENTÓW WZ)
# ==========================================
MOJA_FIRMA = {
    "nazwa": "GrizoThermo Sp. z o.o.",
    "adres": "ul. Fabryczna 14A\n44-100 Katowice",
    "nip": "NIP: 1234567890",
    "kontakt": "biuro@grizothermo.pl",
    "miejscowosc_wystawienia": "Katowice"
}

# ==========================================
# POBIERANIE CZCIONEK DLA POLSKICH ZNAKÓW
# ==========================================
@st.cache_resource
def pobierz_czcionki():
    reg_path = "Roboto-Regular.ttf"
    bold_path = "Roboto-Bold.ttf"
    if not os.path.exists(reg_path):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", reg_path)
    if not os.path.exists(bold_path):
        urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", bold_path)
    return reg_path, bold_path

# ==========================================
# 1. INICJALIZACJA BAZY "NA SUCHO"
# ==========================================
if 'init_v12' not in st.session_state:
    st.session_state.init_v12 = True
    
    st.session_state.wz_counter = 1
    
    st.session_state.uzytkownicy = {
        "admin": {
            "haslo": "admin123", 
            "imie": "Kierownik Magazynu",
            "uprawnienia": {"produkcja": True, "magazyn": True, "admin": True}
        }
    }
    
    st.session_state.kontrahenci = pd.DataFrame([
        {"Nazwa": "Hurtownia Surowców ALUSTAR", "NIP": "1112223344", "Adres": "ul. Hutnicza 10, 40-001 Katowice", "Typ": "Dostawca"},
        {"Nazwa": "Chemia Przemysłowa Sp. z o.o.", "NIP": "9998887766", "Adres": "ul. Barwna 5, 01-234 Warszawa", "Typ": "Dostawca"},
        {"Nazwa": "Bud-Max Materiały Budowlane", "NIP": "5554443322", "Adres": "ul. Wrocławska 100, 30-001 Kraków", "Typ": "Odbiorca"},
        {"Nazwa": "Izolacje Kowalski s.c.", "NIP": "1231231212", "Adres": "ul. Długa 12/4, 80-002 Gdańsk", "Typ": "Odbiorca"}
    ])
    
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
        "Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Użytkownik", "Kontrahent"
    ])

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent="-"):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ,
        "Dokument": dokument,
        "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc,
        "Użytkownik": uzytkownik,
        "Kontrahent": kontrahent
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

# CSS (Z nowymi stylami dla kafelków)
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
        
        .big-metric { font-size: 4rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.2; text-align: center; }
        .big-metric-label { font-size: 1.2rem; color: #6c757d; text-align: center; margin-bottom: 1rem; font-weight: 500; }
        .metric-card { background-color: #ffffff; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef; }
        
        /* NOWE STYLE DLA ELEMENTÓW MAGAZYNU (MNIEJ TECHNICZNE) */
        .item-card { background-color: #ffffff; border-radius: 8px; padding: 18px 24px; margin-bottom: 16px; border: 1px solid #e9ecef; box-shadow: 0 2px 5px rgba(0,0,0,0.02); display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #205493; }
        .item-card-alert { border-left: 4px solid #d32f2f; } /* Czerwony pasek dla braków */
        .item-card-ok { border-left: 4px solid #2e7d32; } /* Zielony pasek dla dobrych stanów */
        
        .item-info { display: flex; flex-direction: column; }
        .item-title { font-size: 1.15rem; font-weight: 600; color: #212529; margin: 0; padding: 0; }
        .item-subtitle { font-size: 0.9rem; color: #6c757d; margin-top: 4px; display: flex; align-items: center; gap: 8px; }
        
        .item-value-box { text-align: right; }
        .item-value { font-size: 1.6rem; font-weight: 700; color: #212529; margin: 0; padding: 0; }
        .item-unit { font-size: 1rem; color: #6c757d; font-weight: 500; }
        
        .badge-ok { background-color: #e8f5e9; color: #2e7d32; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; }
        .badge-alert { background-color: #ffebee; color: #c62828; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; }
        
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
    opcje_menu.append("Baza Kontrahentów (CRM)")
if uprawnienia.get("admin", False):
    opcje_menu.append("Panel Administracyjny")

menu = st.sidebar.radio("Wybierz moduł:", opcje_menu)

# ------------------------------------------
# ZAKŁADKA 1: PULPIT GŁÓWNY (Z KAFELKAMI)
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
    
    tab_prod, tab_komp, tab_hist = st.tabs(["Wyroby Gotowe", "Surowce i Komponenty", "Historia Operacji"])
    
    # ------------------
    # WYROBY GOTOWE - KAFELKI
    # ------------------
    with tab_prod:
        st.write("#### Lista Asortymentu")
        for index, row in st.session_state.produkty.iterrows():
            html_produkt = f"""
            <div class="item-card">
                <div class="item-info">
                    <p class="item-title">📦 {row['Wariant']}</p>
                    <p class="item-subtitle">Kategoria: Wyroby gotowe do sprzedaży</p>
                </div>
                <div class="item-value-box">
                    <p class="item-value">{int(row['Stan'])} <span class="item-unit">szt.</span></p>
                </div>
            </div>
            """
            st.markdown(html_produkt, unsafe_allow_html=True)

    # ------------------
    # SUROWCE - KAFELKI Z ETYKIETAMI
    # ------------------
    with tab_komp:
        st.write("#### Magazyn Komponentów")
        for index, row in st.session_state.komponenty.iterrows():
            jest_malo = row['Stan'] <= row['Min_Stan']
            klasa_karty = "item-card-alert" if jest_malo else "item-card-ok"
            badge = f'<span class="badge-alert">⚠️ Poniżej minimum (Min: {row["Min_Stan"]})</span>' if jest_malo else f'<span class="badge-ok">✅ W normie (Min: {row["Min_Stan"]})</span>'
            
            # Formaty zapisu bez niepotrzebnych zer po przecinku
            stan_format = f"{row['Stan']:g}"
            
            html_surowiec = f"""
            <div class="item-card {klasa_karty}">
                <div class="item-info">
                    <p class="item-title">🧱 {row['Nazwa']} <span style="font-size: 0.8rem; color: #aaa; margin-left: 8px;">[{row['ID']}]</span></p>
                    <p class="item-subtitle">{badge}</p>
                </div>
                <div class="item-value-box">
                    <p class="item-value">{stan_format} <span class="item-unit">{row['Jednostka']}</span></p>
                </div>
            </div>
            """
            st.markdown(html_surowiec, unsafe_allow_html=True)

    # ------------------
    # HISTORIA - POZOSTAJE TABELĄ
    # ------------------
    with tab_hist:
        st.write("#### Dziennik Ruchów Magazynowych")
        st.dataframe(
            st.session_state.historia.sort_values(by="Data", ascending=False), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Data": st.column_config.DatetimeColumn("Data", format="YYYY-MM-DD HH:mm"),
                "Kontrahent": st.column_config.TextColumn("Dostawca/Odbiorca")
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
                dodaj_ruch("PW", "Zlecenie Prod.", wybrany_wariant, ile_produkujemy, "Produkcja Własna")
                
                receptura = st.session_state.receptury[st.session_state.receptury["Wariant"] == wybrany_wariant]
                for _, wiersz in receptura.iterrows():
                    idx_komp = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == wiersz["ID_Komp"]][0]
                    st.session_state.komponenty.at[idx_komp, "Stan"] -= (wiersz["Ilosc"] * ile_produkujemy)
                    dodaj_ruch("RW", "Zlecenie Prod.", st.session_state.komponenty.at[idx_komp, "Nazwa"], (wiersz["Ilosc"] * ile_produkujemy), "Produkcja Własna")
                
                st.success(f"Proces zakończony. Zaksięgowano wyprodukowanie {ile_produkujemy} szt.")
                st.rerun()

# ------------------------------------------
# ZAKŁADKA 3: BAZA KONTRAHENTÓW (CRM)
# ------------------------------------------
elif menu == "Baza Kontrahentów (CRM)":
    st.header("Baza Kontrahentów (Klienci i Dostawcy)")
    st.info("💡 **Aby dodać nową firmę**, przewiń na sam dół tabeli i kliknij w pusty wiersz. Możesz też usuwać firmy, zaznaczając je z lewej strony i wciskając klawisz Delete.")
    
    zmienieni_kontrahenci = st.data_editor(
        st.session_state.kontrahenci,
        key="edit_kontrahenci",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Nazwa": st.column_config.TextColumn("Nazwa Firmy", required=True),
            "NIP": st.column_config.TextColumn("Numer NIP", required=False),
            "Adres": st.column_config.TextColumn("Pełny Adres", required=True),
            "Typ": st.column_config.SelectboxColumn(
                "Typ firmy",
                options=["Dostawca", "Odbiorca"],
                required=True
            )
        }
    )
    
    if st.button("💾 Zapisz zmiany w Bazie Kontrahentów"):
        st.session_state.kontrahenci = zmienieni_kontrahenci
        st.success("Zaktualizowano bazę firm!")
        st.rerun()

# ------------------------------------------
# ZAKŁADKA 4: OPERACJE MAGAZYNOWE (PZ / WZ - GENERATOR)
# ------------------------------------------
elif menu == "Operacje Magazynowe (PZ/WZ)":
    st.header("Zarządzanie Zapasami (PZ/WZ)")
    
    tab_pz, tab_wz = st.tabs(["Przyjęcie Zewnętrzne (PZ)", "Wydanie Zewnętrzne (WZ)"])
    
    with tab_pz:
        st.subheader("Rejestracja nowej dostawy surowców")
        dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]["Nazwa"].tolist()
        
        if not dostawcy:
            st.warning("Brak dostawców w bazie! Przejdź do zakładki 'Baza Kontrahentów (CRM)', aby ich dodać.")
        else:
            with st.form("pz_form"):
                nr_doc = st.text_input("Numer dokumentu (np. nr faktury, WZ dostawcy)")
                wybrany_dostawca = st.selectbox("Dostawca", dostawcy)
                wybrany_komp = st.selectbox("Wybierz przyjmowany surowiec", st.session_state.komponenty["Nazwa"].tolist())
                ilosc = st.number_input("Ilość przyjmowana (zgodnie z jm.)", min_value=0.1, value=100.0)
                
                if st.form_submit_button("Zatwierdź dokument PZ"):
                    idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == wybrany_komp][0]
                    st.session_state.komponenty.at[idx, "Stan"] += ilosc
                    dodaj_ruch("PZ", nr_doc, wybrany_komp, ilosc, wybrany_dostawca)
                    st.success("Dokument PZ został pomyślnie zapisany w systemie.")
                    st.rerun()

    with tab_wz:
        st.subheader("Wydanie produktów do klienta (Generator PDF)")
        odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
        
        if "wygenerowane_pdf" in st.session_state:
            st.success(f"Transakcja zaksięgowana. Dokument {st.session_state.nazwa_pliku_wz} jest gotowy do pobrania.")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                st.download_button(
                    label="📄 Pobierz oficjalny dokument WZ (.pdf)",
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
                    
        elif not odbiorcy:
            st.warning("Brak odbiorców w bazie! Przejdź do zakładki 'Baza Kontrahentów (CRM)', aby ich dodać.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            
            with st.form("wz_form"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    nr_doc_wz = st.text_input("Numer dokumentu (Auto)", value=nr_wz_auto, disabled=True)
                    wybrany_klient = st.selectbox("Nabywca (Wybierz z bazy)", odbiorcy)
                    
                with col_f2:
                    wybrany_prod = st.selectbox("Wybierz asortyment", st.session_state.produkty["Wariant"].tolist())
                    stan_obecny = st.session_state.produkty[st.session_state.produkty["Wariant"] == wybrany_prod]["Stan"].values[0]
                    st.caption(f"Dostępne na magazynie: {stan_obecny} szt.")
                    ilosc_wz = st.number_input("Ilość do wydania", min_value=1, max_value=int(stan_obecny) if stan_obecny > 0 else 1)
                    uwagi_doc = st.text_input("Uwagi do dokumentu", value="Dostawa z magazynu głównego.")

                if st.form_submit_button("Zatwierdź i Wystaw PDF"):
                    if ilosc_wz <= stan_obecny:
                        dane_klienta = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] == wybrany_klient].iloc[0]
                        klient_adres = dane_klienta["Adres"]
                        klient_nip = dane_klienta["NIP"]
                        
                        idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == wybrany_prod][0]
                        st.session_state.produkty.at[idx, "Stan"] -= ilosc_wz
                        dodaj_ruch("WZ", nr_doc_wz, wybrany_prod, ilosc_wz, wybrany_klient)
                        st.session_state.wz_counter += 1
                        
                        font_path, font_bold_path = pobierz_czcionki()
                        
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.add_font("Roboto", "", font_path)
                        pdf.add_font("Roboto", "B", font_bold_path)
                        
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font("Roboto", "B", 15)
                        pdf.cell(0, 12, f"WYDANIE ZEWNĘTRZNE (WZ) NR {nr_doc_wz}", border=0, ln=1, align='C', fill=True)
                        
                        pdf.set_font("Roboto", "", 9)
                        pdf.set_text_color(100, 100, 100)
                        data_aktualna = datetime.now().strftime("%Y-%m-%d")
                        pdf.cell(0, 6, f"Data wydania: {data_aktualna}   |   Miejsce wystawienia: {MOJA_FIRMA['miejscowosc_wystawienia']}", border=0, ln=1, align='R')
                        pdf.set_text_color(0, 0, 0) 
                        pdf.ln(8)
                        
                        y_start = pdf.get_y()
                        
                        pdf.set_fill_color(248, 248, 248)
                        pdf.set_font("Roboto", "B", 10)
                        pdf.cell(90, 7, "  SPRZEDAWCA / WYSTAWCA", border=0, ln=1, fill=True)
                        pdf.set_font("Roboto", "", 9)
                        firma_tekst = f"{MOJA_FIRMA['nazwa']}\n{MOJA_FIRMA['adres']}\n{MOJA_FIRMA['nip']}\n{MOJA_FIRMA['kontakt']}"
                        pdf.multi_cell(90, 5, firma_tekst, border=0)
                        y_left = pdf.get_y()
                        
                        pdf.set_xy(105, y_start)
                        pdf.set_font("Roboto", "B", 10)
                        pdf.cell(90, 7, "  NABYWCA / ODBIORCA", border=0, ln=1, fill=True)
                        pdf.set_xy(105, y_start + 7)
                        pdf.set_font("Roboto", "", 9)
                        nip_czysty = f"NIP: {klient_nip}" if pd.notna(klient_nip) and str(klient_nip).strip() else ""
                        pdf.multi_cell(90, 5, f"{wybrany_klient}\n{klient_adres}\n{nip_czysty}", border=0)
                        y_right = pdf.get_y()
                        
                        pdf.set_y(max(y_left, y_right) + 12)
                        
                        pdf.set_font("Roboto", "B", 10)
                        pdf.cell(0, 8, "POZYCJE DOKUMENTU", border="B", ln=1)
                        pdf.ln(3)
                        
                        pdf.set_fill_color(230, 235, 245)
                        pdf.set_font("Roboto", "B", 9)
                        pdf.cell(15, 8, "Lp.", border=1, align='C', fill=True)
                        pdf.cell(115, 8, "Nazwa asortymentu", border=1, align='L', fill=True)
                        pdf.cell(30, 8, "Ilość", border=1, align='C', fill=True)
                        pdf.cell(30, 8, "Jm.", border=1, align='C', ln=1, fill=True)
                        
                        pdf.set_font("Roboto", "", 9)
                        pdf.cell(15, 8, "1", border=1, align='C')
                        pdf.cell(115, 8, wybrany_prod, border=1, align='L')
                        pdf.cell(30, 8, str(ilosc_wz), border=1, align='C')
                        pdf.cell(30, 8, "szt.", border=1, align='C', ln=1)
                        
                        pdf.ln(10)
                        if uwagi_doc.strip():
                            pdf.set_font("Roboto", "B", 9)
                            pdf.cell(15, 5, "Uwagi:", border=0)
                            pdf.set_font("Roboto", "", 9)
                            pdf.multi_cell(0, 5, uwagi_doc.strip(), border=0)
                        
                        pdf.ln(25)
                        y_sig = pdf.get_y()
                        
                        pdf.set_font("Roboto", "", 8.5)
                        pdf.set_xy(15, y_sig)
                        pdf.cell(60, 5, "..........................................................", align='C', ln=1)
                        pdf.set_x(15)
                        pdf.cell(60, 5, f"Wystawił: {st.session_state.aktualny_uzytkownik}", align='C')
                        
                        pdf.set_xy(135, y_sig)
                        pdf.cell(60, 5, "..........................................................", align='C', ln=1)
                        pdf.set_x(135)
                        pdf.cell(60, 5, "Odebrał (czytelny podpis)", align='C')
                        
                        pdf_bytes = bytes(pdf.output())
                        st.session_state.wygenerowane_pdf = pdf_bytes
                        safe_name = nr_doc_wz.replace('/', '_')
                        st.session_state.nazwa_pliku_wz = f"{safe_name}.pdf"
                        
                        st.rerun()
                    else:
                        st.error("Odrzucono: Niewystarczająca ilość asortymentu na magazynie.")

# ------------------------------------------
# ZAKŁADKA 5: PANEL ADMINA
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
                upr_magazyn = st.checkbox("Dostęp do Operacji Magazynowych (PZ/WZ) oraz CRM")
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
