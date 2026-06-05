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
# 1. INICJALIZACJA BAZY (WERSJA V49 + WORKFLOW PRODUKCJI)
# ==========================================
if 'init_v49' not in st.session_state:
    st.session_state.init_v49 = True
    st.session_state.wz_counter = 1
    st.session_state.jumbo_counter = 1
    st.session_state.konf_counter = 1
    st.session_state.okl_counter = 1
    st.session_state.zk_counter = 1
    st.session_state.pr_counter = 1 # Licznik zleceń produkcyjnych przekazanych na halę
    
    st.session_state.zlecenia_produkcyjne = [] # Rejestr aktywnych planów na reuniu
    
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
    
    st.session_state.zk_koszyk = [] 
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
    st.header("Pulpit Zarządzania: GrizoThermo+")
    st.write("Podsumowanie operacyjne i statystyki krytyczne przedsiębiorstwa.")
    
    suma_gotowych = int(st.session_state.produkty["Stan"].sum())
    stan_jumbo = int(st.session_state.polprodukty.loc[0, "Stan"])
    stan_alu = st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0]
    
    # Liczymy zamówienia, które albo czekają, albo są już produkowane na reuniu
    oczekujace_zk = len([z for z in st.session_state.zamowienia if z["Status"] in ["Czeka na realizację", "W produkcji"]])

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    col_kpi1.metric("WYROBY GOTOWE (SUMA)", f"{suma_gotowych} szt.")
    col_kpi2.metric("ROLKI JUMBO NA STANIE", f"{stan_jumbo} szt.")
    col_kpi3.metric("ZAPAS ALUMINIUM", f"{stan_alu:g} mb")
    col_kpi4.metric("AKTYWNE ZAMÓWIENIA ZK", f"{oczekujace_zk} szt.")
    
    st.divider()
    
    braki_surowcowe = []
    for _, row_k in st.session_state.komponenty.iterrows():
        prog_alarmowy = st.session_state.receptura_baza.get(row_k['ID'], 0) * 20
        if row_k['Stan'] < prog_alarmowy:
            niedobor = prog_alarmowy - row_k['Stan']
            braki_surowcowe.append(f"{row_k['Nazwa']} (Aktualnie: {row_k['Stan']:g} {row_k['Jednostka']}, Deficyt: {niedobor:g} {row_k['Jednostka']})")
            
    if braki_surowcowe:
        st.error("ALERT: Krytyczny poziom surowców produkcyjnych\n\nBieżący stan magazynowy poniżej uniemożliwia realizację partii 20 sztuk rolek Jumbo:\n\n" + "\n".join([f"* {b}" for b in braki_surowcowe]))

    st.write("")
    col_dash1, col_dash2 = st.columns([2, 3])
    
    with col_dash1:
        st.subheader("Porównanie Stanu Surowców")
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
            
            # Formularz nagłówkowy
            col_zk1, col_zk2 = st.columns(2)
            klient = col_zk1.selectbox("Klient zamawiający", odbiorcy, key="zk_klient_sel")
            uwagi = col_zk2.text_input("Uwagi do zamówienia", key="zk_uwagi_in")
            
            st.divider()
            st.subheader("Dodaj produkty do zamówienia")
            
            lista_produktow = st.session_state.produkty["Wariant"].tolist()
            
            col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
            with col_p1:
                wybrany_produkt = st.selectbox("Wybierz asortyment", lista_produktow, key="zk_prod_sel")
            with col_p2:
                ilosc = st.number_input("Ilość (szt.)", min_value=1, value=1, step=1, key="zk_ilosc_in")
            with col_p3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Dodaj do zamówienia", use_container_width=True):
                    istnieje = False
                    for item in st.session_state.zk_koszyk:
                        if item["Wariant"] == wybrany_produkt:
                            item["Ilość (szt.)"] += ilosc
                            istnieje = True
                            break
                    if not istnieje:
                        st.session_state.zk_koszyk.append({"Wariant": wybrany_produkt, "Ilość (szt.)": ilosc})
                    st.rerun()

            if st.session_state.zk_koszyk:
                st.divider()
                st.subheader("Koszyk Zamówienia")
                df_koszyk = pd.DataFrame(st.session_state.zk_koszyk)
                st.dataframe(df_koszyk, use_container_width=True, hide_index=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Wyczyść koszyk", use_container_width=True):
                        st.session_state.zk_koszyk = []
                        st.rerun()
                with col_btn2:
                    if st.button("Zatwierdź i zarejestruj ZK", type="primary", use_container_width=True):
                        szczegoly = st.session_state.zk_koszyk.copy()
                        st.session_state.zamowienia.append({
                            "id": nr_zk_auto,
                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "klient": klient,
                            "pozycje": szczegoly,
                            "uwagi": uwagi,
                            "Status": "Czeka na realizację" # STATUS STARTOWY
                        })
                        st.session_state.zk_counter += 1
                        st.session_state.zk_koszyk = []
                        st.success(f"Zamówienie {nr_zk_auto} zostało przyjęte i oczekuje na plan produkcyjny.")
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
                    if z["Status"] != "Zrealizowane":
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
                pdf.add_font("Roboto", "", font_path, uni=True)
                pdf.add_font("Roboto", "B", font_bold_path, uni=True)
                
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
                
                st.session_state.zk_pdf_do_pobrania = {"nazwa": "Zbiorcza_Lista_Zamowien.pdf", "data": pdf.output(dest="S").encode("latin-1")}
                st.rerun()

# ==========================================
# MODUŁ PRODUKCJI I PLANOWANIA ZAPOTRZEBOWANIA
# ==========================================
elif menu == "Moduł Production":
    st.header("Zarządzanie Produkcją i Planowanie")
    
    # SILNIK MRP - analizuje zamówienia ze statusem "Czeka na realizację"
    oczekujace = [z for z in st.session_state.zamowienia if z["Status"] == "Czeka na realizację"]
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

    # POWIADOMIENIE: Pokazuje się od razu na samej górze po kliknięciu przycisku!
    if "plan_hali_do_pobrania" in st.session_state:
        st.success(f"⚙️ Plan został pomyślnie wygenerowany i wysłany do realizacji!")
        st.download_button(
            label="📥 POBIERZ KATĘ PRACY / PLAN DLA HALI (PDF)",
            data=st.session_state.plan_hali_do_pobrania["data"],
            file_name=st.session_state.plan_hali_do_pobrania["nazwa"],
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        if st.button("Zamknij to powiadomienie", use_container_width=True):
            del st.session_state.plan_hali_do_pobrania
            st.rerun()
        st.divider()

    # ZAKŁADKI: USUNIĘTO zakładkę "Wydruk Planu dla Hali"
    tab_plan, tab1, tab2, tab3, tab4 = st.tabs([
        "Panel MRP (Analiza)", 
        "Krok 1: Wytłaczanie RĘCZNIE", "Krok 2: Rozkrój RĘCZNY", 
        "Krok 3: Oklejanie RĘCZNIE", "🏭 Krok 4: Odbiór z Produkcji (Potwierdzenia)"
    ])
    
    with tab_plan:
        st.subheader("Inteligentna Analiza Zapotrzebowania (MRP)")
        
        if not mrp_data:
            st.info("Brak nowych zamówień oczekujących na realizację. Wszystkie zamówienia są już w toku lub są gotowe do wydania klientom.")
        else:
            if not mrp_data["braki_okl"] and not mrp_data["braki_nie"]:
                st.success("Masz wystarczającą ilość produktów na magazynie, aby pokryć zamówienia bez nowej produkcji.")
                if st.button("Zatwierdź i oznacz zamówienia jako Gotowe do Wydania", type="primary", use_container_width=True):
                    for z in oczekujace:
                        z["Status"] = "Gotowe do wydania"
                    st.rerun()
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
                        st.error("BRAK SUROWCÓW do wytłoczenia potrzebnych rolek Jumbo!")
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
                    # PODPIĘTE GENEROWANIE RAPORTU POD JEDEN I TEN SAM PRZYCISK
                    if st.button("Zatwierdź Plan, wyślij na Halę i generuj Karet Pracy (PDF)", type="primary", use_container_width=True):
                        data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                        nr_pr_auto = f"PR/{data_dzis_str}/{st.session_state.pr_counter:03d}"
                        
                        # 1. Zapisujemy w sesji nową Kartę Pracy dla Kroku 4
                        st.session_state.zlecenia_produkcyjne.append({
                            "id": nr_pr_auto,
                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "mrp_snap": mrp_data, 
                            "zamowienia_powiazane": [z["id"] for z in oczekujace],
                            "status": "W toku"
                        })
                        st.session_state.pr_counter += 1
                        
                        # 2. Aktualizujemy statusy powiązanych zamówień ZK
                        for z in oczekujace:
                            z["Status"] = "W produkcji"
                            
                        # 3. GENEROWANIE STRUKTURY PDF (Przeniesione tutaj na sztywno!)
                        font_path, font_bold_path = pobierz_czcionki()
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.add_font("Roboto", "", font_path, uni=True)
                        pdf.add_font("Roboto", "B", font_bold_path, uni=True)
                        
                        pdf.set_fill_color(240, 240, 240)
                        pdf.set_font("Roboto", "B", 15)
                        pdf.cell(0, 12, f"KOMPLEKSOWY PLAN PRODUKCJI - ZLECENIE {nr_pr_auto}", border=0, ln=1, align='C', fill=True)
                        
                        pdf.set_font("Roboto", "", 9)
                        pdf.cell(0, 6, f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Wydział Production  |  GrizoThermo+", border=0, ln=1, align='C')
                        pdf.ln(8)
                        
                        # PDF Sekcja 1
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
                        
                        # PDF Sekcja 2
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
                        
                        # PDF Sekcja 3
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
                        
                        # 4. Zapisujemy dane do pobrania i przeładowujemy stronę
                        st.session_state.plan_hali_do_pobrania = {
                            "nazwa": f"Plan_Produkcji_{nr_pr_auto.replace('/', '_')}.pdf", 
                            "data": pdf.output(dest="S").encode("latin-1")
                        }
                        st.rerun()
                else:
                    st.button("Zatwierdź Plan, wyślij na Halę i generuj Karet Pracy (PDF)", disabled=True, use_container_width=True)

    # RĘCZNE ETAPY PRODUKCJI
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
                    dodaj_ruch("PW (Półprod.)", nr_jmb_auto, st.session_state.polprodukty.at[0, "Nazwa"], ile_jumbo, "Wytłaczarka")
                    for k_id, zuzycie in st.session_state.receptura_baza.items():
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                        laczne_zuzycie = zuzycie * ile_jumbo
                        st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                        dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Wytłaczarka")
                    st.session_state.jumbo_counter += 1
                    st.success("Zaksięgowano ręczne wytłoczenie rolki.")
                    st.rerun()

    with tab2:
        st.subheader("Konfekcja (Rozkrój) - RĘCZNIE")
        s_jumbo = int(st.session_state.polprodukty.at[0, "Stan"])
        jumbo_w_koszyku = sum(item["ile_rolek"] for item in st.session_state.konf_koszyk)
        jumbo_dostepne = s_jumbo - jumbo_w_koszyku
        st.info(f"Fizyczny stan na magazynie: {s_jumbo} szt. Jumbo. (Dostępne do rozkroju: {jumbo_dostepne} szt.)")
        if s_jumbo == 0: st.warning("Brak rolek Jumbo na magazynie. Wyprodukuj je w Kroku 1.")
        else:
            df_nieoklejone = st.session_state.produkty[st.session_state.produkty['Wariant'].str.contains("Nieoklejona")]
            rozkroj_temp = {}
            c_okl, c_nie = st.columns(2)
            for idx, r in df_nieoklejone.iterrows():
                with c_nie: rozkroj_temp[idx] = st.number_input(r['Wariant'], min_value=0, value=0, key=f"r_temp_{idx}")
            zuzyte_cm = sum(rozkroj_temp[idx] * st.session_state.produkty.at[idx, 'Szerokosc'] for idx in rozkroj_temp)
            laczna_ilosc_rolek = sum(rozkroj_temp.values())
            if zuzyte_cm == 115 and laczna_ilosc_rolek <= 6:
                st.success(f"Szablon cięcia skonfigurowany prawidłowo (115 / 115 cm).")
                col_k1, col_k2 = st.columns([1, 2])
                with col_k1: ile_tym_szablonem = st.number_input("Ile rolek Jumbo chcesz pociąć tym wzorem?", min_value=1, max_value=max(1, jumbo_dostepne), value=1)
                with col_k2:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Dodaj szablon do ręcznego rozkroju", use_container_width=True):
                        wzor_slownik = {}
                        for idx, qty in rozkroj_temp.items():
                            if qty > 0: wzor_slownik[st.session_state.produkty.at[idx, 'Wariant']] = qty
                        st.session_state.konf_koszyk.append({"wzor": wzor_slownik, "ile_rolek": ile_tym_szablonem})
                        st.rerun()
            elif zuzyte_cm > 115: st.error(f"Przekroczyłeś wymiar rolki o {zuzyte_cm - 115} cm!")
            elif zuzyte_cm > 0: st.warning(f"Suma szerokości: {zuzyte_cm} cm. Do 115 cm brakuje: {115 - zuzyte_cm} cm.")

        if st.session_state.konf_koszyk:
            st.divider()
            if st.button("Zatwierdź ręczne zlecenie rozkroju i zaktualizuj magazyn", type="primary"):
                data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                total_jumbo_to_cut = sum(item["ile_rolek"] for item in st.session_state.konf_koszyk)
                st.session_state.polprodukty.at[0, "Stan"] -= total_jumbo_to_cut
                dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", total_jumbo_to_cut, "Konfekcja")
                for item in st.session_state.konf_koszyk:
                    for idx_nazwa, qty_per_roll in item["wzor"].items():
                        produced_qty = qty_per_roll * item["ile_rolek"]
                        idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == idx_nazwa][0]
                        st.session_state.produkty.at[idx, "Stan"] += produced_qty
                        dodaj_ruch("PW (Gotowe)", nr_knf_auto, idx_nazwa, produced_qty, "Konfekcja")
                st.session_state.log_konf.append({"id": nr_knf_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "jumbo_szt": total_jumbo_to_cut})
                st.session_state.konf_counter += 1
                st.session_state.konf_koszyk = []
                st.success("Konfekcja ręczna została zaksięgowana.")
                st.rerun()

    with tab3:
        st.subheader("Oklejanie - RĘCZNIE")
        df_nieokl_dostepne = st.session_state.produkty[(st.session_state.produkty['Wariant'].str.contains("Nieoklejona")) & (st.session_state.produkty['Stan'] > 0)]
        if df_nieokl_dostepne.empty: st.info("Brak gotowych rolek nieoklejonych na magazynie.")
        else:
            with st.form("form_oklejanie"):
                opcje_okl = [f"{int(r['Szerokosc'])}cm (Dostępne: {int(r['Stan'])} szt.)" for _, r in df_nieokl_dostepne.iterrows()]
                wybrana_opcja = st.selectbox("Wybierz szerokość do oklejenia:", opcje_okl)
                szerokosc_wybrana = int(wybrana_opcja.split("cm")[0])
                max_dost = int(wybrana_opcja.split("Dostępne: ")[1].split(" szt")[0])
                ile_okleic = st.number_input("Ilość do oklejenia:", min_value=1, max_value=max_dost, value=1, step=1)
                if st.form_submit_button("Zaksięguj Oklejanie ręczne"):
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
                    st.session_state.log_okl.append({"id": nr_okl_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "opis": f"Oklejono {ile_okleic} szt."})
                    st.session_state.okl_counter += 1
                    st.success("Oklejanie ręczne zaksięgowane.")
                    st.rerun()

    # KROK 4: ODBIÓR Z PRODUKCJI
    with tab4:
        st.subheader("Potwierdzenie Wykonania i Odbiór Towaru z Hali")
        st.write("Kliknij 'Potwierdź wykonanie', gdy pracownicy fizycznie zakończą proces produkcji danej partii.")
        zlecenia_w_toku = [j for j in st.session_state.zlecenia_produkcyjne if j["status"] == "W toku"]
        if not zlecenia_w_toku: st.info("Brak aktywnych planów realizowanych aktualnie na hali.")
        else:
            for job in zlecenia_w_toku:
                with st.expander(f"📋 Karta Produkcji: {job['id']} | Wysłano na hale: {job['data']} | Dotyczy ZK: {', '.join(job['zamowienia_powiazane'])}"):
                    snap = job["mrp_snap"]
                    st.write("**1. Wymagane materiały do pobrania z magazynu:**")
                    if snap["brakuje_jumbo"] > 0:
                        st.caption(f"* Aluminium zbrojone: {snap['req_alu']:g} mb")
                        st.caption(f"* Barwnik biały: {snap['req_bia']:g} kg")
                        st.caption(f"* Barwnik zielony: {snap['req_zie']:g} kg")
                    else: st.caption("Wykorzystanie wyłącznie istniejącego zapasu Jumbo (surowce bazowe: 0)")
                    st.write("**2. Wyroby gotowe, które trafią na magazyn po potwierdzeniu:**")
                    total_produced = {}
                    for r in snap["plan_rolek"]:
                        for n, q in r.items(): total_produced[n] = total_produced.get(n, 0) + q
                    for b in snap["braki_okl"]:
                        total_produced[b["Wariant"]] = total_produced.get(b["Wariant"], 0) + b["Brak_szt"]
                        total_produced[b["Z_czego"]] = total_produced.get(b["Z_czego"], 0) - b["Brak_szt"]
                    df_plan_wyrobow = pd.DataFrame([{"Wariant asortymentu": k, "Ilość planowana (szt.)": v} for k, v in total_produced.items() if v != 0])
                    st.dataframe(df_plan_wyrobow, hide_index=True, use_container_width=True)
                    if st.button(f" Pelne Potwierdzenie Wykonania Partii {job['id']}", key=f"conf_job_{job['id']}", type="primary", use_container_width=True):
                        data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                        if snap["brakuje_jumbo"] > 0:
                            bj = snap["brakuje_jumbo"]
                            nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] += bj
                            dodaj_ruch("PW (Półprod.)", nr_jmb_auto, st.session_state.polprodukty.at[0, "Nazwa"], bj, "Hala-Planer")
                            for k_id, zuzycie in st.session_state.receptura_baza.items():
                                idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                                laczne_zuzycie = zuzycie * bj
                                st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                                dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Hala-Planer")
                            st.session_state.jumbo_counter += 1
                        if snap["potrzeba_jmb"] > 0:
                            pj = snap["potrzeba_jmb"]
                            nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] -= pj
                            dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", pj, "Hala-Planer")
                            temp_produced = {}
                            for r in snap["plan_rolek"]:
                                for n, q in r.items(): temp_produced[n] = temp_produced.get(n, 0) + q
                            for nazwa_gotowego, total_qty in temp_produced.items():
                                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_gotowego][0]
                                st.session_state.produkty.at[idx, "Stan"] += total_qty
                                dodaj_ruch("PW (Gotowe)", nr_knf_auto, nazwa_gotowego, total_qty, "Hala-Planer")
                            st.session_state.konf_counter += 1
                        if snap["braki_okl"]:
                            nr_okl_auto = f"PR-OKL/{data_dzis_str}/{st.session_state.okl_counter:03d}"
                            for b in snap["braki_okl"]:
                                idx_nie = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Z_czego"]][0]
                                idx_okl = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Wariant"]][0]
                                st.session_state.produkty.at[idx_nie, "Stan"] -= b["Brak_szt"]
                                st.session_state.produkty.at[idx_okl, "Stan"] += b["Brak_szt"]
                                dodaj_ruch("RW", nr_okl_auto, b["Z_czego"], b["Brak_szt"], "Hala-Planer")
                                dodaj_ruch("PW (Gotowe)", nr_okl_auto, b["Wariant"], b["Brak_szt"], "Hala-Planer")
                            st.session_state.okl_counter += 1
                        job["status"] = "Zakończone"
                        for zmw in st.session_state.zamowienia:
                            if zmw["id"] in job["zamowienia_powiazane"]: zmw["Status"] = "Gotowe do wydania"
                        st.success(f"Zlecenie {job['id']} zamknięte pomyślnie. Towar trafił na stan magazynu gotowego.")
                        st.rerun()

