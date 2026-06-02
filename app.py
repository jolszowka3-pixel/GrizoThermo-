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
# 1. INICJALIZACJA BAZY (WERSJA V26)
# ==========================================
if 'init_v26' not in st.session_state:
    st.session_state.init_v26 = True
    st.session_state.wz_counter = 1
    st.session_state.jumbo_counter = 1
    st.session_state.konf_counter = 1
    
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
        {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb"},
        {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg"},
        {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg"}
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
    st.session_state.receptura_baza = {"K01": 32.00, "K02": 0.200, "K03": 0.100}
    
    st.session_state.historia = pd.DataFrame(columns=[
        "Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Użytkownik", "Kontrahent"
    ])
    
    st.session_state.archiwum_wz_pdf = []
    st.session_state.archiwum_jumbo_pdf = []
    st.session_state.archiwum_konf_pdf = []

def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent="-"):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ, "Dokument": dokument, "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc, "Użytkownik": uzytkownik, "Kontrahent": kontrahent
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

# CSS Corporate Style
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
opcje = ["Pulpit Główny", "Stan Magazynu"]
if st.session_state.aktualne_uprawnienia.get("produkcja"): opcje.append("Moduł Production")
if st.session_state.aktualne_uprawnienia.get("pz"): opcje.append("Przyjęcie Towaru (PZ)")
if st.session_state.aktualne_uprawnienia.get("wz"): opcje.append("Wydanie Towaru (WZ)")
if st.session_state.aktualne_uprawnienia.get("pz") or st.session_state.aktualne_uprawnienia.get("wz"):
    opcje.append("Baza Kontrahentów (CRM)")
    opcje.append("Archiwum Dokumentów")
if st.session_state.aktualne_uprawnienia.get("admin"): opcje.append("Panel Administracyjny")

menu = st.sidebar.radio("Wybierz moduł:", opcje)

# ==========================================
# MODUŁ 1: PULPIT GŁÓWNY (DASHBOARD)
# ==========================================
if menu == "Pulpit Główny":
    st.header("Pulpit Zarządzania: GrizoThermo+")
    st.write("Podsumowanie operacyjne i statystyki krytyczne przedsiębiorstwa.")
    
    # Obliczenia do KPI
    suma_gotowych = int(st.session_state.produkty["Stan"].sum())
    stan_jumbo = int(st.session_state.polprodukty.loc[0, "Stan"])
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    liczba_wz = len(st.session_state.archiwum_wz_pdf)

    # Siatka wskaźników
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("WYROBY GOTOWE (SUMA)", f"{suma_gotowych} szt.")
    col_kpi2.metric("ROLKI JUMBO NA STANIE", f"{stan_jumbo} szt.")
    col_kpi3.metric("ZAPAS ALUMINIUM", f"{stan_alu:g} mb")
    col_kpi4.metric("WYSTAWIONE DOKUMENTY WZ", f"{liczba_wz} szt.")
    
    st.divider()
    
    # Wykrywanie i alerty braków surowcowych
    braki_surowcowe = []
    for _, row_k in st.session_state.komponenty.iterrows():
        prog_alarmowy = st.session_state.receptura_baza.get(row_k['ID'], 0) * 20
        if row_k['Stan'] < prog_alarmowy:
            niedobor = prog_alarmowy - row_k['Stan']
            braki_surowcowe.append(f"{row_k['Nazwa']} (Aktualnie: {row_k['Stan']:g} {row_k['Jednostka']}, Deficyt: {niedobor:g} {row_k['Jednostka']})")
            
    if braki_surowcowe:
        st.error("ALERT: Krytyczny poziom surowców produkcyjnych\n\nBieżący stan magazynowy poniżej uniemożliwia realizację partii 20 sztuk rolek Jumbo:\n\n" + "\n".join([f"* {b}" for b in braki_surowcowe]))
    else:
        st.success("Wszystkie surowce bazowe zabezpieczają minimum produkcyjne na 20 sztuk rolek Jumbo.")

    # Układ dwukolumnowy dolny: Wykres i Ostatnie Ruchy
    st.write("")
    col_dash1, col_dash2 = st.columns([2, 3])
    
    with col_dash1:
        st.subheader("Porównanie Stanu Surowców")
        # Generowanie prostego wykresu Streamlit dla surowców
        df_chart = st.session_state.komponenty[["Nazwa", "Stan"]].set_index("Nazwa")
        st.bar_chart(df_chart, y="Stan", color="#1e40af")
        
    with col_dash2:
        st.subheader("Ostatnie Operacje Systemowe")
        if st.session_state.historia.empty:
            st.info("Brak zarejestrowanych zdarzeń w bieżącej sesji.")
        else:
            st.dataframe(
                st.session_state.historia.sort_values(by="Data", ascending=False).head(5),
                use_container_width=True,
                hide_index=True
            )

# ==========================================
# MODUŁ 2: STAN MAGAZYNU (WYDZIELONY)
# ==========================================
elif menu == "Stan Magazynu":
    st.header("Ewidencja Stanów Magazynowych")
    st.write("Podgląd fizycznego asortymentu, półproduktów oraz komponentów w przedsiębiorstwie.")
    
    tab_prod, tab_polprod, tab_komp = st.tabs([
        "Magazyn Wyrobów Gotowych", 
        "Magazyn Półproduktów (Jumbo)", 
        "Magazyn Surowców Bazowych"
    ])
    
    with tab_prod:
        pokaz_wszystkie = st.checkbox("Wyświetl warianty z zerowym stanem magazynowym", value=True)
        st.write("")
        for _, row in st.session_state.produkty.iterrows():
            if row['Stan'] > 0 or pokaz_wszystkie:
                st.markdown(f'<div class="item-card"><div class="card-title">{row["Wariant"]}</div><div class="card-details">Szerokość handlowa: {row["Szerokosc"]} cm | Stan: {int(row["Stan"])} szt.</div></div>', unsafe_allow_html=True)

    with tab_polprod:
        st.write("")
        row_p = st.session_state.polprodukty.iloc[0]
        st.markdown(f'<div class="item-card item-card-purple"><div class="card-title">{row_p["Nazwa"]}</div><div class="card-details">Przeznaczenie: Surowiec do rozkroju wzdłużnego | Stan: {int(row_p["Stan"])} szt.</div></div>', unsafe_allow_html=True)

    with tab_komp:
        st.write("")
        for _, row in st.session_state.komponenty.iterrows():
            prog_alarmowy = st.session_state.receptura_baza.get(row['ID'], 0) * 20
            jest_malo = row['Stan'] < prog_alarmowy
            
            alert = "item-card-alert" if jest_malo else "item-card-ok"
            status_txt = "Niski stan" if jest_malo else "Zabezpieczony"
            st.markdown(f'<div class="item-card {alert}"><div class="card-title">{row["Nazwa"]}</div><div class="card-details">Stan bieżący: {row["Stan"]:g} {row["Jednostka"]} | Status operacyjny: {status_txt} (Minimum na 20 szt. Jumbo: {prog_alarmowy:g} {row["Jednostka"]})</div></div>', unsafe_allow_html=True)

# ==========================================
# MODUŁ 3: PRODUKCJA (DWUETAPOWA Z RAPORTAMI PDF)
# ==========================================
elif menu == "Moduł Production":
    st.header("Zarządzanie Produkcją")
    tab1, tab2 = st.tabs(["KROK 1: Maszyna Główna", "KROK 2: Konfekcja"])
    
    if "ostatnia_produkcja_pdf" in st.session_state:
        st.success(f"Zaksięgowano pomyślnie raport: {st.session_state.nazwa_pliku_produkcji}")
        st.download_button(
            label="Pobierz wygenerowaną kartę procesu (.pdf)",
            data=st.session_state.ostatnia_produkcja_pdf,
            file_name=st.session_state.nazwa_pliku_produkcji,
            mime="application/pdf",
            use_container_width=True
        )
        st.divider()
    
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
        c1.metric("Aluminium wystarczy na:", f"{m_alu} szt. Jumbo")
        c2.metric("Barwnik biały wystarczy na:", f"{m_bia} szt. Jumbo")
        c3.metric("Barwnik zielony wystarczy na:", f"{m_zie} szt. Jumbo")
        
        st.divider()
        
        if m_jumbo > 0:
            st.info(f"Z obecnych surowców możesz maksymalnie wytłoczyć: {m_jumbo} szt. Rolek Jumbo.")
            with st.form("prod_jumbo"):
                ile_jumbo = st.number_input("Ile Rolek Jumbo wyprodukowano?", min_value=1, max_value=m_jumbo, value=1)
                if st.form_submit_button("Zaksięguj produkcję z Maszyny Głównej"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                    
                    st.session_state.polprodukty.at[0, "Stan"] += ile_jumbo
                    nazwa_p = st.session_state.polprodukty.at[0, "Nazwa"]
                    dodaj_ruch("PW (Półprod.)", nr_jmb_auto, nazwa_p, ile_jumbo, "Wytłaczarka")
                    
                    font_path, font_bold_path = pobierz_czcionki()
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.add_font("Roboto", "", font_path)
                    pdf.add_font("Roboto", "B", font_bold_path)
                    
                    pdf.set_fill_color(240, 240, 240)
                    pdf.set_font("Roboto", "B", 14)
                    pdf.cell(0, 12, f"KARTA PRZEBIEGU PRODUKCJI JUMBO: {nr_jmb_auto}", border=0, ln=1, align='C', fill=True)
                    
                    pdf.set_font("Roboto", "", 9)
                    pdf.cell(0, 6, f"Data zlecenia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}   |   Stanowisko: Wytłaczarka Główna", border=0, ln=1, align='C')
                    pdf.ln(8)
                    
                    pdf.set_font("Roboto", "B", 11)
                    pdf.cell(0, 6, "1. UZYSKANY ASORTYMENT", border="B", ln=1)
                    pdf.set_font("Roboto", "", 10)
                    pdf.cell(100, 8, f"Nazwa produktu: {nazwa_p}", ln=0)
                    pdf.cell(0, 8, f"Ilość: {ile_jumbo} szt.", ln=1)
                    pdf.ln(5)
                    
                    pdf.set_font("Roboto", "B", 11)
                    pdf.cell(0, 6, "2. ROZLICZENIE ZUŻYCIA SUROWCÓW BAZOWYCH", border="B", ln=1)
                    pdf.ln(2)
                    pdf.set_font("Roboto", "B", 9)
                    pdf.cell(15, 8, "Lp.", border=1, align='C')
                    pdf.cell(115, 8, "Nazwa surowca pobranego z magazynu", border=1, align='L')
                    pdf.cell(60, 8, "Ilość zużyta", border=1, align='C', ln=1)
                    pdf.set_font("Roboto", "", 9)
                    
                    lp_k = 1
                    for k_id, zuzycie in st.session_state.receptura_baza.items():
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                        laczne_zuzycie = zuzycie * ile_jumbo
                        st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                        dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Wytłaczarka")
                        
                        pdf.cell(15, 8, str(lp_k), border=1, align='C')
                        pdf.cell(115, 8, st.session_state.komponenty.at[idx, "Nazwa"], border=1, align='L')
                        pdf.cell(60, 8, f"{laczne_zuzycie:g} {st.session_state.komponenty.at[idx, 'Jednostka']}", border=1, align='C', ln=1)
                        lp_k += 1
                        
                    pdf.ln(25)
                    pdf.cell(95, 5, "..........................................................", align='C')
                    pdf.cell(95, 5, "..........................................................", align='C', ln=1)
                    pdf.cell(95, 5, "Zatwierdził (Operator)", align='C')
                    pdf.cell(95, 5, "Kierownik Produkcji", align='C', ln=1)
                    
                    pdf_bytes = bytes(pdf.output())
                    st.session_state.archiwum_jumbo_pdf.append({"id": nr_jmb_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ilosc": ile_jumbo, "pdf": pdf_bytes})
                    
                    st.session_state.jumbo_counter += 1
                    st.session_state.ostatnia_produkcja_pdf = pdf_bytes
                    st.session_state.nazwa_pliku_produkcji = f"{nr_jmb_auto.replace('/', '_')}.pdf"
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
                st.success(f"Suma szerokości wynosi {zuzyte_cm} cm. Rozkrój idealny.")
                if st.button("Zatwierdź rozkrój i zaktualizuj magazyny"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                    
                    st.session_state.polprodukty.at[0, "Stan"] -= ile_tniemy
                    dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", ile_tniemy, "Konfekcja")
                    
                    font_path, font_bold_path = pobierz_czcionki()
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.add_font("Roboto", "", font_path)
                    pdf.add_font("Roboto", "B", font_bold_path)
                    
                    pdf.set_fill_color(240, 240, 240)
                    pdf.set_font("Roboto", "B", 14)
                    pdf.cell(0, 12, f"KARTA ROZKROJU I KONFEKCJI: {nr_knf_auto}", border=0, ln=1, align='C', fill=True)
                    
                    pdf.set_font("Roboto", "", 9)
                    pdf.cell(0, 6, f"Data operacji: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}   |   Główny stół rozkroju", border=0, ln=1, align='C')
                    pdf.ln(6)
                    
                    pdf.set_font("Roboto", "B", 11)
                    pdf.cell(0, 6, "1. POBRANY MATERIAŁ WEJŚCIOWY", border="B", ln=1)
                    pdf.set_font("Roboto", "", 10)
                    pdf.cell(0, 8, f"Pobrano z magazynu: Rolka Jumbo (115cm x 13mb) - Ilość: {ile_tniemy} szt. (Łącznie: {wymagane_cm} cm)", ln=1)
                    pdf.ln(5)
                    
                    pdf.set_font("Roboto", "B", 11)
                    pdf.cell(0, 6, "2. REJESTR SKONFEKCJONOWANYCH PRODUKTÓW GOTOWYCH", border="B", ln=1)
                    pdf.ln(2)
                    pdf.set_font("Roboto", "B", 9)
                    pdf.cell(15, 8, "Lp.", border=1, align='C')
                    pdf.cell(125, 8, "Wariant gotowy (Szerokość / Wykończenie)", border=1, align='L')
                    pdf.cell(40, 8, "Ilość uzyskana", border=1, align='C', ln=1)
                    pdf.set_font("Roboto", "", 9)
                    
                    lp_k = 1
                    for idx, ilosc in rozkroj.items():
                        if ilosc > 0:
                            st.session_state.produkty.at[idx, "Stan"] += ilosc
                            wariant_nazwa = st.session_state.produkty.at[idx, "Wariant"]
                            dodaj_ruch("PW (Gotowe)", nr_knf_auto, wariant_nazwa, ilosc, "Konfekcja")
                            
                            pdf.cell(15, 8, str(lp_k), border=1, align='C')
                            pdf.cell(125, 8, wariant_nazwa, border=1, align='L')
                            pdf.cell(40, 8, f"{ilosc} szt.", border=1, align='C', ln=1)
                            lp_k += 1
                            
                    pdf.ln(25)
                    pdf.cell(95, 5, "..........................................................", align='C')
                    pdf.cell(95, 5, "..........................................................", align='C', ln=1)
                    pdf.cell(95, 5, "Konfekcjoner (Podpis)", align='C')
                    pdf.cell(95, 5, "Magazynier przyjmujący", align='C', ln=1)
                    
                    pdf_bytes = bytes(pdf.output())
                    st.session_state.archiwum_konf_pdf.append({"id": nr_knf_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "jumbo_szt": ile_tniemy, "pdf": pdf_bytes})
                    
                    st.session_state.konf_counter += 1
                    st.session_state.ostatnia_produkcja_pdf = pdf_bytes
                    st.session_state.nazwa_pliku_produkcji = f"{nr_knf_auto.replace('/', '_')}.pdf"
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
    
    if "wz_koszyk" not in st.session_state:
        st.session_state.wz_koszyk = []
    
    if "wygenerowane_pdf" in st.session_state:
        st.success(f"Zaksięgowano dokument: {st.session_state.nazwa_pliku_wz}")
        st.download_button(
            label="Pobierz dokument WZ (.pdf)", 
            data=st.session_state.wygenerowane_pdf, 
            file_name=st.session_state.nazwa_pliku_wz, 
            mime="application/pdf", 
            use_container_width=True
        )
        st.divider()
        
    if not odbiorcy:
        st.warning("Brak odbiorców w bazie danych CRM.")
    else:
        dostepne_produkty = st.session_state.produkty[st.session_state.produkty["Stan"] > 0].copy()
        
        if dostepne_produkty.empty and not st.session_state.wz_koszyk:
            st.error("Brak gotowych produktów na magazynie! Wykonaj rozkrój z rolki Jumbo w module Produkcji.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            
            st.subheader("1. Dane Odbiorcy i Dokumentu")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                wybrany_klient = st.selectbox("Nabywca (Wybierz z bazy)", odbiorcy)
            with col_f2:
                uwagi_doc = st.text_input("Uwagi do dokumentu", value="Dostawa z magazynu głównego.")
                
            st.divider()
            st.subheader("2. Dodaj produkty do wydania")
            
            opcje_list = []
            opcje_map = {}
            for _, r in dostepne_produkty.iterrows():
                wystepuje_w_koszyku = sum(item["Ilosc"] for item in st.session_state.wz_koszyk if item["Wariant"] == r["Wariant"])
                efektywny_stan = int(r["Stan"] - wystepuje_w_koszyku)
                
                if efektywny_stan > 0:
                    label = f"{r['Wariant']} (Dostępne: {efektywny_stan} szt.)"
                    opcje_list.append(label)
                    opcje_map[label] = (r["Wariant"], efektywny_stan)
            
            if not opcje_list:
                st.info("Wszystkie dostępne produkty zostały już rozdysponowane.")
            else:
                col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                with col_p1:
                    wybrana_opcja = st.selectbox("Wybierz asortyment z magazynu", opcje_list)
                
                prawdziwa_nazwa, max_dostepne = opcje_map[wybrana_opcja]
                
                with col_p2:
                    ile_wydac = st.number_input("Ilość do wydania", min_value=1, max_value=max_dostepne, value=1, step=1)
                    
                with col_p3:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Dodaj do dokumentu", use_container_width=True):
                        istnieje = False
                        for item in st.session_state.wz_koszyk:
                            if item["Wariant"] == prawdziwa_nazwa:
                                item["Ilosc"] += ile_wydac
                                istnieje = True
                                break
                        if not istnieje:
                            st.session_state.wz_koszyk.append({"Wariant": prawdziwa_nazwa, "Ilosc": ile_wydac})
                        st.rerun()

            if st.session_state.wz_koszyk:
                st.divider()
                st.subheader("3. Podsumowanie dokumentu WZ")
                
                df_koszyk = pd.DataFrame(st.session_state.wz_koszyk)
                df_koszyk.columns = ["Nazwa asortymentu", "Ilość do wydania (szt.)"]
                st.dataframe(df_koszyk, use_container_width=True, hide_index=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Wyczyść lista produktów", use_container_width=True):
                        st.session_state.wz_koszyk = []
                        st.rerun()
                with col_btn2:
                    if st.button("Zatwierdź wydanie i generuj PDF", type="primary", use_container_width=True):
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
                        for pozycja in st.session_state.wz_koszyk:
                            nazwa_w = pozycja["Wariant"]
                            ile_w = pozycja["Ilosc"]
                            
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
                        
                        pdf_bytes = bytes(pdf.output())
                        st.session_state.archiwum_wz_pdf.append({"id": nr_wz_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "kontrahent": wybrany_klient, "pdf": pdf_bytes})
                        
                        st.session_state.wygenerowane_pdf = pdf_bytes
                        st.session_state.nazwa_pliku_wz = f"{nr_wz_auto.replace('/', '_')}.pdf"
                        st.session_state.wz_koszyk = []
                        st.rerun()

# ==========================================
# ARCHIWUM DOKUMENTÓW (Z PEŁNYMI PLIKAMI PDF)
# ==========================================
elif menu == "Archiwum Dokumentów":
    st.header("Archiwum Dokumentów Operacyjnych i Technologicznych")
    
    tab_arch_wz, tab_arch_pz, tab_arch_jmb, tab_arch_knf = st.tabs([
        "Wydania Zewnętrzne (WZ)", 
        "Przyjęcia Zewnętrzne (PZ)", 
        "Produkcja - Wytłaczanie JUMBO", 
        "Produkcja - Konfekcja i Rozkrój"
    ])
    
    with tab_arch_wz:
        st.subheader("Rejestr Dokumentów WZ")
        if not st.session_state.archiwum_wz_pdf:
            st.info("Brak wystawionych dokumentów WZ w bazie danych.")
        else:
            df_wz = pd.DataFrame(st.session_state.archiwum_wz_pdf)[["id", "data", "kontrahent"]]
            st.dataframe(df_wz, use_container_width=True, hide_index=True, column_config={"id":"Numer dokumentu", "data":"Data wystawienia", "kontrahent":"Odbiorca"})
            
            lista_wz_id = [item["id"] for item in st.session_state.archiwum_wz_pdf]
            wybrane_wz_id = st.selectbox("Wybierz numer WZ do pobrania pliku PDF", lista_wz_id, key="sel_wz")
            
            wz_data_bytes = next(item["pdf"] for item in st.session_state.archiwum_wz_pdf if item["id"] == wybrane_wz_id)
            st.download_button(
                label=f"Pobierz dokument {wybrane_wz_id} (.pdf)",
                data=wz_data_bytes,
                file_name=f"{wybrane_wz_id.replace('/', '_')}.pdf",
                mime="application/pdf",
                key="btn_dl_wz"
            )

    with tab_arch_pz:
        st.subheader("Rejestr Dokumentów PZ")
        df_pz = st.session_state.historia[st.session_state.historia["Typ"] == "PZ"]
        if df_pz.empty:
            st.info("Brak zarejestrowanych dokumentów PZ w bazie.")
        else:
            st.dataframe(
                df_pz.sort_values(by="Data", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={"Data":"Data przyjęcia", "Dokument":"Numer PZ", "Produkt/Surowiec":"Surowiec", "Ilosc":"Ilość", "Kontrahent":"Dostawca"}
            )

    with tab_arch_jmb:
        st.subheader("Rejestr Procesów Wytłaczania (Krok 1)")
        if not st.session_state.archiwum_jumbo_pdf:
            st.info("Brak zarejestrowanych raportów z wytłaczarki Jumbo.")
        else:
            df_jmb = pd.DataFrame(st.session_state.archiwum_jumbo_pdf)[["id", "data", "ilosc"]]
            st.dataframe(df_jmb, use_container_width=True, hide_index=True, column_config={"id":"Numer zlecenia", "data":"Data produkcji", "ilosc":"Ilość rolek Jumbo"})
            
            lista_jmb_id = [item["id"] for item in st.session_state.archiwum_jumbo_pdf]
            wybrane_jmb_id = st.selectbox("Wybierz numer raportu Jumbo do pobrania PDF", lista_jmb_id, key="sel_jmb")
            
            jmb_data_bytes = next(item["pdf"] for item in st.session_state.archiwum_jumbo_pdf if item["id"] == wybrane_jmb_id)
            st.download_button(
                label=f"Pobierz Kartę Procesu {wybrane_jmb_id} (.pdf)",
                data=jmb_data_bytes,
                file_name=f"{wybrane_jmb_id.replace('/', '_')}.pdf",
                mime="application/pdf",
                key="btn_dl_jmb"
            )

    with tab_arch_knf:
        st.subheader("Rejestr Procesów Konfekcjonowania i Rozkroju (Krok 2)")
        if not st.session_state.archiwum_konf_pdf:
            st.info("Brak zarejestrowanych raportów ze stanowiska rozkroju.")
        else:
            df_knf = pd.DataFrame(st.session_state.archiwum_konf_pdf)[["id", "data", "jumbo_szt"]]
            st.dataframe(df_knf, use_container_width=True, hide_index=True, column_config={"id":"Numer zlecenia rozkroju", "data":"Data operacji", "jumbo_szt":"Zużyte rolki Jumbo (szt.)"})
            
            lista_knf_id = [item["id"] for item in st.session_state.archiwum_konf_pdf]
            wybrane_knf_id = st.selectbox("Wybierz numer raportu konfekcji do pobrania PDF", lista_knf_id, key="sel_knf")
            
            knf_data_bytes = next(item["pdf"] for item in st.session_state.archiwum_konf_pdf if item["id"] == wybrane_knf_id)
            st.download_button(
                label=f"Pobierz Specyfikację Rozkroju {wybrane_knf_id} (.pdf)",
                data=knf_data_bytes,
                file_name=f"{wybrane_knf_id.replace('/', '_')}.pdf",
                mime="application/pdf",
                key="btn_dl_knf"
            )

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
