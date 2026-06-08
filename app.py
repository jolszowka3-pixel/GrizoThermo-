import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.request
from fpdf import FPDF
import json
from streamlit_gsheets import GSheetsConnection

# Konfiguracja strony
st.set_page_config(page_title="System MRP | GrizoThermo+", layout="wide")

# Inicjalizacja połączenia z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# FILTRY ZABEZPIECZAJĄCE FORMAT DANYCH Z CHMURY
# ==========================================
def bezpieczny_str(wartosc):
    if pd.isna(wartosc): return ""
    val = str(wartosc).strip()
    if val.endswith(".0"): return val[:-2]
    return val

def bezpieczny_bool(wartosc, domyslna=False):
    if pd.isna(wartosc): return domyslna
    if isinstance(wartosc, bool): return wartosc
    txt = str(wartosc).strip().upper()
    if txt in ["TRUE", "PRAWDA", "TAK", "YES", "1", "1.0"]: return True
    if txt in ["FALSE", "FAŁSZ", "FALSZ", "NIE", "NO", "0", "0.0", ""]: return False
    return domyslna

def get_col(row, col_name, domyslna=None):
    for c in row.index:
        if str(c).strip().lower() == col_name.strip().lower():
            return row[c]
    return domyslna

# ==========================================
# FUNKCJE CHMUROWE (ODCZYT / BAZA GOOGLE)
# ==========================================
def zaladuj_lub_inicjalizuj_baze():
    kolumny_historii = ["Data", "Typ", "Dokument", "Produkt/Surowiec", "Ilosc", "Użytkownik", "Kontrahent"]

    # 1. Zakładka: Uzytkownicy
    try:
        df_uz = conn.read(worksheet="Uzytkownicy", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_uz.columns]
        if df_uz.empty or "login" not in cols_lower: raise Exception()
    except:
        df_uz = pd.DataFrame([{
            "Login": "admin", "Haslo": "admin123", "Imie": "Kierownik Magazynu",
            "pulpit": True, "magazyn": True, "zk": True, "produkcja": True, "pz": True, "wz": True, "crm": True, "admin": True
        }])
    
    uzytkownicy_dict = {}
    for _, row in df_uz.iterrows():
        log_key = bezpieczny_str(get_col(row, 'login'))
        if not log_key: continue
        
        uzytkownicy_dict[log_key] = {
            "haslo": bezpieczny_str(get_col(row, 'haslo')), 
            "imie": bezpieczny_str(get_col(row, 'imie')),
            "uprawnienia": {
                "pulpit": bezpieczny_bool(get_col(row, 'pulpit', True), True),
                "magazyn": bezpieczny_bool(get_col(row, 'magazyn', True), True),
                "zk": bezpieczny_bool(get_col(row, 'zk', False)),
                "produkcja": bezpieczny_bool(get_col(row, 'produkcja', False)),
                "pz": bezpieczny_bool(get_col(row, 'pz', False)),
                "wz": bezpieczny_bool(get_col(row, 'wz', False)),
                "crm": bezpieczny_bool(get_col(row, 'crm', False)),
                "admin": bezpieczny_bool(get_col(row, 'admin', False))
            }
        }
    st.session_state.uzytkownicy = uzytkownicy_dict

    # 2. Zakładka: Kontrahenci
    try:
        df_kon = conn.read(worksheet="Kontrahenci", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_kon.columns]
        if "nazwa" not in cols_lower: raise Exception() 
        for col in df_kon.columns:
            if str(col).strip().upper() == "NIP":
                df_kon[col] = df_kon[col].apply(bezpieczny_str)
        st.session_state.kontrahenci = df_kon
    except:
        st.session_state.kontrahenci = pd.DataFrame(columns=["Nazwa", "NIP", "Adres", "Typ"])

    # 3. Zakładka: Komponenty (Surowce)
    try:
        df_komp = conn.read(worksheet="Komponenty", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_komp.columns]
        if df_komp.empty or "id" not in cols_lower: raise Exception()
        st.session_state.komponenty = df_komp
    except:
        st.session_state.komponenty = pd.DataFrame([
            {"ID": "K01", "Nazwa": "Aluminium zbrojone 1,15m", "Stan": 3200.0, "Jednostka": "mb"},
            {"ID": "K02", "Nazwa": "Barwnik biały", "Stan": 15.0, "Jednostka": "kg"},
            {"ID": "K03", "Nazwa": "Barwnik zielony", "Stan": 12.0, "Jednostka": "kg"}
        ])

    # 4. Zakładka: Polprodukty
    try:
        df_pol = conn.read(worksheet="Polprodukty", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_pol.columns]
        if df_pol.empty or "id" not in cols_lower: raise Exception()
        st.session_state.polprodukty = df_pol
    except:
        st.session_state.polprodukty = pd.DataFrame([{"ID": "P01", "Nazwa": "Rolka Jumbo (115cm x 13mb)", "Stan": 0, "Jednostka": "szt."}])

    # 5. Zakładka: Produkty (Wyroby gotowe)
    try:
        df_prod = conn.read(worksheet="Produkty", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_prod.columns]
        if df_prod.empty or "wariant" not in cols_lower: raise Exception()
        st.session_state.produkty = df_prod
    except:
        szerokosci = [10, 15, 20, 25, 30, 35, 115]
        warianty_wykonczenia = ["Oklejona", "Nieoklejona"]
        produkty_list = []
        for szer in szerokosci:
            for war in warianty_wykonczenia:
                produkty_list.append({"Wariant": f"GrizoThermo+ {szer}cm - {war} (13mb)", "Stan": 0, "Szerokosc": szer})
        st.session_state.produkty = pd.DataFrame(produkty_list)

    # 6. Zakładka: Historia
    try:
        df_hist = conn.read(worksheet="Historia", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_hist.columns]
        if df_hist.empty or "typ" not in cols_lower: raise Exception()
        st.session_state.historia = df_hist
    except:
        st.session_state.historia = pd.DataFrame(columns=kolumny_historii)

    # 7. Zakładka: Zamowienia
    try:
        df_zam = conn.read(worksheet="Zamowienia", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_zam.columns]
        if df_zam.empty or "id" not in cols_lower: raise Exception()
        zam_list = []
        for _, row_z in df_zam.iterrows():
            try: pozycje_data = json.loads(get_col(row_z, 'pozycje', '[]'))
            except: pozycje_data = []
            uwagi_val = get_col(row_z, 'uwagi', '')
            zam_list.append({
                "id": bezpieczny_str(get_col(row_z, 'id')), 
                "data": bezpieczny_str(get_col(row_z, 'data')), 
                "klient": bezpieczny_str(get_col(row_z, 'klient')),
                "pozycje": pozycje_data, 
                "uwagi": str(uwagi_val) if pd.notna(uwagi_val) else "", 
                "Status": bezpieczny_str(get_col(row_z, 'status'))
            })
        st.session_state.zamowienia = zam_list
    except:
        st.session_state.zamowienia = []

    # 8. Zakładka: ZleceniaProdukcyjne
    try:
        df_zl = conn.read(worksheet="ZleceniaProdukcyjne", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_zl.columns]
        if df_zl.empty or "id" not in cols_lower: raise Exception()
        zl_list = []
        for _, row_l in df_zl.iterrows():
            try: snap = json.loads(get_col(row_l, 'mrpsnap', '{}'))
            except: snap = {}
            try: powiazane = json.loads(get_col(row_l, 'zamowieniapowiazane', '[]'))
            except: powiazane = []
            zl_list.append({
                "id": bezpieczny_str(get_col(row_l, 'id')), 
                "data": bezpieczny_str(get_col(row_l, 'data')), 
                "mrp_snap": snap,
                "zamowienia_powiazane": powiazane, 
                "status": bezpieczny_str(get_col(row_l, 'status'))
            })
        st.session_state.zlecenia_produkcyjne = zl_list
    except:
        st.session_state.zlecenia_produkcyjne = []

    # 9. Zakładka: RejestrWZ
    try:
        df_rwz = conn.read(worksheet="RejestrWZ", ttl=0).dropna(how="all")
        cols_lower = [str(c).strip().lower() for c in df_rwz.columns]
        if df_rwz.empty or "nrwz" not in cols_lower: raise Exception()
        rwz_list = []
        for _, row_w in df_rwz.iterrows():
            try: poz = json.loads(get_col(row_w, 'pozycje', '[]'))
            except: poz = []
            uwagi_val = get_col(row_w, 'uwagi', '')
            rwz_list.append({
                "nr_wz": bezpieczny_str(get_col(row_w, 'nrwz')), 
                "data": bezpieczny_str(get_col(row_w, 'data')), 
                "klient_nazwa": bezpieczny_str(get_col(row_w, 'klientnazwa')),
                "klient_adres": bezpieczny_str(get_col(row_w, 'klientadres')), 
                "klient_nip": bezpieczny_str(get_col(row_w, 'klientnip')), 
                "pozycje": poz, 
                "uwagi": str(uwagi_val) if pd.notna(uwagi_val) else ""
            })
        st.session_state.rejestr_wz = rwz_list
    except:
        st.session_state.rejestr_wz = []

    # Liczniki operacyjne z chmury
    st.session_state.zk_counter = len(st.session_state.zamowienia) + 1
    st.session_state.wz_counter = len(st.session_state.rejestr_wz) + 1
    st.session_state.pr_counter = len(st.session_state.zlecenia_produkcyjne) + 1
    
    kolumna_typ = None
    if not st.session_state.historia.empty:
        for c in st.session_state.historia.columns:
            if str(c).strip().lower() == "typ": kolumna_typ = c; break
                
    if kolumna_typ:
        st.session_state.jumbo_counter = len(st.session_state.historia[st.session_state.historia[kolumna_typ] == "PW (Półprod.)"]) + 1
        st.session_state.konf_counter = len(st.session_state.historia[st.session_state.historia[kolumna_typ] == "PW (Gotowe)"]) + 1
        st.session_state.okl_counter = len(st.session_state.historia[st.session_state.historia[kolumna_typ] == "PW (Gotowe)"]) + 1
    else:
        st.session_state.jumbo_counter = 1
        st.session_state.konf_counter = 1
        st.session_state.okl_counter = 1

