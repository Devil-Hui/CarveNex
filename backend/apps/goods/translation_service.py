"""
腾讯云机器翻译（TMT）服务。

用于商品名称/描述等内容的自动翻译（如翻译成阿拉伯语）。
基于腾讯云 TMT TextTranslate API（TC3-HMAC-SHA256 签名）。

未配置 TMT_SECRET_ID / TMT_SECRET_KEY 时，translate_text 返回 None，
前端可据此优雅降级（隐藏翻译按钮或提示未配置）。
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger('biz')

TMT_ENDPOINT = 'tmt.tencentcloudapi.com'
TMT_VERSION = '2018-03-21'
TMT_ACTION = 'TextTranslate'
TMT_SERVICE = 'tmt'

# 腾讯云机器翻译支持的语种代码（与前端 i18n 语言代码对齐）
LANG_MAP = {
    'zh': 'zh',        # 中文
    'en': 'en',        # 英语
    'ar': 'ar',        # 阿拉伯语
    'auto': 'auto',    # 自动检测
}


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def _sha256_hex(msg: str) -> str:
    return hashlib.sha256(msg.encode('utf-8')).hexdigest()


def _sign(secret_key: str, date: str, service: str, payload: str) -> str:
    """TC3-HMAC-SHA256 签名。"""
    secret_date = _hmac_sha256(('TC3' + secret_key).encode('utf-8'), date)
    secret_service = _hmac_sha256(secret_date, service)
    secret_signing = _hmac_sha256(secret_service, 'tc3_request')
    return hmac.new(secret_signing, payload.encode('utf-8'), hashlib.sha256).hexdigest()


def translate_text(text: str, source: str = 'auto', target: str = 'ar', project_id: int = 0) -> str | None:
    """
    调用腾讯云机器翻译将文本翻译为目标语言。

    :param text: 待翻译文本
    :param source: 源语言代码（zh/en/ar/auto），默认 auto 自动检测
    :param target: 目标语言代码（zh/en/ar）
    :param project_id: 腾讯云项目 ID，默认 0
    :return: 翻译结果字符串；未配置密钥或调用失败时返回 None
    """
    if not text or not text.strip():
        return ''
    secret_id = getattr(settings, 'TMT_SECRET_ID', '')
    secret_key = getattr(settings, 'TMT_SECRET_KEY', '')
    if not secret_id or not secret_key:
        logger.warning('TMT 未配置 TMT_SECRET_ID/TMT_SECRET_KEY，跳过翻译')
        return None

    region = getattr(settings, 'TMT_REGION', 'ap-guangzhou')
    source = LANG_MAP.get(source, source)
    target = LANG_MAP.get(target, target)

    # 请求体（JSON）
    payload = json.dumps({
        'SourceText': text,
        'Source': source,
        'Target': target,
        'ProjectId': project_id,
    }, ensure_ascii=False)

    # 时间戳与日期
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    date = now.strftime('%Y-%m-%d')

    # 规范请求
    canonical_headers = (
        f'content-type:application/json; charset=utf-8\n'
        f'host:{TMT_ENDPOINT}\n'
        f'x-tc-action:{TMT_ACTION.lower()}\n'
    )
    signed_headers = 'content-type;host;x-tc-action'
    hashed_payload = _sha256_hex(payload)
    canonical_request = '\n'.join([
        'POST',
        '/',
        '',
        canonical_headers,
        signed_headers,
        hashed_payload,
    ])

    # 待签名串
    credential_scope = f'{date}/{TMT_SERVICE}/tc3_request'
    hashed_canonical_request = _sha256_hex(canonical_request)
    string_to_sign = '\n'.join([
        'TC3-HMAC-SHA256',
        str(timestamp),
        credential_scope,
        hashed_canonical_request,
    ])

    # 签名
    signature = _sign(secret_key, date, TMT_SERVICE, string_to_sign)
    authorization = (
        f'TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, '
        f'SignedHeaders={signed_headers}, Signature={signature}'
    )

    headers = {
        'Authorization': authorization,
        'Content-Type': 'application/json; charset=utf-8',
        'Host': TMT_ENDPOINT,
        'X-TC-Action': TMT_ACTION,
        'X-TC-Version': TMT_VERSION,
        'X-TC-Timestamp': str(timestamp),
        'X-TC-Region': region,
    }

    try:
        resp = requests.post(
            f'https://{TMT_ENDPOINT}',
            data=payload.encode('utf-8'),
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if 'Response' in data and 'TargetText' in data['Response']:
            return data['Response']['TargetText']
        logger.error('TMT 翻译失败: %s', data)
        return None
    except Exception as e:  # noqa: BLE001
        logger.error('TMT 翻译异常: %s', e)
        return None