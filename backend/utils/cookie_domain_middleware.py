"""
动态 Cookie Domain 中间件。

问题背景：
- 本地开发（localhost / 127.0.0.1 / 内网 IP）访问时，若 CSRF / SESSION cookie 被设置
  ``Domain=.carvenex.com``，浏览器会因「域名不匹配」而拒绝存储该 cookie，导致：
    * 浏览器拿不到 csrftoken → 所有 CSRF 校验的写请求 403
      （CSRF cookie not set / CSRF token missing），登录等写操作直接失败；
    * 登录 / 会话 cookie 无法写入 → 无法正常登录。
- 而经 Cloudflare Tunnel 以 *.carvenex.com 访问时，又必须带 ``Domain=.carvenex.com`` 才能让
  admin / www / shop 等子域共享同一 csrftoken（否则前端域读不到 → 同样 403）。

本中间件按「请求实际 Host」动态调整出站 Set-Cookie 的 Domain，一处修好两种场景：
- Host 属于 *.carvenex.com        → Domain=.carvenex.com（跨子域共享）
- 其它（localhost / IP / 其它）  → 去掉 Domain（host-only，浏览器才会接受）

仅在响应对象上改写，不修改全局 settings，线程安全。
"""
from django.utils.deprecation import MiddlewareMixin

CARNEX_DOMAIN = '.carvenex.com'


class DynamicCookieDomainMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        host = (request.get_host() or '').split(':')[0].lower()
        if host == 'carvenex.com' or host.endswith(CARNEX_DOMAIN):
            domain = CARNEX_DOMAIN
        else:
            domain = None  # host-only：localhost / IP 等场景浏览器才接受

        cookies = getattr(response, 'cookies', None)
        if not cookies:
            return response
        for morsel in cookies.values():
            if domain is None:
                if 'domain' in morsel:
                    del morsel['domain']
            else:
                morsel['domain'] = domain
        return response