elif menu == "Baza Kontrahentów (CRM)":
    st.header("Baza Kontrahentów")
    st.write("Zarządzanie relacjami z klientami oraz dostawcami surowców.")
    tab_odbiorcy, tab_dostawcy, tab_dodaj = st.tabs(["Klienci (Odbiorcy WZ)", "Dostawcy (Przyjęcia PZ)", "Nowy Kontrahent"])
    with tab_odbiorcy:
        df_odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]
        for _, row in df_odbiorcy.iterrows(): st.markdown(f'<div class="item-card"><div class="card-title">{row["Nazwa"]}</div><div class="card-details">NIP: {row["NIP"]} | Adres siedziby: {row["Adres"]}</div></div>', unsafe_allow_html=True)
    with tab_dostawcy:
        df_dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]
        for _, row in df_dostawcy.iterrows(): st.markdown(f'<div class="item-card item-card-purple"><div class="card-title">{row["Nazwa"]}</div><div class="card-details">NIP: {row["NIP"]} | Adres dystrybucji: {row["Adres"]}</div></div>', unsafe_allow_html=True)
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
            if st.form_submit_button("Zarejestruj podmiot w systemie"):
                if nowa_nazwa.strip() and nowy_adres.strip():
                    nowy_wpis = pd.DataFrame([{"Nazwa": nowa_nazwa.strip(), "NIP": nowy_nip.strip(), "Adres": nowy_adres.strip(), "Typ": nowy_typ}])
                    st.session_state.kontrahenci = pd.concat([st.session_state.kontrahenci, nowy_wpis], ignore_index=True)
                    st.success(f"Podmiot {nowa_nazwa} został zapisany w CRM.")
                    st.rerun()

