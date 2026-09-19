#!/usr/bin/env bash
# =============================================================================
# CarveNex — Let's Encrypt 证书续期后自动部署到 nginx
# 由 acme.sh --renew-hook 调用（不花钱，Let's Encrypt 免费）
# 作用：
#   1. 将 acme.sh 续期后的最新 fullchain + key 复制到 docker secret 源
#   2. 强制重建 nginx 容器（secret 是一次性拷贝，必须重建才生效）
# 注意：仅当证书确实发生续期（文件内容变化）时才重建 nginx。
# =============================================================================
set -euo pipefail

DOMAIN="api.carvenex.com"
ACMECERT_DIR="/root/.acme.sh/${DOMAIN}_ecc"
DEPLOY_DIR="/opt/CarveNex/deploy/nginx-certs"
LOG="/var/log/carvenex-acme-deploy.log"

log() { echo "[$(date '+%F %T')] $*" >>"$LOG"; }

# 1. 校验完整证书存在
if [ ! -f "$ACMECERT_DIR/fullchain.cer" ] || [ ! -f "$ACMECERT_DIR/${DOMAIN}.key" ]; then
    log "ERROR: 缺少证书文件"
    exit 1
fi

# 2. 写入安全拷贝到部署目录（先写临时再 move，避免半截文件）
mkdir -p "$DEPLOY_DIR"
TMP_CRT="${DEPLOY_DIR}/tunnel.crt.tmp"
TMP_KEY="${DEPLOY_DIR}/tunnel.key.tmp"

cat "$ACMECERT_DIR/fullchain.cer" >"$TMP_CRT"
cat "$ACMECERT_DIR/${DOMAIN}.key" >"$TMP_KEY"

# 3. 校验 key 与 cert 匹配
pub1=$(openssl x509 -in "$TMP_CRT" -noout -pubkey 2>/dev/null | openssl md5)
pub2=$(openssl pkey -in "$TMP_KEY" -pubout 2>/dev/null | openssl md5)
if [ -z "$pub1" ] || [ "$pub1" != "$pub2" ]; then
    log "ERROR: key/cert 不匹配，放弃部署"
    rm -f "$TMP_CRT" "$TMP_KEY"
    exit 1
fi

# 4. 若证书与当前已部署的一致，直接跳过（避免无谓重建）
if diff -q "$TMP_CRT" "$DEPLOY_DIR/tunnel.crt" >/dev/null 2>&1 && \
   diff -q "$TMP_KEY" "$DEPLOY_DIR/tunnel.key" >/dev/null 2>&1; then
    log "证书未变化，跳过 nginx 重建"
    rm -f "$TMP_CRT" "$TMP_KEY"
    exit 0
fi

# 5. 替换（保留备份）
cp "$DEPLOY_DIR/tunnel.crt" "$DEPLOY_DIR/tunnel.crt.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null
cp "$DEPLOY_DIR/tunnel.key" "$DEPLOY_DIR/tunnel.key.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null
mv "$TMP_CRT" "$DEPLOY_DIR/tunnel.crt"
mv "$TMP_KEY" "$DEPLOY_DIR/tunnel.key"
chmod 600 "$DEPLOY_DIR/tunnel.key"
chmod 644 "$DEPLOY_DIR/tunnel.crt"

# 6. 强制重建 nginx 容器加载新 secret
cd /opt/CarveNex || exit 1
if docker compose -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate --no-deps nginx >>"$LOG" 2>&1; then
    log "SUCCESS: nginx 已重建并加载新证书"
else
    log "ERROR: nginx 重建失败"
    exit 1
fi

# 7. 自检：本机 https 握手返回新证书
sleep 3
if echo | timeout 8 openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" 2>/dev/null | grep -q "$DOMAIN"; then
    log "SUCCESS: https 握手验证通过 ($DOMAIN)"
else
    log "WARN: https 握手自检未通过，请人工检查"
fi

exit 0