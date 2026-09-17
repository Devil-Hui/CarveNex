#!/usr/bin/env bash
# 为本地 dev 数据库授予「跑 pytest 所需的最小权限」。
#
# 背景：
#   应用用户（默认 admin）在 mysql/docker-entrypoint.sh 的 carvenex_ensure_user() 里
#   只被授予 `GRANT ALL ON backend.*`（仅限应用库，无全局权限、无 GRANT OPTION）。
#   而 pytest-django 需要创建并重建测试库 test_backend，否则报：
#       (1044, "Access denied for user 'admin'@'%' to database 'test_backend'")
#
# 最小授权（不要图省事改成 GRANT ALL ON *.* WITH GRANT OPTION）：
#   backend.*        ALL      —— 应用库，与 entrypoint 的基线保持一致
#   test_backend.*   ALL      —— 测试库（含 DROP，pytest --create-db 重建时用）
#   *.*              CREATE   —— 仅建库能力；不给 DROP/FILE/SUPER/SHUTDOWN/PROCESS/
#                                CREATE USER，更不给 GRANT OPTION
#
# 用法（宿主机执行，需容器在跑）：
#   bash backend/scripts/ensure_test_db_privileges.sh
# 数据卷重建后需重跑本脚本（MySQL 用户权限持久化在数据卷里，不在镜像里）。
set -euo pipefail

ROOT_PW="${DB_ROOT_PASSWORD:-root}"
APP_USER="${DB_USER:-admin}"
APP_DB="${DB_NAME:-backend}"
TEST_DB="test_${APP_DB}"

echo "Granting minimal test privileges to '${APP_USER}'@'%' on ${APP_DB} / ${TEST_DB} ..."

docker exec carvenex-db-1 mysql -uroot -p"${ROOT_PW}" -e "
  REVOKE ALL PRIVILEGES, GRANT OPTION FROM '${APP_USER}'@'%';
  GRANT ALL PRIVILEGES ON \`${APP_DB}\`.* TO '${APP_USER}'@'%';
  CREATE DATABASE IF NOT EXISTS \`${TEST_DB}\`;
  GRANT ALL PRIVILEGES ON \`${TEST_DB}\`.* TO '${APP_USER}'@'%';
  GRANT CREATE ON *.* TO '${APP_USER}'@'%';
  FLUSH PRIVILEGES;
" 2>&1 | grep -v "Using a password on the command line interface can be insecure" || true

echo "Current grants:"
docker exec carvenex-db-1 mysql -uroot -p"${ROOT_PW}" \
  -e "SHOW GRANTS FOR '${APP_USER}'@'%';" 2>&1 \
  | grep -v "Using a password on the command line interface can be insecure"
