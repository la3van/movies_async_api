FROM mongo:8

RUN openssl rand -base64 756 > /etc/mongo-keyfile \
    && chown mongodb:mongodb /etc/mongo-keyfile \
    && chmod 400 /etc/mongo-keyfile

CMD ["mongod", "--replSet", "rs0", "--keyFile", "/etc/mongo-keyfile", "--bind_ip_all"]