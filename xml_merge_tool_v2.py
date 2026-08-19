#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import json
import locale
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    TK_AVAILABLE = True
except ImportError:
    # tkinter isn't installed in this environment (e.g. some CI/test
    # sandboxes). The pure diff/merge logic below has no GUI dependency and
    # can still be imported and unit tested; only main()/App/MergeSelector/
    # ManualMergeWizard require a real Tk installation to actually run.
    tk = None
    ttk = filedialog = messagebox = None
    TK_AVAILABLE = False


APP_NAME = "XML / META Merge Tool"
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd(),
    "xml_merge_config.json"
)

MATCH_KEYS = (
    "modelName", "modelname", "name", "Name",
    "filename", "fileName", "hash", "Hash",
    "id", "ID", "key", "Key", "type", "Type"
)


# ---------------------------------------------------------------------------
# Modern i18n layer – 16 languages loaded from i18n/translations/*.json
# ---------------------------------------------------------------------------
import i18n as _i18n

SUPPORTED_LANGUAGES = _i18n.SUPPORTED_LANGUAGES
LANGUAGE_NAMES    = _i18n.LANGUAGE_NAMES
DEFAULT_LANGUAGE  = _i18n.DEFAULT_LANGUAGE

set_language           = _i18n.set_language
get_language           = _i18n.get_language
t                      = _i18n.t
detect_system_language = _i18n.detect_system_language

# ---- Legacy TRANSLATIONS dict (key -> {lang: value}) for existing tests ----
TRANSLATIONS = {}
_EN = _i18n.get_catalog(DEFAULT_LANGUAGE)
for _k in _EN:
    TRANSLATIONS[_k] = {}
    for _code in SUPPORTED_LANGUAGES:
        TRANSLATIONS[_k][_code] = _i18n.get_catalog(_code).get(_k, "") or ""
del _EN


def state_label(kind):
    return t("state_" + kind) if kind else t("state_same")


# ---------------------------------------------------------------------------
# Inline i18n REMOVED: translations now live in i18n/translations/*.json
# 16 languages supported: en zh es hi ar bn fr ru pt id de ja ur ko it tr
# ---------------------------------------------------------------------------


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def save_config(obj):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def strip_namespace(tag):
    if not isinstance(tag, str):
        return str(tag)
    return tag.split("}", 1)[-1] if "}" in tag else tag


def normalize_text(value):
    if value is None:
        return ""
    return " ".join(str(value).split())


def pretty_xml(elem):
    raw = ET.tostring(elem, encoding="unicode")
    try:
        return minidom.parseString(raw).toprettyxml(indent="  ")
    except Exception:
        return raw


def element_to_xml_string(elem):
    """Render a single element as a compact XML string, e.g. <test>1</test>.
    Shows the tag + attributes + text content. For container elements with
    children, shows <tag attrs>...</tag>."""
    if elem is None:
        return ""
    tag = strip_namespace(elem.tag)
    attrs = ""
    for k, v in elem.attrib.items():
        val = str(v)
        if len(val) > 50:
            val = val[:47] + "..."
        attrs += ' %s="%s"' % (k, val)
    text = normalize_text(elem.text)
    children = list(elem)
    if not children and not text:
        return "<%s%s/>" % (tag, attrs)
    if not children:
        return "<%s%s>%s</%s>" % (tag, attrs, text, tag)
    return "<%s%s>...</%s>" % (tag, attrs, tag)


def element_summary(elem):
    """Return a short, human-readable summary of an element's *actual content*
    (not its internal path). Designed for non-developer users.

    Priority:
      1. Attributes shown as key="value" pairs (first 3, most informative)
      2. Leaf text content
      3. Children count for container elements
      4. Fallback: "—"
    """
    if elem is None:
        return ""

    # Attributes — most useful for config-style XML (key="..." value="...")
    attrs = list(elem.attrib.items())
    if attrs:
        parts = []
        for k, v in attrs[:3]:
            val = str(v)
            if len(val) > 40:
                val = val[:37] + "..."
            parts.append('%s="%s"' % (k, val))
        suffix = "" if len(attrs) <= 3 else "  (+%d)" % (len(attrs) - 3)
        return "  ".join(parts) + suffix

    # Leaf text
    text = normalize_text(elem.text)
    if text and not list(elem):
        return text if len(text) <= 60 else text[:57] + "..."

    # Container with children
    n = len(list(elem))
    if n:
        return "(%d)" % n

    return ""


def friendly_location(path):
    """Convert a semantic path like
    /configuration/appSettings[1]/add|@('attr', 'key', 'appName')
    into a readable breadcrumb like:
    appSettings › add  (key=appName)
    """
    if not path:
        return ""
    # Strip leading /
    parts = [p for p in path.split("/") if p]
    if not parts:
        return path

    crumbs = []
    for i, part in enumerate(parts):
        # Remove [N] index suffix
        clean = part
        if "[" in clean:
            clean = clean[:clean.index("[")]
        # Extract semantic key from |@ suffix
        key_info = ""
        if "|" in part:
            after_pipe = part[part.index("|") + 1:]
            # Try to parse @('attr', 'key', 'value') or similar
            if after_pipe.startswith("@"):
                try:
                    import ast
                    parsed = ast.literal_eval(after_pipe[1:])
                    if isinstance(parsed, tuple) and len(parsed) >= 3:
                        key_info = "  (%s=%s)" % (parsed[1], parsed[2])
                except Exception:
                    key_info = ""
            clean = clean[:clean.index("|")] if "|" in clean else clean
        # Skip root tag (usually generic like "configuration")
        if i == 0 and len(parts) > 1:
            continue
        crumbs.append(clean + key_info)

    return " › ".join(crumbs) if crumbs else parts[-1].split("[")[0].split("|")[0]


def compact_xml(elem):
    return ET.tostring(elem, encoding="unicode")


def parse_xml_file(path):
    last_error = None
    for enc in ("utf-8-sig", "utf-8", "utf-16", "utf-16-le",
                "utf-16-be", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                text = f.read()
            text = text.lstrip("\ufeff").lstrip()
            return ET.ElementTree(ET.fromstring(text))
        except (UnicodeDecodeError, ET.ParseError) as exc:
            last_error = exc
    raise ET.ParseError(
        t("parse_error_message", path=path, error=last_error)
    )


def semantic_key(elem):
    for key in MATCH_KEYS:
        value = elem.attrib.get(key)
        if normalize_text(value):
            return ("attr", key, normalize_text(value))

    for child in list(elem):
        tag = strip_namespace(child.tag)
        if tag in MATCH_KEYS and normalize_text(child.text):
            return ("child", tag, normalize_text(child.text))

    if not list(elem) and normalize_text(elem.text):
        return ("text", normalize_text(elem.text))

    return None


def child_identity(elem, occurrence):
    tag = strip_namespace(elem.tag)
    key = semantic_key(elem)
    if key is not None:
        return (tag, "key", repr(key))
    return (tag, "index", occurrence)


def build_node_index(root):
    """
    Returns:
        path -> Element
        ordered list of node records
    Path is based on semantic identity when possible, not raw position.
    """
    index = {}
    records = []

    def walk(elem, path, depth=0):
        index[path] = elem
        records.append((path, elem, depth))

        counters = {}
        for child in list(elem):
            tag = strip_namespace(child.tag)
            counters[tag] = counters.get(tag, 0) + 1
            ident = child_identity(child, counters[tag])
            child_path = path + "/" + tag
            if ident[1] == "key":
                child_path += "|@" + ident[2]
            else:
                child_path += "[%d]" % counters[tag]
            walk(child, child_path, depth + 1)

    walk(root, "/" + strip_namespace(root.tag))
    return index, records


def build_child_maps(parent):
    maps = {}
    counters = {}
    for child in list(parent):
        tag = strip_namespace(child.tag)
        counters[tag] = counters.get(tag, 0) + 1
        ident = child_identity(child, counters[tag])
        maps[ident] = child
    return maps


def compare_nodes(a, b):
    """
    Fast structural comparison.
    Returns a short summary instead of serializing entire subtrees.
    """
    if a is None or b is None:
        return a is not b

    if strip_namespace(a.tag) != strip_namespace(b.tag):
        return True

    if dict(a.attrib) != dict(b.attrib):
        return True

    if normalize_text(a.text) != normalize_text(b.text):
        return True

    ca = build_child_maps(a)
    cb = build_child_maps(b)

    if set(ca) != set(cb):
        return True

    for key in ca:
        if compare_nodes(ca[key], cb[key]):
            return True

    return False


def diff_paths(root1, root2):
    """
    Compare by indexed semantic paths. Avoids O(n*m) sibling scanning.
    """
    i1, r1 = build_node_index(root1)
    i2, r2 = build_node_index(root2)

    paths = set(i1) | set(i2)
    result = set()

    for path in paths:
        a = i1.get(path)
        b = i2.get(path)
        if a is None or b is None or compare_nodes(a, b):
            result.add(path)

    return result, i1, i2, r1, r2


# ---------------------------------------------------------------------------
# Diff classification (git-style coloring, minimal-diff detection, grouping)
# ---------------------------------------------------------------------------

# Modern diff colors – softer, professional, accessible (WCAG AA-ish)
COLOR_ADDED    = "#e6f4ea"    # 新增：Mint 100
COLOR_REMOVED  = "#fce8e6"    # 删除：Coral 100
COLOR_MODIFIED = "#fef7e0"    # 修改：Amber 100
COLOR_CHANGED  = "#e8f0fe"    # 含差异子项：Blue 100

# ---------------------------------------------------------------------------
# Modern UI theme palette (clean, desktop-app style)
# ---------------------------------------------------------------------------
THEME_BG          = "#f5f7fa"   # 窗口背景（浅灰白，避免纯白色刺眼）
THEME_SURFACE     = "#ffffff"   # 卡片/面板背景
THEME_BORDER      = "#e2e8f0"   # 边框线（柔和）
THEME_PRIMARY     = "#2563eb"   # 主色调（Blue 600，按钮/强调）
THEME_PRIMARY_HOV = "#1d4ed8"   # 主色悬停（更深）
THEME_SECONDARY   = "#64748b"   # 次色（Slate 500，取消按钮等）
THEME_TEXT        = "#1e293b"   # 主文字色（Slate 800）
THEME_TEXT_MUTED  = "#64748b"   # 辅助文字色
THEME_ACCENT      = "#0ea5e9"   # 点缀色（Sky 500）

# Spacing scale (consistent 4/8/12/16/24 px – Figma-style step)
SP = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "xxl": 32}

