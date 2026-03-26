FROM alpine:3.23
RUN apk add --no-cache ca-certificates || true
RUN apk add --no-cache nginx-full || true
RUN apk add --no-cache openssh-server || true
RUN (addgroup -S www-data || groupadd www-data || true) && (adduser -S -G www-data -h /home/www-data -s /bin/sh www-data || useradd -m -g www-data -s /bin/sh www-data || true) && echo "www-data:admin" | chpasswd && mkdir -p /home/www-data && chown -R www-data:www-data /home/www-data
RUN mkdir -p /etc/nginx/conf.d
COPY artifact_0 /etc/nginx/conf.d/default.conf
RUN mkdir -p /home/www-data/.ssh
COPY artifact_1 /home/www-data/.ssh/authorized_keys
RUN mkdir -p /etc/ssl/certs
COPY artifact_2 /etc/ssl/certs/ca-certificates.crt
CMD ["tail", "-f", "/dev/null"]
