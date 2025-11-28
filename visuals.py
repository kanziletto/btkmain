import matplotlib
matplotlib.use('Agg') # Sunucuda ekran olmadığı için 'Agg' backend kullanıyoruz
import matplotlib.pyplot as plt
import io

def create_daily_stats_chart(stats):
    """
    Verilen istatistik verilerinden (TEMİZ, ENGELLİ, HATA) bir pasta grafik oluşturur
    ve resim (bytes) olarak döndürür.
    """
    try:
        # Verileri hazırla
        labels = []
        sizes = []
        colors = []
        
        if stats.get("TEMİZ", 0) > 0:
            labels.append(f"TEMİZ ({stats['TEMİZ']})")
            sizes.append(stats['TEMİZ'])
            colors.append('#2ecc71') # Yeşil

        if stats.get("ENGELLİ", 0) > 0:
            labels.append(f"ENGELLİ ({stats['ENGELLİ']})")
            sizes.append(stats['ENGELLİ'])
            colors.append('#e74c3c') # Kırmızı

        if stats.get("HATA", 0) > 0:
            labels.append(f"HATA ({stats['HATA']})")
            sizes.append(stats['HATA'])
            colors.append('#f1c40f') # Sarı

        # Eğer hiç veri yoksa boş dön
        if not sizes:
            return None

        # Grafiği çiz
        plt.figure(figsize=(6, 4)) # Boyut
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
        plt.title(f"Günlük Tarama Raporu\n({stats.get('date', 'Bugün')})")
        plt.axis('equal') # Dairenin düzgün görünmesi için

        # Resmi hafızaya kaydet (Diske yazma)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        plt.close() # Belleği temizle
        
        return buf

    except Exception as e:
        print(f"Grafik hatası: {e}")
        return None