# Typography
FONT_FAMILY_BASE    = ("Segoe UI", "Microsoft YaHei UI", "PingFang SC",
                       "Noto Sans", "Arial", "TkDefaultFont")
FONT_FAMILY_MONO    = ("Consolas", "JetBrains Mono", "Cascadia Code",
                       "Courier New", "TkFixedFont")
FONT_SIZE_LABEL     = 10
FONT_SIZE_TITLE     = 11
FONT_SIZE_HINT      = 9
FONT_SIZE_MONO      = 10

# Note: state_label(kind) (defined in the i18n module above) provides the
# translated text for a given kind ("added"/"removed"/"modified"/"changed"/
# "same") in the current UI language.


def local_diff_kind(a, b):
    """
    Classify a single node-level difference between the node at this path in
    XML1 (a) and XML2 (b):
      - "added":    only exists in XML2
      - "removed":  only exists in XML1
      - "modified": exists in both, but its own attributes/text differ
      - "changed":  exists in both with identical own content, but some
                    descendant differs (ancestor-only diff)
      - "same":     no difference anywhere in the subtree
    """
    if a is None and b is None:
        return "same"
    if a is None:
        return "added"
    if b is None:
        return "removed"
    if dict(a.attrib) != dict(b.attrib) or normalize_text(a.text) != normalize_text(b.text):
        return "modified"
    if compare_nodes(a, b):
        return "changed"
    return "same"


def classify_all_paths(index1, index2):
    """path -> kind, for every node that exists in either tree."""
    kinds = {}
    for path in set(index1) | set(index2):
        kinds[path] = local_diff_kind(index1.get(path), index2.get(path))
    return kinds


def minimal_diff_paths(kinds):
    """
    Reduce the full kind map down to the *minimal* set of diff points that
    should actually be turned into merge rules.

    Ancestors whose only difference comes from a descendant ("changed") are
    dropped entirely - setting a rule there would silently replace an entire
    subtree and hide finer-grained choices made deeper down.

    Likewise, once a node is found to be an atomic add/remove (it exists in
    only one file), none of its descendants are listed separately - picking
    the parent already brings/removes the whole subtree in one step.
    """
    raw = {p: k for p, k in kinds.items() if k in ("added", "removed", "modified")}

    atomic_roots = sorted(
        (p for p, k in raw.items() if k in ("added", "removed")),
        key=lambda p: p.count("/")
    )

    result = dict(raw)
    for root_path in atomic_roots:
        prefix = root_path + "/"
        for p in list(result):
            if p != root_path and p.startswith(prefix):
                del result[p]

    return result


def path_leaf_tag(path):
    if path.startswith("pair:"):
        tail = path.rsplit("/", 1)[-1]
        return tail.split("#", 1)[0]
    leaf = path.rsplit("/", 1)[-1]
    leaf = leaf.split("|", 1)[0]
    leaf = leaf.split("[", 1)[0]
    return leaf


def _direct_children_by_tag(elem):
    groups = {}
    for child in list(elem):
        tag = strip_namespace(child.tag)
        groups.setdefault(tag, []).append(child)
    return groups


def compute_value_pairs(index1, index2):
    """
    The tool identifies most nodes by content (semantic_key), which works
    well for matching reordered siblings but has one sharp edge: a plain
    leaf value node like <a>hello</a> has no identity other than its own
    text, so if that text changes, XML1's <a>hello</a> and XML2's
    <a>HELLO</a> get *different* paths entirely and look like an unrelated
    delete-then-add rather than a single value change.

    This scans every parent that exists in both trees and, for each tag
    where both sides have the same number of plain leaf children (no
    attributes, no sub-elements), pairs them up by occurrence order. Each
    pair whose text actually differs becomes one synthetic diff point
    ("pair:<parent_path>/<tag>#<occurrence>") representing "this Nth <tag>
    under this parent changed", instead of two unrelated add/remove points.

    Returns: pair_key -> {parent_path, tag, occurrence_index,
                           xml1_path, xml2_path}
    """
    pairs = {}
    for parent_path in set(index1) & set(index2):
        groups1 = _direct_children_by_tag(index1[parent_path])
        groups2 = _direct_children_by_tag(index2[parent_path])

        for tag, list1 in groups1.items():
            list2 = groups2.get(tag)
            if not list2 or len(list1) != len(list2):
                continue

            for idx, (c1, c2) in enumerate(zip(list1, list2)):
                if list(c1) or list(c2) or c1.attrib or c2.attrib:
                    continue  # structured nodes are already matched fine
                if normalize_text(c1.text) == normalize_text(c2.text):
                    continue  # identical, nothing to reconcile

                ident1 = child_identity(c1, idx + 1)
                ident2 = child_identity(c2, idx + 1)
                seg1 = ("|@" + ident1[2]) if ident1[1] == "key" else ("[%d]" % (idx + 1))
                seg2 = ("|@" + ident2[2]) if ident2[1] == "key" else ("[%d]" % (idx + 1))

                pairs["pair:%s/%s#%d" % (parent_path, tag, idx)] = {
                    "parent_path": parent_path,
                    "tag": tag,
                    "occurrence_index": idx,
                    "xml1_path": parent_path + "/" + tag + seg1,
                    "xml2_path": parent_path + "/" + tag + seg2,
                }
    return pairs


def reconcile_pairs_into_minimal(minimal, value_pairs):
    """Fold matched remove+add pairs into one synthetic 'modified' entry."""
    result = dict(minimal)
    for pair_key, info in value_pairs.items():
        p1, p2 = info["xml1_path"], info["xml2_path"]
        if result.get(p1) == "removed" and result.get(p2) == "added":
            del result[p1]
            del result[p2]
            result[pair_key] = "modified"
    return result


def build_diff_model(index1, index2):
    """One-stop computation: (kinds, minimal-diff map, value-pair map)."""
    kinds = classify_all_paths(index1, index2)
    raw_minimal = minimal_diff_paths(kinds)
    value_pairs = compute_value_pairs(index1, index2)
    minimal = reconcile_pairs_into_minimal(raw_minimal, value_pairs)
    return kinds, minimal, value_pairs


def resolve_diff_nodes(path, index1, index2, value_pairs):
    """Return (node_in_xml1, node_in_xml2) for a normal path OR a synthetic
    'pair:' key, for display purposes."""
    if path.startswith("pair:"):
        info = value_pairs.get(path)
        if info is None:
            return None, None
        return index1.get(info["xml1_path"]), index2.get(info["xml2_path"])
    return index1.get(path), index2.get(path)


def group_minimal_diffs_by_tag(minimal_paths):
    """
    Group minimal diff paths by their element tag name. This is what lets a
    repeated structure - e.g. item1/a and item2/a inside a loop - be treated
    as "one kind of difference" (element 'a') for the purpose of setting a
    merge rule, instead of forcing the user to pick a source for every single
    occurrence. Occurrences that genuinely need different handling can still
    be expanded and set individually, or handled via the manual merge wizard.
    """
    groups = {}
    for path, kind in minimal_paths.items():
        tag = path_leaf_tag(path)
        groups.setdefault(tag, []).append((path, kind))
    for tag in groups:
        groups[tag].sort(key=lambda x: x[0])
    return groups


