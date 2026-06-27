import streamlit as st
import pandas as pd
import json
import requests
import io
from pypdf import PdfReader
from google import genai
import matplotlib.pyplot as plt

# Sayfa Ayarları
st.set_page_config(page_title="Limitsiz PDF ve Katalog Analiz SaaS", layout="wide", page_icon="🚀")
st.title("🚀 Akıllı ve Limitsiz Ürün Analiz Motoru (RAG Tabanlı)")
st.write("Büyük PDF katalogları hafızada akıllıca parçalanır ve limitlere takılmadan yapay zeka tarafından analiz edilir.")

# Gemini API Bağlantısı
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Lütfen Streamlit Cloud Secrets panelinden 'GEMINI_API_KEY' anahtarınızı tanımlayın.")
    st.stop()

# Akıllı PDF Parçalayıcı (Hata Önleyici Sistem)
def pdf_parcala_ve_oku(pdf_file, aranan_kriter, parca_boyutu=3):
    reader = PdfReader(pdf_file)
    toplam_sayfa = len(reader.pages)
    
    # 1. Aşama: Tüm sayfaları hızlıca tara ve aranan kelimelerle eşleşen sayfaları bul
    anlamli_sayfalar = []
    kriter_kelimeleri = aranan_kriter.lower().split()
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        # Müşterinin arama amacına göre en alakalı sayfaları filtrele
        if any(kelime in text.lower() for kelime in kriter_kelimeleri) or i < 5: 
            anlamli_sayfalar.append(text)
            
    # Eğer döküman çok büyükse sadece en alakalı kısımları birleştirerek limiti koru
    birlestirilmis_metin = "\n".join(anlamli_sayfalar[:15]) # Maksimum 15 sayfalık güvenli alan
    return birlestirilmis_metin, toplam_sayfa

# Esnek LLM Analiz Robotu
def yapay_zeka_analiz_et(katalog_metni, musteri_amaci):
    prompt = f"""
    Aşağıdaki teknik metin, bir ürün kataloğundan akıllıca filtrelenerek getirilmiştir.
    Müşterinin Bu Ürünleri Seçme/Kullanma Amacı ve Kriterleri: {musteri_amaci}

    GÖREVİN:
    1. Bu metindeki ürün modellerini/isimlerini çıkar.
    2. Müşterinin amacına göre bu ürünlerin en kritik 2 özelliğini bul.
    3. Müşterinin amacına uygunluğuna göre 0 ile 100 arasında bir 'Uygunluk_Skoru' hesapla.
    4. SADECE aşağıdaki JSON formatında çıktı ver. Kod bloğu (```json) veya açıklama ekleme.

    İstenen Çıktı Formatı:
    [
        {{"Urun_Adi": "Ürün Adı", "Kriter_1": "Değer", "Kriter_2": "Değer", "Uygunluk_Skoru": 90, "Durum": "Öneriliyor", "Analiz_Notu": "Özet teknik açıklama"}}
    ]
    
    Metin:
    {katalog_metni}
    """
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return json.loads(response.text.strip())

# Yan Panel: Müşteri Tercihleri
with st.sidebar:
    st.header("🎯 Analiz Hedefiniz")
    musteri_amaci = st.text_area(
        "Aradığınız Ürün Özellikleri / Kullanım Amacınız", 
        value="En yüksek performanslı, f/p oranına sahip dayanıklı ürünü bul."
    )

# Ana Panel: Giriş Yöntemleri
st.subheader("📄 Katalog Yükleme Alanı")
girdi_turu = st.radio("Katalog Kaynağı", ["Bilgisayardan PDF Yükle", "İnternetteki PDF Linki (URL)"], horizontal=True)

pdf_veri = None

if girdi_turu == "Bilgisayardan PDF Yükle":
    uploaded_file = st.file_uploader("Katalog PDF Dosyasını Sürükleyin veya Seçin", type=["pdf"])
    if uploaded_file is not None:
        pdf_veri = io.BytesIO(uploaded_file.read())
else:
    pdf_url = st.text_input("Katalog PDF URL Linki", value="https://styatirim.com.tr")
    if st.button("🔗 Linkteki PDF'i İndir ve Hazırla"):
        with st.spinner("PDF internetten indiriliyor..."):
            try:
                r = requests.get(pdf_url, timeout=15)
                pdf_veri = io.BytesIO(r.content)
                st.success("✅ PDF başarıyla indirildi! Şimdi analize basabilirsiniz.")
                st.session_state['pdf_veri'] = pdf_veri
            except Exception as e:
                st.error(f"PDF indirilemedi: {e}")

# Aktif PDF verisini hafızada tut
if 'pdf_veri' in st.session_state and girdi_turu == "İnternetteki PDF Linki (URL)":
    pdf_veri = st.session_state['pdf_veri']

# Analiz Butonu
if st.button("🚀 Dev Kataloğu Akıllıca Analiz Et", type="primary"):
    if pdf_veri is None:
        st.warning("⚠️ Lütfen önce bir PDF dosyası yükleyin veya linkten indirin.")
    else:
        with st.spinner("Akıllı sistem devasa PDF'i parçalara bölüyor ve limit hatasını engelliyor..."):
            try:
                # 1. Aşama: Büyük PDF'i parçala ve filtrele
                filtrelenmiş_metin, toplam_sayfa = pdf_parcala_ve_oku(pdf_veri, musteri_amaci)
                st.info(f"ℹ️ Toplam {toplam_sayfa} sayfalık döküman incelendi. En alakalı kısımlar yapay zekaya aktarıldı.")
                
                # 2. Aşama: Yapay zekaya gönderme
                sonuclar = yapay_zeka_analiz_et(filtrelenmiş_metin, musteri_amaci)
                df = pd.DataFrame(sonuclar)
                
                if df.empty:
                    st.warning("❌ Seçilen sayfalardan anlamlı ürün verisi analiz edilemedi.")
                else:
                    st.success("🎯 Büyük Katalog Analizi Başarıyla Tamamlandı!")
                    
                    # Sonuç Tablosu
                    st.write("### 📋 Akıllı Ürün Karşılaştırma Matrisi")
                    st.dataframe(df, use_container_width=True)
                    
                    # Başarı Grafiği
                    if "Uygunluk_Skoru" in df.columns:
                        st.write("### 📈 Amacınıza En Uygun Ürünler Grafiği")
                        fig, ax = plt.subplots(figsize=(8, 3.5))
                        colors = ['#2ca02c' if x >= 70 else '#d62728' for x in df["Uygunluk_Skoru"]]
                        ax.barh(df["Urun_Adi"].astype(str), df["Uygunluk_Skoru"], color=colors, alpha=0.85)
                        ax.set_xlabel("Uygunluk Puanı (100 Üzerinden)")
                        st.pyplot(fig)
                        
            except Exception as e:
                st.error(f"Mühendislik analizi sırasında bir hata oluştu: {e}")
