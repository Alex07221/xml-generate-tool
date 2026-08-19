# XMLCompareMerge

A modern desktop application for visually comparing and merging XML files. Built with Python and Tkinter, designed for non-developers who need a simple, intuitive tool to spot differences between XML files and selectively merge values.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

### Visual Side-by-Side Comparison
- Displays the **full XML content** in a collapsible tree view — not just the differences
- Each element is shown as raw XML text (e.g. `<test>1</test>`), making it easy to understand at a glance
- Color-coded rows instantly tell you what changed:
  - **Green** — Element exists only in File 1 (added)
  - **Red** — Element exists only in File 2 (removed)
  - **Yellow** — Element structure differs between files
  - **Blue** — Element value differs between files

### Smart Diff Navigation
- **Previous / Next** buttons jump directly between differences
- Parent nodes auto-expand when navigating to a deeply nested change
- Collapsible tree lets you focus on the parts that matter

### Flexible Merge Rules
- **Per-element**: Right-click any row to choose which file's value to keep
- **Bulk by group**: Select multiple elements and apply a rule in one click
- **Clear all**: Reset all rules instantly
- Apply rules to produce a merged output file

### 16 Built-in Languages
The interface automatically detects your system language on first launch. You can also switch manually at any time:

| Language | Code | Language | Code |
|----------|------|----------|------|
| English | en | French | fr |
| Chinese | zh | Russian | ru |
| Spanish | es | Portuguese | pt |
| Hindi | hi | Indonesian | id |
| Arabic | ar | German | de |
| Bengali | bn | Japanese | ja |
| Urdu | ur | Korean | ko |
| Italian | it | Turkish | tr |

### Modern Desktop UI
- Clean, card-based layout with a Slate/Blue color scheme
- High-contrast buttons designed for readability (no more gray-on-white)
- Responsive window with sensible default sizing
- Built-in preview dialog before saving merged results

## Getting Started

### Option 1: Download the Standalone Package (Recommended)

1. Go to the [Releases page](https://github.com/Alex07221/xml-generate-tool/releases)
2. Download `XMLCompareMerge-v1.0.0-windows.zip`
3. Extract the zip file to any folder
4. Double-click `XMLCompareMerge.exe` to run — no installation needed

### Option 2: Run from Source

**Prerequisites**: Python 3.8+

```bash
git clone https://github.com/Alex07221/xml-generate-tool.git
cd xml-generate-tool
python xml_merge_tool_v2.py
```

## Usage Guide

### 1. Load Files
- Click **Browse** next to "File 1" and "File 2" to select the two XML files you want to compare
- Click **Compare** to run the diff

### 2. Review Differences
- The side-by-side tree view shows both files with color-coded differences
- Use **Previous** and **Next** to jump between changes
- Click any row to see details in the bottom panel

### 3. Set Merge Rules
- The "Source" column shows which file's value will be kept (File 1 or File 2)
- Click **Select All → File 1** or **Select All → File 2** for bulk rules
- Use the merge rule dialog for granular per-element control

### 4. Preview and Save
- Click **Preview** to review the merged result before saving
- Click **Save** to write the merged XML file

## Project Structure

```
xml-generate/
├── xml_merge_tool_v2.py       # Main application (GUI + merge logic)
├── i18n/
│   ├── __init__.py            # i18n module (language loading, switching, translation)
│   └── translations/
│       ├── en.json            # English (default)
│       ├── zh.json            # Chinese
│       └── ... (16 languages total)
├── test_diff_logic.py         # Unit tests for diff engine (27 tests)
├── test_e2e_merge.py          # End-to-end merge tests (19 tests)
└── test_i18n_module.py        # i18n module tests (85 tests)
```

## Building from Source

To create a standalone Windows executable:

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name "XMLCompareMerge" xml_merge_tool_v2.py
```

Then copy the `i18n/translations/` folder alongside the built `XMLCompareMerge.exe`:

```
XMLCompareMerge/
├── XMLCompareMerge.exe
├── i18n/
│   └── translations/
│       └── *.json
└── _internal/
```

## Testing

```bash
python test_diff_logic.py      # Diff engine unit tests
python test_e2e_merge.py       # End-to-end merge tests
python test_i18n_module.py     # i18n module tests
```

All 131 tests must pass before any commit.

## Tech Stack

- **Python 3** — Core runtime
- **Tkinter / ttk** — GUI framework
- **xml.etree.ElementTree** — XML parsing
- **PyInstaller** — Standalone packaging
- **Custom i18n module** — JSON-based translations with 16 languages

## License

MIT License — feel free to use, modify, and distribute.