def configure_diff_tags(widget):
    widget.tag_configure("added", background=COLOR_ADDED, foreground=THEME_TEXT)
    widget.tag_configure("removed", background=COLOR_REMOVED, foreground=THEME_TEXT)
    widget.tag_configure("modified", background=COLOR_MODIFIED, foreground=THEME_TEXT)
    widget.tag_configure("changed", background=COLOR_CHANGED, foreground=THEME_TEXT)


def ensure_parent_path(root, path):
    parts = [x for x in path.split("/") if x]
    if not parts:
        return root

    if strip_namespace(root.tag) != parts[0]:
        return None

    current = root
    for part in parts[1:]:
        if part.startswith("@"):
            return current

        tag = part.split("[", 1)[0]
        if "/@" in part:
            tag, _ = part.split("/@", 1)

        candidates = [
            c for c in list(current)
            if strip_namespace(c.tag) == tag
        ]
        if not candidates:
            return None

        # Stable paths normally have semantic key suffix. Find by exact
        # rendered path among current children.
        chosen = None
        counters = {}
        for c in candidates:
            counters[tag] = counters.get(tag, 0) + 1
            if "[" in part:
                try:
                    n = int(part.rsplit("[", 1)[1][:-1])
                    if counters[tag] == n:
                        chosen = c
                except ValueError:
                    pass
        if chosen is None:
            chosen = candidates[0]
        current = chosen

    return current


def apply_merge_rules(root1, root2, rules):
    """
    rules: path -> "xml1" or "xml2"

    Start from XML1. A rule for a node replaces the complete subtree.
    Child-level rules are applied when the parent has no explicit rule.
    """
    result = copy.deepcopy(root1)
    i1, _ = build_node_index(root1)
    i2, _ = build_node_index(root2)

    if rules.get("/" + strip_namespace(root1.tag)) == "xml2":
        return copy.deepcopy(root2)

    # Deepest first is unsafe for parent replacement, so process rules from
    # shallow to deep and skip descendants of an explicitly selected parent.
    sorted_rules = sorted(rules.items(), key=lambda x: x[0].count("/"))

    selected_parent_paths = []
    for path, source in sorted_rules:
        if any(path.startswith(parent + "/") for parent in selected_parent_paths):
            continue

        src_index = i1 if source == "xml1" else i2
        src = src_index.get(path)
        if src is None:
            continue

        if path == "/" + strip_namespace(result.tag):
            result = copy.deepcopy(src)
            selected_parent_paths.append(path)
            continue

        parent_path, leaf = path.rsplit("/", 1)
        parent = find_by_stable_path(result, parent_path)
        if parent is None:
            continue

        target = find_direct_child_by_stable_name(parent, leaf)
        new_node = copy.deepcopy(src)

        if target is not None:
            pos = list(parent).index(target)
            parent.remove(target)
            parent.insert(pos, new_node)
        elif source == "xml2":
            parent.append(new_node)

        selected_parent_paths.append(path)

    # Reconciled value-pair rules (see compute_value_pairs): these represent
    # "this Nth <tag> under this parent changed value" and must replace the
    # existing occurrence in place rather than being treated as an
    # add/remove, which would otherwise duplicate the node.
    value_pairs = compute_value_pairs(i1, i2)
    for pair_key, source in rules.items():
        if not pair_key.startswith("pair:"):
            continue
        info = value_pairs.get(pair_key)
        if info is None:
            continue
        if any(
            info["parent_path"] == p or info["parent_path"].startswith(p + "/")
            for p in selected_parent_paths
        ):
            continue  # an ancestor rule already fully resolved this subtree

        parent = find_by_stable_path(result, info["parent_path"])
        if parent is None:
            continue

        siblings = [c for c in list(parent) if strip_namespace(c.tag) == info["tag"]]
        idx = info["occurrence_index"]
        if idx >= len(siblings):
            continue

        src_root = root1 if source == "xml1" else root2
        src_path = info["xml1_path"] if source == "xml1" else info["xml2_path"]
        chosen = find_by_stable_path(src_root, src_path)
        if chosen is None:
            continue

        current = siblings[idx]
        pos = list(parent).index(current)
        parent.remove(current)
        parent.insert(pos, copy.deepcopy(chosen))

    return result


def find_direct_child_by_stable_name(parent, leaf):
    children = list(parent)
    counters = {}
    for child in children:
        tag = strip_namespace(child.tag)
        counters[tag] = counters.get(tag, 0) + 1
        ident = child_identity(child, counters[tag])

        if ident[1] == "key":
            rendered = tag + "|@" + ident[2]
        else:
            rendered = tag + "[%d]" % counters[tag]

        if rendered == leaf:
            return child
    return None


def find_by_stable_path(root, path):
    parts = [x for x in path.split("/") if x]
    if not parts or strip_namespace(root.tag) != parts[0]:
        return None

    current = root
    for part in parts[1:]:
        child = find_direct_child_by_stable_name(current, part)
        if child is None:
            return None
        current = child
    return current


