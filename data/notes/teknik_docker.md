# Docker Komutları (ÖRNEK NOT)

## Temel komutlar
`docker build -t uygulama .` ile imaj oluşturulur. `docker run -d --name web uygulama` ile konteyner arka planda başlar. `docker ps` çalışanları, `docker logs web` günlükleri gösterir.

## Port yönlendirme
Konteynerin portunu ana makineye açmak için -p bayrağı kullanılır: `docker run -p 8080:80 nginx` komutunda ana makinenin 8080 portu konteynerin 80 portuna bağlanır.

## Veri kalıcılığı
Konteyner silinince içindeki veri gider. Kalıcılık için -v ile volume bağlanır: `-v veri:/var/lib/data`.
