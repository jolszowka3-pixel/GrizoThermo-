import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.request
from fpdf import FPDF

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# ==========================================
# DANE TWOJEJ FIRMY
# ==========================================
MOJA_FIRMA = {
    "nazwa": "GrizoThermo Sp. z o.o.",
    "adres": "ul. Fabryczna 14A\n44-100 Katowice",
    "nip": "NIP: 1234567890",
    "kontakt": "biuro@grizothermo.pl",
    "miejscowosc_wystawienia": "Katowice"
}

# ==========================================
# POBIERANIE CZCIONEK
# ==========================================
@st.cache_resource
def pobierz_czcionki():
    reg_path = "Roboto-Regular.ttf"
    bold_path = "Roboto-Bold.ttf"
    if not os.path.exists(reg_path):
        try:
            urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", reg_path)
        except: pass
    if not os.path.exists(bold_path):
        try:
            urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", bold_path)
        except: pass
    return reg_path, bold_path

# ==========================================
# 1. INICJALIZACJA BAZY 
# ==========================================
if 'init_v19' not in st.session_state:
    st.session_state.init_v19 = True
    st.session_state.wz_counter = 1
    
    st.session_state.uzytkownicy = {
        "admin": {
            "haslo": "admin123", 
            "imie": "Kierownik Magazynu",
            "uprawnienia": {"produkcja": True, "pz": True, "wz": True, "admin": True}
        }
    }
    
    st.session_state.kontrahenci = pd.DataFrame([
        {"Nazwa": "Hurtownia Surowców ALUSTAR", "NIP": "1112223344", "Adres": "ul. Hutnicza 10, 40-001 Katowice", "Typ": "Dostawca"},
        {"Nazwa": "Chemia Przemysłowa Sp. z o.o.", "NIP": "9998887766", "Adres": "ul. Barwna 5, 01-234 Warszawa", "Typ": "Dostawca"},
        {"Nazwa": "Bud-Max Materiały Budowlane", "NIP": "5554443322", "Adres": "ul. Wrocławska 100, 30-001 Kraków", "Typ": "Odbiorca"}
    ])
    
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    
    st.session_state.komponenty = pd.DataFrame([
        {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb", "Min_Stan": 1000.0},
        {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg", "Min_Stan": 5.0},
        {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg", "Min_Stan": 3.0}
    ])
    
    st.session_state.polprodukty = pd.DataFrame([
        {"ID": "P01", "Nazwa": "Rolka Jumbo (115cm x 13mb)", "Stan": 0, "Jednostka": "szt."}
    ])
    
    szerokosci = [10, 15, 20, 25, 30, 35, 115]
    warianty_wykonczenia = ["Oklejona", "Nieoklejona"]
    produkty_list = []
    
    for szer in szerokosci:
        for war in warianty_wykonczenia:
            nazwa_produktu = f"GrizoThermo+ {szer}cm - {war} (13mb)"
            produkty_list.append({
                "Wariant": nazwa_produktu,
                "Stan": 0,
                "Szerokosc": szer
            })
            
    st.session_state.produkty = pd.DataFrame(produkty_list)
    
    st.session_state.receptura_baza = {"K01": 13.00, "K02": 0.195, "K03": 0.104}
    
    st.session_state.historia = pd.DataFrame(columns=[
        "Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Użytkownik", "Kontrahent"
    ])

def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent="-"):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ, "Dokument": dokument, "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc, "Użytkownik": uzytkownik, "Kontrahent": kontrahent
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

# Profesjonalny, oczyszczony styl CSS dla kafelków
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .metric-card { background-color: #ffffff; border-radius: 6px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; } 
        .item-card { background-color: #ffffff; border-radius: 6px; padding: 16px; margin-bottom: 12px; border: 1px solid #e5e7eb; border-left: 4px solid #1e40af; }
        .item-card-purple { border-left: 4px solid #4b5563; }
        .item-card-alert { border-left: 4px solid #dc2626; }
        .item-card-ok { border-left: 4px solid #16a34a; }
        .card-title { font-size: 1.05rem; font-weight: 600; color: #111827; margin-bottom: 4px; }
        .card-details { font-size: 0.9rem; color: #6b7280; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# EKRAN LOGOWANIA
# ==========================================
if not st.session_state.zalogowany:
    st.markdown("<h1 style='text-align: center; color: #1e40af;'>GrizoThermo+ | Logowanie</h1>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("logowanie"):
            login = st.text_input("Identyfikator użytkownika")
            haslo = st.text_input("Hasło", type="password")
            if st.form_submit_button("Zaloguj do systemu", use_container_width=True):
                login = login.strip()
                if login in st.session_state.uzytkownicy and st.session_state.uzytkownicy[login]["haslo"] == haslo:
                    st.session_state.zalogowany = True
                    st.session_state.aktualny_uzytkownik = st.session_state.uzytkownicy[login]["imie"]
                    st.session_state.aktualne_uprawnienia = st.session_state.uzytkownicy[login]["uprawnienia"]
                    st.rerun()
                else: st.error("Nieprawidłowy login lub hasło.")
    st.stop()

# ==========================================
# MENU
# ==========================================
st.sidebar.title("Nawigacja")
st.sidebar.info(f"Zalogowano jako:\n**{st.session_state.aktualny_uzytkownik}**")
if st.sidebar.button("Wyloguj", use_container_width=True):
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    st.rerun()

st.sidebar.divider()
opcje = ["Pulpit Główny"]
if st.session_state.aktualne_uprawnienia.get("produkcja"): opcje.append("Moduł Production")
if st.session_state.aktualne_uprawnienia.get("pz"): opcje.append("Przyjęcie Towaru (PZ)")
if st.session_state.aktualne_uprawnienia.get("wz"): opcje.append("Wydanie Towaru (WZ)")
if st.session_state.aktualne_uprawnienia.get("pz") or st.session_state.aktualne_uprawnienia.get("wz"): opcje.append("Baza Kontrahentów (CRM)")
if st.session_state.aktualne_uprawnienia.get("admin"): opcje.append("Panel Administracyjny")

menu = st.sidebar.radio("Wybierz moduł:", opcje)

# ==========================================
# MODUŁY
# ==========================================
if menu == "Pulpit Główny":
    st.header("Pulpit Zarządzania: GrizoThermo+")
    colA, colB = st.columns(2)
    colA.metric("STAN MAGAZYNU (SUMA GOTOWYCH ROLEK)", f"{int(st.session_state.produkty['Stan'].sum())} szt.")
    colB.metric("MATERIAŁ DO KONFEKCJI (ROLKA JUMBO)", f"{int(st.session_state.polprodukty.loc[0, 'Stan'])} szt.")
    
    st.divider()
    tab_prod, tab_polprod, tab_komp, tab_hist = st.tabs(["Wyroby Gotowe", "Półprodukty", "Surowce", "Historia Operacji"])
    
    with tab_prod:
        pokaz_wszystkie = st.checkbox("Pokaż warianty z zerowym stanem", value=True)
        for _, row in st.session_state.produkty.iterrows():
            if row['Stan'] > 0 or pokaz_wszystkie:
                st.markdown(f'<div class="item-card"><div class="card-title">{row["Wariant"]}</div><div class="card-details">Stan magazynu: {int(row["Stan"])} szt.</div></div>', unsafe_allow_html=True)

    with tab_polprod:
        row_p = st.session_state.polprodukty.iloc[0]
        st.markdown(f'<div class="item-card item-card-purple"><div class="card-title">{row_p["Nazwa"]}</div><div class="card-details">Stan magazynu: {int(row_p["Stan"])} szt.</div></div>', unsafe_allow_html=True)

    with tab_komp:
        for _, row in st.session_state.komponenty.iterrows():
            alert = "item-card-alert" if row['Stan'] <= row['Min_Stan'] else "item-card-ok"
            status_txt = "Niski stan" if row['Stan'] <= row['Min_Stan'] else "W normie"
            st.markdown(f'<div class="item-card {alert}"><div class="card-title">{row["Nazwa"]}</div><div class="card-details">Stan: {row["Stan"]:g} {row["Jednostka"]} ({status_txt})</div></div>', unsafe_allow_html=True)

    with tab_hist:
        st.dataframe(st.session_state.historia.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True)

elif menu == "Moduł Production":
    st.header("Zarządzanie Produkcją")
    tab1, tab2 = st.tabs(["KROK 1: Maszyna Główna", "KROK 2: Konfekcja"])
    
    with tab1:
        st.subheader("Wytłaczanie Rolek Jumbo (115cm x 13mb)")
        s_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
        s_bialy = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
        s_zielony = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]

        m_alu = int(s_alu / st.session_state.receptura_baza["K01"])
        m_bia = int(s_bialy / st.session_state.receptura_baza["K02"])
        m_zie = int(s_zielony / st.session_state.receptura_baza["K03"])
        m_jumbo = min(m_alu, m_bia, m_zie)

        c1, c2, c3 = st.columns(3)
        c1.metric("Aluminium wystarczy na:", f"{m_alu} szt.")
        c2.metric("Barwnik biały wystarczy na:", f"{m_bia} szt.")
        c3.metric("Barwnik zielony wystarczy na:", f"{m_zie} szt.")
        
        st.divider()
        
        if m_jumbo > 0:
            st.info(f"Z obecnych surowców możesz maksymalnie wytłoczyć: {m_jumbo} szt. Rolek Jumbo.")
            with st.form("prod_jumbo"):
                ile_jumbo = st.number_input("Ile Rolek Jumbo wyprodukowano?", min_value=1, max_value=m_jumbo, value=1)
                if st.form_submit_button("Zaksięguj produkcję z Maszyny Głównej"):
                    st.session_state.polprodukty.at[0, "Stan"] += ile_jumbo
                    nazwa_p = st.session_state.polprodukty.at[0, "Nazwa"]
                    dodaj_ruch("PW (Półprod.)", "Hala Główna", nazwa_p, ile_jumbo, "Wytłaczarka")
                    
                    for k_id, zuzycie in st.session_state.receptura_baza.items():
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                        st.session_state.komponenty.at[idx, "Stan"] -= (zuzycie * ile_jumbo)
                        dodaj_ruch("RW", "Hala Główna", st.session_state.komponenty.at[idx, "Nazwa"], zuzycie * ile_jumbo, "Wytłaczarka")
                    st.success("Produkcja została pomyślnie zaksięgowana.")
                    st.rerun()
        else:
            st.error("Brak wystarczających surowców na pełną rolkę Jumbo.")

    with tab2:
        st.subheader("Konfekcja (Rozkrój bez odpadu)")
        s_jumbo = int(st.session_state.polprodukty.at[0, "Stan"])
        
        if s_jumbo > 0:
            st.info(f"Dostępny zapas do cięcia: {s_jumbo} szt. rolek Jumbo.")
            ile_tniemy = st.number_input("Ile rolek Jumbo bierzesz do cięcia z magazynu?", min_value=1, max_value=s_jumbo, value=1)
            wymagane_cm = ile_tniemy * 115
            st.markdown(f"Pocięcie {ile_tniemy} szt. Jumbo daje łącznie **{wymagane_cm} cm** szerokości.")
            
            c_okl, c_nie = st.columns(2)
            rozkroj = {}
            for idx, r in st.session_state.produkty.iterrows():
                with c_nie if "Nieoklejona" in r['Wariant'] else c_okl:
                    rozkroj[idx] = st.number_input(r['Wariant'], min_value=0, value=0, key=f"r_{idx}")
                    
            zuzyte_cm = sum(rozkroj[idx] * st.session_state.produkty.at[idx, 'Szerokosc'] for idx in rozkroj)
            
            st.divider()
            
            if zuzyte_cm == wymagane_cm:
                st.success(f"Suma szerokości: {zuzyte_cm} cm / {wymagane_cm} cm. Rozkrój idealny. Brak odpadu.")
                if st.button("Zatwierdź rozkrój i zaktualizuj magazyny"):
                    st.session_state.polprodukty.at[0, "Stan"] -= ile_tniemy
                    dodaj_ruch("RW (Półprod.)", "Stanowisko Cięcia", "Rolka Jumbo (115cm x 13mb)", ile_tniemy, "Konfekcja")
                    for idx, ilosc in rozkroj.items():
                        if ilosc > 0:
                            st.session_state.produkty.at[idx, "Stan"] += ilosc
                            dodaj_ruch("PW (Gotowe)", "Stanowisko Cięcia", st.session_state.produkty.at[idx, "Wariant"], ilosc, "Konfekcja")
                    st.success("Rozkrój pomyślnie zapisany w bazie.")
                    st.rerun()
            elif zuzyte_cm < wymagane_cm:
                st.warning(f"Suma szerokości wynosi {zuzyte_cm} cm. Rozdysponuj jeszcze {wymagane_cm - zuzyte_cm} cm.")
            else:
                st.error(f"Suma szerokości wynosi {zuzyte_cm} cm. Przekroczono limit o {zuzyte_cm - wymagane_cm} cm!")
        else:
            st.warning("Brak rolek Jumbo na magazynie. Wyprodukuj je w Kroku 1.")

elif menu == "Baza Kontrahentów (CRM)":
    st.header("Baza Kontrahentów")
    zm = st.data_editor(st.session_state.kontrahenci, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("Zapisz zmiany w Bazie Kontrahentów"):
        st.session_state.kontrahenci = zm
        st.success("Baza została zaktualizowana.")
        st.rerun()

elif menu == "Przyjęcie Towaru (PZ)":
    st.header("Przyjęcie Zewnętrzne (PZ)")
    dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]["Nazwa"].tolist()
    if not dostawcy:
        st.error("Brak dostawców w bazie danych CRM.")
    else:
        with st.form("pz"):
            n = st.text_input("Numer dokumentu (np. nr faktury zakupu)")
            d = st.selectbox("Dostawca surowca", dostawcy)
            k = st.selectbox("Wybierz surowiec", st.session_state.komponenty["Nazwa"].tolist())
            i = st.number_input("Ilość przyjmowana", min_value=0.1, value=100.0)
            if st.form_submit_button("Zatwierdź dokument PZ"):
                idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == k][0]
                st.session_state.komponenty.at[idx, "Stan"] += i
                dodaj_ruch("PZ", n, k, i, d)
                st.success("Zapisano przyjęcie zewnętrzne.")
                st.rerun()

elif menu == "Wydanie Towaru (WZ)":
    st.header("Wydanie Zewnętrzne (WZ)")
    odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
    
    if "wygenerowane_pdf" in st.session_state:
        st.success("Transakcja zaksięgowana. Dokument gotowy do pobrania.")
        c1, c2 = st.columns(2)
        c1.download_button("Pobierz dokument WZ (.pdf)", data=st.session_state.wygenerowane_pdf, file_name=st.session_state.nazwa_pliku_wz, mime="application/pdf", use_container_width=True)
        if c2.button("Wystaw nowy dokument WZ", use_container_width=True):
            del st.session_state.wygenerowane_pdf
            del st.session_state.nazwa_pliku_wz
            st.rerun()
            
    elif not odbiorcy:
        st.warning("Brak odbiorców w bazie danych CRM.")
    else:
        dostepne_produkty = st.session_state.produkty[st.session_state.produkty["Stan"] > 0].copy()
        
        if dostepne_produkty.empty:
            st.error("Brak gotowych produktów na magazynie! Wykonaj rozkrój z rolki Jumbo w module Produkcji.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            
            with st.form("wz_form"):
                st.subheader("1. Dane Odbiorcy i Dokumentu")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    nr_doc_wz = st.text_input("Numer dokumentu (Auto)", value=nr_wz_auto, disabled=True)
                    wybrany_klient = st.selectbox("Nabywca (Wybierz z bazy)", odbiorcy)
                with col_f2:
                    uwagi_doc = st.text_input("Uwagi do dokumentu", value="Dostawa z magazynu głównego.")
                    
                st.divider()
                st.subheader("2. Koszyk Wydania: Zaznacz produkty i ilości")
                
                df_do_edycji = dostepne_produkty[["Wariant", "Stan"]].copy()
                df_do_edycji["Wydajemy (szt.)"] = 0
                
                zmienione_dane = st.data_editor(
                    df_do_edycji,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Wariant": st.column_config.TextColumn("Nazwa asortymentu", disabled=True),
                        "Stan": st.column_config.NumberColumn("Dostępne na magazynie", disabled=True),
                        "Wydajemy (szt.)": st.column_config.NumberColumn("Ilość do wydania", min_value=0, step=1)
                    }
                )

                if st.form_submit_button("Zatwierdź wydanie i generuj PDF"):
                    wybrane_do_wydania = zmienione_dane[zmienione_dane["Wydajemy (szt.)"] > 0]
                    bledy = False
                    
                    if wybrane_do_wydania.empty:
                        st.error("Wprowadź ilość większą niż 0 dla przynajmniej jednego produktu.")
                        bledy = True
                    
                    for _, row in wybrane_do_wydania.iterrows():
                        if row["Wydajemy (szt.)"] > row["Stan"]:
                            st.error(f"Niewystarczający zapas dla wariantu '{row['Wariant']}'. Dostępne: {int(row['Stan'])} szt.")
                            bledy = True
                            
                    if not bledy:
                        dane_klienta = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] == wybrany_klient].iloc[0]
                        klient_adres = dane_klienta["Adres"]
                        klient_nip = dane_klienta["NIP"]
                        
                        font_path, font_bold_path = pobierz_czcionki()
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.add_font("Roboto", "", font_path)
                        pdf.add_font("Roboto", "B", font_bold_path)
                        
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font("Roboto", "B", 15)
                        pdf.cell(0, 12, f"WYDANIE ZEWNĘTRZNE (WZ) NR {nr_wz_auto}", border=0, ln=1, align='C', fill=True)
                        
                        pdf.set_font("Roboto", "", 9)
                        pdf.set_text_color(100, 100, 100)
                        pdf.cell(0, 6, f"Data wydania: {datetime.now().strftime('%Y-%m-%d')}   |   Miejsce wystawienia: {MOJA_FIRMA['miejscowosc_wystawienia']}", border=0, ln=1, align='R')
                        pdf.set_text_color(0, 0, 0) 
                        pdf.ln(8)
                        
                        y_start = pdf.get_y()
                        pdf.set_fill_color(248, 248, 248)
                        pdf.set_font("Roboto", "B", 10)
                        pdf.cell(90, 7, "  SPRZEDAWCA / WYSTAWCA", border=0, ln=1, fill=True)
                        pdf.set_font("Roboto", "", 9)
                        pdf.multi_cell(90, 5, f"{MOJA_FIRMA['nazwa']}\n{MOJA_FIRMA['adres']}\n{MOJA_FIRMA['nip']}\n{MOJA_FIRMA['kontakt']}", border=0)
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
                        
                        lp = 1
                        for _, row in wybrane_do_wydania.iterrows():
                            nazwa_w = row["Wariant"]
                            ile_w = int(row["Wydajemy (szt.)"])
                            
                            pdf.cell(15, 8, str(lp), border=1, align='C')
                            pdf.cell(115, 8, nazwa_w, border=1, align='L')
                            pdf.cell(30, 8, str(ile_w), border=1, align='C')
                            pdf.cell(30, 8, "szt.", border=1, align='C', ln=1)
                            
                            idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_w][0]
                            st.session_state.produkty.at[idx, "Stan"] -= ile_w
                            
                            dodaj_ruch("WZ", nr_wz_auto, nazwa_w, ile_w, wybrany_klient)
                            lp += 1
                        
                        st.session_state.wz_counter += 1
                        
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
                        
                        st.session_state.wygenerowane_pdf = bytes(pdf.output())
                        st.session_state.nazwa_pliku_wz = f"{nr_wz_auto.replace('/', '_')}.pdf"
                        st.rerun()

elif menu == "Panel Administracyjny":
    st.header("Narzędzia Administracyjne")
    tab_uzytkownicy, tab_korekt_surowce, tab_korekt_prod = st.tabs(["Konta Użytkowników", "Korekta Surowców", "Korekta Wyrobów Gotowych"])
    
    with tab_uzytkownicy:
        st.write("Wprowadź dane, aby wygenerować profil pracownika.")
        with st.form("dodaj_uzytkownika"):
            c1, c2 = st.columns(2)
            login = c1.text_input("Login")
            imie = c1.text_input("Imię i Nazwisko")
            haslo = c1.text_input("Hasło startowe", type="password")
            
            u_prod = c2.checkbox("Moduł Produkcji")
            u_pz = c2.checkbox("Przyjęcia PZ")
            u_wz = c2.checkbox("Wydania WZ oraz CRM")
            u_admin = c2.checkbox("Panel Administracyjny")
            
            if st.form_submit_button("Utwórz konto"):
                if login and haslo and imie:
                    st.session_state.uzytkownicy[login.strip()] = {
                        "haslo": haslo, "imie": imie,
                        "uprawnienia": {"produkcja": u_prod, "pz": u_pz, "wz": u_wz, "admin": u_admin}
                    }
                    st.success("Konto zostało pomyślnie utworzone.")
                    st.rerun()
                else: st.error("Wszystkie pola formularza są wymagane.")

    with tab_korekt_surowce:
        zm_k = st.data_editor(st.session_state.komponenty, hide_index=True, use_container_width=True)
        if st.button("Zapisz korektę surowców"):
            st.session_state.komponenty = zm_k
            st.success("Korekta surowców pomyślnie zapisana.")
            st.rerun()

    with tab_korekt_prod:
        zm_p = st.data_editor(st.session_state.produkty, hide_index=True, use_container_width=True)
        if st.button("Zapisz korektę produktów gotowych"):
            st.session_state.produkty = zm_p
            st.success("Korekta wyrobów gotowych pomyślnie zapisana.")
            st.rerun()