elif menu == "Przyjęcie Towaru (PZ)":
    st.header("Przyjęcie Zewnętrzne (PZ)")
    dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]["Nazwa"].tolist()
    if not dostawcy: st.error("Brak dostawców w CRM.")
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

# ==========================================
# MODUŁ WYDANIE TOWARU (WZ)
# ==========================================
elif menu == "Wydanie Towaru (WZ)":
    st.header("Wydanie Zewnętrzne (WZ)")
    odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
    if "wz_pdf_do_pobrania" in st.session_state:
        st.success("Zatwierdzono wydanie. Pobierz dokument WZ poniżej:")
        st.download_button(label="📥 Pobierz Dokument WZ (PDF)", data=st.session_state.wz_pdf_do_pobrania["data"], file_name=st.session_state.wz_pdf_do_pobrania["nazwa"], mime="application/pdf", type="primary", use_container_width=True)
        if st.button("Zamknij powiadomienie", use_container_width=True):
            del st.session_state.wz_pdf_do_pobrania
            st.rerun()
        st.divider()
    if not odbiorcy: st.warning("Brak odbiorców w bazie danych CRM.")
    else:
        st.subheader("1. Realizacja Zamówienia (Wczytanie z produkcji)")
        oczekujace_zk = [z for z in st.session_state.zamowienia if z["Status"] == "Gotowe do wydania"]
        if oczekujace_zk:
            opcje_zk = {f"{z['id']} | Kontrahent: {z['klient']}": z for z in oczekujace_zk}
            col_zk1, col_zk2 = st.columns([3, 1])
            with col_zk1: wybrane_zk_klucz = st.selectbox("Wybierz gotowe zamówienie z listy", ["-- Wybierz gotową partię do wysyłki --"] + list(opcje_zk.keys()))
            with col_zk2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Załaduj zamówienie na WZ", use_container_width=True):
                    if wybrane_zk_klucz != "-- Wybierz gotową partię do wysyłki --":
                        z = opcje_zk[wybrane_zk_klucz]
                        st.session_state.wybrany_klient_wz = z["klient"]
                        st.session_state.powiazane_zk = z["id"]
                        st.session_state.wz_koszyk = [{"Wariant": p["Wariant"], "Ilosc": p["Ilość (szt.)"]} for p in z["pozycje"]]
                        st.rerun()
        else: st.info("Brak wyprodukowanych zamówień oczekujących na wydanie. Możesz też wystawić WZ ręcznie z wolnego asortymentu.")
        st.divider()
        dostepne_produkty = st.session_state.produkty[st.session_state.produkty["Stan"] > 0].copy()
        if dostepne_produkty.empty and not st.session_state.wz_koszyk: st.error("Brak gotowych produktów na magazynie! Wymagana konfekcja i odbiór z hali.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
            st.subheader("2. Dane Odbiorcy i Dokumentu")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                idx_klienta = odbiorcy.index(st.session_state.wybrany_klient_wz) if st.session_state.wybrany_klient_wz in odbiorcy else 0
                wybrany_klient = st.selectbox("Nabywca (Wybierz z bazy)", odbiorcy, index=idx_klienta)
                st.session_state.wybrany_klient_wz = wybrany_klient
            with col_f2: uwagi_doc = st.text_input("Uwagi do dokumentu", value="Dostawa z magazynu głównego.")
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
            if opcje_list:
                col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                with col_p1: wybrana_opcja = st.selectbox("Wybierz asortyment z magazynu", opcje_list)
                prawdziwa_nazwa, max_dostepne = opcje_map[wybrana_opcja]
                with col_p2: ile_wydac = st.number_input("Ilość do wydania", min_value=1, max_value=max_dostepne, value=1, step=1)
                with col_p3:
                    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("Dodaj do dokumentu", use_container_width=True):
                        istnieje = False
                        for item in st.session_state.wz_koszyk:
                            if item["Wariant"] == prawdziwa_nazwa:
                                item["Ilosc"] += ile_wydac
                                istnieje = True
                                break
                        if not istnieje: st.session_state.wz_koszyk.append({"Wariant": prawdziwa_nazwa, "Ilosc": ile_wydac})
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
                            if item["Ilosc"] > stan_mag: st.error(f"Braki magazynowe dla: {item['Wariant']}."); bledy = True
                        if not bledy:
                            dane_klienta = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] == wybrany_klient].iloc[0]
                            klient_adres = dane_klienta["Adres"]
                            klient_nip = dane_klienta["NIP"]
                            font_path, font_bold_path = pobierz_czcionki()
                            pdf = FPDF()
                            pdf.add_page()
                            pdf.add_font("Roboto", "", font_path, uni=True)
                            pdf.add_font("Roboto", "B", font_bold_path, uni=True)
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
                            if st.session_state.powiazane_zk:
                                for zmw in st.session_state.zamowienia:
                                    if zmw["id"] == st.session_state.powiazane_zk: zmw["Status"] = "Zrealizowane"; break
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
                            st.session_state.wz_pdf_do_pobrania = {"nazwa": f"{nr_wz_auto.replace('/', '_')}.pdf", "data": pdf.output(dest="S").encode("latin-1")}
                            st.session_state.wz_koszyk = []
                            st.rerun()

