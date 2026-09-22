# -*- coding: utf-8 -*-
"""终端表格与 CSV 导出。"""
import csv


def print_table(rows, columns):
    """打印对齐的终端表格。columns 为 [(列名, 取值函数或字段名), ...]"""
    if not rows:
        print("（无数据）")
        return
    headers = [c[0] for c in columns]
    cells = []
    for r in rows:
        cells.append([_cell(r, c[1]) for c in columns])
    widths = [max(len(h), max((len(cell[i]) for cell in cells), default=0)) for i, h in enumerate(headers)]
    line = "+".join("-" * (w + 2) for w in widths)
    print(line)
    print("| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |")
    print(line)
    for cell in cells:
        print("| " + " | ".join(cell[i].ljust(widths[i]) for i in range(len(headers))) + " |")
    print(line)


def _cell(row, spec):
    """取单元格值并转字符串；spec 为字段名或函数。"""
    if callable(spec):
        v = spec(row)
    else:
        v = row.get(spec)
    if v is None:
        return "-"
    s = str(v)
    return s if len(s) <= 90 else s[:87] + "..."


def export_csv(path, rows, columns, quote_all=False):
    """导出 CSV（UTF-8 with BOM，Excel 可直接打开）。
    防公式注入：以 = + - @ 开头的单元格加单引号前缀。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([c[0] for c in columns])
        for r in rows:
            writer.writerow([_sanitize(_cell(r, c[1])) for c in columns])


def _sanitize(s):
    if s and s[0] in "=+-@":
        return "'" + s
    return s
