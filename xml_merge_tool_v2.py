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
# Internationalization (i18n)
# ---------------------------------------------------------------------------
# Supported UI languages. Native display names are what appear in the
# language switcher dropdown.
SUPPORTED_LANGUAGES = ("zh", "en", "es", "fr", "ru")
LANGUAGE_NAMES = {
    "zh": "中文",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "ru": "Русский",
}
DEFAULT_LANGUAGE = "en"

TRANSLATIONS = {
    "app_title": {
        "zh": "XML / META 合并工具", "en": "XML / META Merge Tool",
        "es": "Herramienta de fusión XML / META", "fr": "Outil de fusion XML / META",
        "ru": "Инструмент слияния XML / META",
    },
    "language_label": {
        "zh": "语言：", "en": "Language:", "es": "Idioma:", "fr": "Langue :", "ru": "Язык:",
    },
    "file1_label": {
        "zh": "文件 1:", "en": "File 1:", "es": "Archivo 1:", "fr": "Fichier 1 :", "ru": "Файл 1:",
    },
    "file2_label": {
        "zh": "文件 2:", "en": "File 2:", "es": "Archivo 2:", "fr": "Fichier 2 :", "ru": "Файл 2:",
    },
    "choose_file_button": {
        "zh": "选择文件", "en": "Choose File", "es": "Elegir archivo",
        "fr": "Choisir un fichier", "ru": "Выбрать файл",
    },
    "load_compare_button": {
        "zh": "加载并比较", "en": "Load && Compare", "es": "Cargar y comparar",
        "fr": "Charger et comparer", "ru": "Загрузить и сравнить",
    },
    "select_merge_button": {
        "zh": "按元素选择合并", "en": "Select Elements to Merge",
        "es": "Seleccionar elementos para fusionar",
        "fr": "Sélectionner les éléments à fusionner",
        "ru": "Выбрать элементы для слияния",
    },
    "manual_wizard_button": {
        "zh": "手动合并向导", "en": "Manual Merge Wizard", "es": "Asistente de fusión manual",
        "fr": "Assistant de fusion manuelle", "ru": "Мастер ручного слияния",
    },
    "clear_rules_button": {
        "zh": "清除全部规则", "en": "Clear All Rules", "es": "Borrar todas las reglas",
        "fr": "Effacer toutes les règles", "ru": "Очистить все правила",
    },
    "only_diff_checkbox": {
        "zh": "只显示有差异节点", "en": "Show Differences Only", "es": "Mostrar solo diferencias",
        "fr": "Afficher uniquement les différences", "ru": "Показывать только различия",
    },
    "preview_button": {
        "zh": "预览合并结果", "en": "Preview Merge Result", "es": "Previsualizar resultado",
        "fr": "Aperçu du résultat", "ru": "Предпросмотр результата",
    },
    "save_button": {
        "zh": "保存合并结果", "en": "Save Merge Result", "es": "Guardar resultado",
        "fr": "Enregistrer le résultat", "ru": "Сохранить результат",
    },
    "rule_count_label": {
        "zh": "合并规则：{n}", "en": "Merge Rules: {n}", "es": "Reglas de fusión: {n}",
        "fr": "Règles de fusion : {n}", "ru": "Правил слияния: {n}",
    },
    "prev_diff_button": {
        "zh": "◀ 上一个差异", "en": "◀ Previous Diff", "es": "◀ Diferencia anterior",
        "fr": "◀ Différence précédente", "ru": "◀ Пред. отличие",
    },
    "next_diff_button": {
        "zh": "下一个差异 ▶", "en": "Next Diff ▶", "es": "Diferencia siguiente ▶",
        "fr": "Différence suivante ▶", "ru": "След. отличие ▶",
    },
    "diff_pos_label": {
        "zh": "差异 {current} / {total}", "en": "Diff {current} / {total}",
        "es": "Diferencia {current} / {total}", "fr": "Différence {current} / {total}",
        "ru": "Отличие {current} / {total}",
    },
    "legend_added": {
        "zh": "新增", "en": "Added", "es": "Añadido", "fr": "Ajouté", "ru": "Добавлено",
    },
    "legend_removed": {
        "zh": "删除", "en": "Removed", "es": "Eliminado", "fr": "Supprimé", "ru": "Удалено",
    },
    "legend_modified": {
        "zh": "修改", "en": "Modified", "es": "Modificado", "fr": "Modifié", "ru": "Изменено",
    },
    "legend_changed": {
        "zh": "子项含差异", "en": "Contains Changes", "es": "Contiene cambios",
        "fr": "Contient des changements", "ru": "Содержит изменения",
    },
    "col_element": {
        "zh": "元素 / 代码块", "en": "Element / Node", "es": "Elemento / Nodo",
        "fr": "Élément / Nœud", "ru": "Элемент / Узел",
    },
    "col_path": {
        "zh": "路径", "en": "Path", "es": "Ruta", "fr": "Chemin", "ru": "Путь",
    },
    "col_state": {
        "zh": "状态", "en": "State", "es": "Estado", "fr": "État", "ru": "Статус",
    },
    "col_source": {
        "zh": "合并来源", "en": "Merge Source", "es": "Origen de fusión",
        "fr": "Source de fusion", "ru": "Источник слияния",
    },
    "frame_file1": {
        "zh": "文件 1", "en": "File 1", "es": "Archivo 1", "fr": "Fichier 1", "ru": "Файл 1",
    },
    "frame_file2": {
        "zh": "文件 2", "en": "File 2", "es": "Archivo 2", "fr": "Fichier 2", "ru": "Файл 2",
    },
    "frame_detail": {
        "zh": "选中节点 / 差异", "en": "Selected Node / Difference",
        "es": "Nodo seleccionado / Diferencia", "fr": "Nœud sélectionné / Différence",
        "ru": "Выбранный узел / Отличие",
    },
    "status_initial": {
        "zh": "请选择两个 XML / META 文件。", "en": "Please select two XML / META files.",
        "es": "Seleccione dos archivos XML / META.",
        "fr": "Veuillez sélectionner deux fichiers XML / META.",
        "ru": "Выберите два файла XML / META.",
    },
    "status_compare_done": {
        "zh": "比较完成：{diff_count} 个节点存在差异（其中 {minimal_count} 个可直接设为合并规则的"
              "最小差异点）。可以点击“按元素选择合并”或“手动合并向导”。",
        "en": "Comparison complete: {diff_count} differing node(s) ({minimal_count} minimal "
              "diff point(s) can be turned directly into merge rules). "
              "Click \"Select Elements to Merge\" or \"Manual Merge Wizard\".",
        "es": "Comparación completa: {diff_count} nodo(s) con diferencias ({minimal_count} "
              "punto(s) mínimos se pueden convertir directamente en reglas de fusión). "
              "Haga clic en \"Seleccionar elementos para fusionar\" o "
              "\"Asistente de fusión manual\".",
        "fr": "Comparaison terminée : {diff_count} nœud(s) en différence ({minimal_count} "
              "point(s) de différence minimaux peuvent devenir directement des règles de "
              "fusion). Cliquez sur « Sélectionner les éléments à fusionner » ou "
              "« Assistant de fusion manuelle ».",
        "ru": "Сравнение завершено: узлов с отличиями — {diff_count} (из них {minimal_count} "
              "можно сразу превратить в правила слияния). Нажмите «Выбрать элементы для "
              "слияния» или «Мастер ручного слияния».",
    },
    "msg_select_both_files": {
        "zh": "请选择文件 1 和文件 2。", "en": "Please select File 1 and File 2.",
        "es": "Seleccione el archivo 1 y el archivo 2.",
        "fr": "Veuillez sélectionner le fichier 1 et le fichier 2.",
        "ru": "Выберите файл 1 и файл 2.",
    },
    "dlg_title_parse_failed": {
        "zh": "解析失败", "en": "Parse Failed", "es": "Error de análisis",
        "fr": "Échec de l'analyse", "ru": "Ошибка разбора",
    },
    "dlg_title_notice": {
        "zh": "提示", "en": "Notice", "es": "Aviso", "fr": "Avis", "ru": "Уведомление",
    },
    "dlg_title_save_failed": {
        "zh": "保存失败", "en": "Save Failed", "es": "Error al guardar",
        "fr": "Échec de l'enregistrement", "ru": "Ошибка сохранения",
    },
    "dlg_title_done": {
        "zh": "完成", "en": "Done", "es": "Listo", "fr": "Terminé", "ru": "Готово",
    },
    "filetype_xmlmeta": {
        "zh": "XML / META 文件", "en": "XML / META Files", "es": "Archivos XML / META",
        "fr": "Fichiers XML / META", "ru": "Файлы XML / META",
    },
    "filetype_xml": {
        "zh": "XML 文件", "en": "XML Files", "es": "Archivos XML", "fr": "Fichiers XML",
        "ru": "Файлы XML",
    },
    "filetype_meta": {
        "zh": "META 文件", "en": "META Files", "es": "Archivos META", "fr": "Fichiers META",
        "ru": "Файлы META",
    },
    "filetype_all": {
        "zh": "所有文件", "en": "All Files", "es": "Todos los archivos", "fr": "Tous les fichiers",
        "ru": "Все файлы",
    },
    "choose_file1_title": {
        "zh": "选择文件 1", "en": "Choose File 1", "es": "Elegir archivo 1",
        "fr": "Choisir le fichier 1", "ru": "Выбрать файл 1",
    },
    "choose_file2_title": {
        "zh": "选择文件 2", "en": "Choose File 2", "es": "Elegir archivo 2",
        "fr": "Choisir le fichier 2", "ru": "Выбрать файл 2",
    },
    "status_saved": {
        "zh": "已保存：{path}", "en": "Saved: {path}", "es": "Guardado: {path}",
        "fr": "Enregistré : {path}", "ru": "Сохранено: {path}",
    },
    "msg_save_done": {
        "zh": "合并结果已保存。", "en": "Merge result saved.", "es": "Resultado de fusión guardado.",
        "fr": "Résultat de fusion enregistré.", "ru": "Результат слияния сохранён.",
    },
    "status_rules_cleared": {
        "zh": "已清除所有元素合并规则。", "en": "All merge rules cleared.",
        "es": "Todas las reglas de fusión borradas.",
        "fr": "Toutes les règles de fusion effacées.", "ru": "Все правила слияния очищены.",
    },
    "status_rules_set": {
        "zh": "已设置 {n} 条元素合并规则。未指定节点保持文件 1。",
        "en": "{n} merge rule(s) set. Unspecified nodes keep File 1.",
        "es": "{n} regla(s) de fusión establecidas. Los nodos no especificados mantienen el archivo 1.",
        "fr": "{n} règle(s) de fusion définies. Les nœuds non spécifiés conservent le fichier 1.",
        "ru": "Установлено правил слияния: {n}. Неуказанные узлы остаются из файла 1.",
    },
    "status_manual_wizard_updated": {
        "zh": "手动合并向导已更新，共有 {n} 条元素合并规则。",
        "en": "Manual merge wizard updated, {n} merge rule(s) total now.",
        "es": "Asistente de fusión manual actualizado, {n} regla(s) de fusión en total.",
        "fr": "Assistant de fusion manuelle mis à jour, {n} règle(s) de fusion au total.",
        "ru": "Мастер ручного слияния обновлён, всего правил слияния: {n}.",
    },
    "msg_load_compare_first": {
        "zh": "请先加载并比较两个文件。", "en": "Please load and compare two files first.",
        "es": "Primero cargue y compare dos archivos.",
        "fr": "Veuillez d'abord charger et comparer deux fichiers.",
        "ru": "Сначала загрузите и сравните два файла.",
    },
    "msg_no_nav_diffs": {
        "zh": "没有检测到可定位的差异点，请先加载并比较文件。",
        "en": "No navigable diff points detected. Please load and compare files first.",
        "es": "No se detectaron diferencias para navegar. Cargue y compare los archivos primero.",
        "fr": "Aucune différence navigable détectée. Chargez et comparez d'abord les fichiers.",
        "ru": "Не найдено отличий для перехода. Сначала загрузите и сравните файлы.",
    },
    "msg_no_manual_diffs": {
        "zh": "没有检测到差异点，无需手动合并。",
        "en": "No diff points detected, nothing to merge manually.",
        "es": "No se detectaron diferencias, no hay nada que fusionar manualmente.",
        "fr": "Aucune différence détectée, rien à fusionner manuellement.",
        "ru": "Отличий не найдено, вручную сливать нечего.",
    },
    "not_exist": {
        "zh": "[不存在]", "en": "[does not exist]", "es": "[no existe]",
        "fr": "[n'existe pas]", "ru": "[отсутствует]",
    },
    "detail_path_header": {
        "zh": "===== 路径 =====\n{path}\n\n", "en": "===== Path =====\n{path}\n\n",
        "es": "===== Ruta =====\n{path}\n\n", "fr": "===== Chemin =====\n{path}\n\n",
        "ru": "===== Путь =====\n{path}\n\n",
    },
    "detail_file1_header": {
        "zh": "===== 文件 1 =====\n", "en": "===== File 1 =====\n", "es": "===== Archivo 1 =====\n",
        "fr": "===== Fichier 1 =====\n", "ru": "===== Файл 1 =====\n",
    },
    "detail_file2_header": {
        "zh": "\n===== 文件 2 =====\n", "en": "\n===== File 2 =====\n",
        "es": "\n===== Archivo 2 =====\n", "fr": "\n===== Fichier 2 =====\n",
        "ru": "\n===== Файл 2 =====\n",
    },
    "detail_current_source": {
        "zh": "当前合并来源：{source}\n\n", "en": "Current merge source: {source}\n\n",
        "es": "Origen de fusión actual: {source}\n\n", "fr": "Source de fusion actuelle : {source}\n\n",
        "ru": "Текущий источник слияния: {source}\n\n",
    },
    "source_file1": {
        "zh": "文件 1", "en": "File 1", "es": "Archivo 1", "fr": "Fichier 1", "ru": "Файл 1",
    },
    "source_file2": {
        "zh": "文件 2", "en": "File 2", "es": "Archivo 2", "fr": "Fichier 2", "ru": "Файл 2",
    },
    "state_added": {
        "zh": "新增", "en": "Added", "es": "Añadido", "fr": "Ajouté", "ru": "Добавлено",
    },
    "state_removed": {
        "zh": "删除", "en": "Removed", "es": "Eliminado", "fr": "Supprimé", "ru": "Удалено",
    },
    "state_modified": {
        "zh": "修改", "en": "Modified", "es": "Modificado", "fr": "Modifié", "ru": "Изменено",
    },
    "state_changed": {
        "zh": "含差异(子项)", "en": "Contains Diff (child)", "es": "Contiene diferencia (hijo)",
        "fr": "Contient une différence (enfant)", "ru": "Есть отличие (дочерний)",
    },
    "state_same": {
        "zh": "相同", "en": "Same", "es": "Igual", "fr": "Identique", "ru": "Совпадает",
    },
    "parse_error_message": {
        "zh": "无法解析为 XML/META。\n{path}\n最后错误：{error}",
        "en": "Could not parse as XML/META.\n{path}\nLast error: {error}",
        "es": "No se pudo interpretar como XML/META.\n{path}\nÚltimo error: {error}",
        "fr": "Impossible d'analyser comme XML/META.\n{path}\nDernière erreur : {error}",
        "ru": "Не удалось разобрать как XML/META.\n{path}\nПоследняя ошибка: {error}",
    },
    "preview_window_title": {
        "zh": "合并结果预览", "en": "Merge Result Preview", "es": "Vista previa del resultado",
        "fr": "Aperçu du résultat de fusion", "ru": "Предпросмотр результата слияния",
    },

    # MergeSelector
    "merge_selector_title": {
        "zh": "按元素选择合并", "en": "Select Elements to Merge",
        "es": "Seleccionar elementos para fusionar",
        "fr": "Sélectionner les éléments à fusionner", "ru": "Выбор элементов для слияния",
    },
    "merge_selector_instruction": {
        "zh": "先选择一个或多个元素，再指定它们使用文件 1 或文件 2。",
        "en": "Select one or more elements, then choose File 1 or File 2 as the source.",
        "es": "Seleccione uno o más elementos y elija el archivo 1 o el archivo 2 como origen.",
        "fr": "Sélectionnez un ou plusieurs éléments, puis choisissez le fichier 1 ou 2 comme source.",
        "ru": "Выберите один или несколько элементов, затем укажите файл 1 или файл 2 как источник.",
    },
    "group_by_type_checkbox": {
        "zh": "按元素类型分组（推荐，同类元素只需设置一次规则）",
        "en": "Group by Element Type (recommended - set once per element kind)",
        "es": "Agrupar por tipo de elemento (recomendado, una sola regla por tipo)",
        "fr": "Regrouper par type d'élément (recommandé, une seule règle par type)",
        "ru": "Группировать по типу элемента (рекомендуется — одно правило на тип)",
    },
    "select_all_diff_button": {
        "zh": "全选差异", "en": "Select All Diffs", "es": "Seleccionar todas las diferencias",
        "fr": "Sélectionner toutes les différences", "ru": "Выбрать все отличия",
    },
    "clear_selection_button": {
        "zh": "清除选择", "en": "Clear Selection", "es": "Borrar selección",
        "fr": "Effacer la sélection", "ru": "Очистить выбор",
    },
    "panel_node_compare": {
        "zh": "节点对比", "en": "Node Comparison", "es": "Comparación de nodos",
        "fr": "Comparaison des nœuds", "ru": "Сравнение узлов",
    },
    "label_set_selected": {
        "zh": "对选中的元素/分组设置：", "en": "For selected element(s)/group(s), use:",
        "es": "Para los elementos/grupos seleccionados, usar:",
        "fr": "Pour les éléments/groupes sélectionnés, utiliser :",
        "ru": "Для выбранных элементов/групп использовать:",
    },
    "use_xml1_button": {
        "zh": "使用 XML 1", "en": "Use XML 1", "es": "Usar XML 1", "fr": "Utiliser XML 1",
        "ru": "Использовать XML 1",
    },
    "use_xml2_button": {
        "zh": "使用 XML 2", "en": "Use XML 2", "es": "Usar XML 2", "fr": "Utiliser XML 2",
        "ru": "Использовать XML 2",
    },
    "clear_source_button": {
        "zh": "取消指定", "en": "Unset", "es": "Anular", "fr": "Désassigner", "ru": "Сбросить",
    },
    "all_xml1_button": {
        "zh": "全部 XML 1", "en": "All XML 1", "es": "Todo XML 1", "fr": "Tout XML 1",
        "ru": "Всё из XML 1",
    },
    "all_xml2_button": {
        "zh": "全部 XML 2", "en": "All XML 2", "es": "Todo XML 2", "fr": "Tout XML 2",
        "ru": "Всё из XML 2",
    },
    "cancel_button": {
        "zh": "取消", "en": "Cancel", "es": "Cancelar", "fr": "Annuler", "ru": "Отмена",
    },
    "apply_rules_button": {
        "zh": "应用合并规则", "en": "Apply Merge Rules", "es": "Aplicar reglas de fusión",
        "fr": "Appliquer les règles de fusion", "ru": "Применить правила слияния",
    },
    "group_row_label": {
        "zh": "{tag}（{n} 处差异）", "en": "{tag} ({n} differences)",
        "es": "{tag} ({n} diferencias)", "fr": "{tag} ({n} différences)",
        "ru": "{tag} (отличий: {n})",
    },
    "status_group": {
        "zh": "分组", "en": "Group", "es": "Grupo", "fr": "Groupe", "ru": "Группа",
    },
    "status_mixed": {
        "zh": "混合", "en": "Mixed", "es": "Mixto", "fr": "Mixte", "ru": "Смешанный",
    },
    "detail_group_header": {
        "zh": "===== 分组：{tag}（{n} 处差异） =====\n\n"
              "展开此分组以查看每一处差异，或直接为整组设置来源。\n\n",
        "en": "===== Group: {tag} ({n} differences) =====\n\n"
              "Expand this group to see each difference, or set a source for the whole group.\n\n",
        "es": "===== Grupo: {tag} ({n} diferencias) =====\n\n"
              "Expanda este grupo para ver cada diferencia, o establezca un origen para todo el grupo.\n\n",
        "fr": "===== Groupe : {tag} ({n} différences) =====\n\n"
              "Développez ce groupe pour voir chaque différence, ou définissez une source pour tout le groupe.\n\n",
        "ru": "===== Группа: {tag} (отличий: {n}) =====\n\n"
              "Разверните группу, чтобы увидеть каждое отличие, либо задайте источник сразу для всей группы.\n\n",
    },
    "blocked_rule_msg": {
        "zh": "{n} 个节点仅因为子元素存在差异而显示为差异，无法直接设为规则（这样会替换整个子树）。"
              "请展开该节点为具体子元素设置规则，或使用“手动合并向导”逐个处理。",
        "en": "{n} node(s) only show as different because a child element differs, so they can't "
              "be turned directly into a rule (that would replace the whole subtree). "
              "Please expand the node to set a rule on the specific child, or use the "
              "\"Manual Merge Wizard\" to handle them one by one.",
        "es": "{n} nodo(s) solo muestran diferencia porque un elemento hijo difiere, por lo que no "
              "se pueden convertir directamente en una regla (reemplazaría todo el subárbol). "
              "Expanda el nodo para establecer una regla en el hijo específico, o use el "
              "\"Asistente de fusión manual\" para procesarlos uno por uno.",
        "fr": "{n} nœud(s) n'apparaissent en différence qu'à cause d'un élément enfant, ils ne "
              "peuvent donc pas devenir directement une règle (cela remplacerait tout le "
              "sous-arbre). Développez le nœud pour définir une règle sur l'enfant concerné, ou "
              "utilisez l'« Assistant de fusion manuelle » pour les traiter un par un.",
        "ru": "{n} узел(узлов) отмечены как отличающиеся только из-за дочернего элемента, "
              "поэтому их нельзя напрямую превратить в правило (это заменило бы всё поддерево). "
              "Разверните узел, чтобы задать правило для конкретного дочернего элемента, либо "
              "используйте «Мастер ручного слияния», чтобы обработать их по одному.",
    },

    # ManualMergeWizard
    "wizard_title": {
        "zh": "手动合并向导", "en": "Manual Merge Wizard", "es": "Asistente de fusión manual",
        "fr": "Assistant de fusion manuelle", "ru": "Мастер ручного слияния",
    },
    "wizard_pos_label": {
        "zh": "差异 {current} / {total}", "en": "Diff {current} / {total}",
        "es": "Diferencia {current} / {total}", "fr": "Différence {current} / {total}",
        "ru": "Отличие {current} / {total}",
    },
    "wizard_no_diffs": {
        "zh": "没有可手动处理的差异点。", "en": "No diff points to handle manually.",
        "es": "No hay diferencias para procesar manualmente.",
        "fr": "Aucune différence à traiter manuellement.",
        "ru": "Нет отличий для ручной обработки.",
    },
    "prev_shortcut": {
        "zh": "◀ 上一个 (←)", "en": "◀ Previous (←)", "es": "◀ Anterior (←)",
        "fr": "◀ Précédent (←)", "ru": "◀ Назад (←)",
    },
    "use_xml1_shortcut": {
        "zh": "使用 XML 1 (1)", "en": "Use XML 1 (1)", "es": "Usar XML 1 (1)",
        "fr": "Utiliser XML 1 (1)", "ru": "Использовать XML 1 (1)",
    },
    "use_xml2_shortcut": {
        "zh": "使用 XML 2 (2)", "en": "Use XML 2 (2)", "es": "Usar XML 2 (2)",
        "fr": "Utiliser XML 2 (2)", "ru": "Использовать XML 2 (2)",
    },
    "next_shortcut": {
        "zh": "下一个 (→)", "en": "Next (→)", "es": "Siguiente (→)", "fr": "Suivant (→)",
        "ru": "Далее (→)",
    },
    "finish_apply_button": {
        "zh": "完成并应用", "en": "Finish && Apply", "es": "Finalizar y aplicar",
        "fr": "Terminer et appliquer", "ru": "Готово и применить",
    },
    "cancel_wizard_button": {
        "zh": "取消向导", "en": "Cancel Wizard", "es": "Cancelar asistente",
        "fr": "Annuler l'assistant", "ru": "Отменить мастер",
    },
    "current_choice_label": {
        "zh": "当前选择：{source}", "en": "Current choice: {source}",
        "es": "Selección actual: {source}", "fr": "Choix actuel : {source}",
        "ru": "Текущий выбор: {source}",
    },
    "current_choice_unset": {
        "zh": "未指定（默认保持文件 1）", "en": "Not set (defaults to keeping File 1)",
        "es": "Sin especificar (por defecto mantiene el archivo 1)",
        "fr": "Non défini (conserve le fichier 1 par défaut)",
        "ru": "Не задано (по умолчанию сохраняется файл 1)",
    },
    "source_file1_xml1": {
        "zh": "文件 1 / XML 1", "en": "File 1 / XML 1", "es": "Archivo 1 / XML 1",
        "fr": "Fichier 1 / XML 1", "ru": "Файл 1 / XML 1",
    },
    "source_file2_xml2": {
        "zh": "文件 2 / XML 2", "en": "File 2 / XML 2", "es": "Archivo 2 / XML 2",
        "fr": "Fichier 2 / XML 2", "ru": "Файл 2 / XML 2",
    },
}