class App:
    def __init__(self, root):
        self.root = root

        self.config = load_config()
        saved_lang = self.config.get("language")
        if saved_lang in SUPPORTED_LANGUAGES:
            set_language(saved_lang)
        else:
            set_language(detect_system_language())

        self.root.title(t("app_title"))
        self.root.geometry("1520x960")
        self.root.minsize(1180, 720)
        # 窗口初始居中
        try:
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2 - 40)
            self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        except Exception:
            pass

        self.file1 = ""
        self.file2 = ""
        self.tree1 = None
        self.tree2 = None
        self.root1 = None
        self.root2 = None
        self.index1 = {}
        self.index2 = {}
        self.records1 = []
        self.records2 = []
        self.diff = set()
        self.kinds = {}
        self.minimal = {}
        self.value_pairs = {}
        self.nav_paths = []
        self.nav_index = -1
        self.rules = {}
        self.merged_root = None

        self.path1 = tk.StringVar()
        self.path2 = tk.StringVar()
        self.status = tk.StringVar(value=t("status_initial"))
        self.only_diff = tk.BooleanVar(value=False)
        self.lang_var = tk.StringVar(value=LANGUAGE_NAMES[get_language()])

        self.build_ui()

    # ------------------------------------------------------------------
    # Language switching
    # ------------------------------------------------------------------

    def on_language_change(self, event=None):
        display = self.lang_var.get()
        code = next(
            (c for c, name in LANGUAGE_NAMES.items() if name == display),
            get_language()
        )
        set_language(code)
        self.config["language"] = code
        save_config(self.config)
        self.rebuild_ui()

    def rebuild_ui(self):
        """Tear down and rebuild every widget in the current language,
        then restore whatever was already loaded/computed (file paths,
        rules, comparison results are plain Python state and survive a
        widget rebuild untouched)."""
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title(t("app_title"))
        self.build_ui()

        if self.root1 is not None and self.root2 is not None:
            self.refresh_trees()
            self.update_diff_pos_label()
            self.status.set(
                t("status_compare_done", diff_count=len(self.diff), minimal_count=len(self.minimal))
            )
        else:
            self.status.set(t("status_initial"))

    def build_ui(self):
        # ------------------------------------------------------------------
        # Language bar (top-right) – slim, unobtrusive
        # ------------------------------------------------------------------
        langbar = ttk.Frame(self.root, padding=(SP["lg"], SP["md"], SP["lg"], SP["xs"]))
        langbar.pack(fill="x")

        self.lang_combo = ttk.Combobox(
            langbar,
            textvariable=self.lang_var,
            values=[LANGUAGE_NAMES[c] for c in SUPPORTED_LANGUAGES],
            state="readonly",
            width=14,
        )
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        ttk.Label(langbar, text=t("language_label"),
                  style="Hint.TLabel").pack(side="right", padx=(0, SP["sm"]))

        # ------------------------------------------------------------------
        # File selection – Card-style panel with border
        # ------------------------------------------------------------------
        top_card = ttk.Frame(self.root, style="Card.TFrame",
                             padding=(SP["lg"], SP["md"]))
        top_card.pack(fill="x", padx=SP["lg"], pady=SP["sm"])
        # Add a 1px bottom border visually using a frame
        try:
            top_card.configure(borderwidth=1, relief="solid")
        except Exception:
            pass

        ttk.Label(top_card, text=t("file1_label"),
                  style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=(0, SP["xs"]))
        ttk.Entry(top_card, textvariable=self.path1).grid(
            row=0, column=1, sticky="ew", padx=(SP["md"], SP["sm"]), pady=(0, SP["xs"])
        )
        ttk.Button(top_card, text=t("choose_file_button"),
                   style="Ghost.TButton", command=self.choose1).grid(
            row=0, column=2, pady=(0, SP["xs"])
        )

        ttk.Label(top_card, text=t("file2_label"),
                  style="Card.TLabel").grid(
            row=1, column=0, sticky="w", pady=(SP["md"], 0)
        )
        ttk.Entry(top_card, textvariable=self.path2).grid(
            row=1, column=1, sticky="ew", padx=(SP["md"], SP["sm"]), pady=(SP["md"], 0)
        )
        ttk.Button(top_card, text=t("choose_file_button"),
                   style="Ghost.TButton", command=self.choose2).grid(
            row=1, column=2, pady=(SP["md"], 0)
        )

        top_card.columnconfigure(1, weight=1)

        # ------------------------------------------------------------------
        # Action bar
        # ------------------------------------------------------------------
        bar = ttk.Frame(self.root, padding=(SP["lg"], SP["xs"], SP["lg"], SP["sm"]))
        bar.pack(fill="x")

        ttk.Button(bar, text=t("load_compare_button"),
                   style="Primary.TButton",
                   command=self.load_compare).pack(side="left", padx=(0, SP["sm"]))
        ttk.Button(
            bar, text=t("select_merge_button"), style="Accent.TButton",
            command=self.open_merge_selector
        ).pack(side="left", padx=(0, SP["sm"]))

        ttk.Button(
            bar, text=t("manual_wizard_button"), style="Ghost.TButton",
            command=self.open_manual_wizard
        ).pack(side="left", padx=(0, SP["sm"]))

        ttk.Button(
            bar, text=t("clear_rules_button"), style="Ghost.TButton",
            command=self.clear_rules
        ).pack(side="left", padx=(0, SP["sm"]))

        ttk.Checkbutton(
            bar,
            text=t("only_diff_checkbox"),
            variable=self.only_diff,
            command=self.refresh_trees
        ).pack(side="left", padx=(SP["md"], 0))

        self.rule_label = ttk.Label(bar, text=t("rule_count_label", n=len(self.rules)),
                                    style="Title.TLabel")
        self.rule_label.pack(side="right", padx=(0, SP["md"]))

        ttk.Button(
            bar, text=t("save_button"), style="Primary.TButton",
            command=self.save_result
        ).pack(side="right", padx=(0, SP["sm"]))
        ttk.Button(
            bar, text=t("preview_button"), style="Ghost.TButton",
            command=self.preview
        ).pack(side="right", padx=(0, SP["sm"]))

        # ------------------------------------------------------------------
        # Navigation bar
        # ------------------------------------------------------------------
        navbar = ttk.Frame(self.root, padding=(SP["lg"], SP["xs"], SP["lg"], SP["sm"]))
        navbar.pack(fill="x")

        ttk.Button(
            navbar, text=t("prev_diff_button"), style="Ghost.TButton",
            command=self.prev_diff
        ).pack(side="left")
        ttk.Button(
            navbar, text=t("next_diff_button"), style="Ghost.TButton",
            command=self.next_diff
        ).pack(side="left", padx=SP["sm"])

        current = self.nav_index + 1 if self.nav_index >= 0 else 0
        self.diff_pos_label = ttk.Label(
            navbar, text=t("diff_pos_label", current=current, total=len(self.nav_paths))
        )
        self.diff_pos_label.pack(side="left", padx=SP["md"])

        # Legend (color swatches + labels)
        legend = ttk.Frame(navbar)
        legend.pack(side="right")
        for i, (text, color) in enumerate((
            (t("legend_added"), COLOR_ADDED),
            (t("legend_removed"), COLOR_REMOVED),
            (t("legend_modified"), COLOR_MODIFIED),
            (t("legend_changed"), COLOR_CHANGED),
        )):
            swatch = tk.Frame(legend, width=16, height=16, bg=color,
                              highlightthickness=1,
                              highlightbackground=THEME_BORDER,
                              highlightcolor=THEME_BORDER,
                              relief="flat")
            swatch.pack(side="left",
                        padx=((SP["md"] if i else 0), SP["xs"]),
                        pady=1)
            swatch.pack_propagate(False)
            ttk.Label(legend, text=text).pack(side="left")

        # ------------------------------------------------------------------
        # Two trees
        # ------------------------------------------------------------------
        pane = ttk.PanedWindow(self.root, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=SP["lg"], pady=(0, SP["sm"]))

        left = ttk.LabelFrame(pane, text=t("frame_file1"),
                              padding=(SP["sm"], SP["sm"]))
        right = ttk.LabelFrame(pane, text=t("frame_file2"),
                               padding=(SP["sm"], SP["sm"]))
        pane.add(left, weight=1)
        pane.add(right, weight=1)

        self.view1 = self.make_tree(left)
        self.view2 = self.make_tree(right)

        # ------------------------------------------------------------------
        # Detail pane
        # ------------------------------------------------------------------
        detail = ttk.LabelFrame(self.root, text=t("frame_detail"),
                                padding=(SP["xs"], SP["xs"]))
        detail.pack(fill="both", expand=False, padx=SP["lg"], pady=(0, SP["sm"]))

        self.detail = tk.Text(
            detail, height=14, wrap="none",
            font=(FONT_FAMILY_MONO, FONT_SIZE_MONO),
            bg=THEME_SURFACE, fg=THEME_TEXT,
            insertbackground=THEME_TEXT,
            selectbackground=THEME_PRIMARY,
            selectforeground="white",
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground=THEME_BORDER,
            highlightcolor=THEME_PRIMARY,
            padx=8, pady=6,
        )
        dsy = ttk.Scrollbar(
            detail, orient="vertical", command=self.detail.yview
        )
        self.detail.configure(yscrollcommand=dsy.set)
        self.detail.pack(side="left", fill="both", expand=True)
        dsy.pack(side="right", fill="y")

        # ------------------------------------------------------------------
        # Status bar – on its own card
        # ------------------------------------------------------------------
        status_card = ttk.Frame(self.root, style="Card.TFrame",
                                padding=(SP["lg"], SP["md"]))
        status_card.pack(fill="x", padx=SP["lg"], pady=(0, SP["lg"]))
        try:
            status_card.configure(borderwidth=1, relief="solid")
        except Exception:
            pass
        ttk.Label(
            status_card, textvariable=self.status, anchor="w",
            style="Card.TLabel"
        ).pack(fill="x")

    def make_tree(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            frame,
            columns=("state", "rule"),
            show="tree headings",
            selectmode="browse"
        )
        tree.heading("#0", text=t("col_content"))
        tree.heading("state", text=t("col_state"))
        tree.heading("rule", text=t("col_source"))

        tree.column("#0", width=500)
        tree.column("state", width=90)
        tree.column("rule", width=90)

        sy = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        tree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        configure_diff_tags(tree)
        tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        return tree

    def choose1(self):
        path = self.ask_file("last_dir1", t("choose_file1_title"))
        if path:
            self.file1 = path
            self.path1.set(path)

    def choose2(self):
        path = self.ask_file("last_dir2", t("choose_file2_title"))
        if path:
            self.file2 = path
            self.path2.set(path)

    def ask_file(self, config_key, title):
        initial = self.config.get(config_key, "")
        if not os.path.isdir(initial):
            initial = os.getcwd()

        path = filedialog.askopenfilename(
            parent=self.root,
            title=title,
            initialdir=initial,
            filetypes=[
                (t("filetype_xmlmeta"), "*.xml *.meta"),
                (t("filetype_xml"), "*.xml"),
                (t("filetype_meta"), "*.meta"),
                (t("filetype_all"), "*.*"),
            ],
        )

        if path:
            self.config[config_key] = os.path.dirname(path)
            save_config(self.config)

        return path

    def load_compare(self):
        if not self.file1 or not self.file2:
            messagebox.showwarning(t("dlg_title_notice"), t("msg_select_both_files"))
            return

        try:
            self.tree1 = parse_xml_file(self.file1)
            self.tree2 = parse_xml_file(self.file2)
            self.root1 = self.tree1.getroot()
            self.root2 = self.tree2.getroot()

            self.diff, self.index1, self.index2, self.records1, self.records2 = (
                diff_paths(self.root1, self.root2)
            )
            self.kinds, self.minimal, self.value_pairs = build_diff_model(
                self.index1, self.index2
            )
            self.nav_paths = self.build_nav_order()
            self.nav_index = -1

            self.rules.clear()
            self.merged_root = None
            self.refresh_trees()
            self.update_diff_pos_label()

            self.status.set(
                t("status_compare_done", diff_count=len(self.diff), minimal_count=len(self.minimal))
            )
        except Exception as exc:
            messagebox.showerror(t("dlg_title_parse_failed"), str(exc))

    def refresh_trees(self):
        self.populate_tree(self.view1, self.records1, self.index1)
        self.populate_tree(self.view2, self.records2, self.index2)
        self.rule_label.config(text=t("rule_count_label", n=len(self.rules)))

    def populate_tree(self, widget, records, index):
        for item in widget.get_children(""):
            widget.delete(item)

        for path, elem, depth in records:
            if self.only_diff.get() and path not in self.diff:
                continue

            kind = self.kinds.get(path, "same")
            state = state_label(kind)

            source = self.rules.get(path, "")
            source_text = (
                t("source_file1") if source == "xml1"
                else t("source_file2") if source == "xml2"
                else ""
            )

            # Show raw XML element text (e.g. <test>1</test>) with indentation
            xml_text = element_to_xml_string(elem)
            indent = "    " * max(0, depth - 1)
            widget.insert(
                "",
                "end",
                iid=path,
                text=indent + xml_text,
                values=(state, source_text),
                tags=(kind,) if kind != "same" else ()
            )

    def on_tree_select(self, event=None):
        widget = event.widget if event else None
        if widget is None:
            return

        selected = widget.selection()
        if not selected:
            return

        self.show_detail(selected[0])

    def show_detail(self, path):
        a, b = resolve_diff_nodes(path, self.index1, self.index2, self.value_pairs)

        self.detail.delete("1.0", "end")
        # Show friendly breadcrumb instead of raw semantic path
        self.detail.insert("end", t("detail_location_header",
                                     location=friendly_location(path)))

        if path in self.rules:
            self.detail.insert(
                "end",
                t(
                    "detail_current_source",
                    source=t("source_file1") if self.rules[path] == "xml1" else t("source_file2")
                )
            )

        self.detail.insert("end", t("detail_file1_header"))
        self.detail.insert(
            "end", t("not_exist") + "\n" if a is None else pretty_xml(a)
        )

        self.detail.insert("end", t("detail_file2_header"))
        self.detail.insert(
            "end", t("not_exist") + "\n" if b is None else pretty_xml(b)
        )

    def build_nav_order(self):
        """Document-order list of minimal diff paths/pair-keys, used by the
        prev/next diff navigation buttons."""
        ordered = []
        seen = set()
        for path, elem, depth in self.records1:
            if path in self.minimal and path not in seen:
                ordered.append(path)
                seen.add(path)
        for path, elem, depth in self.records2:
            if path in self.minimal and path not in seen:
                ordered.append(path)
                seen.add(path)
        for path in self.minimal:
            if path not in seen:  # synthetic pair: keys aren't in either records list
                ordered.append(path)
                seen.add(path)
        return ordered

    def update_diff_pos_label(self):
        total = len(self.nav_paths)
        current = self.nav_index + 1 if self.nav_index >= 0 else 0
        self.diff_pos_label.config(text=t("diff_pos_label", current=current, total=total))

    def next_diff(self):
        if not self.nav_paths:
            messagebox.showinfo(t("dlg_title_notice"), t("msg_no_nav_diffs"))
            return
        self.nav_index = (self.nav_index + 1) % len(self.nav_paths)
        self.goto_nav(self.nav_paths[self.nav_index])

    def prev_diff(self):
        if not self.nav_paths:
            messagebox.showinfo(t("dlg_title_notice"), t("msg_no_nav_diffs"))
            return
        self.nav_index = (self.nav_index - 1) % len(self.nav_paths)
        self.goto_nav(self.nav_paths[self.nav_index])

    def goto_nav(self, path):
        # Synthetic 'pair:' keys don't have their own row in the tree views
        # (they represent a reconciled value change); highlight the real
        # underlying node on each side instead.
        if path.startswith("pair:"):
            info = self.value_pairs.get(path, {})
            highlight1, highlight2 = info.get("xml1_path"), info.get("xml2_path")
        else:
            highlight1 = highlight2 = path

        if highlight1 and self.view1.exists(highlight1):
            self.view1.selection_set(highlight1)
            self.view1.see(highlight1)
            self.view1.focus(highlight1)
        if highlight2 and self.view2.exists(highlight2):
            self.view2.selection_set(highlight2)
            self.view2.see(highlight2)
            self.view2.focus(highlight2)

        self.show_detail(path)
        self.update_diff_pos_label()

    def open_merge_selector(self):
        if self.root1 is None or self.root2 is None:
            messagebox.showwarning(t("dlg_title_notice"), t("msg_load_compare_first"))
            return

        dialog = MergeSelector(
            self.root,
            self.root1,
            self.root2,
            self.diff,
            self.rules,
        )
        self.root.wait_window(dialog.window)

        if dialog.result is not None:
            self.rules = dialog.result
            self.refresh_trees()
            self.status.set(t("status_rules_set", n=len(self.rules)))

    def open_manual_wizard(self):
        if self.root1 is None or self.root2 is None:
            messagebox.showwarning(t("dlg_title_notice"), t("msg_load_compare_first"))
            return
        if not self.nav_paths:
            messagebox.showinfo(t("dlg_title_notice"), t("msg_no_manual_diffs"))
            return

        wizard = ManualMergeWizard(
            self.root,
            self.root1,
            self.root2,
            self.index1,
            self.index2,
            self.value_pairs,
            self.nav_paths,
            self.rules,
        )
        self.root.wait_window(wizard.window)

        if wizard.result is not None:
            self.rules = wizard.result
            self.refresh_trees()
            self.status.set(t("status_manual_wizard_updated", n=len(self.rules)))

    def clear_rules(self):
        self.rules.clear()
        self.merged_root = None
        self.refresh_trees()
        self.status.set(t("status_rules_cleared"))

    def preview(self):
        if self.root1 is None or self.root2 is None:
            messagebox.showwarning(t("dlg_title_notice"), t("msg_load_compare_first"))
            return

        self.merged_root = apply_merge_rules(
            self.root1, self.root2, self.rules
        )

        win = tk.Toplevel(self.root)
        win.title(t("preview_window_title"))
        win.geometry("1040x760")
        try:
            win.configure(bg=THEME_BG)
        except Exception:
            pass

        wrap = ttk.Frame(win, padding=SP["md"])
        wrap.pack(fill="both", expand=True)
        text = tk.Text(
            wrap, wrap="none",
            font=(FONT_FAMILY_MONO, FONT_SIZE_MONO),
            bg=THEME_SURFACE, fg=THEME_TEXT,
            insertbackground=THEME_TEXT,
            selectbackground=THEME_PRIMARY,
            selectforeground="white",
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground=THEME_BORDER,
            highlightcolor=THEME_PRIMARY,
            padx=8, pady=6,
        )
        sy = ttk.Scrollbar(win, orient="vertical", command=text.yview)
        sx = ttk.Scrollbar(win, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        text.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        text.insert("1.0", pretty_xml(self.merged_root))
        text.configure(state="disabled")

    def save_result(self):
        if self.root1 is None or self.root2 is None:
            messagebox.showwarning(t("dlg_title_notice"), t("msg_load_compare_first"))
            return

        self.merged_root = apply_merge_rules(
            self.root1, self.root2, self.rules
        )

        ext = os.path.splitext(self.file1)[1] or ".xml"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t("save_button"),
            defaultextension=ext,
            filetypes=[
                (t("filetype_xmlmeta"), "*.xml *.meta"),
                (t("filetype_xml"), "*.xml"),
                (t("filetype_meta"), "*.meta"),
                (t("filetype_all"), "*.*"),
            ],
        )

        if not path:
            return

        try:
            ET.ElementTree(self.merged_root).write(
                path, encoding="utf-8", xml_declaration=True
            )
            self.status.set(t("status_saved", path=path))
            messagebox.showinfo(t("dlg_title_done"), t("msg_save_done"))
        except Exception as exc:
            messagebox.showerror(t("dlg_title_save_failed"), str(exc))


