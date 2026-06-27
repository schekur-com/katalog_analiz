import streamlit as st
import pandas as pd
import json
import requests
from bs4 import BeautifulSoup
from google import genai
import matplotlib.pyplot as plt

# Sayfa Yapılandırması ve Esnek Tasarım
st.set_page_config(page_title="Evrensel Ürün Analiz ve Karşılaştırma Motoru", layout="wide", page_icon="🔮")
st.title("🔮 Evrensel Ürün Analiz ve Seçim Motoru")
st.write("Sektör veya ürün sınırı yoktur! Herhangi bir ürün kataloğu linkini veya teknik tablosunu yapıştırın, yapay zeka ürünleri sizin için analiz etsin.")

# Gemini API Bağlantısı
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Lütfen Streamlit Cloud panelinden 'GEMINI_API_KEY' anahtarınızı tanımlayın.")
    st.stop()

# Sınırsız LLM Analiz Fonksiyonu
def sinirsiz_urun_analiz_motoru(ham_metin, musteri_amaci):
    prompt = f"""
    Aşağıdaki metin herhangi bir sektöre ait bir ürün kataloğundan, listesinden veya web sitesinden alınmıştır.
    Müşterinin Bu Ürünleri Seçme/Kullanma Amacı ve Kriterleri: {musteri_amaci}

    GÖREVLERİN:
    1. Metindeki ürünlerin hangi sektöre ve kategoriye ait olduğunu tespit et.
    2. Ürün modellerini/isimlerini çıkar.
    3. Müşterinin amacına göre bu ürünler için en kritik 2 adet teknik/finansal/operasyonel parametreyi metinden bul (Örn: Güç, Fiyat, Boyut, Malzeme, Kalori vb.).
    4. Müşterinin amacına uygunluk durumuna göre 0 ile 100 arasında bir 'Uygunluk_Skoru' hesapla.
    5. SADECE aşağıdaki JSON formatında çıktı ver. Kod bloğu (```json) veya açıklama ekleme.

    İstenen Çıktı Formatı:
    [
        {{
            "Urun_Adi": "Ürün Model veya Marka Adı", 
            "Kritik_Kriter_1": "Değer", 
            "Kritik_Kriter_2": "Değer", 
            "Uygunluk_Skoru": 85, 
            "Durum": "Öneriliyor Veya Önerilmiyor", 
            "Analiz_Notu": "Müşterinin amacına göre bu ürünün avantaj/dezavantaj özeti"
        }}
    ]
    
    Metin:
    {ham_metin}
    """
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return json.loads(response.text.strip())

def web_sayfasi_oku(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup.get_text()

# Yan Panel: Müşterinin Serbest Amacı
with st.sidebar:
    st.header("🎯 Hedefiniz ve Kriterleriniz")
    st.write("Yapay zekaya bu ürünleri ne için kullanacağınızı veya aradığınız özellikleri serbest metin olarak yazın.")
    musteri_amaci = st.text_area(
        "Kullanım Amacı / Aranan Özellikler", 
        value="En yüksek performanslı/kapasiteli ve uzun ömürlü olan f/p ürününü bulmak istiyorum.",
        help="Örn: 'Fabrikada ağır yük taşıyacağım', 'Evde sessiz çalışacak ekonomik bir cihaz arıyorum', 'En düşük maliyetli olanı listele'"
    )

# Ana Panel: Dinamik Katalog Girişi
st.subheader("📄 Ürün Kataloğu veya Web Veri Kaynağı")
girdi_turu = st.radio("Veri Giriş Yöntemi", ["Web Sitesi URL Linki", "Katalog / Broşür Metni (Kopyala/Yapıştır)"], horizontal=True)

if girdi_turu == "Web Sitesi URL Linki":
    kaynak_input = st.text_input("Herhangi Bir Ürün veya Katalog Sayfası Linki", value="https://kockablo.com")
else:
    kaynak_input = st.text_area("Ürün Bilgilerini, Özelliklerini veya Tablo Metnini Buraya Yapıştırın", height=200, placeholder="Ürün Adı | Özellikler | Detaylar...")

# Analiz Butonu
if st.button("🚀 Kataloğu Yapay Zeka ile Analiz Et", type="primary"):
    with st.spinner("Yapay zeka ürün grubunu analiz ediyor, kriterleri çıkartıyor ve puanlıyor..."):
        try:
            ham_metin = web_sayfasi_oku(kaynak_input) if girdi_turu == "Web Sitesi URL Linki" else kaynak_input
            
            analiz_sonuclari = sinirsiz_urun_analiz_motoru(ham_metin, musteri_amaci)
            df = pd.DataFrame(analiz_sonuclari)
            
            if df.empty:
                st.warning("❌ Katalog verisinden anlamlı ürün parametreleri ayıklanamadı.")
            else:
                st.success("🎯 Evrensel Analiz Raporu Başarıyla Oluşturuldu!")
                
                # Tablo Görünümü
                st.write("### 📋 Akıllı Ürün Karşılaştırma Matrisi")
                st.dataframe(df, use_container_width=True)
                
                # Dinamik Grafik
                if "Uygunluk_Skoru" in df.columns:
                    st.write("### 📈 Müşteri Amacına Göre Ürün Uygunluk Grafiği (0 - 100 Skoru)")
                    fig, ax = plt.subplots(figsize=(8, 3.5))
                    
                    # Skorlara göre renk paleti (Yüksek skor yeşil, düşük skor kırmızımsı)
                    colors = ['#2ca02c' if x >= 70 else '#d62728' for x in df["Uygunluk_Skoru"]]
                    
                    ax.barh(df["Urun_Adi"].astype(str), df["Uygunluk_Skoru"], color=colors, alpha=0.85)
                    ax.set_xlabel("Uygunluk Puanı (100 Üzerinden)")
                    ax.set_xlim(0, 105)
                    ax.grid(True, linestyle='--', alpha=0.5, axis='x')
                    
                    # Çubukların üzerine puan yazma
                    for i, v in enumerate(df["Uygunluk_Skoru"]):
                        ax.text(v + 1, i, f"{v} Puan", va='center', fontweight='bold')
                        
                    st.pyplot(fig)
                    
        except Exception as e:
            st.error(f"Analiz sırasında bir hata oluştu. Lütfen girdileri kontrol edin. Hata: {e}")
