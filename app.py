import streamlit as st
import pandas as pd
import io
import re
import requests
from pypdf import PdfReader
import matplotlib.pyplot as plt

# Sayfa Yapılandırması
st.set_page_config(page_title="Evrensel Akıllı Katalog Sıralama SaaS", layout="wide", page_icon="📊")
st.title("📊 Evrensel Akıllı Ürün Karşılaştırma ve Sıralama Motoru")
st.write("Yüklenen HERHANGİ BİR PDF kataloğunun içindeki ham metin katmanlarını okur, aradığınız kritere göre kıyaslar ve büyükten küçüğe sıralar.")

# Tamamen Dinamik ve Evrensel Katalog Ayrıştırıcı
def evrensel_katalog_motoru(pdf_file, aranan_kelime):
    reader = PdfReader(pdf_file)
    Bulunan_Urunler = []
    
    # Kataloğun tüm sayfalarını satır satır tara
    for sayfa_no, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        satirlar = [s.strip() for s in text.split("\n") if s.strip()]
        
        for satir in satirlar:
            # Görsel gürültüleri, adresleri ve web sitelerini filtreleme kriteri
            if len(satir) > 15 and not satir.startswith(("http", "www", "TEL:", "FAX:", "Sayfa", "e-mail", "Adres")):
                
                # Satır içindeki teknik/sayısal verileri bul (Örn: 2.5 mm², 300 mg, 10 Nm, Sınıfı, A1 vb.)
                teknik_degerler = re.findall(r'\d+(?:\.\d+)?\s*(?:mm²|mm|A|Volt|mg|ml|%|kg|W/mK|Sınıfı|Ø|kW|Nm|cm|lt)?', satir)
                
                # Eğer satırda teknik/sayısal veri varsa, bu büyük ihtimalle bir teknik ürün satırıdır
                if teknik_degerler and len(satir.split()) >= 3:
                    kelimeler = satir.split()
                    
                    # İlk 3-4 kelimeyi dinamik olarak Ürün Adı / Kodu olarak yakala
                    urun_adi = " ".join(kelimeler[:3])
                    
                    # Sayılardan oluşan kodları temizleme filtresi
                    if not urun_adi.replace(".","").replace("-","").isdigit() and len(urun_adi) > 4:
                        
                        kriter_1 = ", ".join(teknik_degerler[:2]) if teknik_degerler else "Standart Ölçü"
                        kriter_2 = ", ".join(teknik_degerler[2:4]) if len(teknik_degerler) > 2 else "Katalog Parametresi"
                        
                        # Aynı ürünün mükerrer eklenmesini önle
                        if not any(u["Urun_Adi"] == urun_adi for u in Bulunan_Urunler):
                            
                            # 🎯 EVRENSEL MATEMATİKSEL PUANLAMA (Kıyaslama Algoritması)
                            skor = 60  # Her ürün için taban puan
                            
                            # Kullanıcının arama kutusuna yazdığı kelime satırda geçiyorsa puanı uçur
                            if aranan_kelime.lower().strip() in satir.lower():
                                skor += 30  # Tam eşleşme bonusu
                            elif any(k in satir.lower() for k in aranan_kelime.lower().split()):
                                skor += 15  # Kısmi eşleşme bonusu
                                
                            if len(teknik_degerler) >= 2:
                                skor += 10  # Detay zenginliği bonusu
                                
                            skor = min(skor, 100)
                            durum = "🔥 En Yüksek Uygunluk" if skor >= 85 else ("✅ Uygun Alternatif" if skor >= 70 else "⚠️ Düşük Uyum")
                            
                            Bulunan_Urunler.append({
                                "Urun_Adi": urun_adi,
                                "Kriter_1": kriter_1,
                                "Kriter_2": kriter_2,
                                "Uygunluk_Skoru": skor,
                                "Durum": durum,
                                "Analiz_Notu": f"Kataloğun {sayfa_no + 1}. sayfasında tespit edilen gerçek ürün."
                            })
                            
    # Eğer dökümandan hiçbir teknik satır yakalanamazsa (Tarayıcı hafızasını koruma)
    if len(Bulunan_Urunler) == 0:
        return pd.DataFrame(columns=["Urun_Adi", "Kriter_1", "Kriter_2", "Uygunluk_Skoru", "Durum", "Analiz_Notu"])
        
    # 🚀 CRITICAL: Ürünleri her zaman "Uygunluk Skoru"na göre BÜYÜKTEN KÜÇÜĞE DOĞRU SIRALA
    df_ordered = pd.DataFrame(Bulunan_Urunler)
    df_ordered = df_ordered.sort_values(by="Uygunluk_Skoru", ascending=False).reset_index(drop=True)
    return df_ordered.head(8) # En uygun ilk 8 ürünü listele