class ManualMergeWizard:
    """
    Step through the minimal diff points one at a time (in document order)
    and pick XML 1 / XML 2 for each. This is the fine-grained counterpart to
    the grouped rule selector: useful when different occurrences of the
    same element genuinely need different treatment.
    """

    def __init__(self, parent, root1, root2, index1, index2,
                 value_pairs, nav_paths, existing_rules):
        self.window = tk.Toplevel(parent)
        self.window.title(t("wizard_title"))
        self.window.geometry("1120x720")
        self.window.minsize(860, 560)
        self.window.transient(parent)
        try:
            self.window.configure(bg=THEME_BG)
        except Exception:
            pass
        self.window.grab_set()

        self.root1 = root1
        self.root2 = root2
        self.index1 = index1
        self.index2 = index2
        self.value_pairs = value_pairs
        self.paths = list(nav_paths)
        self.rules = dict(existing_rules)
        self.result = None
        self.pos = 0

        self.build_ui()
        if self.paths:
            self.show_current()
        else:
            self.pos_label.config(text=t("wizard_no_diffs"))

    def build_ui(self):
        top = ttk.Frame(self.window, padding=SP["md"])
        top.pack(fill="x")

        self.pos_label = ttk.Label(top, text="", style="Title.TLabel")
        self.pos_label.pack(side="left")

        self.path_label = ttk.Label(top, text="", style="Hint.TLabel")
        self.path_label.pack(side="left", padx=SP["md"])

        main = ttk.PanedWindow(self.window, orient="horizontal")
        main.pack(fill="both", expand=True, padx=SP["md"], pady=(0, SP["sm"]))

        left = ttk.LabelFrame(main, text="XML 1", padding=(SP["xs"], SP["xs"]))
        right = ttk.LabelFrame(main, text="XML 2", padding=(SP["xs"], SP["xs"]))
        main.add(left, weight=1)
        main.add(right, weight=1)

        common_text_opts = dict(
            wrap="none",
            font=(FONT_FAMILY_MONO, FONT_SIZE_MONO),
            bg=THEME_SURFACE, fg=THEME_TEXT,
            insertbackground=THEME_TEXT,
            selectbackground=THEME_PRIMARY,
            selectforeground="white",
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground=THEME_BORDER,
            highlightcolor=THEME_PRIMARY,
            padx=8, pady=6,
        )
        self.text1 = tk.Text(left, **common_text_opts)
        self.text2 = tk.Text(right, **common_text_opts)
        self.text1.pack(fill="both", expand=True)
        self.text2.pack(fill="both", expand=True)

        self.choice_label = ttk.Label(
            self.window,
            text=t("current_choice_label", source=t("current_choice_unset")),
            style="Title.TLabel"
        )
        self.choice_label.pack(fill="x", padx=SP["md"], pady=(0, SP["sm"]))

        bottom = ttk.Frame(self.window, padding=8)
        bottom.pack(fill="x")

        ttk.Button(bottom, text=t("prev_shortcut"), style="Ghost.TButton",
                   command=self.go_prev).pack(side="left")
        ttk.Button(
            bottom, text=t("use_xml1_shortcut"), style="Ghost.TButton",
            command=lambda: self.choose("xml1")
        ).pack(side="left", padx=SP["sm"])
        ttk.Button(
            bottom, text=t("use_xml2_shortcut"), style="Ghost.TButton",
            command=lambda: self.choose("xml2")
        ).pack(side="left", padx=SP["sm"])
        ttk.Button(
            bottom, text=t("clear_source_button"), style="Ghost.TButton",
            command=lambda: self.choose(None)
        ).pack(side="left", padx=SP["sm"])
        ttk.Button(bottom, text=t("next_shortcut"), style="Ghost.TButton",
                   command=self.go_next).pack(side="left", padx=SP["sm"])

        ttk.Button(bottom, text=t("finish_apply_button"), style="Primary.TButton",
                   command=self.finish).pack(side="right")
        ttk.Button(bottom, text=t("cancel_wizard_button"), style="Ghost.TButton",
                   command=self.cancel).pack(side="right", padx=SP["sm"])

        self.window.bind("<Left>", lambda e: self.go_prev())
        self.window.bind("<Right>", lambda e: self.go_next())
        self.window.bind("<Key-1>", lambda e: self.choose("xml1"))
        self.window.bind("<Key-2>", lambda e: self.choose("xml2"))

    def show_current(self):
        path = self.paths[self.pos]
        self.pos_label.config(text=t("wizard_pos_label", current=self.pos + 1, total=len(self.paths)))
        self.path_label.config(text=path)

        a, b = resolve_diff_nodes(path, self.index1, self.index2, self.value_pairs)

        self.text1.configure(state="normal")
        self.text1.delete("1.0", "end")
        self.text1.insert("end", t("not_exist") if a is None else pretty_xml(a))
        self.text1.configure(state="disabled")

        self.text2.configure(state="normal")
        self.text2.delete("1.0", "end")
        self.text2.insert("end", t("not_exist") if b is None else pretty_xml(b))
        self.text2.configure(state="disabled")

        self.update_choice_label()

    def update_choice_label(self):
        source = self.rules.get(self.paths[self.pos])
        text = (
            t("source_file1_xml1") if source == "xml1"
            else t("source_file2_xml2") if source == "xml2"
            else t("current_choice_unset")
        )
        self.choice_label.config(text=t("current_choice_label", source=text))

    def choose(self, source):
        if not self.paths:
            return
        path = self.paths[self.pos]
        if source is None:
            self.rules.pop(path, None)
        else:
            self.rules[path] = source
        self.update_choice_label()

    def go_next(self):
        if self.pos < len(self.paths) - 1:
            self.pos += 1
            self.show_current()

    def go_prev(self):
        if self.pos > 0:
            self.pos -= 1
            self.show_current()

    def finish(self):
        self.result = dict(self.rules)
        self.window.destroy()

    def cancel(self):
        self.result = None
        self.window.destroy()


