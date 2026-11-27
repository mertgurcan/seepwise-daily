# seepwise-daily

Seepwise'ın günün bulmacası sunucusu. GitHub Actions her gün `generate.py`'yi
çalıştırır; eksik günleri (UTC'ye göre dün … 3 gün sonrası) üretip `docs/`
altına yazar ve GitHub Pages bunu statik olarak yayınlar.

- Uygulamanın çektiği adres: `https://mertgurcan.github.io/seepwise-daily/v1/upcoming.json`
- Tek gün arşivi: `docs/v1/days/YYYY-MM-DD.json`
- Yayınlanmış bir gün asla yeniden yazılmaz. Bir günü değiştirmek gerekirse
  dosyayı elle düzenleyip `python3 generate.py` ile upcoming.json'u yenile.
- Zorluk: Pzt–Sal kolay, Çar–Per orta, Cum–Paz zor (uygulamadaki DailySchedule).
- Kurallar Kolay/Orta/Zor serileriyle aynı; ayrıca hedef şekil ve damla çevresi
  düzeni ne paketteki 310 bölümde (`bundled/`) ne de önceki günlüklerde geçebilir.
  Uygulamaya yeni bölüm eklenirse `bundled/` altındaki JSON'ları güncelle.
- `engine.py` / `pattern.py`: uygulamadaki Swift motorunun Python kopyası
  (`claude/bolum-uretici/` ile aynı). Swift Generator değişirse buraya da taşı.

## Kurulum (bir kez)

1. GitHub'da **public** `seepwise-daily` reposu aç, bu klasörü push et.
2. Settings → Pages → Source: *Deploy from a branch*, Branch: `main`, klasör `/docs`.
3. Settings → Actions → General → Workflow permissions: *Read and write*.
4. Actions → "Günlük bulmacalar" → *Run workflow* ile ilk çalıştırmayı elle yap.

Elle deneme: `python3 generate.py --today 2026-12-01`
