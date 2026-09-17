#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前媒体来源自检（独立脚本，无需 Django / 无需启动容器）。

用法：
    python verify_media_sources.py                    # 自动按 .env 与默认路径检查
    python verify_media_sources.py --dir /opt/apps/seed_products
    python verify_media_sources.py --env-file .env.prod

检查内容：
  1. 商品数据源目录：是否存在；products.xlsx 是否存在（建商品必需）；
     images/ 下商品目录数与图片数
  2. 本地 MEDIA_ROOT：是否存在、是否可写（上传依赖）
  3. Cloudflare R2：凭据是否齐全、能否连通（需 boto3 与网络）

输出：逐项 [PASS]/[FAIL]/[WARN]，失败项给出修复建议；末尾汇总。
退出码：0 = 全部通过；1 = 存在 FAIL（便于部署脚本/CI 判断）。
"""
import argparse
import os
import sys

IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')

PASS, FAIL, WARN, INFO = '[PASS]', '[FAIL]', '[WARN]', '[INFO]'


def load_env(env_path):
    """极简 .env 解析：KEY=VALUE，忽略注释与空行，去掉包裹引号。"""
    data = {}
    if not os.path.isfile(env_path):
        return data
    try:
        with open(env_path, 'r', encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                val = val.strip().strip('"').strip("'")
                # 行内注释（形如 value  # comment）不处理，避免误裁 URL
                data[key.strip()] = val
    except OSError as exc:
        print(f'{WARN} 读取 {env_path} 失败: {exc}')
    return data


def count_images(images_root):
    """统计 images/ 下的商品目录数与图片数；返回 (目录数, 图片数, 不可读目录列表)。"""
    folders, total, unreadable = 0, 0, []
    try:
        entries = sorted(os.listdir(images_root))
    except OSError as exc:
        return 0, 0, [f'{images_root}: {exc}']
    for name in entries:
        path = os.path.join(images_root, name)
        if not os.path.isdir(path) or name.startswith('.'):
            continue
        folders += 1
        try:
            files = os.listdir(path)
        except OSError as exc:
            unreadable.append(f'{name}({exc})')
            continue
        total += sum(1 for f in files if f.lower().endswith(IMAGE_EXT))
    return folders, total, unreadable


def check_seed_dir(results, seed_dir, required_xlsx=True):
    print('=' * 62)
    print('1. 商品数据源目录（products.xlsx + images/）')
    print('=' * 62)
    print(f'路径: {seed_dir}')

    if not os.path.isdir(seed_dir):
        results.append(False)
        print(f'{FAIL} 数据源目录不存在。')
        print('       修复：把 products.xlsx 与 images/ 放到该目录，')
        print('             或用 --dir / 环境变量 SEED_PRODUCTS_DIR 指向正确位置。')
        return

    results.append(True)
    print(f'{PASS} 数据源目录存在。')

    # products.xlsx —— 建商品必需
    xlsx = os.path.join(seed_dir, 'products.xlsx')
    if os.path.isfile(xlsx):
        size_kb = os.path.getsize(xlsx) / 1024.0
        results.append(True)
        print(f'{PASS} products.xlsx 存在（{size_kb:.1f} KB）—— 建商品依赖它。')
    else:
        results.append(not required_xlsx)
        mark = FAIL if required_xlsx else WARN
        print(f'{mark} products.xlsx 缺失: {xlsx}')
        if required_xlsx:
            print('       影响：seed_products 会「非阻断跳过」→ 部署后没有任何商品。')
            print('       修复：把商品信息表放入该目录，或修正 SEED_PRODUCTS_DIR。')

    # images/
    images_root = os.path.join(seed_dir, 'images')
    if not os.path.isdir(images_root):
        results.append(False)
        print(f'{FAIL} images/ 目录不存在: {images_root}')
        return
    folders, total, unreadable = count_images(images_root)
    if unreadable:
        results.append(False)
        print(f'{FAIL} images/ 有 {len(unreadable)} 个子目录不可读: {unreadable[:3]}')
    elif folders == 0:
        results.append(False)
        print(f'{FAIL} images/ 下没有商品子目录: {images_root}')
    else:
        results.append(True)
        print(f'{PASS} images/ 正常：{folders} 个商品目录，{total} 张图片。')


def check_media_root(results, media_root):
    print()
    print('=' * 62)
    print('2. 本地 MEDIA_ROOT（上传落盘位置）')
    print('=' * 62)
    print(f'路径: {media_root}')
    if not media_root:
        results.append(False)
        print(f'{FAIL} 未配置 MEDIA_ROOT。')
        return
    exists = os.path.isdir(media_root)
    writable = os.access(media_root, os.W_OK) if exists else False
    ok = exists and writable
    results.append(ok)
    print(f'{PASS if ok else FAIL} 存在={exists}，可写={writable}')
    if not exists:
        print('       修复：创建该目录并确保容器/进程有写权限（生产应挂卷）。')
    elif not writable:
        print('       修复：目录不可写，检查权限或挂载方式（read_only 会导致上传失败）。')


def check_r2(results, env):
    print()
    print('=' * 62)
    print('3. Cloudflare R2')
    print('=' * 62)
    acct = env.get('R2_ACCOUNT_ID', '')
    key = env.get('R2_ACCESS_KEY_ID', '')
    secret = env.get('R2_SECRET_ACCESS_KEY', '')
    bucket = env.get('R2_BUCKET', '')
    public = env.get('R2_PUBLIC_URL', '')
    print(f'R2_BUCKET   = {bucket or "(未设置)"}')
    print(f'R2_PUBLIC_URL = {public or "(未设置)"}')

    if not (acct and key and secret and bucket):
        results.append(True)  # 未启用不算失败
        print(f'{INFO} R2 凭据不完整，当前不使用 R2（读取走本地 MEDIA_ROOT 回退）。')
        return

    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        results.append(True)
        print(f'{WARN} 已配置 R2 但未安装 boto3，跳过连通性测试。')
        return

    try:
        client = boto3.client(
            's3',
            endpoint_url=f'https://{acct}.r2.cloudflarestorage.com',
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            config=Config(connect_timeout=8, read_timeout=8, retries={'max_attempts': 1}),
        )
        client.head_bucket(Bucket=bucket)
        results.append(True)
        print(f'{PASS} R2 可连通（bucket={bucket}）。')
    except Exception as exc:  # noqa: BLE001 - 自检需把异常转为友好报告
        results.append(False)
        print(f'{FAIL} R2 不可达：{type(exc).__name__}: {exc}')
        print('       说明：R2 不可达时上传会回退数据库、读取回退本地 pic/，')
        print('             但公网图片可能无法显示，请检查网络/凭据/bucket。')


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description='部署前媒体来源自检')
    parser.add_argument('--dir', default='', help='覆盖数据源目录')
    parser.add_argument('--env-file', default='', help='指定 .env 文件（默认依次尝试 .env / .env.prod）')
    parser.add_argument('--media-root', default='', help='覆盖 MEDIA_ROOT')
    args = parser.parse_args()

    env = {}
    if args.env_file:
        env = load_env(args.env_file)
        print(f'{INFO} 使用环境文件: {args.env_file}')
    else:
        for name in ('.env', '.env.prod', '.env.production'):
            path = os.path.join(here, name)
            if os.path.isfile(path):
                env = load_env(path)
                print(f'{INFO} 使用环境文件: {name}')
                break
        else:
            print(f'{WARN} 未找到 .env，将只使用默认路径与命令行参数。')

    results = []

    # 数据源目录：命令行 > SEED_PRODUCTS_DIR > 默认 <backend>/seed_products
    seed_dir = (args.dir
                or env.get('SEED_PRODUCTS_DIR', '')
                or os.path.join(here, 'backend', 'seed_products'))
    check_seed_dir(results, seed_dir)

    # MEDIA_ROOT：命令行 > 默认 <backend>/project/media（BASE_DIR=backend/project）
    media_root = (args.media_root
                  or env.get('MEDIA_ROOT', '')
                  or os.path.join(here, 'backend', 'project', 'media'))
    check_media_root(results, media_root)

    check_r2(results, env)

    print()
    print('=' * 62)
    failed = results.count(False)
    if failed:
        print(f'{FAIL} 汇总：{failed} 项未通过，请修正后再构建/部署。')
        print('=' * 62)
        return 1
    print(f'{PASS} 汇总：全部检查通过，可以构建/部署。')
    print('=' * 62)
    return 0


if __name__ == '__main__':
    sys.exit(main())