def zapisz_tabele_w_chmurze(nazwa_tabeli):
    """Wysyła zaktualizowane dane z sesji bezpośrednio do Arkusza Google"""
    try:
        if nazwa_tabeli == "Komponenty": conn.update(worksheet="Komponenty", data=st.session_state.komponenty)
        elif nazwa_tabeli == "Polprodukty": conn.update(worksheet="Polprodukty", data=st.session_state.polprodukty)
        elif nazwa_tabeli == "Produkty": conn.update(worksheet="Produkty", data=st.session_state.produkty)
        elif nazwa_tabeli == "Kontrahenci": conn.update(worksheet="Kontrahenci", data=st.session_state.kontrahenci)
        elif nazwa_tabeli == "Historia": conn.update(worksheet="Historia", data=st.session_state.historia)
        elif nazwa_tabeli == "Uzytkownicy":
            rows = []
            for log, dane in st.session_state.uzytkownicy.items():
                rows.append({
                    "Login": log, "Haslo": dane["haslo"], "Imie": dane["imie"],
                    "pulpit": dane["uprawnienia"].get("pulpit", True), "magazyn": dane["uprawnienia"].get("magazyn", True),
                    "zk": dane["uprawnienia"].get("zk", False), "produkcja": dane["uprawnienia"].get("produkcja", False),
                    "pz": dane["uprawnienia"].get("pz", False), "wz": dane["uprawnienia"].get("wz", False),
                    "crm": dane["uprawnienia"].get("crm", False), "admin": dane["uprawnienia"].get("admin", False)
                })
            conn.update(worksheet="Uzytkownicy", data=pd.DataFrame(rows))
        elif nazwa_tabeli == "Zamowienia":
            rows = []
            for z in st.session_state.zamowienia:
                rows.append({"ID": z["id"], "Data": z["data"], "Klient": z["klient"], "Pozycje": json.dumps(z["pozycje"]), "Uwagi": z["uwagi"], "Status": z["Status"]})
            df_to_save = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["ID", "Data", "Klient", "Pozycje", "Uwagi", "Status"])
            conn.update(worksheet="Zamowienia", data=df_to_save)
        elif nazwa_tabeli == "ZleceniaProdukcyjne":
            rows = []
            for j in st.session_state.zlecenia_produkcyjne:
                rows.append({"ID": j["id"], "Data": j["data"], "MrpSnap": json.dumps(j["mrp_snap"]), "ZamowieniaPowiazane": json.dumps(j["zamowienia_powiazane"]), "Status": j["status"]})
            df_to_save = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["ID", "Data", "MrpSnap", "ZamowieniaPowiazane", "Status"])
            conn.update(worksheet="ZleceniaProdukcyjne", data=df_to_save)
        elif nazwa_tabeli == "RejestrWZ":
            rows = []
            for d in st.session_state.rejestr_wz:
                rows.append({"NrWz": d["nr_wz"], "Data": d["data"], "KlientNazwa": d["klient_nazwa"], "KlientAdres": d["klient_adres"], "KlientNip": d["klient_nip"], "Pozycje": json.dumps(d["pozycje"]), "Uwagi": d["uwagi"]})
            df_to_save = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["NrWz", "Data", "KlientNazwa", "KlientAdres", "KlientNip", "Pozycje", "Uwagi"])
            conn.update(worksheet="RejestrWZ", data=df_to_save)
    except Exception as e:
        st.error(f"Błąd zapisu w chmurze (Tabela: {nazwa_tabeli}): {e}")

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
# POBIERANIE CZCIONEK Z ZABEZPIECZENIEM
# ==========================================
@st.cache_resource
def pobierz_czcionki():
    reg_path = "Roboto-Regular.ttf"
    bold_path = "Roboto-Bold.ttf"
    
    # KROK 1: Usuwamy stare, "uszkodzone" pliki (błędy pobierania Google ważą kilka bajtów)
    for path in [reg_path, bold_path]:
        if os.path.exists(path) and os.path.getsize(path) < 10000:
            try: os.remove(path)
            except: pass

    # KROK 2: Nowe, w pełni stabilne linki bezpośrednie do czcionek z oficjalnego repozytorium
    url_reg = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto-Regular.ttf"
    url_bold = "https://raw.githubusercontent.com/google/fonts/main/ofl/roboto/Roboto-Bold.ttf"
    
    if not os.path.exists(reg_path):
        try: urllib.request.urlretrieve(url_reg, reg_path)
        except: pass
    if not os.path.exists(bold_path):
        try: urllib.request.urlretrieve(url_bold, bold_path)
        except: pass
        
    return reg_path, bold_path

# ==========================================
# GENEROWANIE PLANU PRODUKCJI DLA HALI (PDF)
# ==========================================
def generuj_plan_pdf(nr_pr, data_wystawienia, mrp_snap):
    font_path, font_bold_path = pobierz_czcionki()
    pdf = FPDF()
    pdf.add_page()
    
    # Dodatkowe zabezpieczenie: jeśli pobieranie by się nie udało, wracamy do brzydszej czcionki systemowej bez błędu
    try:
        pdf.add_font("Roboto", "", font_path, uni=True)
        pdf.add_font("Roboto", "B", font_bold_path, uni=True)
        czcionka = "Roboto"
    except:
        czcionka = "Arial"
        
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(czcionka, "B", 15)
    pdf.cell(0, 12, f"PLAN PRODUKCJI DLA HALI - {nr_pr}", border=0, ln=1, align='C', fill=True)
    
    pdf.set_font(czcionka, "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Data wygenerowania: {data_wystawienia}", border=0, ln=1, align='R')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    if mrp_snap.get("brakuje_jumbo", 0) > 0:
        pdf.set_fill_color(230, 235, 245)
        pdf.set_font(czcionka, "B", 11)
        pdf.cell(0, 8, "  KROK 1: WYTŁACZANIE ROLEK JUMBO", ln=1, fill=True)
        pdf.set_font(czcionka, "B", 10)
        pdf.cell(0, 6, f"Do wyprodukowania: {mrp_snap['brakuje_jumbo']} szt. rolek Jumbo.", ln=1)
        pdf.set_font(czcionka, "", 10)
        pdf.cell(0, 6, f"- Wymagane Aluminium: {mrp_snap['req_alu']:g} mb", ln=1)
        pdf.cell(0, 6, f"- Wymagany Barwnik Bialy: {mrp_snap['req_bia']:g} kg", ln=1)
        pdf.cell(0, 6, f"- Wymagany Barwnik Zielony: {mrp_snap['req_zie']:g} kg", ln=1)
        pdf.ln(5)
        
    if mrp_snap.get("potrzeba_jmb", 0) > 0:
        pdf.set_fill_color(230, 235, 245)
        pdf.set_font(czcionka, "B", 11)
        pdf.cell(0, 8, "  KROK 2: ROZKRÓJ WZDŁUŻNY (KONFEKCJA)", ln=1, fill=True)
        pdf.set_font(czcionka, "B", 10)
        pdf.cell(0, 6, f"Lacznie do pociecia: {mrp_snap['potrzeba_jmb']} szt. rolek Jumbo.", ln=1)
        szablony = mrp_snap.get("szablony", {})
        i = 1
        for klucz, dane in szablony.items():
            wzor_txt = " | ".join([f"{qty}x {k.split(' - ')[0].replace('GrizoThermo+ ', '')}" for k, qty in dane["wzor"].items()])
            pdf.set_font(czcionka, "B", 9)
            pdf.cell(0, 6, f"SZABLON NR {i} (Ciac tak {dane['ile']} szt. rolek Jumbo):", ln=1)
            pdf.set_font(czcionka, "", 9)
            pdf.multi_cell(0, 5, f"Uklad ciecia: {wzor_txt}", border=0)
            i += 1
            pdf.ln(2)
            
    braki_okl = mrp_snap.get("braki_okl", [])
    if braki_okl:
        pdf.set_fill_color(230, 235, 245)
        pdf.set_font(czcionka, "B", 11)
        pdf.cell(0, 8, "  KROK 3: OKLEJANIE KRAWĘDZI", ln=1, fill=True)
        pdf.set_font(czcionka, "", 10)
        for b in braki_okl:
            pdf.cell(0, 6, f"- Pobrac z regalu: {b['Z_czego']} -> Okleic: {b['Brak_szt']} szt.", ln=1)
        pdf.ln(5)
    
    pdf.ln(15)
    pdf.set_font(czcionka, "", 8.5)
    pdf.cell(60, 5, "..........................................................", align='C', ln=1)
    pdf.cell(60, 5, "Podpis Odbierajacego (Kierownik Zmiany)", align='C')
    
    return pdf.output(dest="S").encode("latin-1")

