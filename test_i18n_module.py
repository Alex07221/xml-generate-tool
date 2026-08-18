#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TDD: 新 i18n 模块（独立目录 + 16种语言 JSON）的单元测试。
第一步运行应 FAIL（模块/文件还不存在），第二步实现后应全部 PASS。
"""
import os
import sys
import tempfile
import json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILURES = []

def check(name, cond):
    s = "PASS" if cond else "FAIL"
    print("[%s] %s" % (s, name))
    if not cond:
        FAILURES.append(name)

# ---------------------------------------------------------------------------
# 1. 模块本身可导入
# ---------------------------------------------------------------------------
try:
    from i18n import (
        SUPPORTED_LANGUAGES,
        LANGUAGE_NAMES,
        DEFAULT_LANGUAGE,
        set_language,
        get_language,
        t,
        detect_system_language,
        load_translations,
        get_catalog,
    )
    MODULE_IMPORTABLE = True
except Exception as e:
    print("IMPORT ERROR:", e)
    MODULE_IMPORTABLE = False

check("i18n 模块可导入", MODULE_IMPORTABLE)

if not MODULE_IMPORTABLE:
    print("\n终止：模块无法导入，后续测试无法进行。")
    sys.exit(1)

# ---------------------------------------------------------------------------
# 2. 语言数量与名称完整性
# ---------------------------------------------------------------------------
TOP_16 = {"en", "zh", "es", "hi", "ar", "bn", "fr", "ru", "pt",
          "id", "de", "ja", "ur", "ko", "it", "tr"}

check("SUPPORTED_LANGUAGES 正好 16 种", len(SUPPORTED_LANGUAGES) == 16)
check("SUPPORTED_LANGUAGES 覆盖 Top16 语言代码", TOP_16.issubset(set(SUPPORTED_LANGUAGES)))
check("DEFAULT_LANGUAGE 为 en", DEFAULT_LANGUAGE == "en")
check("LANGUAGE_NAMES 中每种语言都有母语显示名",
      all(LANGUAGE_NAMES.get(code) for code in SUPPORTED_LANGUAGES))

# ---------------------------------------------------------------------------
# 3. 翻译目录 & JSON 文件完整性
# ---------------------------------------------------------------------------
TRANSLATIONS_DIR = os.path.join(HERE, "i18n", "translations")
check("translations/ 目录存在", os.path.isdir(TRANSLATIONS_DIR))
if os.path.isdir(TRANSLATIONS_DIR):
    for code in SUPPORTED_LANGUAGES:
        path = os.path.join(TRANSLATIONS_DIR, "%s.json" % code)
        check("翻译文件存在: %s.json" % code, os.path.isfile(path))
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                check("%s.json 是一个 JSON 对象" % code, isinstance(data, dict))
                check("%s.json 内容非空" % code, len(data) > 0)
            except Exception as e:
                check("%s.json 可被正确解析为 JSON" % code, False)
                print("   ->", e)

# ---------------------------------------------------------------------------
# 4. get_catalog / t() 基本功能
# ---------------------------------------------------------------------------
catalog_en = get_catalog("en")
check("get_catalog('en') 返回非空 dict", isinstance(catalog_en, dict) and len(catalog_en) > 0)

# 主程序中用到的一些关键 key 必须在英文里有（这是基准语言）
REQUIRED_KEYS = [
    "app_title", "file1_label", "file2_label",
    "load_compare_button", "save_button", "preview_button",
    "legend_added", "legend_removed", "legend_modified", "legend_changed",
    "col_element", "col_path", "col_state", "col_source",
    "source_file1", "source_file2",
    "state_added", "state_removed", "state_modified", "state_changed", "state_same",
    "choose_file_button", "only_diff_checkbox",
]
missing = [k for k in REQUIRED_KEYS if k not in catalog_en]
check("英文 catalog 包含所有必需的 UI key（%d 个）" % len(REQUIRED_KEYS), len(missing) == 0)
if missing:
    print("   missing:", missing[:10])

# ---------------------------------------------------------------------------
# 5. set_language / get_language / t() 工作流
# ---------------------------------------------------------------------------
set_language("en")
check("set_language('en') 后 get_language() == 'en'", get_language() == "en")
check("t('state_added') 在英文下返回 'Added' 或同值",
      t("state_added").lower() in ("added", "new"))

# 切换到中文，看常见 key 是否存在且不同于英文
set_language("zh")
zh_val = t("app_title")
en_val = catalog_en.get("app_title", "")
check("切换到中文后 get_language() == 'zh'", get_language() == "zh")
check("中文 app_title 存在且非空", bool(zh_val))
check("中文 app_title 与英文不同（避免全抄英文）", zh_val != en_val)

# ---------------------------------------------------------------------------
# 6. 占位符格式化
# ---------------------------------------------------------------------------
# rule_count_label / diff_pos_label / status_compare_done / status_saved
# 必须在每一种语言里都能成功 .format(n=?, current=?, total=?, diff_count=?, minimal_count=?, path=?)
FORMAT_KEYS = {
    "rule_count_label": {"n": 5},
    "diff_pos_label": {"current": 2, "total": 10},
    "status_compare_done": {"diff_count": 20, "minimal_count": 8},
    "status_saved": {"path": "/tmp/x.xml"},
    "status_rules_set": {"n": 9},
    "status_manual_wizard_updated": {"n": 4},
    "detail_path_header": {"path": "/root/a/b"},
    "detail_current_source": {"source": "File 1"},
    "parse_error_message": {"path": "/x/y.xml", "error": "boom"},
    "group_row_label": {"tag": "item", "n": 3},
    "detail_group_header": {"tag": "item", "n": 3},
    "blocked_rule_msg": {"n": 2},
    "wizard_pos_label": {"current": 1, "total": 5},
    "current_choice_label": {"source": "File 1"},
}

# 先检查英文 catalog 中这些 key 都存在
for fk in FORMAT_KEYS:
    check("英文 catalog 存在带参数的 key: %s" % fk, fk in catalog_en)

# 再逐语言渲染，不允许出现未替换的 {xxx}
render_errors = []
for code in SUPPORTED_LANGUAGES:
    set_language(code)
    for fk, kwargs in FORMAT_KEYS.items():
        try:
            rendered = t(fk, **kwargs)
            if "{" in rendered and "}" in rendered:
                render_errors.append((code, fk, rendered))
        except Exception as e:
            render_errors.append((code, fk, "EXCEPTION: %s" % e))
check("16 种语言中 %d 个带参数 key 全部干净渲染（无残留占位符/异常）" % len(FORMAT_KEYS),
      len(render_errors) == 0)
if render_errors:
    print("   render errors:", render_errors[:12])

# ---------------------------------------------------------------------------
# 7. detect_system_language 必须返回一个支持的代码
# ---------------------------------------------------------------------------
detected = detect_system_language()
check("detect_system_language() 返回值在 SUPPORTED_LANGUAGES 中",
      detected in SUPPORTED_LANGUAGES)

# ---------------------------------------------------------------------------
# 8. 未知代码不切换 / 未知 key 回退到 key 本身（不崩溃）
# ---------------------------------------------------------------------------
set_language("en")
set_language("xx_yy_unsupported_1234")
check("set_language(未知代码) 不会崩溃，并且语言保持不变", get_language() == "en")

rendered_unknown = t("this_key_does_not_exist_at_all_xyz_123")
check("t(未知 key) 返回 key 本身，不崩溃",
      rendered_unknown == "this_key_does_not_exist_at_all_xyz_123")

# ---------------------------------------------------------------------------
# 9. load_translations() 对缺失文件返回空 dict / 不崩溃
# ---------------------------------------------------------------------------
bogus = load_translations("zzzz_not_exist_code")
check("load_translations(不存在的语言) 返回空 dict 不崩溃",
      isinstance(bogus, dict) and len(bogus) == 0)

# ---------------------------------------------------------------------------
# 10. 跨 key 一致性：带参数和不带参数的都有
# ---------------------------------------------------------------------------
# 简单统计英文 catalog 的大小，确认不是一个残缺文件
check("英文 catalog 至少包含 60 个以上的翻译键（规模合理）",
      len(catalog_en) >= 60)

# ---------------------------------------------------------------------------
print()
if FAILURES:
    print("%d 个测试 FAILED: %s" % (len(FAILURES), FAILURES))
    sys.exit(1)
else:
    print("全部 i18n 模块测试通过（%d 种语言 / %d 个用例）。"
          % (len(SUPPORTED_LANGUAGES),
             sum(1 for _ in FAILURES) + 1))  # placeholder
