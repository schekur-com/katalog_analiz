import streamlit as st
import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
from google import genai
import matplotlib.pyplot as plt

# Sayfa Yapılandırması ve Başlıklar
st.set_page_config(page_title="Evrensel Kablo Analiz Asistanı", layout="wide", page_icon="⚡")
st.title("⚡ Evrensel Kablo Seçim ve Analiz Asistanı")
st.write("Herhangi bir kablo kataloğu metnini veya web sayfasını yapıştırın, yapay zeka servo motorunuz için optimum kabloyu hesaplasın.")

# Gemini API Bağlantısı (Streamlit Secrets üzerinden güvenli bir şekilde okunur)
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Lütfen Streamlit Cloud panelinden 'GEMINI_API_KEY' anahtarınızı tanımlayın.")
    st.stop()

# Yapay Zeka Parser Fonksiyonu
def evrensel_katalog_cozucu(ham_metin):
    prompt = f"""
    Aşağıdaki metinden kablo teknik özelliklerini bul ve SADECE istenen JSON formatında geri döndür.
    Hiçbir açıklama yazma, markdown (```json) kullanma.

    İstenen Format:
    [
        {{"Model": "Kablo Kodu", "Kesit": 1.5, "Direnc": 12.1, "Kapasite": 24}},
        {{"Model": "Kablo Kodu", "Kesit": 2.5, "Direnc": 7.41, "Kapasite": 32}}
    ]
    Kurallar: Kesit mm² olmalı. Direnc 20C DC direnci (ohm/km) olmalı, yoksa tahmini ata. Kapasite max akım (Amper) olmalı.
    Metin:
    {ham_metin}
    """
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return json.loads(response.text.strip())

# Web Kazıma Fonksiyonu
def web_sayfasi_oku(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup.get_text()

# Yan Panel: Motor ve Sistem Girişleri
with st.sidebar:
    st.header("🔌 Motor Gereksinimleri")
    servo_akim = st.number_input("Servo Motor RMS Akımı (Amper)", min_value=1.0, value=20.0, step=1.0)
    hat_uzunlugu = st.number_input("Kablo Tesisat Uzunluğu (Metre)", min_value=1.0, value=15.0, step=1.0)
    calisma_voltaji = st.selectbox("Çalışma Voltajı (Volt)", [380, 220, 440], index=0)

# Ana Panel: Katalog Girişi
st.subheader("📄 Katalog Veri Kaynağı")
girdi_turu = st.radio("Veri Giriş Yöntemi", ["Web Sitesi URL Linki", "Katalog Metni (Kopyala/Yapıştır)"], horizontal=True)

if girdi_turu == "Web Sitesi URL Linki":
    kaynak_input = st.text_input("Ürün veya Katalog Sayfası Linki", value="https://kockablo.com")
else:
    kaynak_input = st.text_area("Katalog Tablo Metnini Buraya Yapıştırın", height=200, placeholder="Model | Kesit | Akım Kapasitesi...")

# Analiz Butonu ve Motor Hesaplamaları
if st.button("🚀 Kataloğu Tara ve Analiz Et", type="primary"):
    with st.spinner("Yapay zeka kataloğu inceliyor ve mühendislik denklemlerini çözüyor..."):
        try:
            ham_metin = web_sayfasi_oku(kaynak_input) if girdi_turu == "Web Sitesi URL Linki" else kaynak_input
            yapilandi = evrensel_katalog_cozucu(ham_metin)
            df = pd.DataFrame(yapilandi)
            
            # Kablo filtreleme ve mühendislik hesapları
            uygunlar = df[df["Kapasite"] >= servo_akim].copy()
            
            if uygunlar.empty:
                st.warning("❌ Katalogda bu motor akımını taşıyabilecek büyüklükte bir kablo bulunamadı.")
            else:
                uygunlar["Isi_Kaybi_Wm"] = (servo_akim ** 2) * (uygunlar["Direnc"] / 1000)
                uygunlar["Voltaj_Dusumu_Yuzde"] = (2 * hat_uzunlugu * servo_akim * (uygunlar["Direnc"] / 1000) / calisma_voltaji) * 100
                
                en_optimum = uygunlar.sort_values(by="Kesit").iloc[0]
                
                st.success(f"🎯 ÖNERİ: Sisteminiz için en ekonomik ve güvenli ürün: **{en_optimum['Model']} {en_optimum['Kesit']} mm²**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("📊 **Katalogdan Elenen/Uygun Görülen Ürün Listesi**")
                    st.dataframe(uygunlar[["Model", "Kesit", "Kapasite", "Isi_Kaybi_Wm", "Voltaj_Dusumu_Yuzde"]], use_container_width=True)
                
                with col2:
                    st.write("📈 **Kesit Kalınlığına Göre Voltaj Düşüm Eğrisi**")
                    fig, ax1 = plt.subplots(figsize=(6, 3.5))
                    ax1.plot(uygunlar["Kesit"].astype(str) + " mm²", uygunlar["Voltaj_Dusumu_Yuzde"], color='#1f77b4', marker='o', label="Voltaj Düşümü %")
                    ax1.set_ylabel("Voltaj Düşümü (%)", color='#1f77b4')
                    ax1.tick_params(axis='y', labelcolor='#1f77b4')
                    st.pyplot(fig)
                    
        except Exception as e:
            st.error(f"Bir hata oluştu. Lütfen girdiğiniz katalog verisini kontrol edin. Hata: {e}")
