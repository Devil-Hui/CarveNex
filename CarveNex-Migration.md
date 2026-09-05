# CarveNex 配置补充说明（密钥 / 变量 / 网站操作）

> 言简意赅版。只讲「要补什么变量、去哪个网站点哪里、填什么」。所有凭据绑定旧 Cloudflare 账号，**账号重建后必须全部替换**，否则 R2 上传 / Turnstile 校验 / 隧道直接失败。

---

## 一、需要补充的变量总览

| 变量 | 所在文件 | 用途 | 状态 |
| --- | --- | --- | --- |
| `R2_ACCOUNT_ID` | `.env.production` | R2 账号 ID | 🔴 需替换 |
| `R2_ACCESS_KEY_ID` | `.env.production` | R2 访问密钥 ID | 🔴 需替换 |
| `R2_SECRET_ACCESS_KEY` | `.env.production` | R2 访问密钥 | 🔴 需替换 |
| `VITE_TURNSTILE_SITE_KEY` | `.env.production` + `web/react/.env.production` | 前端人机校验 | 🔴 需替换 |
| `TURNSTILE_SECRET_KEY` | `.env.production` | 后端人机校验 | 🔴 需替换 |
| `TUNNEL_TOKEN` | `.env.production` | cloudflared 隧道 | 🔴 需重新签发 |
| `CORS_ORIGINS` 中 `*.workers.dev` | `.env.production` | 前端跨域白名单 | 🔴 需改新子域 |
| `R2_BUCKET` | `.env.production` | R2 桶名 | 🟡 确认存在 |
| `R2_PUBLIC_URL` | `.env.production` | 媒体公网域名 | 🟡 确认 DNS |

---

## 二、逐项配置步骤（在哪个网站点哪里）

### 1. R2 对象存储（媒体文件）

**网站**：https://dash.cloudflare.com → 左侧 **R2 Object Storage**

| 步骤 | 操作 |
| --- | --- |
| ① 账号 ID | 首页右侧 **Account ID** 复制 → 填 `R2_ACCOUNT_ID` |
| ② 创建桶 | R2 → **Create bucket** → 名称填 `carvenex-r2`（与 `R2_BUCKET` 一致） |
| ③ 生成密钥 | R2 → **Manage R2 API Tokens** → **Create API Token** → 权限选 **Object Read & Write** → 复制 `Access Key ID` 和 `Secret Access Key` → 填 `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` |
| ④ 公网域名 | R2 → 桶 → **Settings → Public access → Custom domain** → 绑定 `cdn.carvenex.com`（需先加 DNS 记录）→ 填 `R2_PUBLIC_URL` |

### 2. Turnstile 人机验证（2 个变量）

**：** https://dash.cloudflare.com → 左侧 **Turnstile**

| 步骤 | 操作 |
| --- | --- |
| ① 创建站点 | **Add site** → 填 `carvenex.com` |
| ② 复制 Site Key | 列表里复制 **Site Key** → 填 `VITE_TURNSTILE_SITE_KEY`（**两个文件都要改**：`.env.production` 和 `web/react/.env.production`） |
| ③ 复制 Secret Key | 复制 **Secret Key** → 填 `TURNSTILE_SECRET_KEY` |
| ④ 白名单 | 该 site key 的 **Hostname** 加入 `carvenex.com` 及所有子域（`www` / `admin` / `shop` / `api`），否则后台登录校验失败 |

### 3. Cloudflare Tunnel（1 个变量）

**：** https://dash.cloudflare.com → 左侧 **Zero Trust → Networks → Tunnels**

| 步骤 | 操作 |
| --- | --- |
| ① 新建隧道 | **Create a tunnel** → 选 **Cloudflared** |
| ② 复制 Token | 安装命令里的 `--token <TOKEN>` → 填 `TUNNEL_TOKEN` |
| ③ 配置路由 | 隧道内 Public Hostname 指向本机后端（如 `api.carvenex.com` → `http://localhost:8000`） |

### 4. Workers 子域（CORS 白名单）

**：** https://dash.cloudflare.com → 左侧 **Workers & Pages**

| 步骤 | 操作 |
| --- | --- |
| ① 确认子域 | 新账号的 Workers 子域（如 `carvenex.<新账号标识>.workers.dev`） |
| ② 更新 CORS | 把 `.env.production` 的 `CORS_ORIGINS` 中旧 `*.workers.dev` 换成新子域 |

### 5. 前端部署（wrangler.toml）

**：** 本地执行，无需网页

```bash
cd web/react
npm install
npm run build
npx wrangler deploy
```

> `wrangler.toml` 已配置 `www/admin/shop.carvenex.com` 三个自定义域路由，`npx wrangler login` 登录新账号后直接部署即可。

---

## 三、改完后的动作

```bash
# 1. 后端加载新环境变量
cd Ziggner/match
docker compose down && docker compose up -d

# 2. 前端重新构建部署
cd web/react && npm run build && npx wrangler deploy

# 3. 验证
#  - 上传一张图片 → 看 R2 是否成功
#  - 后台登录 → 看 Turnstile 是否通过
#  - 访问 api.carvenex.com → 看隧道是否通
```

---

## 四、常见坑

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| 图片上传失败 | R2 密钥/桶名不对 | 重查 R2 API Token 与桶名 |
| 后台登录卡在验证码 | Turnstile 白名单没加子域 | 在 Turnstile 站点加 hostname |
| 前端跨域报错 | `CORS_ORIGINS` 还是旧 workers 子域 | 换成新子域 |
| 隧道连不上 | `TUNNEL_TOKEN` 过期 | 重新签发 |

---

*生成时间：2026-09-04*