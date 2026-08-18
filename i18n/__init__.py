#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i18n 模块：从独立的 JSON 文件加载 16 种语言的翻译。

目录结构:
    i18n/
        __init__.py            <- 本文件
        translations/
            en.json
            zh.json
            es.json
            hi.json
            ar.json
            bn.json
            fr.json
            ru.json
            pt.json
            id.json
            de.json
            ja.json
            ur.json
            ko.json
            it.json
            tr.json

使用方法:
    from i18n import t, set_language, get_language
    set_language("zh")
    print(t("app_title"))               # 不带参数
    print(t("rule_count_label", n=5))   # 带占位符
"""

import json
import locale
import os

# ---------------------------------------------------------------------------
# 基本常量：Top 16 种最常用语言
# （按母语使用者排名 + 互联网覆盖综合选的 16 种常见语言）
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = (
    "en", "zh", "es", "hi", "ar", "bn", "fr", "ru", "pt",
    "id", "de", "ja", "ur", "ko", "it", "tr",
)

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "中文",
    "es": "Español",
    "hi": "हिन्दी",
    "ar": "العربية",
    "bn": "বাংলা",
    "fr": "Français",
    "ru": "Русский",
    "pt": "Português",
    "id": "Bahasa Indonesia",
    "de": "Deutsch",
    "ja": "日本語",
    "ur": "اردو",
    "ko": "한국어",
    "it": "Italiano",
    "tr": "Türkçe",
}

DEFAULT_LANGUAGE = "en"

# ---------------------------------------------------------------------------
# 运行时状态
# ---------------------------------------------------------------------------
_TRANSLATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "translations")
_CATALOG_CACHE = {}          # lang_code -> dict
_CURRENT_LANGUAGE = DEFAULT_LANGUAGE


def load_translations(code):
    """加载指定语言的 catalog。文件不存在/损坏时返回空 dict，不崩溃。"""
    if not isinstance(code, str):
        return {}
    if code in _CATALOG_CACHE:
        return _CATALOG_CACHE[code]

    path = os.path.join(_TRANSLATIONS_DIR, "%s.json" % code)
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            result = data
    except Exception:
        result = {}

    _CATALOG_CACHE[code] = result
    return result


def get_catalog(code):
    """返回指定语言的 catalog dict（只读使用）。"""
    return load_translations(code)


def set_language(code):
    """切换当前语言。无效代码被忽略（保持之前的语言）。"""
    global _CURRENT_LANGUAGE
    if code in SUPPORTED_LANGUAGES:
        # 触发一次加载（确保缓存中有；失败了也没关系）
        load_translations(code)
        _CURRENT_LANGUAGE = code


def get_language():
    return _CURRENT_LANGUAGE


def detect_system_language():
    """尽力检测系统语言，映射到 16 种支持的代码之一。
    失败则回退到 DEFAULT_LANGUAGE。"""
    candidates = []
    try:
        loc = locale.getlocale()
        if loc and loc[0]:
            candidates.append(loc[0])
    except Exception:
        pass
    try:
        loc = locale.getdefaultlocale()
        if loc and loc[0]:
            candidates.append(loc[0])
    except Exception:
        pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(var)
        if val:
            candidates.append(val)

    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        code = candidate.replace("-", "_").split(".")[0].split("_")[0].lower()
        # 部分特殊映射：例如 zh-cn / zh-tw 都归为 zh；pt-br 归为 pt
        if code == "zh":
            return "zh"
        if code in SUPPORTED_LANGUAGES:
            return code

    return DEFAULT_LANGUAGE


def t(key, **kwargs):
    """翻译 key。优先当前语言 → 回退英文 → 回退 key 本身。
    任何错误都不抛出，仅尽力渲染。"""
    cur = _CURRENT_LANGUAGE
    current_catalog = load_translations(cur) if cur != DEFAULT_LANGUAGE else {}
    if cur == DEFAULT_LANGUAGE:
        current_catalog = load_translations(DEFAULT_LANGUAGE)

    text = None
    if key in current_catalog:
        text = current_catalog[key]
    if not text and cur != DEFAULT_LANGUAGE:
        fallback = load_translations(DEFAULT_LANGUAGE)
        text = fallback.get(key)
    if not text:
        text = key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