elif menu == "Archiwum Dokumentów":
    st.header("Archiwum Dokumentów Operacyjnych i Technologicznych")
    tab_arch_pz, tab_arch_jmb, tab_arch_knf, tab_arch_okl = st.tabs(["Przyjęcia (PZ)", "Wytłaczanie JUMBO", "Konfekcja (Rozkrój)", "Oklejanie"])
    with tab_arch_pz:
        df_pz = st.session_state.historia[st.session_state.historia["Typ"] == "PZ"]
        if not df_pz.empty: st.dataframe(df_pz, use_container_width=True, hide_index=True)
        else: st.info("Brak dokumentów PZ.")
    with tab_arch_jmb:
        if st.session_state.log_jumbo: st.dataframe(pd.DataFrame(st.session_state.log_jumbo), use_container_width=True, hide_index=True)
    with tab_arch_knf:
        if st.session_state.log_konf: st.dataframe(pd.DataFrame(st.session_state.log_konf), use_container_width=True, hide_index=True)
    with tab_arch_okl:
        if st.session_state.log_okl: st.dataframe(pd.DataFrame(st.session_state.log_okl), use_container_width=True, hide_index=True)

elif menu == "Panel Administracyjny":
    st.header("Narzędzia Administracyjne")
    tab_uzytkownicy, tab_korekt_surowce, tab_korekt_prod = st.tabs(["Konta Użytkowników", "Korekta Surowców", "Korekta Wyrobów Gotowych"])
    with tab_uzytkownicy:
        with st.form("dodaj_uzytkownika"):
            login = st.text_input("Login")
            imie = st.text_input("Imię i Nazwisko")
            haslo = st.text_input("Hasło startowe", type="password")
            if st.form_submit_button("Utwórz konto"):
                if login and haslo and imie:
                    st.session_state.uzytkownicy[login.strip()] = {"haslo": haslo, "imie": imie, "uprawnienia": {"produkcja": True, "pz": True, "wz": True, "admin": False}}
                    st.success("Konto zostało pomyślnie utworzone.")
                    st.rerun()
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
