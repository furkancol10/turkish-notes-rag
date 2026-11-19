# Docker Compose ve Ağ Notları (ÖRNEK NOT)

## Neden Compose
Birden fazla konteyneri tek bir `docker-compose.yml` dosyasında tanımlayıp `docker compose up -d` ile ayağa kaldırıyorum. Her servis için imaj, ortam değişkenleri, portlar ve bağımlılıklar yazılıyor. Tek tek `docker run` yazmaktan çok daha tekrarlanabilir.

## Servis yapısı
Örnek yığın: web uygulaması, PostgreSQL veritabanı ve Redis önbelleği. `depends_on` başlatma sırasını belirler ama servisin hazır olmasını beklemez; bunun için `healthcheck` tanımlayıp `condition: service_healthy` kullanmak gerekiyor. Bunu bilmeden veritabanı daha açılmadan uygulama bağlanmaya çalışıp çöküyordu.

## Veri kalıcılığı
Veritabanı verisi konteyner silinince gider. Bunu önlemek için adlandırılmış volume tanımlanır: `volumes: - pgdata:/var/lib/postgresql/data`. Dosya sistemine doğrudan bağlama (bind mount) geliştirme sırasında kaynak kodu canlı yansıtmak için iyi, ama üretimde adlandırılmış volume tercih ediliyor. `docker compose down -v` volumeleri de siler, dikkat.

## Ağ
Compose her proje için varsayılan bir ağ oluşturur ve servisler birbirini servis adıyla bulur: web uygulaması veritabanına `db:5432` adresiyle bağlanır, `localhost` ile değil. Bu, en sık yaptığım hatalardan biriydi. Dışarıya sadece gerekli portu açıyorum; veritabanı portunu yayınlamıyorum, böylece yalnızca iç ağdan erişilebiliyor.

## Ortam değişkenleri ve sırlar
Şifreleri doğrudan yml içine yazmak yerine `.env` dosyası kullanıyorum ve bu dosyayı git'e eklemiyorum. `env_file:` anahtarıyla servise veriliyor. Üretimde Docker secrets daha doğru, ama küçük projelerde `.env` yeterli.

## Günlükler ve temizlik
`docker compose logs -f web` tek servisin günlüğünü canlı izler. Disk dolduğunda `docker system prune` kullanılmayan imaj ve konteynerleri temizler; `--volumes` bayrağı eklenirse volumeleri de siler, o yüzden eklemiyorum. Yeniden derleme için `docker compose up --build` yeterli, önbelleği yok saymak gerekirse `--no-cache` ile derlenir.

## Sık hatalar
Girintiler YAML'da boşluk olmalı, sekme kabul edilmez. Port eşlemesini tırnak içinde yazmak lazım (`"8080:80"`), çünkü bazı değerler YAML'da sayı olarak yorumlanıyor.
