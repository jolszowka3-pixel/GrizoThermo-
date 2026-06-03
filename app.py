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
# 1. INICJALIZACJA BAZY (WERSJA V48)
# ==========================================
if 'init_v48' not in st.session_state:
    st.session_state.init_v48 = True
    st.session_state.wz_counter = 1
    st.session_state.jumbo_counter = 1
    st.session_state.konf_counter = 1
    st.session_state.okl_counter = 1
    st.session_state.zk_counter = 1
    
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
    st.session_state.log_jumbo = []
    st.session_state.log_konf = []
    st.session_state.log_okl = []
    
    st.session_state.wz_koszyk = []
    st.session_state.konf_koszyk = []
    st.session_state.zamowienia = []
    st.session_state.powiazane_zk = None
    st.session_state.wybrany_klient_wz = None

def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent="-"):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": typ, "Dokument": dokument, "Produkt/Surowiec": nazwa,
        "Ilosc": ilosc, "Użytkownik": uzytkownik, "Kontrahent": kontrahent
    }])
    st.session_state.historia = pd.concat([st.session_state.historia, nowy_ruch], ignore_index=True)

# CSS
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
if st.session_state.aktualne_uprawnienia.get("wz"): opcje.append("Zamówienia (ZK)")
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
    st.markdown("<h2 style='text-align: center; color: #1e3a8a; padding-bottom: 20px;'>🎛️ Centrum Dowodzenia: GrizoThermo+</h2>", unsafe_allow_html=True)
    
    suma_gotowych = int(st.session_state.produkty["Stan"].sum())
    stan_jumbo = int(st.session_state.polprodukty.loc[0, "Stan"])
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    oczekujace_zk = len([z for z in st.session_state.zamowienia if z["Status"] == "Oczekujące"])

    # 1. KAFELKI KPI (NOWY WYGLĄD)
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.markdown(f"""
        <div style="background-color:#eff6ff;padding:20px;border-radius:10px;border-left:5px solid #2563eb;box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <p style="margin:0;color:#1e3a8a;font-size:13px;font-weight:bold;text-transform:uppercase;">📦 Wyroby Gotowe</p>
            <h2 style="margin:0;color:#1e3a8a;font-size:32px;">{suma_gotowych} <span style="font-size:16px;">szt.</span></h2>
        </div>
        """, unsafe_allow_html=True)
        
    with col_kpi2:
        st.markdown(f"""
        <div style="background-color:#f5f3ff;padding:20px;border-radius:10px;border-left:5px solid #7c3aed;box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <p style="margin:0;color:#4c1d95;font-size:13px;font-weight:bold;text-transform:uppercase;">🧻 Półprodukt (Jumbo)</p>
            <h2 style="margin:0;color:#4c1d95;font-size:32px;">{stan_jumbo} <span style="font-size:16px;">szt.</span></h2>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi3:
        st.markdown(f"""
        <div style="background-color:#ecfdf5;padding:20px;border-radius:10px;border-left:5px solid #059669;box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <p style="margin:0;color:#064e3b;font-size:13px;font-weight:bold;text-transform:uppercase;">🛠️ Zapas Aluminium</p>
            <h2 style="margin:0;color:#064e3b;font-size:32px;">{stan_alu:g} <span style="font-size:16px;">mb</span></h2>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi4:
        st.markdown(f"""
        <div style="background-color:#fffbeb;padding:20px;border-radius:10px;border-left:5px solid #d97706;box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <p style="margin:0;color:#78350f;font-size:13px;font-weight:bold;text-transform:uppercase;">📋 Oczekujące ZK</p>
            <h2 style="margin:0;color:#78350f;font-size:32px;">{oczekujace_zk} <span style="font-size:16px;">zlec.</span></h2>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    # 2. ALERTY SUROWCOWE
    braki_surowcowe = []
    for _, row_k in st.session_state.komponenty.iterrows():
        prog_alarmowy = st.session_state.receptura_baza.get(row_k['ID'], 0) * 20
        if row_k['Stan'] < prog_alarmowy:
            niedobor = prog_alarmowy - row_k['Stan']
            braki_surowcowe.append(f"**{row_k['Nazwa']}** (Aktualnie: {row_k['Stan']:g} {row_k['Jednostka']}, brakuje: {niedobor:g} {row_k['Jednostka']})")
            
    if braki_surowcowe:
        st.error("⚠️ **KRYTYCZNY POZIOM ZAPASÓW:** Aktualny stan nie pozwala na płynną produkcję (wymagane minimum na 20 szt. Jumbo). Zleć zamówienie do dostawców na:")
        for b in braki_surowcowe:
            st.markdown(f"- {b}")
    else:
        st.success("✅ **STATUS MAGAZYNU BAZOWEGO:** Wszystkie surowce są zabezpieczone i gotowe do produkcji pełnych partii.")

    st.write("---")

    # 3. WYKRESY I HISTORIA
    col_dash1, col_dash2 = st.columns([1, 1])
    
    with col_dash1:
        st.subheader("📊 Stan Surowców Bazowych")
        df_chart = st.session_state.komponenty[["Nazwa", "Stan"]].set_index("Nazwa")
        st.bar_chart(df_chart, color="#2563eb")
        
        df_prod = st.session_state.produkty[st.session_state.produkty["Stan"] > 0]
        if not df_prod.empty:
            st.write("")
            st.subheader("📦 Najwięcej na magazynie (Wyroby Gotowe)")
            df_prod_chart = df_prod[["Wariant", "Stan"]].set_index("Wariant")
            st.bar_chart(df_prod_chart, color="#10b981")
        else:
            st.info("Brak gotowych produktów na magazynie. Hala czeka na produkcję!")
        
    with col_dash2:
        st.subheader("⏱️ Ostatnie Zdarzenia w Systemie")
        if st.session_state.historia.empty:
            st.info("Brak zarejestrowanych zdarzeń w bieżącej sesji.")
        else:
            st.dataframe(
                st.session_state.historia.sort_values(by="Data", ascending=False).head(12),
                use_container_width=True,
                hide_index=True
            )

# ==========================================
# MODUŁ 2: STAN MAGAZYNU
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
# MODUŁ ZAMÓWIENIA (ZK) 
# ==========================================
elif menu == "Zamówienia (ZK)":
    st.header("Zamówienia Klientów (ZK)")
    
    if "zk_pdf_do_pobrania" in st.session_state:
        st.success("Zestawienie wygenerowane pomyślnie. Pobierz dokument poniżej:")
        st.download_button(
            label="📥 Pobierz Zbiorczą Listę Zamówień (PDF)",
            data=st.session_state.zk_pdf_do_pobrania["data"],
            file_name=st.session_state.zk_pdf_do_pobrania["nazwa"],
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        if st.button("Ukryj powiadomienie", use_container_width=True):
            del st.session_state.zk_pdf_do_pobrania
            st.rerun()
        st.divider()

    tab_nowe, tab_lista, tab_wydruk = st.tabs(["Wprowadź Nowe Zamówienie", "Rejestr Zamówień", "Generuj Listę (PDF)"])

    with tab_nowe:
        st.subheader("Nowe Zamówienie ZK")
        odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
        if not odbiorcy:
            st.warning("Brak odbiorców w bazie. Przejdź do CRM.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_zk_auto = f"ZK/{data_dzis_str}/{st.session_state.zk_counter:03d}"
            
            with st.form("nowe_zk"):
                col_zk1, col_zk2 = st.columns(2)
                klient = col_zk1.selectbox("Klient zamawiający", odbiorcy)
                uwagi = col_zk2.text_input("Uwagi do zamówienia")
                
                st.write("Wprowadź ilości zamawianych produktów:")
                df_zk = st.session_state.produkty[["Wariant"]].copy()
                df_zk["Ilość (szt.)"] = 0
                
                zamawiane_dane = st.data_editor(
                    df_zk, hide_index=True, use_container_width=True,
                    column_config={
                        "Wariant": st.column_config.TextColumn("Nazwa asortymentu", disabled=True),
                        "Ilość (szt.)": st.column_config.NumberColumn("Zamawiana ilość", min_value=0, step=1)
                    }
                )
                
                if st.form_submit_button("Zarejestruj Zamówienie"):
                    pozycje = zamawiane_dane[zamawiane_dane["Ilość (szt.)"] > 0]
                    if pozycje.empty:
                        st.error("Musisz zamówić przynajmniej 1 produkt.")
                    else:
                        szczegoly = pozycje.to_dict('records')
                        st.session_state.zamowienia.append({
                            "id": nr_zk_auto,
                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "klient": klient,
                            "pozycje": szczegoly,
                            "uwagi": uwagi,
                            "Status": "Oczekujące"
                        })
                        st.session_state.zk_counter += 1
                        st.success(f"Zamówienie {nr_zk_auto} zostało przyjęte w systemie.")
                        st.rerun()

    with tab_lista:
        st.subheader("Bieżące Zamówienia")
        if not st.session_state.zamowienia:
            st.info("Brak zarejestrowanych zamówień.")
        else:
            for z in reversed(st.session_state.zamowienia):
                with st.expander(f"{z['id']} | {z['klient']} | Data: {z['data']} | Status: {z['Status']}"):
                    st.write(f"**Uwagi:** {z['uwagi']}")
                    st.table(pd.DataFrame(z["pozycje"]).set_index("Wariant"))
                    if z["Status"] == "Oczekujące":
                        if st.button("Ręcznie oznacz jako zrealizowane", key=f"btn_{z['id']}"):
                            z["Status"] = "Zrealizowane"
                            st.rerun()

    with tab_wydruk:
        st.subheader("Wydruk Zbiorczej Listy Zamówień")
        st.write("Generuj zestawienie wszystkich zarejestrowanych zamówień do celów ewidencyjnych.")
        if st.button("Generuj listę zamówień (PDF)", type="primary"):
            if not st.session_state.zamowienia:
                st.error("Brak zamówień do wygenerowania raportu.")
            else:
                font_path, font_bold_path = pobierz_czcionki()
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Roboto", "", font_path)
                pdf.add_font("Roboto", "B", font_bold_path)
                
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Roboto", "B", 14)
                pdf.cell(0, 12, "ZBIORCZA LISTA ZAMÓWIEŃ (ZK)", border=0, ln=1, align='C', fill=True)
                pdf.set_font("Roboto", "", 9)
                pdf.cell(0, 6, f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", border=0, ln=1, align='C')
                pdf.ln(6)
                
                for z in reversed(st.session_state.zamowienia):
                    pdf.set_font("Roboto", "B", 10)
                    pdf.set_fill_color(248, 248, 248)
                    pdf.cell(0, 8, f" {z['id']} | Klient: {z['klient']} | Status: {z['Status']}", border=1, ln=1, fill=True)
                    pdf.set_font("Roboto", "", 9)
                    for p in z['pozycje']:
                        pdf.cell(10, 6, "-", align='R')
                        pdf.cell(120, 6, p['Wariant'])
                        pdf.cell(40, 6, f"{p['Ilość (szt.)']} szt.", ln=1)
                    if z['uwagi']:
                        pdf.set_font("Roboto", "B", 8)
                        pdf.cell(10, 6, "")
                        pdf.cell(160, 6, f"Uwagi: {z['uwagi']}", ln=1)
                        pdf.set_font("Roboto", "", 9)
                    pdf.ln(3)
                
                st.session_state.zk_pdf_do_pobrania = {"nazwa": "Zbiorcza_Lista_Zamowien.pdf", "data": bytes(pdf.output())}
                st.rerun()

# ==========================================
# MODUŁ PRODUKCJI I PLANOWANIA ZAPOTRZEBOWANIA
# ==========================================
elif menu == "Moduł Production":
    st.header("Zarządzanie Produkcją i Planowanie")
    
    # SILNIK MRP
    oczekujace = [z for z in st.session_state.zamowienia if z["Status"] == "Oczekujące"]
    mrp_data = None
    
    if oczekujace:
        zapotrzebowanie = {}
        for z in oczekujace:
            for p in z["pozycje"]:
                wariant = p["Wariant"]
                zapotrzebowanie[wariant] = zapotrzebowanie.get(wariant, 0) + p["Ilość (szt.)"]
                
        braki_do_oklejenia = []
        braki_do_rozkroju = []
        
        szerokosci_baza = [10, 15, 20, 25, 30, 35, 115]
        for szer in szerokosci_baza:
            war_okl = f"GrizoThermo+ {szer}cm - Oklejona (13mb)"
            war_nie = f"GrizoThermo+ {szer}cm - Nieoklejona (13mb)"
            
            dem_okl = zapotrzebowanie.get(war_okl, 0)
            dem_nie = zapotrzebowanie.get(war_nie, 0)
            
            stock_okl = st.session_state.produkty[st.session_state.produkty["Wariant"] == war_okl]["Stan"].values[0]
            stock_nie = st.session_state.produkty[st.session_state.produkty["Wariant"] == war_nie]["Stan"].values[0]
            
            brakuje_okl = max(0, dem_okl - stock_okl)
            brakuje_nie = max(0, dem_nie - stock_nie)
            nadwyzka_nie = max(0, stock_nie - dem_nie)
            
            if brakuje_okl > 0:
                braki_do_oklejenia.append({"Wariant": war_okl, "Brak_szt": int(brakuje_okl), "Z_czego": war_nie})
            
            pokryte_z_mag_nieokl = min(brakuje_okl, nadwyzka_nie)
            do_wyciecia_łącznie = brakuje_nie + (brakuje_okl - pokryte_z_mag_nieokl)
            
            if do_wyciecia_łącznie > 0:
                braki_do_rozkroju.append({"Wariant": war_nie, "Brak_szt": int(do_wyciecia_łącznie), "Szerokosc": int(szer)})
        
        items_to_pack = []
        for b in braki_do_rozkroju:
            items_to_pack.extend([(b["Wariant"], b["Szerokosc"])] * b["Brak_szt"])
        
        items_to_pack.sort(key=lambda x: x[1], reverse=True)
        
        def is_valid_partial(used_cm, count):
            rem = 115 - used_cm
            c = 6 - count
            if rem == 0: return True
            if rem < 0: return False
            if c == 0: return False
            if rem == 5: return False
            if rem > 35 * c: return False
            return True

        plan_rolek = []
        while items_to_pack:
            rolka = {}
            used_cm = 0
            count = 0
            i = 0
            while i < len(items_to_pack):
                nazwa, szer = items_to_pack[i]
                if is_valid_partial(used_cm + szer, count + 1):
                    rolka[nazwa] = rolka.get(nazwa, 0) + 1
                    used_cm += szer
                    count += 1
                    items_to_pack.pop(i)
                    if used_cm == 115 or count == 6:
                        break
                else:
                    i += 1
                    
            while used_cm < 115:
                for pw in [35, 30, 25, 20, 15, 10]:
                    if is_valid_partial(used_cm + pw, count + 1):
                        pad_nazwa = f"GrizoThermo+ {pw}cm - Nieoklejona (13mb)"
                        rolka[pad_nazwa] = rolka.get(pad_nazwa, 0) + 1
                        used_cm += pw
                        count += 1
                        break
                
            plan_rolek.append(rolka)
        
        potrzeba_jumbo_calkowita = len(plan_rolek)
        s_jumbo_akt = int(st.session_state.polprodukty.at[0, "Stan"])
        brakuje_jumbo = max(0, potrzeba_jumbo_calkowita - s_jumbo_akt)
        
        req_alu = brakuje_jumbo * st.session_state.receptura_baza["K01"]
        req_bia = brakuje_jumbo * st.session_state.receptura_baza["K02"]
        req_zie = brakuje_jumbo * st.session_state.receptura_baza["K03"]
        
        stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
        stan_bia = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0]
        stan_zie = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0]
        gotowe_do_auto = (stan_alu >= req_alu and stan_bia >= req_bia and stan_zie >= req_zie)

        zliczone_szablony = {}
        for r in plan_rolek:
            klucz = str(dict(sorted(r.items())))
            if klucz not in zliczone_szablony:
                zliczone_szablony[klucz] = {"wzor": r, "ile": 1}
            else:
                zliczone_szablony[klucz]["ile"] += 1
                
        mrp_data = {
            "braki_okl": braki_do_oklejenia,
            "braki_nie": braki_do_rozkroju,
            "potrzeba_jmb": potrzeba_jumbo_calkowita,
            "s_jumbo_akt": s_jumbo_akt,
            "brakuje_jumbo": brakuje_jumbo,
            "req_alu": req_alu, "req_bia": req_bia, "req_zie": req_zie,
            "szablony": zliczone_szablony,
            "plan_rolek": plan_rolek,
            "gotowe_do_auto": gotowe_do_auto
        }

    # Powiadomienia operacyjne - ODPORNE NA BLOKADY
    if "plan_hali_do_pobrania" in st.session_state:
        st.success("Wygenerowano kompleksowy plan produkcji dla hali.")
        st.download_button(
            label="📥 Pobierz Plan dla Hali (PDF)",
            data=st.session_state.plan_hali_do_pobrania["data"],
            file_name=st.session_state.plan_hali_do_pobrania["nazwa"],
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        if st.button("Zamknij powiadomienie", use_container_width=True):
            del st.session_state.plan_hali_do_pobrania
            st.rerun()
        st.divider()

    tab_plan, tab_wydruk, tab1, tab2, tab3 = st.tabs(["Panel MRP (Analiza)", "Wydruk Planu dla Hali", "Krok 1: Wytłaczanie", "Krok 2: Rozkrój", "Krok 3: Oklejanie"])
    
    with tab_plan:
        st.subheader("Inteligentna Analiza Zapotrzebowania (MRP)")
        
        if not mrp_data:
            st.info("Brak oczekujących zamówień zlecających produkcję. Magazyn nie wymaga uzupełnień celowych.")
        else:
            if not mrp_data["braki_okl"] and not mrp_data["braki_nie"]:
                st.success("Masz wystarczającą ilość produktów na magazynie, aby zrealizować wszystkie bieżące zamówienia.")
            else:
                st.error("Wykryto braki asortymentu w stosunku do zamówień. Wymagane procesy produkcyjne.")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.write("**Wymagany KROK 2: Rozkrój Jumbo na (Nieoklejone)**")
                    if mrp_data["braki_nie"]: st.dataframe(pd.DataFrame(mrp_data["braki_nie"])[["Wariant", "Brak_szt"]], hide_index=True)
                    else: st.info("Brak potrzeb rozkroju.")
                with col_b2:
                    st.write("**Wymagany KROK 3: Oklejanie**")
                    if mrp_data["braki_okl"]: st.dataframe(pd.DataFrame(mrp_data["braki_okl"])[["Wariant", "Brak_szt"]], hide_index=True)
                    else: st.info("Brak potrzeb oklejania.")

                st.divider()
                st.subheader("Bilanse Wytłaczarki i Surowców (KROK 1)")
                if mrp_data["potrzeba_jmb"] > 0:
                    st.write(f"Do pocięcia potrzebujesz łącznie: **{mrp_data['potrzeba_jmb']} szt. rolek Jumbo**.")
                    st.write(f"Twój aktualny stan rolek Jumbo: **{mrp_data['s_jumbo_akt']} szt.**")

                if mrp_data["brakuje_jumbo"] > 0:
                    st.warning(f"Zlecenia wymagają wytłoczenia dodatkowych **{mrp_data['brakuje_jumbo']} szt.** rolek Jumbo na Maszynie Głównej.")
                    if mrp_data["gotowe_do_auto"]:
                        st.success("Magazyn surowców w pełni pokrywa zapotrzebowanie na wytłoczenie tych rolek.")
                    else:
                        st.error("BRAK SUROWCÓW do wytłoczenia potrzebnych rolek Jumbo! Należy wystawić zapotrzebowanie dla dostawców.")
                else:
                    if mrp_data["potrzeba_jmb"] > 0:
                        st.success("Posiadasz wystarczającą ilość rolek Jumbo na magazynie, aby przejść od razu do konfekcji.")

                if mrp_data["potrzeba_jmb"] > 0:
                    st.write("")
                    st.subheader("Zoptymalizowany Plan Konfekcji (KROK 2)")
                    for i, (_, dane) in enumerate(mrp_data["szablony"].items()):
                        wzor_txt = " | ".join([f"{qty}x {k.split(' - ')[0].replace('GrizoThermo+ ', '')}" for k, qty in dane["wzor"].items()])
                        st.markdown(f"**SZABLON {i+1}** (Użyj na **{dane['ile']} szt.** rolek Jumbo): {wzor_txt}")
                    
                st.divider()
                if mrp_data["gotowe_do_auto"]:
                    if st.button("Zleć i Zrealizuj Automatycznie w Systemie (Aktualizacja Stanów)", type="primary", use_container_width=True):
                        data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                        
                        # 1. AUTO WYTŁACZANIE
                        if mrp_data["brakuje_jumbo"] > 0:
                            bj = mrp_data["brakuje_jumbo"]
                            nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] += bj
                            dodaj_ruch("PW (Półprod.)", nr_jmb_auto, st.session_state.polprodukty.at[0, "Nazwa"], bj, "Auto-Planer")
                            
                            for k_id, zuzycie in st.session_state.receptura_baza.items():
                                idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                                laczne_zuzycie = zuzycie * bj
                                st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                                dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Auto-Planer")
                            
                            st.session_state.log_jumbo.append({"id": nr_jmb_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ilosc": bj})
                            st.session_state.jumbo_counter += 1
                            
                        # 2. AUTO ROZKRÓJ
                        if mrp_data["potrzeba_jmb"] > 0:
                            pj = mrp_data["potrzeba_jmb"]
                            nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] -= pj
                            dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", pj, "Auto-Planer")
                            
                            total_produced = {}
                            for r in mrp_data["plan_rolek"]:
                                for n, q in r.items():
                                    total_produced[n] = total_produced.get(n, 0) + q
                                    
                            for nazwa_gotowego, total_qty in total_produced.items():
                                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_gotowego][0]
                                st.session_state.produkty.at[idx, "Stan"] += total_qty
                                dodaj_ruch("PW (Gotowe)", nr_knf_auto, nazwa_gotowego, total_qty, "Auto-Planer")
                            
                            st.session_state.log_konf.append({"id": nr_knf_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "jumbo_szt": pj})
                            st.session_state.konf_counter += 1

                        # 3. AUTO OKLEJANIE
                        if mrp_data["braki_okl"]:
                            nr_okl_auto = f"PR-OKL/{data_dzis_str}/{st.session_state.okl_counter:03d}"
                            for b in mrp_data["braki_okl"]:
                                idx_nie = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Z_czego"]][0]
                                idx_okl = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Wariant"]][0]
                                
                                st.session_state.produkty.at[idx_nie, "Stan"] -= b["Brak_szt"]
                                st.session_state.produkty.at[idx_okl, "Stan"] += b["Brak_szt"]
                                
                                dodaj_ruch("RW", nr_okl_auto, b["Z_czego"], b["Brak_szt"], "Auto-Planer")
                                dodaj_ruch("PW (Gotowe)", nr_okl_auto, b["Wariant"], b["Brak_szt"], "Auto-Planer")
                            
                            st.session_state.log_okl.append({"id": nr_okl_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "opis": "Proces oklejania automatyczny"})
                            st.session_state.okl_counter += 1

                        st.success("System automatycznie zaktualizował stany magazynowe w oparciu o plan.")
                else:
                    st.button("Zleć i Zrealizuj Automatycznie", disabled=True, use_container_width=True)

    with tab_wydruk:
        st.subheader("Kompleksowy Plan dla Hali Produkcyjnej")
        st.write("Wygeneruj jeden wspólny dokument PDF dla operatorów maszyn.")
        
        if not mrp_data or (not mrp_data["braki_okl"] and not mrp_data["braki_nie"]):
            st.info("Brak zadań produkcyjnych do wygenerowania na karcie.")
        else:
            if st.button("Generuj Kompleksowy Plan Produkcji (PDF)", type="primary"):
                font_path, font_bold_path = pobierz_czcionki()
                pdf = FPDF()
                pdf.add_page()
                pdf.add_font("Roboto", "", font_path)
                pdf.add_font("Roboto", "B", font_bold_path)
                
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font("Roboto", "B", 15)
                pdf.cell(0, 12, "KOMPLEKSOWY PLAN PRODUKCJI ZLECEŃ", border=0, ln=1, align='C', fill=True)
                
                pdf.set_font("Roboto", "", 9)
                pdf.cell(0, 6, f"Dokument wygenerowany: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Wydział Produkcji", border=0, ln=1, align='C')
                pdf.ln(8)
                
                # SEKCJA 1
                pdf.set_font("Roboto", "B", 12)
                pdf.cell(0, 8, "KROK 1: WYTŁACZARKA GŁÓWNA (PRODUKCJA JUMBO)", border="B", ln=1)
                pdf.set_font("Roboto", "", 10)
                if mrp_data["brakuje_jumbo"] > 0:
                    pdf.cell(0, 8, f"Do wyprodukowania: {mrp_data['brakuje_jumbo']} szt. rolek Jumbo (115cm x 13mb).", ln=1)
                    pdf.set_font("Roboto", "B", 9)
                    pdf.cell(0, 6, "Zlecenie wydania materiału z magazynu surowców:", ln=1)
                    pdf.set_font("Roboto", "", 9)
                    pdf.cell(0, 6, f" - Aluminium zbrojone 1,15m: {mrp_data['req_alu']:g} mb", ln=1)
                    pdf.cell(0, 6, f" - Barwnik biały: {mrp_data['req_bia']:g} kg", ln=1)
                    pdf.cell(0, 6, f" - Barwnik zielony: {mrp_data['req_zie']:g} kg", ln=1)
                else:
                    pdf.cell(0, 8, "Brak zaleceń. Wykorzystać zapas Jumbo z magazynu.", ln=1)
                pdf.ln(5)
                
                # SEKCJA 2
                pdf.set_font("Roboto", "B", 12)
                pdf.cell(0, 8, "KROK 2: STACJA ROZKROJU (KONFEKCJA WZDŁUŻNA)", border="B", ln=1)
                if mrp_data["potrzeba_jmb"] > 0:
                    pdf.set_font("Roboto", "B", 11)
                    pdf.cell(0, 8, f"POBIERZ Z MAGAZYNU: {mrp_data['potrzeba_jmb']} szt. rolek Jumbo (115cm)", ln=1)
                    pdf.ln(2)
                    for i, (_, dane) in enumerate(mrp_data["szablony"].items()):
                        pdf.set_font("Roboto", "B", 11)
                        pdf.set_fill_color(240, 240, 240)
                        pdf.cell(0, 8, f" SZABLON {i+1} --- Weź {dane['ile']} szt. Jumbo i każdą potnij na:", border=1, ln=1, fill=True)
                        
                        pdf.set_font("Roboto", "B", 10)
                        pdf.cell(70, 6, "Szerokość paska", border="L")
                        pdf.cell(40, 6, "Ile takich pasków?", align="C")
                        pdf.cell(0, 6, "Suma cm", border="R", align="C", ln=1)
                        
                        pdf.set_font("Roboto", "", 10)
                        suma_cm = 0
                        for n, q in dane["wzor"].items():
                            try: szer = int(n.split('cm')[0].split(' ')[-1])
                            except: szer = 0
                            suma_cm += szer * q
                            pdf.cell(70, 6, f" {szer} cm", border="L")
                            pdf.cell(40, 6, f"{q} szt.", align="C")
                            pdf.cell(0, 6, f"{szer * q} cm", border="R", align="C", ln=1)
                        
                        pdf.set_font("Roboto", "", 9)
                        odpad = 115 - suma_cm
                        pdf.cell(0, 6, f" *Wykorzystano {suma_cm} cm z 115 cm. Odpad/ścinka: {odpad} cm.", border="LRB", ln=1)
                        pdf.ln(2)
                else:
                    pdf.set_font("Roboto", "", 10)
                    pdf.cell(0, 8, "Brak zaleceń dla cięcia.", ln=1)
                pdf.ln(5)
                
                # SEKCJA 3
                pdf.set_font("Roboto", "B", 12)
                pdf.cell(0, 8, "KROK 3: STACJA OKLEJANIA", border="B", ln=1)
                if mrp_data["braki_okl"]:
                    pdf.set_font("Roboto", "", 10)
                    pdf.cell(0, 8, "Pobrać po cięciu warianty NIEoklejone i przenieść na stację nakładania kleju:", ln=1)
                    pdf.ln(2)
                    pdf.set_font("Roboto", "B", 9)
                    pdf.cell(100, 8, "Z wariantu bazowego (Nieokl.)", border=1)
                    pdf.cell(50, 8, "Docelowo (Oklejony)", border=1)
                    pdf.cell(30, 8, "Ilość", border=1, ln=1, align='C')
                    pdf.set_font("Roboto", "", 9)
                    for b in mrp_data["braki_okl"]:
                        pdf.cell(100, 6, b["Z_czego"], border=1)
                        pdf.cell(50, 6, b["Wariant"].split(" - ")[0], border=1)
                        pdf.cell(30, 6, f"{b['Brak_szt']} szt.", border=1, ln=1, align='C')
                else:
                    pdf.set_font("Roboto", "", 10)
                    pdf.cell(0, 8, "Brak zaleceń oklejania na tę zmianę.", ln=1)
                
                st.session_state.plan_hali_do_pobrania = {"nazwa": "Plan_Dla_Hali.pdf", "data": bytes(pdf.output())}
                st.rerun()

    with tab1:
        st.subheader("Wytłaczanie Rolek Jumbo (115cm x 13mb) - RĘCZNIE")
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
            with st.form("prod_jumbo"):
                ile_jumbo = st.number_input("Ile Rolek Jumbo wyprodukowano?", min_value=1, max_value=m_jumbo, value=1)
                if st.form_submit_button("Zaksięguj produkcję (aktualizacja stanów)"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                    
                    st.session_state.polprodukty.at[0, "Stan"] += ile_jumbo
                    nazwa_p = st.session_state.polprodukty.at[0, "Nazwa"]
                    dodaj_ruch("PW (Półprod.)", nr_jmb_auto, nazwa_p, ile_jumbo, "Wytłaczarka")
                    
                    for k_id, zuzycie in st.session_state.receptura_baza.items():
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                        laczne_zuzycie = zuzycie * ile_jumbo
                        st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                        dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Wytłaczarka")
                    
                    st.session_state.log_jumbo.append({"id": nr_jmb_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ilosc": ile_jumbo})
                    st.session_state.jumbo_counter += 1
                    st.success("Zaksięgowano z sukcesem.")
        else:
            st.error("Brak wystarczających surowców na pełną rolkę Jumbo.")

    with tab2:
        st.subheader("Konfekcja (Rozkrój) - RĘCZNIE")
        s_jumbo = int(st.session_state.polprodukty.at[0, "Stan"])
        jumbo_w_koszyku = sum(item["ile_rolek"] for item in st.session_state.konf_koszyk)
        jumbo_dostepne = s_jumbo - jumbo_w_koszyku
        
        st.info(f"Fizyczny stan na magazynie: {s_jumbo} szt. Jumbo. (Dostępne do zaplanowania w tym zleceniu: {jumbo_dostepne} szt.)")
        
        if s_jumbo == 0:
            st.warning("Brak rolek Jumbo na magazynie. Wyprodukuj je w Kroku 1.")
        elif jumbo_dostepne == 0 and not st.session_state.konf_koszyk:
            st.warning("Wszystkie dostępne rolki Jumbo zostały już przydzielone do poniższego zlecenia.")
        else:
            st.write("**Zdefiniuj szablon cięcia dla POJEDYNCZEJ rolki:** (Max 6 rolek)")
            df_nieoklejone = st.session_state.produkty[st.session_state.produkty['Wariant'].str.contains("Nieoklejona")]
            
            rozkroj_temp = {}
            c_okl, c_nie = st.columns(2)
            for idx, r in df_nieoklejone.iterrows():
                with c_nie if "Nieoklejona" in r['Wariant'] else c_okl:
                    rozkroj_temp[idx] = st.number_input(r['Wariant'], min_value=0, value=0, key=f"r_temp_{idx}")
                    
            zuzyte_cm = sum(rozkroj_temp[idx] * st.session_state.produkty.at[idx, 'Szerokosc'] for idx in rozkroj_temp)
            laczna_ilosc_rolek = sum(rozkroj_temp.values())
            
            st.write("")
            if zuzyte_cm == 115 and laczna_ilosc_rolek <= 6:
                st.success(f"Szablon cięcia skonfigurowany prawidłowo (115 / 115 cm, {laczna_ilosc_rolek} rolek).")
                col_k1, col_k2 = st.columns([1, 2])
                with col_k1:
                    ile_tym_szablonem = st.number_input("Ile rolek Jumbo chcesz pociąć tym wzorem?", min_value=1, max_value=max(1, jumbo_dostepne), value=1)
                with col_k2:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Dodaj szablon do zlecenia produkcyjnego", use_container_width=True):
                        if ile_tym_szablonem > jumbo_dostepne:
                            st.error("Nie masz tyle wolnych rolek Jumbo na stanie!")
                        else:
                            wzor_slownik = {}
                            for idx, qty in rozkroj_temp.items():
                                if qty > 0:
                                    nazwa_szer = st.session_state.produkty.at[idx, 'Wariant']
                                    wzor_slownik[nazwa_szer] = qty
                            st.session_state.konf_koszyk.append({
                                "wzor": wzor_slownik,
                                "ile_rolek": ile_tym_szablonem,
                                "ile": ile_tym_szablonem
                            })
                            st.rerun()
            elif laczna_ilosc_rolek > 6:
                st.error(f"Błąd techniczny: Szablon zawiera {laczna_ilosc_rolek} rolek. Maksymalna wydajność to 6 noży.")
            elif zuzyte_cm > 115:
                st.error(f"Przekroczyłeś wymiar rolki bazowej o {zuzyte_cm - 115} cm!")
            elif zuzyte_cm > 0:
                st.warning(f"Suma szerokości: {zuzyte_cm} cm. Do zagospodarowania pozostało: {115 - zuzyte_cm} cm.")

        if st.session_state.konf_koszyk:
            st.divider()
            st.subheader("Podsumowanie Zlecenia Rozkroju")
            
            wielki_slownik = []
            for item in st.session_state.konf_koszyk:
                op_str = " | ".join([f"{q}x {k.split('cm')[0].split(' ')[-1]}cm" for k, q in item["wzor"].items()])
                wielki_slownik.append({"Szablon (Rozkład na 1 rolce)": op_str, "Zadeklarowane rolki Jumbo (szt.)": item["ile_rolek"]})
                
            st.dataframe(pd.DataFrame(wielki_slownik), use_container_width=True, hide_index=True)
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Wyczyść zlecenie i zacznij od nowa", use_container_width=True):
                    st.session_state.konf_koszyk = []
                    st.rerun()
            with col_b2:
                if st.button("Zatwierdź zlecenie (aktualizacja stanów)", type="primary", use_container_width=True):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                    total_jumbo_to_cut = sum(item["ile_rolek"] for item in st.session_state.konf_koszyk)
                    
                    st.session_state.polprodukty.at[0, "Stan"] -= total_jumbo_to_cut
                    dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", total_jumbo_to_cut, "Konfekcja")
                    
                    total_produced = {}
                    for item in st.session_state.konf_koszyk:
                        for idx_nazwa, qty_per_roll in item["wzor"].items():
                            if qty_per_roll > 0:
                                produced_qty = qty_per_roll * item["ile_rolek"]
                                total_produced[idx_nazwa] = total_produced.get(idx_nazwa, 0) + produced_qty
                                    
                    for nazwa_gotowego, total_qty in total_produced.items():
                        idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_gotowego][0]
                        st.session_state.produkty.at[idx, "Stan"] += total_qty
                        dodaj_ruch("PW (Gotowe)", nr_knf_auto, nazwa_gotowego, total_qty, "Konfekcja")

                    st.session_state.log_konf.append({"id": nr_knf_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "jumbo_szt": total_jumbo_to_cut})
                    st.session_state.konf_counter += 1
                    st.session_state.konf_koszyk = []
                    st.success("Konfekcja zaksięgowana z sukcesem.")
                    st.rerun()

    with tab3:
        st.subheader("Oklejanie - RĘCZNIE")
        st.write("Wybierz rolki Nieoklejone z magazynu i zewidencjuj proces nałożenia okleiny.")
        
        df_nieokl_dostepne = st.session_state.produkty[(st.session_state.produkty['Wariant'].str.contains("Nieoklejona")) & (st.session_state.produkty['Stan'] > 0)]
        
        if df_nieokl_dostepne.empty:
            st.info("Brak gotowych rolek nieoklejonych na magazynie. Wykonaj najpierw proces Konfekcji (Krok 2).")
        else:
            with st.form("form_oklejanie"):
                opcje_okl = []
                for _, r in df_nieokl_dostepne.iterrows():
                    opcje_okl.append(f"{int(r['Szerokosc'])}cm (Dostępne: {int(r['Stan'])} szt.)")
                
                c_okl1, c_okl2 = st.columns(2)
                wybrana_opcja = c_okl1.selectbox("Wybierz szerokość do oklejenia:", opcje_okl)
                
                szerokosc_wybrana = int(wybrana_opcja.split("cm")[0])
                max_dost = int(wybrana_opcja.split("Dostępne: ")[1].split(" szt")[0])
                
                ile_okleic = c_okl2.number_input("Ilość do oklejenia:", min_value=1, max_value=max_dost, value=1, step=1)
                
                st.divider()
                if st.form_submit_button("Zaksięguj Oklejanie"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_okl_auto = f"PR-OKL/{data_dzis_str}/{st.session_state.okl_counter:03d}"
                    
                    war_nie = f"GrizoThermo+ {szerokosc_wybrana}cm - Nieoklejona (13mb)"
                    war_okl = f"GrizoThermo+ {szerokosc_wybrana}cm - Oklejona (13mb)"
                    
                    idx_nie = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == war_nie][0]
                    idx_okl = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == war_okl][0]
                    
                    st.session_state.produkty.at[idx_nie, "Stan"] -= ile_okleic
                    st.session_state.produkty.at[idx_okl, "Stan"] += ile_okleic
                    
                    dodaj_ruch("RW", nr_okl_auto, war_nie, ile_okleic, "Stacja Oklejania")
                    dodaj_ruch("PW (Gotowe)", nr_okl_auto, war_okl, ile_okleic, "Stacja Oklejania")
                    
                    st.session_state.log_okl.append({"id": nr_okl_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "opis": f"Oklejono {ile_okleic} szt. ({szerokosc_wybrana}cm)"})
                    st.session_state.okl_counter += 1
                    st.success("Oklejanie zaksięgowane z sukcesem.")
                    st.rerun()

elif menu == "Baza Kontrahentów (CRM)":
    st.header("Baza Kontrahentów")
    st.write("Zarządzanie relacjami z klientami oraz dostawcami surowców.")
    
    tab_odbiorcy, tab_dostawcy, tab_dodaj = st.tabs([
        "Klienci (Odbiorcy WZ)", 
        "Dostawcy (Przyjęcia PZ)", 
        "Nowy Kontrahent"
    ])
    
    with tab_odbiorcy:
        df_odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]
        if df_odbiorcy.empty:
            st.info("Brak zarejestrowanych klientów w bazie danych.")
        else:
            for _, row in df_odbiorcy.iterrows():
                st.markdown(f'''
                <div class="item-card">
                    <div class="card-title">{row["Nazwa"]}</div>
                    <div class="card-details">NIP: {row["NIP"]} | Adres siedziby: {row["Adres"]}</div>
                </div>
                ''', unsafe_allow_html=True)
                
    with tab_dostawcy:
        df_dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]
        if df_dostawcy.empty:
            st.info("Brak zarejestrowanych dostawców w bazie danych.")
        else:
            for _, row in df_dostawcy.iterrows():
                st.markdown(f'''
                <div class="item-card item-card-purple">
                    <div class="card-title">{row["Nazwa"]}</div>
                    <div class="card-details">NIP: {row["NIP"]} | Adres dystrybucji: {row["Adres"]}</div>
                </div>
                ''', unsafe_allow_html=True)

    with tab_dodaj:
        st.subheader("Formularz rejestracji nowego podmiotu")
        with st.form("nowy_kontrahent_form"):
            col1, col2 = st.columns(2)
            with col1:
                nowa_nazwa = st.text_input("Pełna nazwa firmy (Wymagane)")
                nowy_nip = st.text_input("Numer identyfikacji podatkowej (NIP)")
            with col2:
                nowy_typ = st.selectbox("Typ operacyjny podmiotu", ["Odbiorca", "Dostawca"])
                nowy_adres = st.text_input("Adres rejestracyjny (Wymagane)")
            
            st.write("")
            if st.form_submit_button("Zarejestruj podmiot w systemie"):
                if nowa_nazwa.strip() and nowy_adres.strip():
                    nowy_wpis = pd.DataFrame([{
                        "Nazwa": nowa_nazwa.strip(),
                        "NIP": nowy_nip.strip(),
                        "Adres": nowy_adres.strip(),
                        "Typ": nowy_typ
                    }])
                    st.session_state.kontrahenci = pd.concat([st.session_state.kontrahenci, nowy_wpis], ignore_index=True)
                    st.success(f"Podmiot {nowa_nazwa} został pomyślnie zapisany w bazie CRM.")
                    st.rerun()
                else:
                    st.error("Odrzucono. Pola Nazwa firmy oraz Adres rejestracyjny są obowiązkowe.")

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
    
    if "wz_pdf_do_pobrania" in st.session_state:
        st.success("Zatwierdzono wydanie. Pobierz dokument WZ poniżej:")
        st.download_button(
            label="📥 Pobierz Dokument WZ (PDF)",
            data=st.session_state.wz_pdf_do_pobrania["data"],
            file_name=st.session_state.wz_pdf_do_pobrania["nazwa"],
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        if st.button("Zamknij powiadomienie", use_container_width=True):
            del st.session_state.wz_pdf_do_pobrania
            st.rerun()
        st.divider()
        
    if not odbiorcy:
        st.warning("Brak odbiorców w bazie danych CRM.")
    else:
        st.subheader("1. Realizacja Zamówienia (Opcjonalne wczytanie z ZK)")
        oczekujace_zk = [z for z in st.session_state.zamowienia if z["Status"] == "Oczekujące"]
        if oczekujace_zk:
            opcje_zk = {f"{z['id']} | Kontrahent: {z['klient']}": z for z in oczekujace_zk}
            col_zk1, col_zk2 = st.columns([3, 1])
            with col_zk1:
                wybrane_zk_klucz = st.selectbox("Wybierz oczekujące zamówienie z listy", ["-- Wybierz (lub pomiń dla wydania ręcznego) --"] + list(opcje_zk.keys()))
            with col_zk2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Załaduj zamówienie na WZ", use_container_width=True):
                    if wybrane_zk_klucz != "-- Wybierz (lub pomiń dla wydania ręcznego) --":
                        z = opcje_zk[wybrane_zk_klucz]
                        st.session_state.wybrany_klient_wz = z["klient"]
                        st.session_state.powiazane_zk = z["id"]
                        st.session_state.wz_koszyk = [{"Wariant": p["Wariant"], "Ilosc": p["Ilość (szt.)"]} for p in z["pozycje"]]
                        st.rerun()
        else:
            st.info("Brak oczekujących zamówień w systemie. Możesz wystawić WZ ręcznie.")
            
        st.divider()
        
        dostepne_produkty = st.session_state.produkty[st.session_state.produkty["Stan"] > 0].copy()
        
        if dostepne_produkty.empty and not st.session_state.wz_koszyk:
            st.error("Brak gotowych produktów na magazynie! Wymagana konfekcja.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            
            st.subheader("2. Dane Odbiorcy i Dokumentu")
            if st.session_state.powiazane_zk:
                st.success(f"Aktywne powiązanie: Wydanie realizuje zamówienie {st.session_state.powiazane_zk}. Zostanie ono zamknięte po wygenerowaniu WZ.")
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                idx_klienta = odbiorcy.index(st.session_state.wybrany_klient_wz) if st.session_state.wybrany_klient_wz in odbiorcy else 0
                wybrany_klient = st.selectbox("Nabywca (Wybierz z bazy)", odbiorcy, index=idx_klienta)
                st.session_state.wybrany_klient_wz = wybrany_klient
            with col_f2:
                uwagi_doc = st.text_input("Uwagi do dokumentu", value="Dostawa z magazynu głównego.")
                
            st.divider()
            st.subheader("3. Dodaj produkty do wydania")
            
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
                st.info("Brak dostępnych pozycji magazynowych do ręcznego dodania.")
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
                st.subheader("4. Podsumowanie dokumentu WZ")
                
                df_koszyk = pd.DataFrame(st.session_state.wz_koszyk)
                df_koszyk.columns = ["Nazwa asortymentu", "Ilość do wydania (szt.)"]
                st.dataframe(df_koszyk, use_container_width=True, hide_index=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Wyczyść formularz", use_container_width=True):
                        st.session_state.wz_koszyk = []
                        st.session_state.powiazane_zk = None
                        st.rerun()
                with col_btn2:
                    if st.button("Zatwierdź wydanie i generuj PDF", type="primary", use_container_width=True):
                        bledy = False
                        for item in st.session_state.wz_koszyk:
                            stan_mag = st.session_state.produkty[st.session_state.produkty["Wariant"] == item["Wariant"]]["Stan"].values[0]
                            if item["Ilosc"] > stan_mag:
                                st.error(f"Braki magazynowe uniemożliwiają wydanie dla: {item['Wariant']}. Potrzeba {item['Ilosc']} szt., dostępnych: {int(stan_mag)} szt.")
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
                            
                            if st.session_state.powiazane_zk:
                                pdf.set_font("Roboto", "", 11)
                                pdf.cell(0, 8, f"Dotyczy zamówienia nr: {st.session_state.powiazane_zk}", border=0, ln=1, align='C')
                            
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
                            
                            powiazanie_info = st.session_state.powiazane_zk if st.session_state.powiazane_zk else "-"
                            
                            if st.session_state.powiazane_zk:
                                for zmw in st.session_state.zamowienia:
                                    if zmw["id"] == st.session_state.powiazane_zk:
                                        zmw["Status"] = "Zrealizowane"
                                        break
                                st.session_state.powiazane_zk = None
                            
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
                            st.session_state.archiwum_wz_pdf.append({"id": nr_wz_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "kontrahent": wybrany_klient, "zamowienie": powiazanie_info, "pdf": pdf_bytes})
                            
                            st.session_state.wz_pdf_do_pobrania = {"nazwa": f"{nr_wz_auto.replace('/', '_')}.pdf", "data": pdf_bytes}
                            st.session_state.wz_koszyk = []
                            st.rerun()

elif menu == "Archiwum Dokumentów":
    st.header("Archiwum Dokumentów Operacyjnych i Technologicznych")
    
    tab_arch_wz, tab_arch_pz, tab_arch_jmb, tab_arch_knf, tab_arch_okl = st.tabs([
        "Wydania (WZ)", 
        "Przyjęcia (PZ)", 
        "Wytłaczanie JUMBO", 
        "Konfekcja (Rozkrój)",
        "Oklejanie"
    ])
    
    with tab_arch_wz:
        st.subheader("Rejestr Dokumentów WZ")
        if not st.session_state.archiwum_wz_pdf:
            st.info("Brak wystawionych dokumentów WZ w bazie danych.")
        else:
            df_wz = pd.DataFrame(st.session_state.archiwum_wz_pdf)[["id", "data", "kontrahent", "zamowienie"]]
            st.dataframe(df_wz, use_container_width=True, hide_index=True, column_config={"id":"Numer dokumentu", "data":"Data wystawienia", "kontrahent":"Odbiorca", "zamowienie": "Dotyczy ZK"})
            
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
        st.subheader("Ewidencja Procesów Wytłaczania (Krok 1)")
        if not st.session_state.log_jumbo:
            st.info("Brak zarejestrowanych procesów.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.log_jumbo), use_container_width=True, hide_index=True)

    with tab_arch_knf:
        st.subheader("Ewidencja Procesów Konfekcjonowania (Krok 2)")
        if not st.session_state.log_konf:
            st.info("Brak zarejestrowanych procesów.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.log_konf), use_container_width=True, hide_index=True)
            
    with tab_arch_okl:
        st.subheader("Ewidencja Procesów Oklejania (Krok 3)")
        if not st.session_state.log_okl:
            st.info("Brak zarejestrowanych procesów.")
        else:
            st.dataframe(pd.DataFrame(st.session_state.log_okl), use_container_width=True, hide_index=True)

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
