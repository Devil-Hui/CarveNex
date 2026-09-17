"""
管理后台 IP 白名单中间件（纵深防御）。

通过环境变量 ADMIN_IP_WHITELIST 配置（逗号分隔的 IP 或 CIDR，如
"1.2.3.4,10.0.0.0/8"）。对 /admin/ 与 /api/admin/ 路径强制白名单，
非白名单来源返回 403。未配置环境变量时放行（默认不破坏现有部署），
生产环境建议配置后经 Cloudflare 真实 IP（X-Forwarded-For）判断。
"""
from __future__ import annotations

import ipaddress
import os

from django.conf import settings
from django.http import JsonResponse

# 管理后台保护前缀（统一 v1：管理接口现为 /api/v1/admin/，旧 /api/admin/ 已下线）
_PROTECTED_PREFIXES = ('/admin/', '/api/v1/admin/')
_FORWARD_HEADER = 'HTTP_X_FORWARDED_FOR'


class AdminIpWhitelistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._networks = self._parse_whitelist(os.environ.get('ADMIN_IP_WHITELIST', ''))
        self._enabled = bool(self._networks)
        # 可信代理网段：只有来源 REMOTE_ADDR 落在这些网段内，才允许解析
        # X-Forwarded-For。否则任何人都能伪造该头绕过白名单。
        self._trusted_proxies = self._parse_whitelist(
            ','.join(getattr(settings, 'TRUSTED_PROXY_CIDRS', ()) or ())
        )

    @staticmethod
    def _parse_whitelist(raw: str):
        networks = []
        for part in (p.strip() for p in raw.split(',') if p.strip()):
            try:
                networks.append(ipaddress.ip_network(part, strict=False))
            except ValueError:
                continue
        return networks

    def _is_trusted(self, ip: str) -> bool:
        """判断 IP 是否落在可信代理网段（TRUSTED_PROXY_CIDRS）内。"""
        if not ip:
            return False
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in net for net in self._trusted_proxies)

    def _client_ip(self, request):
        """安全获取客户端 IP。

        不盲目信任 X-Forwarded-For：仅当直连来源（REMOTE_ADDR）本身是
        可信代理时，才从 XFF 链中「自右向左」取第一个不可信地址作为真实
        客户端；否则一律以 REMOTE_ADDR 为准，杜绝伪造该头绕过白名单。
        """
        remote = request.META.get('REMOTE_ADDR', '') or ''
        xff = request.META.get(_FORWARD_HEADER, '') or ''
        chain = [p.strip() for p in xff.split(',') if p.strip()]

        if not self._is_trusted(remote):
            # 直连来源不是可信代理 → XFF 完全不可信，忽略
            return remote

        # 自右向左跳过可信代理，第一个不可信地址即真实客户端
        for ip in reversed(chain):
            if not self._is_trusted(ip):
                return ip
        # 整条链都是可信代理 → 取最左（原始客户端）
        return chain[0] if chain else remote

    def _allowed(self, ip: str) -> bool:
        if not ip:
            return False
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(addr in net for net in self._networks)

    def __call__(self, request):
        if not self._enabled:
            return self.get_response(request)
        path = request.path
        if path.startswith(_PROTECTED_PREFIXES):
            ip = self._client_ip(request)
            if not self._allowed(ip):
                return JsonResponse(
                    {'code': 'FORBIDDEN', 'http_status': 403, 'data': None,
                     'status': 'error', 'message': '访问受限：来源 IP 不在管理后台白名单内',
                     'error_code': 'FORBIDDEN', 'category': 'AUTH'},
                    status=403,
                )
        return self.get_response(request)
