#!/usr/bin/env python3
"""Regression tests for the pure (non-GUI) diff/merge logic in
xml_merge_tool_v2.py. Run with: python3 test_diff_logic.py
"""
import xml.etree.ElementTree as ET
import sys

import xml_merge_tool_v2 as tool

failures = []


def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print("[%s] %s" % (status, name))
    if not condition:
        failures.append(name)


def parse(s):
    return ET.fromstring(s)


# ---------------------------------------------------------------------------
# Scenario 1: the user's example - item1/a and item2/a both change, inside a
# loop-like structure. Expectation: two independent "modified" diffs, both
# under tag 'a', groupable together.
# ---------------------------------------------------------------------------
xml1 = parse("""
<root>
  <item1><a>hello</a><b>same</b></item1>
  <item2><a>world</a><b>same</b></item2>
</root>
""")
xml2 = parse("""
<root>
  <item1><a>HELLO</a><b>same</b></item1>
  <item2><a>WORLD</a><b>same</b></item2>
</root>
""")

diff, i1, i2, r1, r2 = tool.diff_paths(xml1, xml2)
kinds, minimal, value_pairs = tool.build_diff_model(i1, i2)

a_paths = [p for p in minimal if tool.path_leaf_tag(p) == "a"]
check("scenario1: exactly two minimal 'a' diffs found (one per item)", len(a_paths) == 2)
check("scenario1: both 'a' diffs reconciled into single 'modified' pairs",
      all(minimal[p] == "modified" and p.startswith("pair:") for p in a_paths))
check("scenario1: 'b' (identical) not in minimal set",
      not any(tool.path_leaf_tag(p) == "b" for p in minimal))

groups = tool.group_minimal_diffs_by_tag(minimal)
check("scenario1: grouping produces one 'a' group with 2 members",
      "a" in groups and len(groups["a"]) == 2)

# root and item1/item2 should show as "changed" (ancestor-only), not minimal
check("scenario1: root is 'changed', not in minimal",
      kinds["/root"] == "changed" and "/root" not in minimal)

a1, a2 = tool.resolve_diff_nodes(a_paths[0], i1, i2, value_pairs)
check("scenario1: resolve_diff_nodes finds both sides of a reconciled pair",
      a1 is not None and a2 is not None and a1.text != a2.text)


# ---------------------------------------------------------------------------
# Scenario 2: whole subtree added / removed. Expectation: only the top node
# of the added/removed subtree is minimal; descendants are NOT listed
# separately (selecting the parent rule already brings the whole subtree).
# ---------------------------------------------------------------------------
xml1b = parse("""
<root>
  <keep>1</keep>
  <gone><child><grandchild>x</grandchild></child></gone>
</root>
""")
xml2b = parse("""
<root>
  <keep>1</keep>
  <fresh><child><grandchild>y</grandchild></child></fresh>
</root>
""")

diffb, i1b, i2b, r1b, r2b = tool.diff_paths(xml1b, xml2b)
kindsb, minimalb, value_pairsb = tool.build_diff_model(i1b, i2b)

removed_roots = [p for p, k in minimalb.items() if k == "removed"]
added_roots = [p for p, k in minimalb.items() if k == "added"]
check("scenario2: exactly one 'removed' minimal root (<gone>)",
      len(removed_roots) == 1 and tool.path_leaf_tag(removed_roots[0]) == "gone")
check("scenario2: exactly one 'added' minimal root (<fresh>)",
      len(added_roots) == 1 and tool.path_leaf_tag(added_roots[0]) == "fresh")
check("scenario2: no descendants of <gone>/<fresh> appear in minimal set",
      not any(p.startswith(removed_roots[0] + "/") for p in minimalb) and
      not any(p.startswith(added_roots[0] + "/") for p in minimalb))
check("scenario2: unrelated identical node <keep> is 'same'",
      all(kindsb[p] == "same" for p in kindsb if tool.path_leaf_tag(p) == "keep"))


# ---------------------------------------------------------------------------
# Scenario 3: apply_merge_rules still works correctly with ONLY minimal
# (leaf-level) rules - this is the scenario that used to be fragile when
# ancestor paths could also be selected as rules.
# ---------------------------------------------------------------------------
item1_pair = next(p for p in a_paths if "item1" in value_pairs[p]["parent_path"])
item2_pair = next(p for p in a_paths if "item2" in value_pairs[p]["parent_path"])
rules = {item1_pair: "xml2", item2_pair: "xml1"}
merged = tool.apply_merge_rules(xml1, xml2, rules)
item1_a = merged.find("./item1/a").text
item2_a = merged.find("./item2/a").text
check("scenario3: item1/a took XML2 value", item1_a == "HELLO")
check("scenario3: item2/a took XML1 value (default, explicit)", item2_a == "world")

rules2 = {removed_roots[0]: "xml1", added_roots[0]: "xml2"}
merged2 = tool.apply_merge_rules(xml1b, xml2b, rules2)
check("scenario3b: merged result keeps <gone> subtree intact",
      merged2.find("./gone/child/grandchild").text == "x")
check("scenario3b: merged result pulls in whole <fresh> subtree from xml2",
      merged2.find("./fresh/child/grandchild").text == "y")