class MergeSelector:
    """
    Rule-creation dialog. Defaults to a *grouped* view built from the
    minimal diff points (see minimal_diff_paths / compute_value_pairs):
    repeated elements across a loop-like structure (e.g. item1/a and
    item2/a) are shown as one group ("a x2") so a single rule can cover
    every occurrence. Expanding a group - or unchecking "group by type"
    to see the flat, ungrouped node list - lets specific occurrences be
    overridden individually.
    """

    def __init__(self, parent, root1, root2, diff, existing_rules):
        self.window = tk.Toplevel(parent)
        self.window.title(t("merge_selector_title"))
        self.window.geometry("1320x830")
        self.window.minsize(1040, 680)
        self.window.transient(parent)
        try:
            self.window.configure(bg=THEME_BG)
        except Exception:
            pass
        self.window.grab_set()

        self.root1 = root1
        self.root2 = root2
        self.diff = diff
        self.rules = dict(existing_rules)
        self.result = None

        self.index1, self.records1 = build_node_index(root1)
        self.index2, self.records2 = build_node_index(root2)

        self.kinds, self.minimal, self.value_pairs = build_diff_model(
            self.index1, self.index2
        )
        self.groups = group_minimal_diffs_by_tag(self.minimal)

        self.all_paths = sorted(
            set(self.index1) | set(self.index2),
            key=lambda p: (p.count("/"), p)
        )

        self.only_diff = tk.BooleanVar(value=True)
        self.group_by_type = tk.BooleanVar(value=True)

        self.build_ui()
        self.populate()

    def build_ui(self):
        top = ttk.Frame(self.window, padding=SP["md"])
        top.pack(fill="x")

        ttk.Label(
            top,
            text=t("merge_selector_instruction"),
            style="Title.TLabel"
        ).pack(side="left")

        ttk.Checkbutton(
            top,
            text=t("group_by_type_checkbox"),
            variable=self.group_by_type,
            command=self.populate
        ).pack(side="left", padx=15)

        ttk.Checkbutton(
            top,
            text=t("only_diff_checkbox"),
            variable=self.only_diff,
            command=self.populate
        ).pack(side="right", padx=10)

        ttk.Button(
            top, text=t("select_all_diff_button"), style="Ghost.TButton",
            command=self.select_diff
        ).pack(side="right", padx=SP["sm"])

        ttk.Button(
            top, text=t("clear_selection_button"), style="Ghost.TButton",
            command=lambda: self.tree.selection_set(())
        ).pack(side="right")

        main = ttk.PanedWindow(self.window, orient="horizontal")
        main.pack(fill="both", expand=True, padx=SP["md"], pady=SP["xs"])

        left = ttk.Frame(main)
        right = ttk.LabelFrame(main, text=t("panel_node_compare"),
                               padding=(SP["xs"], SP["xs"]))
        main.add(left, weight=3)
        main.add(right, weight=2)

        self.tree = ttk.Treeview(
            left,
            columns=("status", "source"),
            show="tree headings",
            selectmode="extended"
        )
        self.tree.heading("#0", text=t("col_content"))
        self.tree.heading("status", text=t("col_state"))
        self.tree.heading("source", text=t("col_source"))

        self.tree.column("#0", width=520)
        self.tree.column("status", width=90)
        self.tree.column("source", width=90)

        sy = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        configure_diff_tags(self.tree)
        self.tree.tag_configure("group", font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL, "bold"))
        self.tree.bind("<<TreeviewSelect>>", self.show_selected)

        self.detail = tk.Text(
            right, wrap="none",
            font=(FONT_FAMILY_MONO, FONT_SIZE_MONO),
            bg=THEME_SURFACE, fg=THEME_TEXT,
            insertbackground=THEME_TEXT,
            selectbackground=THEME_PRIMARY,
            selectforeground="white",
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground=THEME_BORDER,
            highlightcolor=THEME_PRIMARY,
            padx=8, pady=6,
        )
        dsy = ttk.Scrollbar(right, orient="vertical", command=self.detail.yview)
        self.detail.configure(yscrollcommand=dsy.set)
        self.detail.pack(side="left", fill="both", expand=True)
        dsy.pack(side="right", fill="y")

        bottom = ttk.Frame(self.window, padding=SP["md"])
        bottom.pack(fill="x")

        ttk.Label(bottom, text=t("label_set_selected")).pack(side="left")

        ttk.Button(
            bottom, text=t("use_xml1_button"), style="Ghost.TButton",
            command=lambda: self.apply_source("xml1")
        ).pack(side="left", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("use_xml2_button"), style="Ghost.TButton",
            command=lambda: self.apply_source("xml2")
        ).pack(side="left", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("clear_source_button"), style="Ghost.TButton",
            command=self.clear_source
        ).pack(side="left", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("cancel_button"), style="Ghost.TButton",
            command=self.cancel
        ).pack(side="right", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("all_xml1_button"), style="Ghost.TButton",
            command=lambda: self.set_all("xml1")
        ).pack(side="right", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("all_xml2_button"), style="Ghost.TButton",
            command=lambda: self.set_all("xml2")
        ).pack(side="right", padx=SP["sm"])

        ttk.Button(
            bottom, text=t("apply_rules_button"), style="Primary.TButton",
            command=self.finish
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Populate: dispatch to grouped or flat view
    # ------------------------------------------------------------------

    def populate(self):
        for item in self.tree.get_children(""):
            self.tree.delete(item)

        if self.group_by_type.get():
            self.populate_grouped()
        else:
            self.populate_flat()

    def populate_grouped(self):
        """
        Minimal-diff, type-grouped view: one row per element tag, showing
        how many occurrences differ. Expand a group to see (and optionally
        override) individual occurrences.
        """
        for tag in sorted(self.groups):
            items = self.groups[tag]
            group_iid = "group:" + tag

            sources = {self.rules.get(p) for p, _k in items}
            if sources == {"xml1"}:
                group_source_text = t("source_file1")
            elif sources == {"xml2"}:
                group_source_text = t("source_file2")
            elif len(sources - {None}) == 0:
                group_source_text = ""
            else:
                group_source_text = t("status_mixed")

            self.tree.insert(
                "", "end", iid=group_iid,
                text=t("group_row_label", tag=tag, n=len(items)),
                values=(t("status_group"), group_source_text),
                tags=("group",),
                open=False
            )

            for path, kind in items:
                source = self.rules.get(path, "")
                source_text = (
                    t("source_file1") if source == "xml1"
                    else t("source_file2") if source == "xml2"
                    else ""
                )
                elem = self.index1.get(path) or self.index2.get(path)
                self.tree.insert(
                    group_iid, "end", iid=path,
                    text=element_to_xml_string(elem),
                    values=(state_label(kind), source_text),
                    tags=(kind,)
                )

    def populate_flat(self):
        """Full node list (original behaviour), with git-style kind labels/
        colors. Includes ancestor "changed" nodes for context, but those
        cannot be turned into rules directly (see _apply_one)."""
        for path in self.all_paths:
            if self.only_diff.get() and path not in self.diff:
                continue

            a = self.index1.get(path)
            b = self.index2.get(path)
            elem = a if a is not None else b
            kind = self.kinds.get(path, "same")

            source = self.rules.get(path, "")
            source_text = (
                t("source_file1") if source == "xml1"
                else t("source_file2") if source == "xml2"
                else ""
            )

            self.tree.insert(
                "", "end", iid=path,
                text=element_to_xml_string(elem),
                values=(state_label(kind), source_text),
                tags=(kind,) if kind != "same" else ()
            )

    # ------------------------------------------------------------------
    # Selection / rule assignment
    # ------------------------------------------------------------------

    def select_diff(self):
        if self.group_by_type.get():
            ids = list(self.tree.get_children(""))  # all group rows
        else:
            visible = set(self.tree.get_children(""))
            ids = [p for p in self.minimal if p in visible]
        self.tree.selection_set(ids)

    def apply_source(self, source):
        blocked = []
        for iid in self.tree.selection():
            if iid.startswith("group:"):
                tag = iid.split(":", 1)[1]
                for path, kind in self.groups.get(tag, []):
                    self._apply_one(path, kind, source, blocked)
            else:
                kind = self.kinds.get(iid)
                self._apply_one(iid, kind, source, blocked)

        self.populate()

        if blocked:
            messagebox.showinfo(t("dlg_title_notice"), t("blocked_rule_msg", n=len(blocked)))

    def _apply_one(self, path, kind, source, blocked):
        if kind == "changed":
            blocked.append(path)
            return
        if path.startswith("pair:"):
            self.rules[path] = source
            return
        if source == "xml2" and path not in self.index2:
            return
        if source == "xml1" and path not in self.index1:
            return
        self.rules[path] = source

    def clear_source(self):
        for iid in self.tree.selection():
            if iid.startswith("group:"):
                tag = iid.split(":", 1)[1]
                for path, _kind in self.groups.get(tag, []):
                    self.rules.pop(path, None)
            else:
                self.rules.pop(iid, None)
        self.populate()

    def set_all(self, source):
        for path, kind in self.minimal.items():
            self._apply_one(path, kind, source, [])
        self.populate()

    def show_selected(self, event=None):
        selection = self.tree.selection()
        self.detail.delete("1.0", "end")
        if not selection:
            return

        iid = selection[-1]
        if iid.startswith("group:"):
            tag = iid.split(":", 1)[1]
            items = self.groups.get(tag, [])
            self.detail.insert("end", t("detail_group_header", tag=tag, n=len(items)))
            for path, kind in items:
                elem = self.index1.get(path) or self.index2.get(path)
                summary = element_summary(elem)
                self.detail.insert("end", "· %s  [%s]  %s\n"
                                   % (strip_namespace(elem.tag) if elem is not None else "?",
                                      state_label(kind), summary))
            return

        path = iid
        a, b = resolve_diff_nodes(path, self.index1, self.index2, self.value_pairs)

        self.detail.insert("end", t("detail_location_header",
                                     location=friendly_location(path)))
        self.detail.insert("end", t("detail_file1_header"))
        self.detail.insert(
            "end", t("not_exist") + "\n" if a is None else pretty_xml(a)
        )
        self.detail.insert("end", t("detail_file2_header"))
        self.detail.insert(
            "end", t("not_exist") + "\n" if b is None else pretty_xml(b)
        )

    def finish(self):
        self.result = dict(self.rules)
        self.window.destroy()

    def cancel(self):
        self.result = None
        self.window.destroy()


def apply_modern_theme(root, style_obj):
    """Apply a clean, modern desktop-app look using ttk with *clam* theme.

    CRITICAL: We force "clam" (cross-platform) instead of "vista/xpnative".
    The Windows native themes silently ignore TButton.background, so on top of
    the OS's default "gray gradient button" our foreground=white would produce
    the classic "灰底白字看不清" symptom. Clam renders our ttk styles reliably
    on every OS so the palette below is what you actually see on screen.
    """

    # ---- Theme: always start from clam; graceful fallback alt/default ----
    for theme_candidate in ("clam", "alt", "default", "classic"):
        try:
            style_obj.theme_use(theme_candidate)
            break
        except Exception:
            continue

    root.configure(bg=THEME_BG)

    # Global font / neutral defaults
    style_obj.configure(".",
                        background=THEME_BG,
                        foreground=THEME_TEXT,
                        fieldbackground=THEME_SURFACE,
                        bordercolor=THEME_BORDER,
                        lightcolor=THEME_BORDER,
                        darkcolor=THEME_BORDER,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL))
    try:
        style_obj.map(".", background=[("active", THEME_BG)])
    except Exception:
        pass

    # ---- TFrame / TLabelFrame: card-style surfaces ----
    style_obj.configure("TFrame", background=THEME_BG)
    style_obj.configure("Card.TFrame",
                        background=THEME_SURFACE,
                        relief="flat")
    style_obj.configure("TLabelframe",
                        background=THEME_SURFACE,
                        relief="solid",
                        borderwidth=1)
    style_obj.configure("TLabelframe.Label",
                        background=THEME_SURFACE,
                        foreground=THEME_PRIMARY,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_TITLE, "bold"))
    style_obj.configure("TLabel",
                        background=THEME_BG,
                        foreground=THEME_TEXT,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL))
    style_obj.configure("Title.TLabel",
                        background=THEME_BG,
                        foreground=THEME_PRIMARY,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_TITLE, "bold"))
    style_obj.configure("Hint.TLabel",
                        background=THEME_BG,
                        foreground=THEME_TEXT_MUTED,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_HINT))
    style_obj.configure("Card.TLabel",
                        background=THEME_SURFACE,
                        foreground=THEME_TEXT,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL))

    # =================================================================
    # TButton family – HIGH CONTRAST redesigned (no "灰底白字" ever again)
    # -----------------------------------------------------------------
    #  - Default TButton : Slate-800 (near-black) deep solid + white text
    #                      (WCAG AAA contrast on clam). Acts as safe base
    #                      for any button we forget to style.
    #  - Primary.TButton : Blue-600 solid + white ("主操作")
    #  - Accent.TButton  : Sky-600 solid + white ("强调操作")
    #  - Ghost.TButton   : Light off-white card + Slate-700 DARK text
    #                      ("次要/浏览"按钮，outlined 风格)
    # 所有按钮统一 1px 实体边框 + 稍微加大内边距，形成清晰的"按钮轮廓"。
    # =================================================================
    BTN_BORDER = 1
    BTN_PAD_X = 16
    BTN_PAD_Y = 8
    BTN_FONT = (FONT_FAMILY_BASE, FONT_SIZE_LABEL, "bold")

    # ---- Default TButton (deep slate solid → white) -------------------
    style_obj.configure("TButton",
                        padding=(BTN_PAD_X, BTN_PAD_Y),
                        font=BTN_FONT,
                        borderwidth=BTN_BORDER,
                        focusthickness=1,
                        relief="solid")
    style_obj.map("TButton",
                  background=[("!disabled", "#334155"),   # Slate-800 deep (近黑)
                              ("active",    "#1e293b"),   # Slate-900 hover 再深一级
                              ("pressed",   "#0f172a"),   # Slate-950 按下
                              ("disabled",  "#cbd5e1")],
                  foreground=[("!disabled", "white"),
                              ("disabled",  "#94a3b8")],
                  bordercolor=[("!disabled", "#1e293b"),
                               ("active",    "#0f172a"),
                               ("pressed",   "#020617"),
                               ("disabled",  "#cbd5e1")])

    # ---- Primary.TButton (Blue solid → white) ------------------------
    style_obj.configure("Primary.TButton",
                        padding=(BTN_PAD_X, BTN_PAD_Y),
                        font=BTN_FONT,
                        borderwidth=BTN_BORDER,
                        focusthickness=1,
                        relief="solid")
    style_obj.map("Primary.TButton",
                  background=[("!disabled", "#2563eb"),   # Blue-600 主色
                              ("active",    "#1d4ed8"),   # Blue-700 hover
                              ("pressed",   "#1e3a8a"),   # Blue-900 pressed
                              ("disabled",  "#cbd5e1")],
                  foreground=[("!disabled", "white"),
                              ("disabled",  "#94a3b8")],
                  bordercolor=[("!disabled", "#1d4ed8"),
                               ("active",    "#1e40af"),
                               ("pressed",   "#1e3a8a"),
                               ("disabled",  "#cbd5e1")])

    # ---- Accent.TButton (Sky solid → white) --------------------------
    style_obj.configure("Accent.TButton",
                        padding=(BTN_PAD_X, BTN_PAD_Y),
                        font=BTN_FONT,
                        borderwidth=BTN_BORDER,
                        focusthickness=1,
                        relief="solid")
    style_obj.map("Accent.TButton",
                  background=[("!disabled", "#0284c7"),   # Sky-600
                              ("active",    "#0369a1"),   # Sky-700 hover
                              ("pressed",   "#075985"),   # Sky-800 pressed
                              ("disabled",  "#cbd5e1")],
                  foreground=[("!disabled", "white"),
                              ("disabled",  "#94a3b8")],
                  bordercolor=[("!disabled", "#0369a1"),
                               ("active",    "#075985"),
                               ("pressed",   "#0c4a6e"),
                               ("disabled",  "#cbd5e1")])

    # ---- Ghost.TButton (outlined: 浅色背景 + 深色字 + 边框) -----------
    # 重要：这里故意是"浅底 + 深字"，高对比，绝不会"灰底白字看不清"。
    style_obj.configure("Ghost.TButton",
                        padding=(BTN_PAD_X, BTN_PAD_Y),
                        font=BTN_FONT,
                        borderwidth=BTN_BORDER,
                        focusthickness=1,
                        relief="solid")
    style_obj.map("Ghost.TButton",
                  background=[("!disabled", "#f8fafc"),   # Slate-50 (比 THEME_SURFACE 浅一级，可辨识)
                              ("active",    "#e2e8f0"),   # Slate-200 hover
                              ("pressed",   "#cbd5e1"),   # Slate-300 pressed
                              ("disabled",  "#f1f5f9")],
                  foreground=[("!disabled", "#1e293b"),   # Slate-800 深色字
                              ("disabled",  "#94a3b8")],
                  bordercolor=[("!disabled", "#94a3b8"),  # Slate-500 边框
                               ("active",    "#64748b"),  # Slate-500 hover 更深
                               ("pressed",   "#334155"),  # Slate-700 pressed
                               ("disabled",  "#e2e8f0")])

    # ---- TEntry / TCombobox ------------------------------------------
    style_obj.configure("TEntry",
                        padding=(8, 8),
                        fieldbackground=THEME_SURFACE,
                        foreground=THEME_TEXT,
                        bordercolor=THEME_BORDER,
                        lightcolor=THEME_BORDER,
                        darkcolor=THEME_BORDER,
                        insertcolor=THEME_TEXT,
                        arrowcolor=THEME_TEXT,
                        borderwidth=1,
                        relief="solid")
    style_obj.map("TEntry",
                  bordercolor=[("focus", THEME_PRIMARY)],
                  lightcolor=[("focus", THEME_PRIMARY)],
                  darkcolor=[("focus", THEME_PRIMARY)])

    style_obj.configure("TCombobox",
                        padding=(8, 8),
                        fieldbackground=THEME_SURFACE,
                        foreground=THEME_TEXT,
                        arrowcolor=THEME_TEXT,
                        borderwidth=1,
                        relief="solid")
    style_obj.map("TCombobox",
                  bordercolor=[("focus", THEME_PRIMARY)],
                  lightcolor=[("focus", THEME_PRIMARY)],
                  darkcolor=[("focus", THEME_PRIMARY)])
    try:
        style_obj.configure("TCombobox.field",
                            padding=(4, 4),
                            background=THEME_SURFACE,
                            foreground=THEME_TEXT)
    except Exception:
        pass

    # ---- TCheckbutton / TRadiobutton ----
    style_obj.configure("TCheckbutton",
                        background=THEME_BG,
                        foreground=THEME_TEXT,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL))
    style_obj.map("TCheckbutton",
                  background=[("active", THEME_BG)],
                  foreground=[("active", THEME_TEXT)])

    # ---- TPanedWindow ----
    style_obj.configure("TPanedwindow", background=THEME_BG)
    try:
        style_obj.configure("TPanedwindow.Sash",
                            background=THEME_BG,
                            sashwidth=4, sashrelief="flat")
    except Exception:
        pass

    # ---- TScrollbar: slim, minimal ----
    style_obj.configure("TScrollbar",
                        background="#94a3b8",
                        troughcolor=THEME_BG,
                        borderwidth=0,
                        arrowcolor="#64748b",
                        width=10)
    style_obj.map("TScrollbar",
                  background=[("active", "#475569"),
                              ("disabled", "#e2e8f0")])

    # ---- Treeview (the heart of the diff display) ----
    style_obj.configure("Treeview",
                        background=THEME_SURFACE,
                        fieldbackground=THEME_SURFACE,
                        foreground=THEME_TEXT,
                        rowheight=28,
                        bordercolor=THEME_BORDER,
                        lightcolor=THEME_BORDER,
                        darkcolor=THEME_BORDER,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL),
                        borderwidth=1,
                        relief="solid")
    style_obj.configure("Treeview.Heading",
                        background="#f1f5f9",
                        foreground=THEME_TEXT,
                        relief="solid",
                        borderwidth=1,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL, "bold"))
    style_obj.map("Treeview",
                  background=[("selected", THEME_PRIMARY)],
                  foreground=[("selected", "white")])
    style_obj.map("Treeview.Heading",
                  background=[("active", "#e2e8f0")])

    # ---- Notebook / Tabs (optional, reserved for future use) ----
    style_obj.configure("TNotebook",
                        background=THEME_BG,
                        borderwidth=0,
                        tabmargins=(0, 2, 0, 0))
    style_obj.configure("TNotebook.Tab",
                        padding=(SP["lg"], SP["sm"]),
                        background=THEME_BG,
                        foreground=THEME_TEXT_MUTED,
                        font=(FONT_FAMILY_BASE, FONT_SIZE_LABEL))
    style_obj.map("TNotebook.Tab",
                  background=[("selected", THEME_SURFACE)],
                  foreground=[("selected", THEME_PRIMARY)],
                  expand=[("selected", [1, 1, 1, 0])])


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        apply_modern_theme(root, style)
    except Exception:
        # Graceful fallback: theme setup must never crash the app
        try:
            ttk.Style().theme_use("clam")
        except Exception:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
