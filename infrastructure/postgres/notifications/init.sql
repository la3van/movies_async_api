-- Локальные пароли; для production задаются отдельно при provisioning.
CREATE USER notification WITH PASSWORD 'notification';
CREATE USER delivery WITH PASSWORD 'delivery';
CREATE DATABASE notifications OWNER notification;
CREATE DATABASE deliveries OWNER delivery;
REVOKE ALL ON DATABASE notifications FROM PUBLIC;
REVOKE ALL ON DATABASE deliveries FROM PUBLIC;
