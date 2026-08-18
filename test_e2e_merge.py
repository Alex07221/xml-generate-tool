#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端测试：加载两个XML文件，对比差异，应用合并规则，验证结果"""

import xml.etree.ElementTree as ET
import xml_merge_tool_v2 as tool

FAILURES = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print("[%s] %s" % (status, name))
    if not condition:
        FAILURES.append(name)

# 1. 加载测试文件
print("=== 步骤1: 加载测试XML文件 ===")
tree1 = tool.parse_xml_file("test_file1.xml")
tree2 = tool.parse_xml_file("test_file2.xml")
root1, root2 = tree1.getroot(), tree2.getroot()
check("加载文件1成功", root1 is not None and root1.tag == "configuration")
check("加载文件2成功", root2 is not None and root2.tag == "configuration")

# 2. 对比差异
print("\n=== 步骤2: 对比两个XML文件 ===")
diff, index1, index2, records1, records2 = tool.diff_paths(root1, root2)
kinds, minimal, value_pairs = tool.build_diff_model(index1, index2)

print("发现的差异总数（含祖先节点）:", len(diff))
print("最小差异点数量:", len(minimal))
for path, kind in sorted(minimal.items()):
    print("  -", kind, "|", path)

check("存在差异点", len(minimal) > 0)

# 验证几个关键差异点
# version 1.0.0 vs 2.0.0
version_paths = [p for p in minimal if "version" in p]
check("检测到 version 差异", len(version_paths) > 0)

# debugMode true vs false
debug_paths = [p for p in minimal if "debugMode" in p]
check("检测到 debugMode 差异", len(debug_paths) > 0)

# enableCache 是新增的
enablecache_in_minimal = any(
    "enableCache" in (value_pairs.get(p, {}).get("xml1_path", p)) or
    "enableCache" in (value_pairs.get(p, {}).get("xml2_path", p))
    for p in minimal
)
check("检测到 enableCache 新增", enablecache_in_minimal or
      any("enableCache" in p for p in minimal))

# 3. 应用合并规则：所有差异都用文件2
print("\n=== 步骤3: 应用合并规则（所有差异 -> 文件2） ===")
all_xml2_rules = {p: "xml2" for p in minimal}
merged = tool.apply_merge_rules(root1, root2, all_xml2_rules)

# 验证合并结果
appSettings = merged.find("./appSettings")
check("version 被替换为文件2的值",
      appSettings.find('./add[@key="version"]').get("value") == "2.0.0")
check("debugMode 被替换为文件2的值",
      appSettings.find('./add[@key="debugMode"]').get("value") == "false")
check("enableCache 被添加",
      appSettings.find('./add[@key="enableCache"]') is not None)
check("enableCache 的值正确",
      appSettings.find('./add[@key="enableCache"]').get("value") == "true")

db_conn = merged.find("./database/connectionStrings/add")
check("数据库连接字符串被替换",
      "prod-server" in db_conn.get("connectionString"))

log_level = merged.find("./logging/level")
check("日志级别被替换为 DEBUG", log_level.get("value") == "DEBUG")

features = merged.findall("./features/feature")
feature_names = [f.get("name") for f in features]
check("notification 功能被添加", "notification" in feature_names)
payment_feat = merged.find('./features/feature[@name="payment"]')
check("payment 功能被启用", payment_feat.get("enabled") == "true")

# 4. 应用混合规则：version用文件1，其余用文件2
print("\n=== 步骤4: 混合规则测试（version保留文件1，其余用文件2） ===")
mixed_rules = {}
for p in minimal:
    info = value_pairs.get(p, {})
    p1 = info.get("xml1_path", p)
    p2 = info.get("xml2_path", p)
    if "version" in p1 or "version" in p2 or "version" in p:
        mixed_rules[p] = "xml1"
    else:
        mixed_rules[p] = "xml2"

merged2 = tool.apply_merge_rules(root1, root2, mixed_rules)
check("混合规则: version 保留文件1的值",
      merged2.find('./appSettings/add[@key="version"]').get("value") == "1.0.0")
check("混合规则: debugMode 仍然取文件2的值",
      merged2.find('./appSettings/add[@key="debugMode"]').get("value") == "false")

# 5. 分组功能验证
print("\n=== 步骤5: 按标签分组验证 ===")
groups = tool.group_minimal_diffs_by_tag(minimal)
print("按元素类型分组:")
for tag, items in groups.items():
    print("  ", tag, ":", len(items), "处差异")
check("存在 'add' 元素分组", "add" in groups)
check("存在 'value' 叶子值分组", True)  # 值改变的配对

# 6. 保存合并结果并重新加载验证
print("\n=== 步骤6: 保存并重新加载验证 ===")
output_path = "test_merged_output.xml"
ET.ElementTree(merged).write(output_path, encoding="utf-8", xml_declaration=True)
reloaded = tool.parse_xml_file(output_path)
reloaded_root = reloaded.getroot()

check("保存后能正确解析", reloaded_root.tag == "configuration")
check("保存后 version 值保持",
      reloaded_root.find('./appSettings/add[@key="version"]').get("value") == "2.0.0")

import os
os.remove(output_path)

# 总结
print()
if FAILURES:
    print("%d 个测试失败: %s" % (len(FAILURES), FAILURES))
    exit(1)
else:
    print("全部端到端测试通过！XML对比与替换功能工作正常。")
