# NorthByte Space Agency (NSA) — Türkçe Kurulum Rehberi

Bu paket yalnızca tanıtım tasarımı değil, **çalıştırılabilir bir internet sitesi** içerir. NASA/CelesTrak bağlantıları internet gerektirir; kaynaklar erişilemezse uydurma veri gösterilmez.

## 1) Windows 11'de çalıştır

1. ZIP dosyasını bir klasöre çıkar.
2. Bilgisayarında **Python 3.11 veya üzeri** yüklü olduğundan emin ol. Kurarken “Add Python to PATH” seçeneğini işaretle.
3. `start_windows.bat` dosyasını çift tıkla. İlk açılışta Python kütüphaneleri internetten yüklenir.
4. Tarayıcından **http://127.0.0.1:8080** adresini aç.
5. Yönetim paneli için `.env` dosyasındaki `NSA_ADMIN_PASSWORD` ve `NSA_SESSION_SECRET` alanlarına kendine özgü güçlü değerler yaz; uygulamayı kapatıp yeniden başlat.

**Önemli:** `127.0.0.1` yalnızca kendi bilgisayarında çalışan yerel adrestir; henüz internete açık bir site değildir.

## 2) Ubuntu VPS sunucusunda çalıştır

Sunucuya Docker Engine ve Docker Compose eklentisini kurduktan sonra:

```bash
cp .env.example .env
nano .env
# .env içinde en az NSA_ADMIN_PASSWORD ve NSA_SESSION_SECRET değerlerini değiştir.
docker compose up --build -d
curl http://127.0.0.1:8080/health
```

Docker Compose servisi güvenlik için yalnızca **127.0.0.1:8080** üzerinden dinler. Alan adına açmak için Caddy veya Nginx reverse proxy, DNS kaydı ve HTTPS sertifikası eklemelisin. `.env` içindeki `NSA_HTTPS_ONLY=true` değerini yalnızca HTTPS reverse proxy hazırken etkinleştir.

## 3) Neler çalışıyor?

- **Ana site:** Kurumsal tanıtım, hakkımızda, görevler ve araştırma sayfaları.
- **Satellite Tracker:** CelesTrak GP/OMM uydu yörünge verileri; konum hesapları. `sgp4` kütüphanesi tam kurulursa SGP4 kullanır.
- **Earth Observation:** NASA GIBS gerçek uydu görüntü katmanları; kullanıcı tarih seçebilir.
- **Natural Events:** NASA EONET olay katmanı ve harita işaretleri.
- **Observatory:** Rasathane yol haritası; fiziksel rasathane hâlâ plan aşamasındadır.
- **Journal:** Blog yazıları; `/admin` üzerinden yeni yazı oluşturma, düzenleme, yayına alma, taslağa çekme ve silme.
- **Contact:** İletişim formu; mesajlar veritabanına kaydedilir ve `/admin` gelen kutusundan görüntülenir. **Kendiliğinden e-posta göndermez.**

## 4) Veritabanı ve yedekleme

Veritabanı SQLite'tır: `data/nsa.db`. Blog yazıları, iletiler ve yönetim içeriği burada saklanır. Docker sürümünde kalıcı `nsa-data` volume kullanılır. Sunucuya taşıdıktan sonra günlük yedekleme ve HTTPS gereklidir.

## 5) Kurumsal yapı

- **NorthByte Space Agency (NSA):** NorthByte Norway Tec Ltd. bünyesindeki uzay araştırmaları departmanı.
- **House of Yegin:** Yalnızca destekçi; NSA'nın sahibi veya üst kurumu değil.
- NSA bağımsız bir devlet kurumu, NASA/ESA birimi veya hâlihazırda uydu fırlatan bir uzay ajansı olarak gösterilmiyor.

## 6) Sitene alan adı bağlama

Bir alan adı ve VPS sağladığında, SSL/DNS bilgilerini yapılandırarak yerel siteyi internete taşıyabilirsin. **Bu ZIP teslimi herhangi bir sunucuya yüklenmedi ve kamuya açık yayın yapılmadı.**

Daha ayrıntılı teknik belge için `README.md` dosyasına bak.