# ---------------------------------------------------------------------------
# Scenario 4: end-to-end "group rule" workflow, as MergeSelector.set_all /
# apply_source would drive it - set ONE rule for the whole 'a' group and
# confirm it applies to every occurrence.
# ---------------------------------------------------------------------------
group_rules = {p: "xml2" for p in a_paths}  # simulate "apply to whole group"
merged3 = tool.apply_merge_rules(xml1, xml2, group_rules)
check("scenario4: group rule (all 'a' -> xml2) updates item1/a",
      merged3.find("./item1/a").text == "HELLO")
check("scenario4: group rule (all 'a' -> xml2) updates item2/a",
      merged3.find("./item2/a").text == "WORLD")
check("scenario4: unrelated 'b' elements untouched by the group rule",
      merged3.find("./item1/b").text == "same" and merged3.find("./item2/b").text == "same")


# ---------------------------------------------------------------------------
# Scenario 5: i18n - translation catalog completeness and language switching
# ---------------------------------------------------------------------------
missing_translations = []
for key, entry in tool.TRANSLATIONS.items():
    for lang in tool.SUPPORTED_LANGUAGES:
        if not entry.get(lang):
            missing_translations.append((key, lang))

check("i18n: every key has all %d supported languages (Top 16: en zh es hi ar bn fr ru pt id de ja ur ko it tr)"
      % len(tool.SUPPORTED_LANGUAGES),
      len(missing_translations) == 0)
if missing_translations:
    print("    missing:", missing_translations[:10])

TOP_16 = {"en", "zh", "es", "hi", "ar", "bn", "fr", "ru", "pt",
          "id", "de", "ja", "ur", "ko", "it", "tr"}
check("i18n: exactly 16 supported languages (Top 16 worldwide)",
      set(tool.SUPPORTED_LANGUAGES) == TOP_16 and len(tool.SUPPORTED_LANGUAGES) == 16)

tool.set_language("fr")
check("i18n: set_language + t() switches text", tool.t("cancel_button") == "Annuler")
check("i18n: t() supports placeholder formatting",
      tool.t("rule_count_label", n=5) == "Règles de fusion : 5")

tool.set_language("xx")  # unsupported code should be ignored, not crash
check("i18n: set_language ignores unsupported codes (stays on previous)",
      tool.get_language() == "fr")

tool.set_language("en")
check("i18n: unknown key falls back to the key itself, no crash",
      tool.t("this_key_does_not_exist") == "this_key_does_not_exist")

check("i18n: detect_system_language always returns a supported code",
      tool.detect_system_language() in tool.SUPPORTED_LANGUAGES)


# ---------------------------------------------------------------------------
# Scenario 6: every parameterized translation key actually renders in all 5
# languages without raising (catches placeholder-name typos in any one
# language's translation, which would otherwise only surface when a user
# happens to be on that specific language).
# ---------------------------------------------------------------------------
PARAM_KEYS_AND_SAMPLE_KWARGS = {
    "rule_count_label": {"n": 3},
    "diff_pos_label": {"current": 2, "total": 5},
    "status_compare_done": {"diff_count": 10, "minimal_count": 3},
    "status_saved": {"path": "/tmp/out.xml"},
    "status_manual_wizard_updated": {"n": 4},
    "status_rules_set": {"n": 4},
    "detail_location_header": {"location": "/root/a"},
    "detail_current_source": {"source": "File 1"},
    "parse_error_message": {"path": "/tmp/x.xml", "error": "boom"},
    "group_row_label": {"tag": "a", "n": 2},
    "detail_group_header": {"tag": "a", "n": 2},
    "blocked_rule_msg": {"n": 1},
    "wizard_pos_label": {"current": 1, "total": 3},
    "current_choice_label": {"source": "File 1"},
}

render_failures = []
for key, kwargs in PARAM_KEYS_AND_SAMPLE_KWARGS.items():
    for lang in tool.SUPPORTED_LANGUAGES:
        tool.set_language(lang)
        rendered = tool.t(key, **kwargs)
        if "{" in rendered and "}" in rendered:
            # a raw {placeholder} surviving .format() means a mismatched
            # kwarg name in that language's translation
            render_failures.append((key, lang, rendered))
tool.set_language("en")

check("i18n: all parameterized keys render cleanly in every language (no leftover {placeholders})",
      len(render_failures) == 0)
if render_failures:
    print("    failures:", render_failures)


# ---------------------------------------------------------------------------
# Scenario 7: language choice persists through config load/save round trip
# ---------------------------------------------------------------------------
import tempfile

with tempfile.TemporaryDirectory() as tmpdir:
    cfg_path = tmpdir + "/xml_merge_config.json"
    original_config_file = tool.CONFIG_FILE
    tool.CONFIG_FILE = cfg_path
    try:
        cfg = tool.load_config()
        check("i18n: load_config on missing file returns empty dict", cfg == {})

        cfg["language"] = "ru"
        tool.save_config(cfg)
        reloaded = tool.load_config()
        check("i18n: saved language choice round-trips through config file",
              reloaded.get("language") == "ru")
    finally:
        tool.CONFIG_FILE = original_config_file


print()
if failures:
    print("%d test(s) FAILED: %s" % (len(failures), failures))
    sys.exit(1)
else:
    print("All tests passed.")
