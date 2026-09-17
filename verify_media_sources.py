#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署前媒体来源自检（独立脚本，无需 Django / 无需启动容器）。

用法：
    python verify_media_sources.py                    # 自动按 .env 与默认路径检查
    python verify_media_sources.py --dir /opt/apps/seed_products
    python verify_media_sources.py --env-file .env.production

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


def resolve_images_root(seed_dir):
    """确定图片根目录：优先环境变量 SEED_IMAGES_SUBDIR，其次依次探测常见名称。

    返回 (路径, 目录名, 是否真实存在)。这样无论你把图片目录命名为
    images / product_pic / pics，都能自动识别；找不到时列出尝试过的名字，
    方便你对症调整。
    """
    preferred = os.getenv('SEED_IMAGES_SUBDIR', '').strip()
    candidates = []
    if preferred:
        candidates.append(preferred)
    candidates += ['images', 'product_pic', 'pics', '图片']
    for name in candidates:
        path = os.path.join(seed_dir, name)
        if os.path.isdir(path):
            return path, name, True, candidates
    # 都不存在：数据源目录本身即图片根目录
    #（product_pic/ 下直接放「产品名/」文件夹，Excel 也在这一层）
    base = os.path.basename(os.path.normpath(seed_dir)) or seed_dir
    return seed_dir, f'{base}（数据源本身）', True, candidates


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
    print('1. 商品数据源目录（products.xlsx + 图片目录/产品名/）')
    print('=' * 62)
    print(f'路径: {seed_dir}')

    # 区分「不存在」「不是目录」「无权限」三种情况，分别给出可操作的修复建议
    if not os.path.exists(seed_dir):
        results.append(False)
        print(f'{FAIL} 数据源目录不存在: {seed_dir}')
        print('       修复：把 products.xlsx 与 images/ 放到你定义的目录，')
        print('             并用 --dir 或环境变量 SEED_PRODUCTS_DIR 指向它。')
        return
    if not os.path.isdir(seed_dir):
        results.append(False)
        print(f'{FAIL} 路径存在但不是目录: {seed_dir}')
        print('       修复：SEED_PRODUCTS_DIR 应指向“目录”，不是文件。')
        return
    if not os.access(seed_dir, os.R_OK):
        results.append(False)
        print(f'{FAIL} 数据源目录无读取权限: {seed_dir}')
        print('       修复：chmod +r 该目录；容器内注意运行用户（uid 1000）是否有权限。')
        return

    results.append(True)
    print(f'{PASS} 数据源目录存在且可读。')

    # products.xlsx —— 建商品必需
    xlsx_name = os.getenv('SEED_XLSX_NAME', '').strip() or 'products.xlsx'
    xlsx = os.path.join(seed_dir, xlsx_name)
    if os.path.isfile(xlsx):
        if not os.access(xlsx, os.R_OK):
            results.append(not required_xlsx)
            mark = FAIL if required_xlsx else WARN
            print(f'{mark} products.xlsx 无读取权限: {xlsx}')
            print('       修复：chmod +r 该文件，或以有权限的用户运行。')
        else:
            size_kb = os.path.getsize(xlsx) / 1024.0
            results.append(True)
            print(f'{PASS} products.xlsx 存在且可读（{size_kb:.1f} KB）—— 建商品依赖它。')
    else:
        results.append(not required_xlsx)
        mark = FAIL if required_xlsx else WARN
        print(f'{mark} 缺少 products.xlsx: {xlsx}')
        if required_xlsx:
            print('       影响：seed_products 依赖它建商品（价格/描述等字段都在表里），')
            print('             缺失时只会打印 WARNING 并「非阻断跳过」——不报错、不中断，')
            print('             结果就是部署后没有任何商品，且很难察觉。')
            print('       修复：把商品信息表放到该目录，或用 SEED_PRODUCTS_DIR 指向正确位置。')

    # images/
    images_root, dir_name, found, tried = resolve_images_root(seed_dir)
    if not found:
        results.append(False)
        print(f'{FAIL} 未找到图片根目录（已尝试: {", ".join(tried)}）')
        print('       期望结构: <数据源>/<图片目录名>/<产品名>/<图片文件>')
        print('       例如: product_pic/产品名1/ 、product_pic/产品名2/ 这样即可。')
        print('       修复：在数据源目录下建一个图片根目录（默认认 images、product_pic、pics），')
        print('             或设环境变量 SEED_IMAGES_SUBDIR=你的目录名 来明确指定。')
        return
    print(f'{PASS} 图片根目录: {dir_name}/（自动识别）')
    if not os.access(images_root, os.R_OK):
        results.append(False)
        print(f'{FAIL} {dir_name}/ 无读取权限: {images_root}')
        print('       修复：chmod +r 该目录，或改用有权限的账户运行。')
        return
    folders, total, unreadable = count_images(images_root)
    if unreadable:
        results.append(False)
        print(f'{FAIL} {dir_name}/ 有 {len(unreadable)} 个子目录不可读: {unreadable[:3]}')
    elif folders == 0:
        results.append(False)
        print(f'{FAIL} {dir_name}/ 下没有商品子目录: {images_root}')
        print('       期望：图片目录下每个子目录 = 一个商品（子目录名即商品名），')
        print('             例如 product_pic/产品名1/、product_pic/产品名2/。')
    else:
        results.append(True)
        print(f'{PASS} {dir_name}/ 正常：{folders} 个商品目录，{total} 张图片。')


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
    parser.add_argument('--env-file', default='', help='指定 .env 文件（默认依次尝试 .env / .env.production）')
    parser.add_argument('--media-root', default='', help='覆盖 MEDIA_ROOT')
    args = parser.parse_args()

    env = {}
    if args.env_file:
        env = load_env(args.env_file)
        print(f'{INFO} 使用环境文件: {args.env_file}')
    else:
        for name in ('.env', '.env.production'):
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
