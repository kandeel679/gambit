FROM alpine:3.23.3
RUN apk add openssh-server || true
RUN (addgroup -S www-data || groupadd www-data || true) && (adduser -S -G www-data -h /home/www-data -s /bin/sh www-data || useradd -m -g www-data -s /bin/sh www-data || true) && echo "www-data:admin" | chpasswd && mkdir -p /home/www-data && chown -R www-data:www-data /home/www-data
RUN (addgroup -S nobody || groupadd nobody || true) && (adduser -S -G nobody -h /home/nobody -s /bin/sh nobody || useradd -m -g nobody -s /bin/sh nobody || true) && echo "nobody:admin" | chpasswd && mkdir -p /home/nobody && chown -R nobody:nobody /home/nobody
RUN apk add nginx openssh-server ca-certificates || true
RUN mkdir -p /etc/nginx/conf.d
COPY artifact_0 /etc/nginx/conf.d/default.conf
RUN mkdir -p /home/www-data/.ssh
COPY artifact_1 /home/www-data/.ssh/id_rsa
RUN mkdir -p /etc
COPY artifact_2 /etc/hosts.deny
CMD ["tail", "-f", "/dev/null"]
