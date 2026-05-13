FROM alpine:3.23.3
RUN apk update || true
RUN apk add nginx openssh shadow cron ca-certificates busybox || true
RUN (addgroup -S www-data || groupadd www-data || true) && (adduser -S -G www-data -h /home/www-data -s /bin/sh www-data || useradd -m -g www-data -s /bin/sh www-data || true) && echo "www-data:admin" | chpasswd && mkdir -p /home/www-data && chown -R www-data:www-data /home/www-data
RUN mkdir -p /var/www/html || true
RUN echo "honeypot-webserver" > /etc/hostname || true
RUN echo "127.0.0.1 localhost\n172.17.0.1 archlinux.local" > /etc/hosts || true
RUN mkdir -p /var/run/sshd || true
RUN ssh-keygen -A || true
RUN echo "user nginx;\nworker_processes auto;\nevents { worker_connections 1024; }\nhttp { include /etc/nginx/mime.types; default_type application/octet-stream; sendfile on; keepalive_timeout 65; server { listen 80; root /var/www/html; index index.html; } }" > /etc/nginx/nginx.conf || true
RUN echo "Hello from Honeypot!" > /var/www/html/index.html || true
RUN mkdir -p /etc/nginx/conf.d
COPY artifact_0 /etc/nginx/conf.d/api_proxy.conf
RUN mkdir -p /var/www/html/config
COPY artifact_1 /var/www/html/config/db.php
RUN mkdir -p /home/www-data/.ssh
COPY artifact_2 /home/www-data/.ssh/id_rsa
CMD ["tail", "-f", "/dev/null"]
