#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤 1：把商品数据源路径写入 .env / .env.prod。

只修改（或新增）指定的键，其余内容、注释、顺序原样保留，不会破坏已有配置
（如数据库密码、R2 密钥等）。

用法：
    python setup_seed_path.py /data/my_seed                  # 写入 .env
    python setup_seed_path.py /data/my_seed --env-file .env.prod
    python setup_seed_path.py                                # 交互式询问路径
    python setup_seed_path.py /data/my_seed --create         # 路径不存在时自动创建
    python setup_seed_path.py --show                         # 只看当前配置，不修改

也可以完全不用本脚本，直接用编辑器手动在 .env 里加一行：
    SEED_PRODUCTS_DIR=/你的/路径
"""
import argparse
import os
import sys

KEY = 'SEED_PRODUCTS_DIR'
PASS, FAIL, WARN, INFO = '[PASS]', '[FAIL]', '[WARN]', '[INFO]'


def read_env_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.readlines()


def get_env_value(lines, key):
    """返回 key 当前的值（忽略被注释掉的同名行），未设置返回 None。"""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith(f'{key}='):
            return stripped.split('=', 1)[1].strip()
    return None


def upsert_env(lines, key, value):
    """更新已有的 key（含被注释的同名行），否则追加到末尾。返回 (新内容, 动作)。"""
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f'{key}=') or stripped.startswith(f'#{key}='):
            lines[idx] = f'{key}={value}\n'
            return lines, 'updated'
    if lines and not lines[-1].endswith('\n'):
        lines.append('\n')
    lines.append(f'\n# 商品数据源目录（products.xlsx + images/），由 setup_seed_path.py 写入\n')
    lines.append(f'{key}={value}\n')
    return lines, 'added'


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description='配置商品数据源路径到 env 文件')
    parser.add_argument('path', nargs='?', default='',
                        help='商品数据源目录（products.xlsx + images/ 所在目录）')
    parser.add_argument('--env-file', default='.env',
                        help='要修改的 env 文件（默认 .env，生产可用 .env.prod）')
    parser.add_argument('--create', action='store_true',
                        help='路径不存在时自动创建该目录')
    parser.add_argument('--show', action='store_true',
                        help='仅显示当前配置，不做任何修改')
    args = parser.parse_args()

    env_path = args.env_file
    if not os.path.isabs(env_path):
        env_path = os.path.join(here, env_path)

    lines = read_env_lines(env_path)
    current = get_env_value(lines, KEY)

    # 仅查看
    if args.show:
        print(f'环境文件: {env_path}')
        print(f'{KEY} = {current if current else "(未设置)"}')
        if current:
            exists = os.path.isdir(current)
            print(f'目录存在: {exists}')
            if exists:
                xlsx = os.path.isfile(os.path.join(current, 'products.xlsx'))
                print(f'products.xlsx: {"存在" if xlsx else "缺失"}')
        return 0

    # 取得目标路径
    target = args.path
    if not target:
        default_hint = current or os.path.join(here, 'backend', 'seed_products')
        print('请输入商品数据源目录（products.xlsx + images/ 所在目录）。')
        print(f'直接回车使用默认: {default_hint}')
        try:
            typed = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print(f'\n{WARN} 已取消。')
            return 1
        target = typed or default_hint

    target = os.path.abspath(os.path.expanduser(target))

    # 路径处理
    if not os.path.exists(target):
        if args.create:
            try:
                os.makedirs(target, exist_ok=True)
                print(f'{PASS} 已创建目录: {target}')
            except OSError as exc:
                print(f'{FAIL} 无法创建目录 {target}: {exc}')
                print('       修复：换一个你有权限的路径，或用管理员权限运行。')
                return 1
        else:
            print(f'{WARN} 目录尚不存在: {target}')
            print('       仍会写入配置；请先放入 products.xlsx 与 images/，')
            print('       之后用 verify_media_sources.py 检查（缺少文件会明确报出）。')
            print('       若想现在就创建，可加 --create 参数。')
    elif not os.path.isdir(target):
        print(f'{FAIL} 路径存在但不是目录: {target}')
        print('       修复：请指向一个目录，而不是文件。')
        return 1

    # 写入 env（保留其他配置）
    new_lines, action = upsert_env(lines, KEY, target)
    try:
        with open(env_path, 'w', encoding='utf-8') as fh:
            fh.writelines(new_lines)
    except OSError as exc:
        print(f'{FAIL} 写入失败 {env_path}: {exc}')
        print('       修复：确认文件可写；也可以直接用编辑器手动添加这一行：')
        print(f'       {KEY}={target}')
        return 1

    verb = '已更新' if action == 'updated' else '已新增'
    print(f'{PASS} {verb} {env_path}')
    print(f'       {KEY}={target}')
    print(f'{INFO} 文件其余内容（数据库密码、R2 密钥等）未改动。')

    print()
    print('=' * 58)
    print('下一步：用第二个脚本测试')
    print('=' * 58)
    print(f'    python verify_media_sources.py --dir "{target}"')
    print('确认全部 [PASS] 后，再执行 docker 构建。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
