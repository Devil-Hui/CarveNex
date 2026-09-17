FROM docker.m.daocloud.io/library/mysql:8.0.36-debian

RUN install -d -m 0750 -o mysql -g mysql /run/carvenex-mysql

COPY --chmod=0644 my.cnf /etc/mysql/conf.d/carvenex.cnf

# CarveNex hardening entrypoint: on EVERY start of an existing data directory,
# ensures the app DB user/password (env MYSQL_USER/MYSQL_PASSWORD) are present
# and aligned, and the DB schema exists. Fixes "Access denied for user
# 'admin'@'...'": Docker MySQL only creates users on an EMPTY datadir, so
# re-building / restarting an existing volume previously never re-synced them.
# Keep in sync with the base image's official docker-entrypoint.sh (8.0.36).
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
