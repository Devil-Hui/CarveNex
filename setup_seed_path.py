#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤 1（引导式）：声明产品图片与信息的位置，并写入 .env / .env.production。

目录约定：
    <第1问输入的路径，末尾为 product_pic>/
        products.xlsx        # 产品信息 Excel（第2问，放在 product_pic 下面）
        产品名1/             # 带有产品名称的文件夹（其上级目录即 product_pic）
        产品名2/

只修改（或新增）SEED_PRODUCTS_DIR / SEED_XLSX_NAME 两个键，
其余内容、注释、顺序原样保留，不会破坏已有配置（数据库密码、R2 密钥等）。

用法：
    python setup_seed_path.py                          # 引导式输入（推荐）
    python setup_seed_path.py /data/product_pic        # 非交互：直接指定目录
    python setup_seed_path.py --env-file .env.production     # 写入生产环境文件
    python setup_seed_path.py --show                   # 只看当前配置
"""
import argparse
import os
import sys

KEY_DIR = 'SEED_PRODUCTS_DIR'
KEY_XLSX = 'SEED_XLSX_NAME'
DEFAULT_XLSX = 'products.xlsx'
PASS, FAIL, WARN, INFO = '[PASS]', '[FAIL]', '[WARN]', '[INFO]'


def read_env_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.readlines()


def get_env_value(lines, key):
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith(f'{key}='):
            return stripped.split('=', 1)[1].strip()
    return None


def upsert_env(lines, key, value):
    """更新已有键（含被注释的同名行），否则追加。返回 (新内容, 动作)。"""
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f'{key}=') or stripped.startswith(f'#{key}='):
            lines[idx] = f'{key}={value}\n'
            return lines, 'updated'
    if lines and not lines[-1].endswith('\n'):
        lines.append('\n')
    lines.append(f'{key}={value}\n')
    return lines, 'added'


def ask(prompt, default):
    """读取一行输入；直接回车用默认值。中断时返回 None。"""
    print(prompt)
    if default:
        print(f'   （直接回车使用: {default}）')
    try:
        typed = input('   > ')
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    # 清理粘贴时常混入的 BOM、不可见字符与包裹引号，
    # 否则路径会变成 "C:\xxx\<BOM>D:\..." 这种拼接错误。
    typed = typed.replace('\ufeff', '').replace('\u200b', '').strip()
    typed = typed.strip('"').strip("'").strip()
    return typed or default


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description='声明产品图片与信息的位置')
    parser.add_argument('path', nargs='?', default='',
                        help='product_pic 目录路径（末尾为 product_pic）')
    parser.add_argument('--env-file', default='.env',
                        help='要修改的 env 文件（默认 .env，生产用 .env.production）')
    parser.add_argument('--xlsx', default='', help=f'Excel 文件名（默认 {DEFAULT_XLSX}）')
    parser.add_argument('--create', action='store_true', help='目录不存在时自动创建')
    parser.add_argument('--show', action='store_true', help='仅查看当前配置，不修改')
    args = parser.parse_args()

    env_path = args.env_file
    if not os.path.isabs(env_path):
        env_path = os.path.join(here, env_path)

    lines = read_env_lines(env_path)
    cur_dir = get_env_value(lines, KEY_DIR)
    cur_xlsx = get_env_value(lines, KEY_XLSX)

    if args.show:
        print(f'环境文件: {env_path}')
        print(f'{KEY_DIR} = {cur_dir or "(未设置)"}')
        print(f'{KEY_XLSX} = {cur_xlsx or f"(默认 {DEFAULT_XLSX})"}')
        if cur_dir:
            print(f'目录存在: {os.path.isdir(cur_dir)}')
        return 0

    print()
    print('现在是产品图片及信息声明，请按照顺序进行依次完成：')
    print('注意-此处需要将带有产品名称的文件夹的上级目录为/product_pic/')
    print()

    # ── 第 1 问：product_pic 路径 ─────────────────────────────
    # 统一默认到 <仓库>/backend/seed_products，与 verify_media_sources.py、
    # seed_products 命令的默认值保持一致，避免多处路径各说各话。
    default_dir = cur_dir or args.path or os.path.join(here, 'backend', 'seed_products')
    print('1.当前/product_pic/的路径为(包含/product_pic/),请输入：')
    typed = ask('', default_dir)
    if typed is None:
        print(f'{WARN} 已取消，未做任何修改。')
        return 1
    target = os.path.abspath(os.path.expanduser(typed))

    # 友好校验该路径
    if not os.path.exists(target):
        if args.create:
            try:
                os.makedirs(target, exist_ok=True)
                print(f'{PASS} 已创建目录: {target}')
            except OSError as exc:
                print(f'{FAIL} 无法创建: {exc}（换一个有权限的路径，或加 sudo）')
                return 1
        else:
            print(f'{WARN} 该目录尚不存在，仍会写入配置；请稍后创建并放入内容。')
    elif not os.path.isdir(target):
        print(f'{FAIL} 该路径是文件不是目录，请输入目录路径。')
        return 1
    print()

    # ── 第 2 问：Excel ────────────────────────────────────────
    print('2.将产品信息excel放到/product_pic/下面，请输入：')
    default_xlsx = cur_xlsx or args.xlsx or DEFAULT_XLSX
    typed_x = ask('', default_xlsx)
    if typed_x is None:
        print(f'{WARN} 已取消，未做任何修改。')
        return 1
    xlsx_name = os.path.basename(typed_x) or DEFAULT_XLSX

    xlsx_path = os.path.join(target, xlsx_name)
    if os.path.isfile(xlsx_path):
        size_kb = os.path.getsize(xlsx_path) / 1024.0
        print(f'{PASS} 已找到 Excel: {xlsx_path}（{size_kb:.1f} KB）')
    else:
        print(f'{WARN} 该 Excel 目前不在 product_pic 下: {xlsx_path}')
        print('       请先把它放进去，之后用 verify_media_sources.py 会明确检查。')
    print()

    # ── 写入配置 ─────────────────────────────────────────────
    try:
        new_lines, a1 = upsert_env(lines, KEY_DIR, target)
        new_lines, a2 = upsert_env(new_lines, KEY_XLSX, xlsx_name)
        with open(env_path, 'w', encoding='utf-8') as fh:
            fh.writelines(new_lines)
    except OSError as exc:
        print(f'{FAIL} 写入失败 {env_path}: {exc}')
        print(f'       你也可以手动在 {env_path} 里加这两行：')
        print(f'       {KEY_DIR}={target}')
        print(f'       {KEY_XLSX}={xlsx_name}')
        return 1

    print('已完成配置更新')
    print(f'       {KEY_DIR}={target}（{"更新" if a1 == "updated" else "新增"}）')
    print(f'       {KEY_XLSX}={xlsx_name}（{"更新" if a2 == "updated" else "新增"}）')
    print(f'{INFO} 文件其余内容（数据库密码、R2 密钥等）未改动。')
    print()
    print('=' * 58)
    print('下一步（步骤 2）：检验')
    print('=' * 58)
    print('    python verify_media_sources.py')
    print('全部 [PASS] 后再执行 docker 构建。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