# ==========================================
# FUNKCJA POMOCNICZA DO GENEROWANIA WZ PDF
# ==========================================
def generuj_wz_pdf(nr_wz, data_wydania, klient_nazwa, klient_adres, klient_nip, pozycje, uwagi):
    font_path, font_bold_path = pobierz_czcionki()
    pdf = FPDF()
    pdf.add_page()
    
    try:
        pdf.add_font("Roboto", "", font_path, uni=True)
        pdf.add_font("Roboto", "B", font_bold_path, uni=True)
        czcionka = "Roboto"
    except:
        czcionka = "Arial"
    
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(czcionka, "B", 15)
    pdf.cell(0, 12, f"WYDANIE ZEWNĘTRZNE (WZ) NR {nr_wz}", border=0, ln=1, align='C', fill=True)
    
    pdf.set_font(czcionka, "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Data wydania: {data_wydania}   |   Miejsce wystawienia: {MOJA_FIRMA['miejscowosc_wystawienia']}", border=0, ln=1, align='R')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    
    y_start = pdf.get_y()
    pdf.set_fill_color(248, 248, 248)
    pdf.set_font(czcionka, "B", 10)
    pdf.cell(90, 7, "  SPRZEDAWCA / WYSTAWCA", border=0, ln=1, fill=True)
    pdf.set_font(czcionka, "", 9)
    pdf.multi_cell(90, 5, f"{MOJA_FIRMA['nazwa']}\n{MOJA_FIRMA['adres']}\n{MOJA_FIRMA['nip']}\n{MOJA_FIRMA['kontakt']}", border=0)
    y_left = pdf.get_y()
    
    pdf.set_xy(105, y_start)
    pdf.set_font(czcionka, "B", 10)
    pdf.cell(90, 7, "  NABYWCA / ODBIORCA", border=0, ln=1, fill=True)
    pdf.set_xy(105, y_start + 7)
    pdf.set_font(czcionka, "", 9)
    nip_czysty = f"NIP: {klient_nip}" if klient_nip and str(klient_nip).strip() else ""
    pdf.multi_cell(90, 5, f"{klient_nazwa}\n{klient_adres}\n{nip_czysty}", border=0)
    y_right = pdf.get_y()
    
    pdf.set_y(max(y_left, y_right) + 12)
    pdf.set_font(czcionka, "B", 10)
    pdf.cell(0, 8, "POZYCJE DOKUMENTU", border="B", ln=1)
    pdf.ln(3)
    
    pdf.set_fill_color(230, 235, 245)
    pdf.set_font(czcionka, "B", 9)
    pdf.cell(15, 8, "Lp.", border=1, align='C', fill=True)
    pdf.cell(115, 8, "Nazwa asortymentu", border=1, align='L', fill=True)
    pdf.cell(30, 8, "Ilosc", border=1, align='C', fill=True)
    pdf.cell(30, 8, "Jm.", border=1, align='C', ln=1, fill=True)
    
    pdf.set_font(czcionka, "", 9)
    
    for lp, pozycja in enumerate(pozycje, start=1):
        pdf.cell(15, 8, str(lp), border=1, align='C')
        pdf.cell(115, 8, pozycja["Wariant"], border=1, align='L')
        pdf.cell(30, 8, str(pozycja["Ilosc"]), border=1, align='C')
        pdf.cell(30, 8, "szt.", border=1, align='C', ln=1)
    
    pdf.ln(10)
    if uwagi and uwagi.strip():
        pdf.set_font(czcionka, "B", 9)
        pdf.cell(15, 5, "Uwagi:", border=0)
        pdf.set_font(czcionka, "", 9)
        pdf.multi_cell(0, 5, uwagi.strip(), border=0)
    
    pdf.ln(25)
    y_sig = pdf.get_y()
    pdf.set_font(czcionka, "", 8.5)
    pdf.set_xy(15, y_sig)
    pdf.cell(60, 5, "..........................................................", align='C', ln=1)
    pdf.set_x(15)
    pdf.cell(60, 5, "Wystawil (osoba uprawniona)", align='C')
    
    pdf.set_xy(135, y_sig)
    pdf.cell(60, 5, "..........................................................", align='C', ln=1)
    pdf.set_x(135)
    pdf.cell(60, 5, "Odebral (czytelny podpis)", align='C')
    
    return pdf.output(dest="S").encode("latin-1")

# ==========================================
# 1. INICJALIZACJA SYSTEMU I SYNCHRONIZACJA Z CHMURĄ
# ==========================================
if 'init_v62' not in st.session_state:
    st.session_state.init_v62 = True
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    st.session_state.zk_koszyk = [] 
    st.session_state.wz_koszyk = []
    st.session_state.konf_koszyk = []
    st.session_state.powiazane_zk = None
    st.session_state.wybrany_klient_wz = None
    st.session_state.receptura_baza = {"K01": 32.00, "K02": 0.200, "K03": 0.100}
    zaladuj_lub_inicjalizuj_baze()

# ==========================================
# ZAAWANSOWANY SILNIK REZERWACJI TOWARU
# ==========================================
rezerwacje_systemowe = {}
for z in st.session_state.zamowienia:
    if z["Status"] in ["Czeka na realizację", "W produkcji", "Gotowe do wydania"]:
        for p in z["pozycje"]:
            wariant = p.get("Wariant", "")
            if wariant:
                qty = int(p.get("Ilość (szt.)", p.get("Ilosc", 0)))
                rezerwacje_systemowe[wariant] = rezerwacje_systemowe.get(wariant, 0) + qty

def dodaj_ruch(typ, dokument, nazwa, ilosc, kontrahent="-"):
    uzytkownik = st.session_state.aktualny_uzytkownik if st.session_state.aktualny_uzytkownik else "System"
    nowy_ruch = pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Typ": str(typ), "Dokument": str(dokument), "Produkt/Surowiec": str(nazwa),
        "Ilosc": float(ilosc), "Użytkownik": str(uzytkownik), "Kontrahent": str(kontrahent)
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
# MENU SIDEBAR
# ==========================================
st.sidebar.title("Nawigacja")
st.sidebar.info(f"Zalogowano jako:\n**{st.session_state.aktualny_uzytkownik}**")
if st.sidebar.button("Wyloguj", use_container_width=True):
    st.session_state.zalogowany = False
    st.session_state.aktualny_uzytkownik = None
    st.session_state.aktualne_uprawnienia = {}
    st.rerun()

st.sidebar.divider()

opcje = []
u_perms = st.session_state.aktualne_uprawnienia

if u_perms.get("pulpit", True): opcje.append("Pulpit Główny")
if u_perms.get("magazyn", True): opcje.append("Stan Magazynu")
if u_perms.get("zk", False): opcje.append("Zamówienia (ZK)")
if u_perms.get("produkcja", False): opcje.append("Moduł Production")
if u_perms.get("pz", False): opcje.append("Przyjęcie Towaru (PZ)")
if u_perms.get("wz", False): opcje.append("Wydanie Towaru (WZ)")
if u_perms.get("crm", False): opcje.append("Baza Kontrahentów (CRM)")
if u_perms.get("admin", False): opcje.append("Panel Administracyjny")

if not opcje:
    st.warning("Twoje konto nie ma przypisanych żadnych modułów. Skontaktuj się z administratorem.")
    st.stop()

menu = st.sidebar.radio("Wybierz moduł:", opcje)

if st.sidebar.button("🔄 Wymuś synchronizację z chmurą"):
    zaladuj_lub_inicjalizuj_baze()
    st.rerun()

# ==========================================
# MODUŁ 1: PULPIT GŁÓWNY (DASHBOARD)
# ==========================================
if menu == "Pulpit Główny":
    st.header("Pulpit Zarządzania: GrizoThermo+")
    
    stan_jumbo = int(st.session_state.polprodukty.loc[0, "Stan"])
    
    s_alu = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0])
    s_bia = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0])
    s_zie = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0])
    rec_alu = float(st.session_state.receptura_baza["K01"])
    rec_bia = float(st.session_state.receptura_baza["K02"])
    rec_zie = float(st.session_state.receptura_baza["K03"])
    potencjal_jumbo = int(min(s_alu / rec_alu, s_bia / rec_bia, s_zie / rec_zie))
    
    aktywne_zk = [z for z in st.session_state.zamowienia if z["Status"] != "Zrealizowane"]
    ile_aktywnych = len(aktywne_zk)

    braki_na_10 = []
    for _, row_k in st.session_state.komponenty.iterrows():
        prog_10_szt = float(st.session_state.receptura_baza.get(row_k['ID'], 0)) * 10
        aktualny_stan = float(row_k['Stan'])
        if aktualny_stan < prog_10_szt:
            brakuje = prog_10_szt - aktualny_stan
            braki_na_10.append(f"**{row_k['Nazwa']}** (Brakuje {brakuje:g} {row_k['Jednostka']} do bezpiecznego minimum 10 szt.)")

    if braki_na_10:
        st.error("⚠️ **ALERT SUROWCOWY:** Brakuje surowców do wyprodukowania 10 szt. rolek Jumbo!\n\n" + "\n".join([f"- {b}" for b in braki_na_10]))
    else:
        st.success("✅ **STATUS SUROWCÓW:** Magazyn zabezpieczony na wyprodukowanie co najmniej 10 rolek Jumbo.")

    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="metric-card" style="border-left: 5px solid #8b5cf6;"><div class="card-details">Rzeczywisty stan magazynu</div><div style="font-size: 1.8rem; font-weight: 700;">{stan_jumbo} <span style="font-size: 1rem; color: #6b7280;">rolek Jumbo</span></div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card" style="border-left: 5px solid #10b981;"><div class="card-details">Potencjał produkcyjny (z dostępnych surowców)</div><div style="font-size: 1.8rem; font-weight: 700;">{potencjal_jumbo} <span style="font-size: 1rem; color: #6b7280;">rolek Jumbo</span></div></div>', unsafe_allow_html=True)

    st.write("")
    
    st.subheader(f"🛒 Obecne zamówienia do realizacji ({ile_aktywnych})")
    if not aktywne_zk:
        st.info("Brak aktywnych zamówień. Wszystko zostało zrealizowane i wydane klientom.")
    else:
        df_aktywne = pd.DataFrame([{
            "Nr Zamówienia": z["id"], 
            "Firma zamawiająca": z["klient"], 
            "Status na produkcji": z["Status"]
        } for z in aktywne_zk])
        st.dataframe(df_aktywne, use_container_width=True, hide_index=True)