_CURRENT_LANGUAGE = DEFAULT_LANGUAGE


def detect_system_language():
    """
    Best-effort detection of the OS UI language, mapped to one of
    SUPPORTED_LANGUAGES. Falls back to DEFAULT_LANGUAGE if the system
    locale can't be read or isn't one of the five supported languages.
    """
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
        code = candidate.replace("-", "_").split(".")[0].split("_")[0].lower()
        if code in SUPPORTED_LANGUAGES:
            return code

    return DEFAULT_LANGUAGE


def set_language(code):
    global _CURRENT_LANGUAGE
    if code in SUPPORTED_LANGUAGES:
        _CURRENT_LANGUAGE = code


def get_language():
    return _CURRENT_LANGUAGE


def t(key, **kwargs):
    """Translate `key` into the current language, formatting placeholders
    (e.g. t('rule_count_label', n=3)). Falls back to English, then to the
    raw key, so a missing translation never crashes the UI."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    text = entry.get(_CURRENT_LANGUAGE) or entry.get(DEFAULT_LANGUAGE) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def state_label(kind):
    return t("state_" + kind) if kind else t("state_same")


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

COLOR_ADDED = "#d9f2d9"      # only exists in XML2 (git "added" green)
COLOR_REMOVED = "#f9d9d9"    # only exists in XML1 (git "removed" red)
COLOR_MODIFIED = "#fff2cc"   # exists in both, own attrs/text differ (yellow)
COLOR_CHANGED = "#dde8fb"    # exists in both, own content same, a descendant
                              # differs (light blue "contains changes")
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
    widget.tag_configure("added", background=COLOR_ADDED)
    widget.tag_configure("removed", background=COLOR_REMOVED)
    widget.tag_configure("modified", background=COLOR_MODIFIED)
    widget.tag_configure("changed", background=COLOR_CHANGED)


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
        self.root.geometry("1450x900")
        self.root.minsize(1100, 700)

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
        langbar = ttk.Frame(self.root, padding=(8, 6, 8, 0))
        langbar.pack(fill="x")

        self.lang_combo = ttk.Combobox(
            langbar,
            textvariable=self.lang_var,
            values=[LANGUAGE_NAMES[c] for c in SUPPORTED_LANGUAGES],
            state="readonly",
            width=12,
        )
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", self.on_language_change)

        ttk.Label(langbar, text=t("language_label")).pack(side="right", padx=(0, 5))

        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text=t("file1_label")).grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path1).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ttk.Button(top, text=t("choose_file_button"), command=self.choose1).grid(
            row=0, column=2
        )

        ttk.Label(top, text=t("file2_label")).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Entry(top, textvariable=self.path2).grid(
            row=1, column=1, sticky="ew", padx=5, pady=(6, 0)
        )
        ttk.Button(top, text=t("choose_file_button"), command=self.choose2).grid(
            row=1, column=2, pady=(6, 0)
        )

        top.columnconfigure(1, weight=1)

        bar = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        bar.pack(fill="x")

        ttk.Button(bar, text=t("load_compare_button"), command=self.load_compare).pack(
            side="left"
        )
        ttk.Button(
            bar, text=t("select_merge_button"), command=self.open_merge_selector
        ).pack(side="left", padx=5)

        ttk.Button(
            bar, text=t("manual_wizard_button"), command=self.open_manual_wizard
        ).pack(side="left", padx=5)

        ttk.Button(
            bar, text=t("clear_rules_button"), command=self.clear_rules
        ).pack(side="left", padx=5)

        ttk.Checkbutton(
            bar,
            text=t("only_diff_checkbox"),
            variable=self.only_diff,
            command=self.refresh_trees
        ).pack(side="left", padx=12)

        ttk.Button(
            bar, text=t("preview_button"), command=self.preview
        ).pack(side="right", padx=5)
        ttk.Button(
            bar, text=t("save_button"), command=self.save_result
        ).pack(side="right")

        self.rule_label = ttk.Label(bar, text=t("rule_count_label", n=len(self.rules)))
        self.rule_label.pack(side="right", padx=15)

        navbar = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        navbar.pack(fill="x")

        ttk.Button(
            navbar, text=t("prev_diff_button"), command=self.prev_diff
        ).pack(side="left")
        ttk.Button(
            navbar, text=t("next_diff_button"), command=self.next_diff
        ).pack(side="left", padx=5)

        current = self.nav_index + 1 if self.nav_index >= 0 else 0
        self.diff_pos_label = ttk.Label(
            navbar, text=t("diff_pos_label", current=current, total=len(self.nav_paths))
        )
        self.diff_pos_label.pack(side="left", padx=10)

        legend = ttk.Frame(navbar)
        legend.pack(side="right")
        for text, color in (
            (t("legend_added"), COLOR_ADDED),
            (t("legend_removed"), COLOR_REMOVED),
            (t("legend_modified"), COLOR_MODIFIED),
            (t("legend_changed"), COLOR_CHANGED),
        ):
            swatch = tk.Frame(legend, width=14, height=14, bg=color, relief="solid", borderwidth=1)
            swatch.pack(side="left", padx=(10, 3))
            swatch.pack_propagate(False)
            ttk.Label(legend, text=text).pack(side="left")

        pane = ttk.PanedWindow(self.root, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=8, pady=5)

        left = ttk.LabelFrame(pane, text=t("frame_file1"))
        right = ttk.LabelFrame(pane, text=t("frame_file2"))
        pane.add(left, weight=1)
        pane.add(right, weight=1)

        self.view1 = self.make_tree(left)
        self.view2 = self.make_tree(right)

        detail = ttk.LabelFrame(self.root, text=t("frame_detail"))
        detail.pack(fill="both", expand=False, padx=8, pady=(0, 8))

        self.detail = tk.Text(
            detail, height=12, wrap="none", font=("Consolas", 9)
        )
        dsy = ttk.Scrollbar(
            detail, orient="vertical", command=self.detail.yview
        )
        self.detail.configure(yscrollcommand=dsy.set)
        self.detail.pack(side="left", fill="both", expand=True)
        dsy.pack(side="right", fill="y")

        ttk.Label(
            self.root, textvariable=self.status, anchor="w"
        ).pack(fill="x", padx=8, pady=(0, 5))

    def make_tree(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            frame,
            columns=("path", "state", "rule"),
            show="tree headings",
            selectmode="browse"
        )
        tree.heading("#0", text=t("col_element"))
        tree.heading("path", text=t("col_path"))
        tree.heading("state", text=t("col_state"))
        tree.heading("rule", text=t("col_source"))

        tree.column("#0", width=260)
        tree.column("path", width=480)
        tree.column("state", width=100)
        tree.column("rule", width=100)

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

            tag = strip_namespace(elem.tag)
            kind = self.kinds.get(path, "same")
            state = state_label(kind)

            source = self.rules.get(path, "")
            source_text = (
                t("source_file1") if source == "xml1"
                else t("source_file2") if source == "xml2"
                else ""
            )

            # Flat tree with indentation encoded in display text. This avoids
            # recursively constructing thousands of Tk nodes at once.
            indent = "    " * max(0, depth - 1)
            widget.insert(
                "",
                "end",
                iid=path,
                text=indent + tag,
                values=(path, state, source_text),
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
        self.detail.insert("end", t("detail_path_header", path=path))

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
        win.geometry("1000x750")

        text = tk.Text(win, wrap="none", font=("Consolas", 9))
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
        self.window.geometry("1100x700")
        self.window.minsize(800, 500)
        self.window.transient(parent)
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
        top = ttk.Frame(self.window, padding=8)
        top.pack(fill="x")

        self.pos_label = ttk.Label(top, text="", font=("Arial", 11, "bold"))
        self.pos_label.pack(side="left")

        self.path_label = ttk.Label(top, text="", foreground="#555")
        self.path_label.pack(side="left", padx=12)

        main = ttk.PanedWindow(self.window, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=5)

        left = ttk.LabelFrame(main, text="XML 1")
        right = ttk.LabelFrame(main, text="XML 2")
        main.add(left, weight=1)
        main.add(right, weight=1)

        self.text1 = tk.Text(left, wrap="none", font=("Consolas", 9))
        self.text2 = tk.Text(right, wrap="none", font=("Consolas", 9))
        self.text1.pack(fill="both", expand=True)
        self.text2.pack(fill="both", expand=True)

        self.choice_label = ttk.Label(
            self.window, text=t("current_choice_label", source=t("current_choice_unset")),
            font=("Arial", 10, "bold")
        )
        self.choice_label.pack(fill="x", padx=8, pady=(0, 4))

        bottom = ttk.Frame(self.window, padding=8)
        bottom.pack(fill="x")

        ttk.Button(bottom, text=t("prev_shortcut"), command=self.go_prev).pack(side="left")
        ttk.Button(
            bottom, text=t("use_xml1_shortcut"), command=lambda: self.choose("xml1")
        ).pack(side="left", padx=5)
        ttk.Button(
            bottom, text=t("use_xml2_shortcut"), command=lambda: self.choose("xml2")
        ).pack(side="left", padx=5)
        ttk.Button(
            bottom, text=t("clear_source_button"), command=lambda: self.choose(None)
        ).pack(side="left", padx=5)
        ttk.Button(bottom, text=t("next_shortcut"), command=self.go_next).pack(side="left", padx=5)

        ttk.Button(bottom, text=t("finish_apply_button"), command=self.finish).pack(side="right")
        ttk.Button(bottom, text=t("cancel_wizard_button"), command=self.cancel).pack(side="right", padx=5)

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
        self.window.geometry("1300x820")
        self.window.minsize(1000, 650)
        self.window.transient(parent)
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
        top = ttk.Frame(self.window, padding=8)
        top.pack(fill="x")

        ttk.Label(
            top,
            text=t("merge_selector_instruction"),
            font=("Arial", 10, "bold")
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
            top, text=t("select_all_diff_button"), command=self.select_diff
        ).pack(side="right", padx=5)

        ttk.Button(
            top, text=t("clear_selection_button"), command=lambda: self.tree.selection_set(())
        ).pack(side="right")

        main = ttk.PanedWindow(self.window, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=5)

        left = ttk.Frame(main)
        right = ttk.LabelFrame(main, text=t("panel_node_compare"))
        main.add(left, weight=3)
        main.add(right, weight=2)

        self.tree = ttk.Treeview(
            left,
            columns=("path", "status", "source"),
            show="tree headings",
            selectmode="extended"
        )
        self.tree.heading("#0", text=t("col_element"))
        self.tree.heading("path", text=t("col_path"))
        self.tree.heading("status", text=t("col_state"))
        self.tree.heading("source", text=t("col_source"))

        self.tree.column("#0", width=260)
        self.tree.column("path", width=500)
        self.tree.column("status", width=100)
        self.tree.column("source", width=100)

        sy = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(left, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")

        configure_diff_tags(self.tree)
        self.tree.tag_configure("group", font=("Arial", 9, "bold"))
        self.tree.bind("<<TreeviewSelect>>", self.show_selected)

        self.detail = tk.Text(right, wrap="none", font=("Consolas", 9))
        dsy = ttk.Scrollbar(right, orient="vertical", command=self.detail.yview)
        self.detail.configure(yscrollcommand=dsy.set)
        self.detail.pack(side="left", fill="both", expand=True)
        dsy.pack(side="right", fill="y")

        bottom = ttk.Frame(self.window, padding=8)
        bottom.pack(fill="x")

        ttk.Label(bottom, text=t("label_set_selected")).pack(side="left")

        ttk.Button(
            bottom, text=t("use_xml1_button"),
            command=lambda: self.apply_source("xml1")
        ).pack(side="left", padx=5)

        ttk.Button(
            bottom, text=t("use_xml2_button"),
            command=lambda: self.apply_source("xml2")
        ).pack(side="left", padx=5)

        ttk.Button(
            bottom, text=t("clear_source_button"),
            command=self.clear_source
        ).pack(side="left", padx=5)

        ttk.Button(
            bottom, text=t("all_xml1_button"),
            command=lambda: self.set_all("xml1")
        ).pack(side="right", padx=5)

        ttk.Button(
            bottom, text=t("all_xml2_button"),
            command=lambda: self.set_all("xml2")
        ).pack(side="right", padx=5)

        ttk.Button(
            bottom, text=t("cancel_button"),
            command=self.cancel
        ).pack(side="right", padx=5)

        ttk.Button(
            bottom, text=t("apply_rules_button"),
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
                values=("", t("status_group"), group_source_text),
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
                self.tree.insert(
                    group_iid, "end", iid=path,
                    text=tag,
                    values=(path, state_label(kind), source_text),
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
            tag = strip_namespace(elem.tag)
            kind = self.kinds.get(path, "same")

            source = self.rules.get(path, "")
            source_text = (
                t("source_file1") if source == "xml1"
                else t("source_file2") if source == "xml2"
                else ""
            )

            self.tree.insert(
                "", "end", iid=path,
                text=tag,
                values=(path, state_label(kind), source_text),
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
                self.detail.insert("end", "· %s  [%s]\n" % (path, state_label(kind)))
            return

        path = iid
        a, b = resolve_diff_nodes(path, self.index1, self.index2, self.value_pairs)

        self.detail.insert("end", t("detail_path_header", path=path))
        self.detail.insert("end", "===== XML 1 =====\n")
        self.detail.insert(
            "end", t("not_exist") + "\n" if a is None else pretty_xml(a)
        )
        self.detail.insert("end", "\n===== XML 2 =====\n")
        self.detail.insert(
            "end", t("not_exist") + "\n" if b is None else pretty_xml(b)
        )

    def finish(self):
        self.result = dict(self.rules)
        self.window.destroy()

    def cancel(self):
        self.result = None
        self.window.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