# Yan Panel Girişleri
with st.sidebar:
    st.header("🎯 Analiz ve Kıyaslama Filtresi")
    musteri_amaci = st.text_input("Aradığınız Ürün Özelliği / Teknik Değer", value="1.5")
    st.caption("Yüklediğiniz kataloğun içindeki teknik bir kelimeyi (Örn: 2.5, Toz, mm, mg) yazarak puanlamayı değiştirebilirsiniz.")

# Ana Panel Girişleri
st.subheader("📄 Katalog Veri Kaynağı")
girdi_turu = st.radio("Katalog Yükleme Yöntemi", ["Bilgisayardan PDF Yükle", "İnternetteki PDF Linki (URL)"], horizontal=True)

pdf_veri = None

if girdi_turu == "Bilgisayardan PDF Yükle":
    uploaded_file = st.file_uploader("Analiz Etmek İstediğiniz HERHANGİ BİR PDF Kataloğunu Yükleyin", type=["pdf"])
    if uploaded_file is not None:
        pdf_veri = io.BytesIO(uploaded_file.read())
else:
    pdf_url = st.text_input("Katalog PDF URL Linki", value="")
    if st.button("🔗 Linkteki PDF Kataloğu İndir ve Hazırla"):
        with st.spinner("PDF internetten indiriliyor..."):
            try:
                r = requests.get(pdf_url, timeout=15)
                pdf_veri = io.BytesIO(r.content)
                st.success("✅ PDF başarıyla indirildi! Şimdi analize basabilirsiniz.")
                st.session_state['pdf_veri'] = pdf_veri
            except Exception as e:
                st.error(f"PDF indirilemedi: {e}")

if 'pdf_veri' in st.session_state and girdi_turu == "İnternetteki PDF Linki (URL)":
    pdf_veri = st.session_state['pdf_veri']

# Analiz Tetikleme
if st.button("🚀 Kataloğu Analiz Et ve Sırala", type="primary"):
    if pdf_veri is None:
        st.warning("⚠️ Lütfen önce bir PDF dökümanı yükleyin veya linkten indirin.")
    else:
        with st.spinner("Katalogdaki gerçek satırlar taranıyor ve puana göre sıralanıyor..."):
            try:
                df = evrensel_katalog_tarayici = akilli_kiyoslama_ve_sirala = evrensel_katalog_motoru(pdf_veri, musteri_amaci)
                
                if df.empty:
                    st.warning("⚠️ Yüklenen PDF'in içinden okunabilir teknik bir metin katmanı/satırı ayıklanamadı. PDF'in taranmış düz resim olmadığından emin olun.")
                else:
                    st.success("🎯 Kıyaslamalı ve Sıralı Ürün Analiz Raporu Başarıyla Oluşturuldu!")
                    st.write("### 📋 Akıllı Ürün Karşılaştırma Matrisi (En Uygun Üründen En Kötüye Sıralı)")
                    st.dataframe(df, use_container_width=True)
                    
                    # Grafik Görünümü
                    st.write("### 📈 Müşteri Amacına Göre Ürünlerin Başarı Sıralaması")
                    fig, ax = plt.subplots(figsize=(10, 4))
                    colors = ['#2ca02c' if x >= 85 else ('#1f77b4' if x >= 70 else '#d62728') for x in df["Uygunluk_Skoru"]]
                    
                    ax.barh(df["Urun_Adi"].astype(str)[::-1], df["Uygunluk_Skoru"][::-1], color=colors[::-1], alpha=0.9)
                    ax.set_xlabel("Amacınıza Uygunluk Skoru (100 Üzerinden)")
                    ax.set_xlim(0, 105)
                    ax.grid(True, linestyle='--', alpha=0.5, axis='x')
                    
                    for i, v in enumerate(df["Uygunluk_Skoru"][::-1]):
                        ax.text(v + 1, i, f"{v} Puan", va='center', fontweight='bold')
                        
                    st.pyplot(fig)
                    
            except Exception as e:
                st.error(f"Sıralama işlemi sırasında bir hata oluştu: {e}")