# ==========================================
# MODUŁ 2: STAN MAGAZYNU (Rezerwacje)
# ==========================================
elif menu == "Stan Magazynu":
    st.header("Ewidencja Stanów Magazynowych")
    st.write("Szczegółowy podgląd towaru dostępnego do sprzedaży vs fizycznie na regale.")
    
    tab_prod, tab_polprod, tab_komp = st.tabs([
        "Magazyn Wyrobów Gotowych", "Magazyn Półproduktów (Jumbo)", "Magazyn Surowców Bazowych"
    ])
    
    with tab_prod:
        pokaz_wszystkie = st.checkbox("Wyświetl warianty z zerowym stanem magazynowym", value=True)
        st.write("")
        for _, row in st.session_state.produkty.iterrows():
            wariant = row["Wariant"]
            stan_fizyczny = int(row["Stan"])
            zarezerwowano = rezerwacje_systemowe.get(wariant, 0)
            dostepne = stan_fizyczny - zarezerwowano
            
            if stan_fizyczny > 0 or zarezerwowano > 0 or pokaz_wszystkie:
                kolor_dost = "#dc2626" if dostepne < 0 else "#16a34a"
                st.markdown(f'''
                <div class="item-card">
                    <div class="card-title">{wariant}</div>
                    <div class="card-details" style="margin-bottom: 8px;">Szerokość handlowa: {row["Szerokosc"]} cm</div>
                    <div style="display: flex; gap: 20px; font-size: 0.95rem; background-color: #f9fafb; padding: 10px; border-radius: 4px;">
                        <div style="color: #4b5563;">📦 Stan fizyczny na regale: <b style="color: #1f2937;">{stan_fizyczny} szt.</b></div>
                        <div style="color: #4b5563;">🔒 Rezerwacje pod ZK: <b style="color: #ea580c;">{zarezerwowano} szt.</b></div>
                        <div style="color: {kolor_dost}; font-weight: 600;">✅ Dostępne od ręki: {dostepne} szt.</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

    with tab_polprod:
        st.write("")
        row_p = st.session_state.polprodukty.iloc[0]
        st.markdown(f'<div class="item-card item-card-purple"><div class="card-title">{row_p["Nazwa"]}</div><div class="card-details">Przeznaczenie: Surowiec do rozkroju wzdłużnego | Stan: {int(row_p["Stan"])} szt.</div></div>', unsafe_allow_html=True)

    with tab_komp:
        st.write("")
        for _, row in st.session_state.komponenty.iterrows():
            prog_alarmowy = float(st.session_state.receptura_baza.get(row['ID'], 0)) * 20
            aktualny_stan = float(row['Stan'])
            jest_malo = aktualny_stan < prog_alarmowy
            alert = "item-card-alert" if jest_malo else "item-card-ok"
            status_txt = "Niski stan" if jest_malo else "Zabezpieczony"
            st.markdown(f'<div class="item-card {alert}"><div class="card-title">{row["Nazwa"]}</div><div class="card-details">Stan bieżący: {aktualny_stan:g} {row["Jednostka"]} | Status operacyjny: {status_txt} (Minimum na 20 szt. Jumbo: {prog_alarmowy:g} {row["Jednostka"]})</div></div>', unsafe_allow_html=True)

# ==========================================
# MODUŁ ZAMÓWIENIA (ZK)
# ==========================================
elif menu == "Zamówienia (ZK)":
    st.header("Zamówienia Klientów (ZK)")
    
    if "zk_pdf_do_pobrania" in st.session_state:
        st.success("Zestawienie wygenerowane pomyślnie. Pobierz dokument poniżej:")
        st.download_button(
            label="📥 Pobierz Dokument PDF", data=st.session_state.zk_pdf_do_pobrania["data"],
            file_name=st.session_state.zk_pdf_do_pobrania["nazwa"], mime="application/pdf", type="primary", use_container_width=True
        )
        if st.button("Ukryj powiadomienie", use_container_width=True):
            del st.session_state.zk_pdf_do_pobrania
            st.rerun()
        st.divider()

    tab_nowe, tab_aktywne, tab_archiwum, tab_wydruk = st.tabs([
        "Wprowadź Nowe Zamówienie", "Bieżące Zamówienia", "Archiwum Zrealizowanych", "Generuj Listę (PDF)"
    ])

    with tab_nowe:
        st.subheader("Nowe Zamówienie ZK")
        odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
        if not odbiorcy: st.warning("Brak odbiorców w bazie. Przejdź do CRM.")
        else:
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_zk_auto = f"ZK/{data_dzis_str}/{st.session_state.zk_counter:03d}"
            col_zk1, col_zk2 = st.columns(2)
            klient = col_zk1.selectbox("Klient zamawiający", odbiorcy, key="zk_klient_sel")
            uwagi = col_zk2.text_input("Uwagi do zamówienia", key="zk_uwagi_in")
            
            st.divider()
            st.subheader("Dodaj produkty do zamówienia")
            
            lista_produktow_do_wyboru = []
            for _, row in st.session_state.produkty.iterrows():
                wariant = row["Wariant"]
                dostepne = int(row["Stan"]) - rezerwacje_systemowe.get(wariant, 0)
                lista_produktow_do_wyboru.append(f"{wariant} (Dostępne od ręki: {dostepne} szt.)")
            
            col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
            with col_p1: wybrana_opcja_zk = st.selectbox("Wybierz asortyment", lista_produktow_do_wyboru, key="zk_prod_sel")
            with col_p2: ilosc = st.number_input("Ilość (szt.)", min_value=1, value=1, step=1, key="zk_ilosc_in")
            with col_p3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Dodaj do zamówienia", use_container_width=True):
                    prawdziwa_nazwa_z_listy = wybrana_opcja_zk.split(" (Dostępne")[0]
                    istnieje = False
                    for item in st.session_state.zk_koszyk:
                        if item["Wariant"] == prawdziwa_nazwa_z_listy:
                            item["Ilość (szt.)"] += int(ilosc)
                            istnieje = True
                            break
                    if not istnieje: st.session_state.zk_koszyk.append({"Wariant": prawdziwa_nazwa_z_listy, "Ilość (szt.)": int(ilosc)})
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
                            "id": nr_zk_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "klient": klient,
                            "pozycje": szczegoly, "uwagi": uwagi, "Status": "Czeka na realizację"
                        })
                        st.session_state.zk_counter += 1
                        st.session_state.zk_koszyk = []
                        zapisz_tabele_w_chmurze("Zamowienia")
                        st.success(f"Zamówienie {nr_zk_auto} zostało pomyślnie zapisane w chmurze.")
                        st.rerun()

    with tab_aktywne:
        st.subheader("Zamówienia w trakcie obsługi")
        aktywne_zk = [z for z in st.session_state.zamowienia if z["Status"] != "Zrealizowane"]
        if not aktywne_zk: st.info("Brak aktywnych zamówień.")
        else:
            for z in reversed(aktywne_zk):
                with st.expander(f"{z['id']} | {z['klient']} | Data: {z['data']} | Status: {z['Status']}"):
                    st.write(f"**Uwagi:** {z['uwagi']}")
                    st.table(pd.DataFrame(z["pozycje"]).set_index("Wariant"))

    with tab_archiwum:
        st.subheader("Zrealizowane Zamówienia (Archiwum)")
        zrealizowane_zk = [z for z in st.session_state.zamowienia if z["Status"] == "Zrealizowane"]
        if not zrealizowane_zk: st.info("Brak zrealizowanych zamówień w archiwum.")
        else:
            for z in reversed(zrealizowane_zk):
                with st.expander(f"ZAKOŃCZONE: {z['id']} | {z['klient']} | Data: {z['data']}"):
                    st.write(f"**Uwagi:** {z['uwagi']}")
                    st.table(pd.DataFrame(z["pozycje"]).set_index("Wariant"))

    with tab_wydruk:
        st.subheader("Wydruk Zbiorczej Listy Zamówień")
        if st.button("Generuj listę zamówień (PDF)", type="primary"):
            if not st.session_state.zamowienia: st.error("Brak zamówień.")
            else:
                font_path, font_bold_path = pobierz_czcionki()
                pdf = FPDF()
                pdf.add_page()
                try:
                    pdf.add_font("Roboto", "", font_path, uni=True)
                    pdf.add_font("Roboto", "B", font_bold_path, uni=True)
                    czcionka = "Roboto"
                except:
                    czcionka = "Arial"
                pdf.set_fill_color(240, 240, 240)
                pdf.set_font(czcionka, "B", 14)
                pdf.cell(0, 12, "ZBIORCZA LISTA ZAMÓWIEŃ (ZK)", border=0, ln=1, align='C', fill=True)
                pdf.set_font(czcionka, "", 9)
                pdf.cell(0, 6, f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", border=0, ln=1, align='C')
                pdf.ln(6)
                for z in reversed(st.session_state.zamowienia):
                    pdf.set_font(czcionka, "B", 10)
                    pdf.set_fill_color(248, 248, 248)
                    pdf.cell(0, 8, f" {z['id']} | Klient: {z['klient']} | Status: {z['Status']}", border=1, ln=1, fill=True)
                    pdf.set_font(czcionka, "", 9)
                    for p in z['pozycje']:
                        pdf.cell(10, 6, "-", align='R')
                        pdf.cell(120, 6, p['Wariant'])
                        pdf.cell(40, 6, f"{p['Ilość (szt.)']} szt.", ln=1)
                st.session_state.zk_pdf_do_pobrania = {"nazwa": "Zbiorcza_Lista_Zamowien.pdf", "data": pdf.output(dest="S").encode("latin-1")}
                st.rerun()

# ==========================================
# MODUŁ PRODUKCJI I PLANOWANIA ZAPOTRZEBOWANIA
# ==========================================
elif menu == "Moduł Production":
    st.header("Zarządzanie Produkcją i Planowanie")
    oczekujace = [z for z in st.session_state.zamowienia if z["Status"] == "Czeka na realizację"]
    mrp_data = None
    
    if oczekujace:
        zapotrzebowanie = {}
        for z in oczekujace:
            for p in z["pozycje"]:
                wariant = p["Wariant"]
                zapotrzebowanie[wariant] = zapotrzebowanie.get(wariant, 0) + int(p["Ilość (szt.)"])
                
        braki_do_oklejenia = []
        braki_do_rozkroju = []
        szerokosci_baza = [10, 15, 20, 25, 30, 35, 115]
        for szer in szerokosci_baza:
            war_okl = f"GrizoThermo+ {szer}cm - Oklejona (13mb)"
            war_nie = f"GrizoThermo+ {szer}cm - Nieoklejona (13mb)"
            dem_okl = zapotrzebowanie.get(war_okl, 0)
            dem_nie = zapotrzebowanie.get(war_nie, 0)
            stock_okl = int(st.session_state.produkty[st.session_state.produkty["Wariant"] == war_okl]["Stan"].values[0])
            stock_nie = int(st.session_state.produkty[st.session_state.produkty["Wariant"] == war_nie]["Stan"].values[0])
            
            brakuje_okl = max(0, dem_okl - stock_okl)
            brakuje_nie = max(0, dem_nie - stock_nie)
            nadwyzka_nie = max(0, stock_nie - dem_nie)
            
            if brakuje_okl > 0: braki_do_oklejenia.append({"Wariant": war_okl, "Brak_szt": int(brakuje_okl), "Z_czego": war_nie})
            pokryte_z_mag_nieokl = min(brakuje_okl, nadwyzka_nie)
            do_wyciecia_łącznie = brakuje_nie + (brakuje_okl - pokryte_z_mag_nieokl)
            if do_wyciecia_łącznie > 0: braki_do_rozkroju.append({"Wariant": war_nie, "Brak_szt": int(do_wyciecia_łącznie), "Szerokosc": int(szer)})
        
        items_to_pack = []
        for b in braki_do_rozkroju: items_to_pack.extend([(b["Wariant"], b["Szerokosc"])] * b["Brak_szt"])
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
            used_cm, count, i = 0, 0, 0
            while i < len(items_to_pack):
                nazwa, szer = items_to_pack[i]
                if is_valid_partial(used_cm + szer, count + 1):
                    rolka[nazwa] = rolka.get(nazwa, 0) + 1
                    used_cm += szer
                    count += 1
                    items_to_pack.pop(i)
                    if used_cm == 115 or count == 6: break
                else: i += 1
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
        
        req_alu = float(brakuje_jumbo * st.session_state.receptura_baza["K01"])
        req_bia = float(brakuje_jumbo * st.session_state.receptura_baza["K02"])
        req_zie = float(brakuje_jumbo * st.session_state.receptura_baza["K03"])
        stan_alu = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0])
        stan_bia = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0])
        stan_zie = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0])
        gotowe_do_auto = bool(stan_alu >= req_alu and stan_bia >= req_bia and stan_zie >= req_zie)

        zliczone_szablony = {}
        for r in plan_rolek:
            klucz = str(dict(sorted(r.items())))
            if klucz not in zliczone_szablony: zliczone_szablony[klucz] = {"wzor": r, "ile": 1}
            else: zliczone_szablony[klucz]["ile"] += 1
                
        mrp_data = {
            "braki_okl": braki_do_oklejenia, 
            "braki_nie": braki_do_rozkroju, 
            "potrzeba_jmb": int(potrzeba_jumbo_calkowita),
            "s_jumbo_akt": int(s_jumbo_akt), 
            "brakuje_jumbo": int(brakuje_jumbo), 
            "req_alu": float(req_alu), 
            "req_bia": float(req_bia), 
            "req_zie": float(req_zie),
            "szablony": zliczone_szablony, 
            "plan_rolek": plan_rolek, 
            "gotowe_do_auto": bool(gotowe_do_auto)
        }

    if "plan_hali_do_pobrania" in st.session_state:
        st.success(f"⚙️ Plan został pomyślnie wygenerowany i wysłany do realizacji!")
        st.download_button(
            label="📥 POBIERZ DOKUMENT PLANU DLA HALI (PDF)", data=st.session_state.plan_hali_do_pobrania["data"],
            file_name=st.session_state.plan_hali_do_pobrania["nazwa"], mime="application/pdf", type="primary", use_container_width=True
        )
        if st.button("Zamknij to powiadomienie", use_container_width=True):
            del st.session_state.plan_hali_do_pobrania
            st.rerun()
        st.divider()

    tab_plan, tab1, tab2, tab3, tab4 = st.tabs([
        "Panel MRP (Analiza)", "Krok 1: Wytłaczanie RĘCZNIE", "Krok 2: Rozkrój RĘCZNY", "Krok 3: Oklejanie RĘCZNIE", "🏭 Krok 4: Odbiór z Produkcji"
    ])
    
    with tab_plan:
        st.subheader("Inteligentna Analiza Zapotrzebowania (MRP)")
        if not mrp_data: st.info("Brak nowych zamówień oczekujących na realizację.")
        else:
            if not mrp_data["braki_okl"] and not mrp_data["braki_nie"]:
                st.success("Magazyn pokrywa zapotrzebowanie.")
                if st.button("Oznacz jako Gotowe do Wydania", type="primary", use_container_width=True):
                    for z in oczekujace: z["Status"] = "Gotowe do wydania"
                    zapisz_tabele_w_chmurze("Zamowienia")
                    st.rerun()
            else:
                st.error("Wykryto braki asortymentu.")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.write("**Wymagany KROK 2: Rozkrój**")
                    if mrp_data["braki_nie"]: st.dataframe(pd.DataFrame(mrp_data["braki_nie"])[["Wariant", "Brak_szt"]], hide_index=True)
                with col_b2:
                    st.write("**Wymagany KROK 3: Oklejanie**")
                    if mrp_data["braki_okl"]: st.dataframe(pd.DataFrame(mrp_data["braki_okl"])[["Wariant", "Brak_szt"]], hide_index=True)

                st.divider()
                st.write(f"Łącznie potrzeba: **{mrp_data['potrzeba_jmb']} szt. rolek Jumbo**.")
                
                if mrp_data["brakuje_jumbo"] > 0:
                    st.warning(f"Zlecenia wymagają wytłoczenia dodatkowych **{mrp_data['brakuje_jumbo']} szt.** rolek Jumbo na Maszynie Głównej.")
                    if mrp_data["gotowe_do_auto"]: st.success("Magazyn surowców w pełni pokrywa zapotrzebowanie.")
                    else: st.error("BRAK SUROWCÓW do wytłoczenia potrzebnych rolek Jumbo!")
                
                if mrp_data["potrzeba_jmb"] > 0:
                    st.write("")
                    st.subheader("Zoptymalizowany Plan Konfekcji (KROK 2)")
                    for i, (_, dane) in enumerate(mrp_data["szablony"].items()):
                        wzor_txt = " | ".join([f"{qty}x {k.split(' - ')[0].replace('GrizoThermo+ ', '')}" for k, qty in dane["wzor"].items()])
                        st.markdown(f"**SZABLON {i+1}** (Użyj na **{dane['ile']} szt.** rolek Jumbo): {wzor_txt}")
                    
                st.divider()
                if mrp_data["gotowe_do_auto"]:
                    if st.button("Zatwierdź Plan, wyślij na Halę i generuj PDF", type="primary", use_container_width=True):
                        data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                        nr_pr_auto = f"PR/{data_dzis_str}/{st.session_state.pr_counter:03d}"
                        
                        st.session_state.zlecenia_produkcyjne.append({
                            "id": nr_pr_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "mrp_snap": mrp_data, 
                            "zamowienia_powiazane": [z["id"] for z in oczekujace], "status": "W toku"
                        })
                        st.session_state.pr_counter += 1
                        for z in oczekujace: z["Status"] = "W produkcji"
                            
                        zapisz_tabele_w_chmurze("ZleceniaProdukcyjne")
                        zapisz_tabele_w_chmurze("Zamowienia")
                        
                        pdf_data = generuj_plan_pdf(nr_pr_auto, datetime.now().strftime("%Y-%m-%d %H:%M"), mrp_data)
                        
                        st.session_state.plan_hali_do_pobrania = {
                            "nazwa": f"Plan_Produkcji_{nr_pr_auto.replace('/', '_')}.pdf", "data": pdf_data
                        }
                        st.rerun()

    with tab1:
        st.subheader("Wytłaczanie Rolek Jumbo - RĘCZNIE")
        s_alu_manual = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K01", "Stan"].values[0])
        s_bia_manual = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K02", "Stan"].values[0])
        s_zie_manual = float(st.session_state.komponenty.loc[st.session_state.komponenty["ID"] == "K03", "Stan"].values[0])
        m_alu_m = int(s_alu_manual / float(st.session_state.receptura_baza["K01"]))
        m_bia_m = int(s_bia_manual / float(st.session_state.receptura_baza["K02"]))
        m_zie_m = int(s_zie_manual / float(st.session_state.receptura_baza["K03"]))
        m_jumbo = min(m_alu_m, m_bia_m, m_zie_m)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Aluminium wystarczy na:", f"{m_alu_m} szt. Jumbo")
        c2.metric("Barwnik biały wystarczy na:", f"{m_bia_m} szt. Jumbo")
        c3.metric("Barwnik zielony wystarczy na:", f"{m_zie_m} szt. Jumbo")
        
        if m_jumbo > 0:
            with st.form("prod_jumbo"):
                ile_jumbo = st.number_input("Ile Rolek Jumbo wyprodukowano?", min_value=1, max_value=m_jumbo, value=1)
                if st.form_submit_button("Zaksięguj produkcję (ręcznie)"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                    st.session_state.polprodukty.at[0, "Stan"] += int(ile_jumbo)
                    dodaj_ruch("PW (Półprod.)", nr_jmb_auto, st.session_state.polprodukty.at[0, "Nazwa"], int(ile_jumbo), "Wytłaczarka")
                    for k_id, zuzycie in st.session_state.receptura_baza.items():
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                        laczne_zuzycie = float(zuzycie * ile_jumbo)
                        st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                        dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Wytłaczarka")
                    st.session_state.jumbo_counter += 1
                    zapisz_tabele_w_chmurze("Polprodukty")
                    zapisz_tabele_w_chmurze("Komponenty")
                    zapisz_tabele_w_chmurze("Historia")
                    st.success("Zaksięgowano.")
                    st.rerun()

    with tab2:
        st.subheader("Konfekcja (Rozkrój) - RĘCZNIE")
        df_nieoklejone = st.session_state.produkty[st.session_state.produkty['Wariant'].str.contains("Nieoklejona")]
        rozkroj_temp = {}
        for idx, r in df_nieoklejone.iterrows(): rozkroj_temp[idx] = st.number_input(r['Wariant'], min_value=0, value=0, key=f"r_temp_{idx}")
        if st.button("Zatwierdź rozkrój ręczny"):
            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
            nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
            st.session_state.polprodukty.at[0, "Stan"] -= 1
            for idx_nazwa, qty in rozkroj_temp.items():
                if qty > 0:
                    st.session_state.produkty.at[idx_nazwa, "Stan"] += int(qty)
                    dodaj_ruch("PW (Gotowe)", nr_knf_auto, st.session_state.produkty.at[idx_nazwa, 'Wariant'], int(qty), "Konfekcja")
            st.session_state.konf_counter += 1
            zapisz_tabele_w_chmurze("Polprodukty")
            zapisz_tabele_w_chmurze("Produkty")
            zapisz_tabele_w_chmurze("Historia")
            st.success("Zapisano.")
            st.rerun()

    with tab3:
        st.subheader("Oklejanie - RĘCZNIE (Zabezpieczone rezerwacjami)")
        dostepne_do_oklejenia = []
        for _, r in st.session_state.produkty.iterrows():
            if "Nieoklejona" in r['Wariant']:
                wariant_nieokl = r['Wariant']
                stan_fiz = int(r['Stan'])
                zarezerw = rezerwacje_systemowe.get(wariant_nieokl, 0)
                wolne = stan_fiz - zarezerw
                if wolne > 0:
                    dostepne_do_oklejenia.append({"Wariant": wariant_nieokl, "Dostepne": wolne, "Szerokosc": int(r['Szerokosc'])})
                    
        if not dostepne_do_oklejenia:
            st.info("Brak wolnych (niezarezerwowanych) rolek nieoklejonych na magazynie, by przesłać je na okleiniarkę.")
        else:
            with st.form("form_oklejanie"):
                opcje_okl = [f"{x['Szerokosc']}cm (Wolne szt.: {x['Dostepne']})" for x in dostepne_do_oklejenia]
                wybrana_opcja = st.selectbox("Wybierz szerokość do oklejenia:", opcje_okl)
                szerokosc_wybrana = int(wybrana_opcja.split("cm")[0])
                max_dost = int(wybrana_opcja.split("Wolne szt.: ")[1].split(")")[0])
                ile_okleic = st.number_input("Ilość do oklejenia:", min_value=1, max_value=max_dost, value=1)
                if st.form_submit_button("Zatwierdź oklejanie"):
                    data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                    nr_okl_auto = f"PR-OKL/{data_dzis_str}/{st.session_state.okl_counter:03d}"
                    idx_nie = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == f"GrizoThermo+ {szerokosc_wybrana}cm - Nieoklejona (13mb)"][0]
                    idx_okl = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == f"GrizoThermo+ {szerokosc_wybrana}cm - Oklejona (13mb)"][0]
                    st.session_state.produkty.at[idx_nie, "Stan"] -= int(ile_okleic)
                    st.session_state.produkty.at[idx_okl, "Stan"] += int(ile_okleic)
                    dodaj_ruch("RW", nr_okl_auto, f"GrizoThermo+ {szerokosc_wybrana}cm - Nieoklejona (13mb)", int(ile_okleic), "Hala")
                    st.session_state.okl_counter += 1
                    zapisz_tabele_w_chmurze("Produkty")
                    zapisz_tabele_w_chmurze("Historia")
                    st.success("Zakończono. Towar został przeksiegowany na wariant oklejony.")
                    st.rerun()

    with tab4:
        st.subheader("Potwierdzenie Wykonania i Odbiór Towaru z Hali")
        zlecenia_w_toku = [j for j in st.session_state.zlecenia_produkcyjne if str(j.get("status")) == "W toku"]
        if not zlecenia_w_toku: st.info("Brak aktywnych planów na hali.")
        else:
            for job in zlecenia_w_toku:
                with st.expander(f"📋 Zlecenie: {job['id']} | Powiązane ZK: {', '.join(job['zamowienia_powiazane'])}"):
                    snap = job["mrp_snap"]
                    if st.button(f"🟢 POTWIERDŹ ZAKOŃCZENIE ZLECENIA {job['id']}", key=f"conf_job_{job['id']}", type="primary", use_container_width=True):
                        data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                        if snap["brakuje_jumbo"] > 0:
                            bj = int(snap["brakuje_jumbo"])
                            nr_jmb_auto = f"PR-JMB/{data_dzis_str}/{st.session_state.jumbo_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] += bj
                            dodaj_ruch("PW (Półprod.)", nr_jmb_auto, st.session_state.polprodukty.at[0, "Nazwa"], bj, "Hala-Planer")
                            for k_id, zuzycie in st.session_state.receptura_baza.items():
                                idx = st.session_state.komponenty.index[st.session_state.komponenty["ID"] == k_id][0]
                                laczne_zuzycie = float(zuzycie * bj)
                                st.session_state.komponenty.at[idx, "Stan"] -= laczne_zuzycie
                                dodaj_ruch("RW", nr_jmb_auto, st.session_state.komponenty.at[idx, "Nazwa"], laczne_zuzycie, "Hala-Planer")
                            st.session_state.jumbo_counter += 1
                            
                        if snap["potrzeba_jmb"] > 0:
                            pj = int(snap["potrzeba_jmb"])
                            nr_knf_auto = f"PR-KNF/{data_dzis_str}/{st.session_state.konf_counter:03d}"
                            st.session_state.polprodukty.at[0, "Stan"] -= pj
                            dodaj_ruch("RW (Półprod.)", nr_knf_auto, "Rolka Jumbo (115cm x 13mb)", pj, "Hala-Planer")
                            temp_produced = {}
                            for r in snap["plan_rolek"]:
                                for n, q in r.items(): temp_produced[n] = temp_produced.get(n, 0) + int(q)
                            for nazwa_gotowego, total_qty in temp_produced.items():
                                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_gotowego][0]
                                st.session_state.produkty.at[idx, "Stan"] += int(total_qty)
                                dodaj_ruch("PW (Gotowe)", nr_knf_auto, nazwa_gotowego, int(total_qty), "Hala-Planer")
                            st.session_state.konf_counter += 1
                            
                        if snap["braki_okl"]:
                            nr_okl_auto = f"PR-OKL/{data_dzis_str}/{st.session_state.okl_counter:03d}"
                            for b in snap["braki_okl"]:
                                idx_nie = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Z_czego"]][0]
                                idx_okl = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == b["Wariant"]][0]
                                st.session_state.produkty.at[idx_nie, "Stan"] -= int(b["Brak_szt"])
                                st.session_state.produkty.at[idx_okl, "Stan"] += int(b["Brak_szt"])
                            st.session_state.okl_counter += 1
                            
                        job["status"] = "Zakończone"
                        for zmw in st.session_state.zamowienia:
                            if zmw["id"] in job["zamowienia_powiazane"]: zmw["Status"] = "Gotowe do wydania"
                        
                        zapisz_tabele_w_chmurze("Komponenty")
                        zapisz_tabele_w_chmurze("Polprodukty")
                        zapisz_tabele_w_chmurze("Produkty")
                        zapisz_tabele_w_chmurze("ZleceniaProdukcyjne")
                        zapisz_tabele_w_chmurze("Zamowienia")
                        zapisz_tabele_w_chmurze("Historia")
                        st.success("Zrealizowano pomyślnie. Towar trafił na magazyn.")
                        st.rerun()

elif menu == "Baza Kontrahentów (CRM)":
    st.header("Zarządzanie Bazą Kontrahentów (CRM)")
    
    if "crm_edycja_nazwa" not in st.session_state: st.session_state.crm_edycja_nazwa = None
    
    tab_przeglad, tab_dodaj = st.tabs(["📋 Rejestr i Modyfikacja Firm", "➕ Dodaj Nowy Podmiot"])
    
    with tab_przeglad:
        filtr_typ = st.radio("Filtruj:", ["Wszystkie podmioty", "Klienci (Odbiorcy)", "Dostawcy surowców"], horizontal=True)
        df_crm = st.session_state.kontrahenci.copy()
        
        if not df_crm.empty:
            if filtr_typ == "Klienci (Odbiorcy)": df_crm = df_crm[df_crm["Typ"] == "Odbiorca"]
            elif filtr_typ == "Dostawcy surowców": df_crm = df_crm[df_crm["Typ"] == "Dostawca"]
            
        if df_crm.empty:
            st.info("Brak podmiotów spełniających wybrane kryteria.")
        else:
            for _, row in df_crm.iterrows():
                firma_nazwa = row["Nazwa"]
                col_dane, col_akcje = st.columns([4, 1])
                with col_dane:
                    border_style = "item-card-purple" if row["Typ"] == "Dostawca" else "item-card"
                    st.markdown(f'<div class="{border_style}"><div class="card-title">{row["Nazwa"]}</div></div>', unsafe_allow_html=True)
                with col_akcje:
                    c_edit, c_del = st.columns(2)
                    if c_edit.button("✏️", key=f"edit_btn_{firma_nazwa}"): 
                        st.session_state.crm_edycja_nazwa = firma_nazwa
                        st.rerun()
                    if c_del.button("🗑️", key=f"del_btn_{firma_nazwa}"):
                        st.session_state.kontrahenci = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] != firma_nazwa].reset_index(drop=True)
                        zapisz_tabele_w_chmurze("Kontrahenci")
                        st.rerun()
                        
        if st.session_state.crm_edycja_nazwa is not None:
            firma_dane = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] == st.session_state.crm_edycja_nazwa].iloc[0]
            with st.form("edycja_firmy_form"):
                e_nazwa = st.text_input("Nazwa", value=firma_dane["Nazwa"])
                e_nip = st.text_input("NIP", value=firma_dane["NIP"])
                e_adres = st.text_input("Adres", value=firma_dane["Adres"])
                e_typ = st.selectbox("Typ", ["Odbiorca", "Dostawca"], index=0 if firma_dane["Typ"] == "Odbiorca" else 1)
                if st.form_submit_button("Zapisz"):
                    idx_prawdziwy = st.session_state.kontrahenci.index[st.session_state.kontrahenci["Nazwa"] == st.session_state.crm_edycja_nazwa][0]
                    st.session_state.kontrahenci.at[idx_prawdziwy, "Nazwa"] = e_nazwa.strip()
                    st.session_state.kontrahenci.at[idx_prawdziwy, "NIP"] = e_nip.strip()
                    st.session_state.kontrahenci.at[idx_prawdziwy, "Adres"] = e_adres.strip()
                    st.session_state.kontrahenci.at[idx_prawdziwy, "Typ"] = e_typ
                    st.session_state.crm_edycja_nazwa = None
                    zapisz_tabele_w_chmurze("Kontrahenci")
                    st.rerun()

    with tab_dodaj:
        with st.form("nowy_kontrahent_rozbudowany_form"):
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                nowa_nazwa = st.text_input("🏢 Nazwa *")
                nowy_nip = st.text_input("📌 NIP")
            with col_form2:
                nowy_typ = st.selectbox("🏷️ Typ", ["Odbiorca", "Dostawca"])
                nowy_adres = st.text_input("📍 Adres *")
            if st.form_submit_button("Zapisz w CRM", type="primary"):
                if nowa_nazwa.strip() and nowy_adres.strip():
                    nowy_wpis = pd.DataFrame([{"Nazwa": nowa_nazwa.strip(), "NIP": nowy_nip.strip(), "Adres": nowy_adres.strip(), "Typ": nowy_typ}])
                    st.session_state.kontrahenci = pd.concat([st.session_state.kontrahenci, nowy_wpis], ignore_index=True)
                    zapisz_tabele_w_chmurze("Kontrahenci")
                    st.success("Zapisano.")
                    st.rerun()
                else: st.error("Pola 'Nazwa firmy' oraz 'Adres siedziby' są obowiązkowe.")

elif menu == "Przyjęcie Towaru (PZ)":
    st.header("Przyjęcie Zewnętrzne (PZ)")
    tab_nowe_pz, tab_rejestr_pz = st.tabs(["Wprowadź Dokument PZ", "🗂️ Rejestr Dokumentów PZ"])
    with tab_nowe_pz:
        if st.session_state.kontrahenci.empty:
            st.error("Brak dostawców w CRM.")
        else:
            dostawcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Dostawca"]["Nazwa"].tolist()
            if dostawcy:
                with st.form("pz"):
                    n = st.text_input("Numer dokumentu")
                    d = st.selectbox("Dostawca", dostawcy)
                    k = st.selectbox("Surowiec", st.session_state.komponenty["Nazwa"].tolist())
                    i = st.number_input("Ilość", min_value=0.1, value=100.0)
                    if st.form_submit_button("Zatwierdź"):
                        idx = st.session_state.komponenty.index[st.session_state.komponenty["Nazwa"] == k][0]
                        st.session_state.komponenty.at[idx, "Stan"] += float(i)
                        dodaj_ruch("PZ", n, k, float(i), d)
                        zapisz_tabele_w_chmurze("Komponenty")
                        zapisz_tabele_w_chmurze("Historia")
                        st.success("Zapisano.")
                        st.rerun()
            else:
                st.error("Brak dostawców w CRM.")
    with tab_rejestr_pz:
        df_pz = st.session_state.historia[st.session_state.historia["Typ"] == "PZ"]
        if not df_pz.empty: st.dataframe(df_pz.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True)

elif menu == "Wydanie Towaru (WZ)":
    st.header("Wydanie Zewnętrzne (WZ)")
    tab_nowe_wz, tab_rejestr_wz = st.tabs(["Wprowadź Dokument WZ", "🗂️ Rejestr Dokumentów WZ / Ponowny Wydruk"])
    with tab_nowe_wz:
        if st.session_state.kontrahenci.empty:
            st.warning("Brak odbiorców w bazie danych CRM.")
            odbiorcy = []
        else:
            odbiorcy = st.session_state.kontrahenci[st.session_state.kontrahenci["Typ"] == "Odbiorca"]["Nazwa"].tolist()
            
        if "wz_pdf_do_pobrania" in st.session_state:
            st.success("Zatwierdzono wydanie. Pobierz dokument WZ poniżej:")
            st.download_button(label="📥 Pobierz Dokument WZ (PDF)", data=st.session_state.wz_pdf_do_pobrania["data"], file_name=st.session_state.wz_pdf_do_pobrania["nazwa"], mime="application/pdf", type="primary", use_container_width=True)
            if st.button("Zamknij powiadomienie", use_container_width=True): del st.session_state.wz_pdf_do_pobrania; st.rerun()
        
        if odbiorcy:
            oczekujace_zk = [z for z in st.session_state.zamowienia if z["Status"] == "Gotowe do wydania"]
            if oczekujace_zk:
                opcje_zk = {f"{z['id']} | Kontrahent: {z['klient']}": z for z in oczekujace_zk}
                wybrane_zk_klucz = st.selectbox("Wybierz gotowe zamówienie z listy", ["-- Wybierz --"] + list(opcje_zk.keys()))
                if st.button("Załaduj zamówienie na WZ"):
                    if wybrane_zk_klucz != "-- Wybierz --":
                        z = opcje_zk[wybrane_zk_klucz]
                        st.session_state.wybrany_klient_wz = z["klient"]
                        st.session_state.powiazane_zk = z["id"]
                        st.session_state.wz_koszyk = [{"Wariant": p["Wariant"], "Ilosc": int(p["Ilość (szt.)"])} for p in z["pozycje"]]
                        st.rerun()
            
            idx_klienta = 0
            if st.session_state.wybrany_klient_wz and st.session_state.wybrany_klient_wz in odbiorcy:
                idx_klienta = odbiorcy.index(st.session_state.wybrany_klient_wz)
            
            wybrany_klient = st.selectbox("Nabywca", odbiorcy, index=idx_klienta)
            uwagi_doc = st.text_input("Uwagi", value="Dostawa z magazynu głównego.")
            
            dostepne_opcje = []
            dostepnosci_map = {}
            for _, row in st.session_state.produkty.iterrows():
                wariant_nazwa = row["Wariant"]
                stan_fizyczny = int(row["Stan"])
                zarezerwowane = rezerwacje_systemowe.get(wariant_nazwa, 0)
                w_koszyku_juz_jest = sum([x["Ilosc"] for x in st.session_state.wz_koszyk if x["Wariant"] == wariant_nazwa])
                
                wolne_dostepne = stan_fizyczny - zarezerwowane - w_koszyku_juz_jest
                if wolne_dostepne > 0:
                    opcja_string = f"{wariant_nazwa} (Dostępne z wolnej puli: {wolne_dostepne} szt.)"
                    dostepne_opcje.append(opcja_string)
                    dostepnosci_map[opcja_string] = wolne_dostepne
            
            if dostepne_opcje:
                wybrana_opcja = st.selectbox("Wybierz asortyment z magazynu (tylko wolne stany)", dostepne_opcje)
                max_w_opcji = dostepnosci_map[wybrana_opcja]
                ile_w = st.number_input("Ilość do wydania", min_value=1, max_value=max_w_opcji, value=1)
                if st.button("Dodaj do dokumentu"):
                    prawdziwa_nazwa = wybrana_opcja.split(" (Dostępne")[0]
                    istnieje = False
                    for item in st.session_state.wz_koszyk:
                        if item["Wariant"] == prawdziwa_nazwa:
                            item["Ilosc"] += int(ile_w)
                            istnieje = True
                            break
                    if not istnieje:
                        st.session_state.wz_koszyk.append({"Wariant": prawdziwa_nazwa, "Ilosc": int(ile_w)})
                    st.rerun()
            else:
                st.info("Brak wolnego asortymentu do wydania z ręki (cały magazyn jest pusty, w całości zarezerwowany pod ZK, lub wszystko jest w koszyku).")
                
            if st.session_state.wz_koszyk:
                st.dataframe(pd.DataFrame(st.session_state.wz_koszyk))
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Wyczyść koszyk", use_container_width=True):
                        st.session_state.wz_koszyk = []
                        st.rerun()
                with col_btn2:
                    if st.button("Zatwierdź wydanie i generuj PDF", type="primary", use_container_width=True):
                        braki_wz = []
                        for pozycja in st.session_state.wz_koszyk:
                            nazwa_w = pozycja["Wariant"]
                            ile_w = pozycja["Ilosc"]
                            idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_w][0]
                            if int(st.session_state.produkty.at[idx, "Stan"]) < ile_w:
                                braki_wz.append(nazwa_w)
                                
                        if braki_wz:
                            st.error(f"Operacja odrzucona! Brak fizycznego towaru na regale dla: {', '.join(braki_wz)}. Prawdopodobnie towar został wydany w międzyczasie.")
                        else:
                            data_dzis_str = datetime.now().strftime("%Y/%m/%d")
                            nr_wz_auto = f"WZ/{data_dzis_str}/{st.session_state.wz_counter:03d}"
                            
                            dane_klienta = st.session_state.kontrahenci[st.session_state.kontrahenci["Nazwa"] == wybrany_klient].iloc[0]
                            klient_adres = dane_klienta["Adres"]
                            klient_nip = dane_klienta["NIP"]
                            for pozycja in st.session_state.wz_koszyk:
                                nazwa_w = pozycja["Wariant"]
                                ile_w = pozycja["Ilosc"]
                                idx = st.session_state.produkty.index[st.session_state.produkty["Wariant"] == nazwa_w][0]
                                st.session_state.produkty.at[idx, "Stan"] -= int(ile_w)
                                dodaj_ruch("WZ", nr_wz_auto, nazwa_w, int(ile_w), wybrany_klient)
                            
                            st.session_state.rejestr_wz.append({
                                "nr_wz": nr_wz_auto, "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "klient_nazwa": wybrany_klient,
                                "klient_adres": klient_adres, "klient_nip": klient_nip, "pozycje": st.session_state.wz_koszyk.copy(), "uwagi": uwagi_doc
                            })
                            st.session_state.wz_counter += 1
                            
                            if st.session_state.powiazane_zk:
                                for zmw in st.session_state.zamowienia:
                                    if zmw["id"] == st.session_state.powiazane_zk: zmw["Status"] = "Zrealizowane"; break
                                st.session_state.powiazane_zk = None
                                st.session_state.wybrany_klient_wz = None
                            
                            zapisz_tabele_w_chmurze("Produkty")
                            zapisz_tabele_w_chmurze("RejestrWZ")
                            zapisz_tabele_w_chmurze("Zamowienia")
                            zapisz_tabele_w_chmurze("Historia")
                            
                            pdf_data = generuj_wz_pdf(nr_wz_auto, datetime.now().strftime("%Y-%m-%d"), wybrany_klient, klient_adres, klient_nip, st.session_state.rejestr_wz[-1]["pozycje"], uwagi_doc)
                            st.session_state.wz_pdf_do_pobrania = {"nazwa": f"{nr_wz_auto.replace('/', '_')}.pdf", "data": pdf_data}
                            st.session_state.wz_koszyk = []
                            st.rerun()
    with tab_rejestr_wz:
        for dokument in reversed(st.session_state.rejestr_wz):
            with st.expander(f"📄 {dokument['nr_wz']} | {dokument['klient_nazwa']}"):
                st.dataframe(pd.DataFrame(dokument["pozycje"]), hide_index=True)
                pdf_ponowny = generuj_wz_pdf(dokument['nr_wz'], dokument['data'].split(" ")[0], dokument['klient_nazwa'], dokument['klient_adres'], dokument['klient_nip'], dokument['pozycje'], dokument['uwagi'])
                st.download_button(label="📥 Pobierz ponownie PDF", data=pdf_ponowny, file_name=f"Kopia_{dokument['nr_wz'].replace('/', '_')}.pdf", mime="application/pdf", key=f"reprint_{dokument['nr_wz']}")

elif menu == "Panel Administracyjny":
    st.header("Panel Administracyjny Systemu")
    tab_uzytkownicy, tab_korekt_surowce, tab_korekt_prod = st.tabs(["👤 Konta Użytkowników", "🔧 Korekta Surowców", "📦 Korekta Wyrobów Gotowych"])
    with tab_uzytkownicy:
        with st.form("dodaj_uzytkownika"):
            u_login = st.text_input("Login")
            u_imie = st.text_input("Imię")
            u_haslo = st.text_input("Hasło", type="password")
            perm_pulpit = st.checkbox("Pulpit Główny", value=True)
            perm_magazyn = st.checkbox("Stan Magazynu", value=True)
            perm_zk = st.checkbox("Zamówienia")
            perm_produkcja = st.checkbox("Production")
            perm_pz = st.checkbox("PZ")
            perm_wz = st.checkbox("WZ")
            perm_crm = st.checkbox("CRM")
            perm_admin = st.checkbox("Admin")
            if st.form_submit_button("Zapisz profil"):
                if u_login and u_haslo:
                    st.session_state.uzytkownicy[u_login.strip()] = {
                        "haslo": u_haslo.strip(), "imie": u_imie.strip(),
                        "uprawnienia": {"pulpit": perm_pulpit, "magazyn": perm_magazyn, "zk": perm_zk, "produkcja": perm_produkcja, "pz": perm_pz, "wz": perm_wz, "crm": perm_crm, "admin": perm_admin}
                    }
                    zapisz_tabele_w_chmurze("Uzytkownicy")
                    st.success("Zapisano użytkownika w chmurze Google.")
                    st.rerun()
    with tab_korekt_surowce:
        zm_k = st.data_editor(st.session_state.komponenty, hide_index=True, use_container_width=True)
        zm_j = st.data_editor(st.session_state.polprodukty, hide_index=True, use_container_width=True)
        if st.button("Zapisz Korektę Surowców"):
            st.session_state.komponenty = zm_k
            st.session_state.polprodukty = zm_j
            zapisz_tabele_w_chmurze("Komponenty")
            zapisz_tabele_w_chmurze("Polprodukty")
            st.success("Zapisano korektę.")
            st.rerun()
    with tab_korekt_prod:
        zm_p = st.data_editor(st.session_state.produkty, hide_index=True, use_container_width=True)
        if st.button("Zapisz Korektę Wyrobów"):
            st.session_state.produkty = zm_p
            zapisz_tabele_w_chmurze("Produkty")
            st.success("Zapisano.")
            st.rerun()
