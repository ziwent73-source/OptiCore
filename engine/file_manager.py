"""
FileManager — CSV 导出 + 表格格式化

将计算结果导出为 outdata.csv 风格的长表格式：
列：参数 | 波长 | 视场 | 孔径 | 数值
"""

import csv
import io
import re as _re
from typing import Dict, Callable


# ═══════════════════════════════════════════════════════════
# 参数名 → 中文显示名 映射表
# ═══════════════════════════════════════════════════════════

_PARAM_TEMPLATES: Dict[str, str] = {
    "f_prime":               "像方焦距 f' (mm)",
    "l_prime":               "像方截距 l' (mm)",
    "lH_prime":              "后主面位置 lH' (mm)",
    "lp_prime":              "出瞳位置 lp' (mm)",
    "y0_prime":              "0 视场近轴像高 y0' (mm)",
    "y07_prime":             "{fld} 视场近轴像高 y{fld}' (mm)",
    "y_full_prime":          "{fld} 视场近轴像高 y_full' (mm)",
    "xt_prime":              "子午场曲 xt' (mm)",
    "xs_prime":              "弧矢场曲 xs' (mm)",
    "delta_xts":             "像散 Δxts' (mm)",
    "lF_prime":              "F 光近轴像位置 lF' (mm)",
    "lC_prime":              "C 光近轴像位置 lC' (mm)",
    "axial_image_{apt}_d":   "{apt} 孔径 d 光实际像点 (mm)",
    "axial_image_{apt}_F":   "{apt} 孔径 F 光实际像点 (mm)",
    "axial_image_{apt}_C":   "{apt} 孔径 C 光实际像点 (mm)",
    "spherical_aberration_{apt}": "{apt} 孔径球差 δL' (mm)",
    "axial_chromatic_{apt}": "{apt} 孔径位置色差 Δl'FC (mm)",
    "meridional_coma_{fld}_{apt}": "{fld} 视场 · {apt} 孔径 子午彗差 K' (mm)",
    "image_height_{fld}_d": "{fld} 视场 d 光实际像高 (mm)",
    "image_height_{fld}_F": "{fld} 视场 F 光实际像高 (mm)",
    "image_height_{fld}_C": "{fld} 视场 C 光实际像高 (mm)",
    "absolute_distortion_{fld}": "{fld} 视场绝对畸变 δy' (mm)",
    "relative_distortion_{fld}": "{fld} 视场相对畸变 (%)",
    "lateral_chromatic_{fld}": "{fld} 视场倍率色差 Δy'FC (mm)",
}

PARAM_CN: Dict[str, str] = {
    "f_prime": "像方焦距 f' (mm)",
    "l_prime": "像方截距 l' (mm)",
    "lH_prime": "后主面位置 lH' (mm)",
    "lp_prime": "出瞳位置 lp' (mm)",
    "y0_prime": "0 视场近轴像高 y0' (mm)",
    "y07_prime": "0.7 视场近轴像高 y0.7' (mm)",
    "y_full_prime": "全视场近轴像高 y_full' (mm)",
    "xt_prime": "子午场曲 xt' (mm)",
    "xs_prime": "弧矢场曲 xs' (mm)",
    "delta_xts": "像散 Δxts' (mm)",
    "lF_prime": "F 光近轴像位置 lF' (mm)",
    "lC_prime": "C 光近轴像位置 lC' (mm)",
    "axial_image_full_d": "全孔径 d 光实际像点 (mm)",
    "axial_image_full_F": "全孔径 F 光实际像点 (mm)",
    "axial_image_full_C": "全孔径 C 光实际像点 (mm)",
    "axial_image_0.7_d": "0.7 孔径 d 光实际像点 (mm)",
    "axial_image_0.7_F": "0.7 孔径 F 光实际像点 (mm)",
    "axial_image_0.7_C": "0.7 孔径 C 光实际像点 (mm)",
    "spherical_aberration_full": "全孔径球差 δL' (mm)",
    "spherical_aberration_0.7": "0.7 孔径球差 δL' (mm)",
    "axial_chromatic_full": "全孔径位置色差 Δl'FC (mm)",
    "axial_chromatic_0.7": "0.7 孔径位置色差 Δl'FC (mm)",
    "axial_chromatic_0": "0 孔径位置色差 Δl'FC (mm)",
    "meridional_coma_full_field_full_apt": "全视场·全孔径 子午彗差 K' (mm)",
    "meridional_coma_full_field_0.7_apt": "全视场·0.7 孔径 子午彗差 K' (mm)",
    "meridional_coma_0.7_field_full_apt": "0.7 视场·全孔径 子午彗差 K' (mm)",
    "meridional_coma_0.7_field_0.7_apt": "0.7 视场·0.7 孔径 子午彗差 K' (mm)",
    "image_height_full_field_d": "全视场 d 光实际像高 (mm)",
    "image_height_full_field_F": "全视场 F 光实际像高 (mm)",
    "image_height_full_field_C": "全视场 C 光实际像高 (mm)",
    "image_height_0.7_field_d": "0.7 视场 d 光实际像高 (mm)",
    "image_height_0.7_field_F": "0.7 视场 F 光实际像高 (mm)",
    "image_height_0.7_field_C": "0.7 视场 C 光实际像高 (mm)",
    "absolute_distortion_full_field": "全视场绝对畸变 δy' (mm)",
    "absolute_distortion_0.7_field": "0.7 视场绝对畸变 δy' (mm)",
    "relative_distortion_full_field": "全视场相对畸变 (%)",
    "relative_distortion_0.7_field": "0.7 视场相对畸变 (%)",
    "lateral_chromatic_full_field": "全视场倍率色差 Δy'FC (mm)",
    "lateral_chromatic_0.7_field": "0.7 视场倍率色差 Δy'FC (mm)",
}

# 旧排序列表（保留兼容）
DISPLAY_ORDER: list[str] = [
    "f_prime", "l_prime", "lC_prime", "lF_prime",
    "axial_image_full_d", "axial_image_0.7_d",
    "axial_image_full_C", "axial_image_0.7_C",
    "axial_image_full_F", "axial_image_0.7_F",
    "lH_prime", "lp_prime",
    "y0_prime", "y_full_prime", "y07_prime",
    "spherical_aberration_0.7", "spherical_aberration_full",
    "axial_chromatic_0.7", "axial_chromatic_full", "axial_chromatic_0",
    "xt_prime", "xs_prime", "delta_xts",
    "image_height_0.7_field_F", "image_height_full_field_F",
    "image_height_0.7_field_d", "image_height_full_field_d",
    "image_height_0.7_field_C", "image_height_full_field_C",
    "relative_distortion_0.7_field", "relative_distortion_full_field",
    "absolute_distortion_0.7_field", "absolute_distortion_full_field",
    "lateral_chromatic_0.7_field", "lateral_chromatic_full_field",
    "meridional_coma_0.7_field_0.7_apt", "meridional_coma_0.7_field_full_apt",
    "meridional_coma_full_field_0.7_apt", "meridional_coma_full_field_full_apt",
]

_PARA_KEYWORDS = {
    "f_prime", "l_prime", "lF_prime", "lC_prime", "lH_prime", "lp_prime",
    "y0_prime", "y07_prime", "y_full_prime",
}


def _sort_key(param_name: str) -> tuple:
    try:
        idx = DISPLAY_ORDER.index(param_name)
        return (idx // 100, param_name)
    except ValueError:
        pass
    if param_name in _PARA_KEYWORDS:
        return (0, param_name)
    if param_name in {"xt_prime", "xs_prime", "delta_xts"}:
        return (1, param_name)
    if param_name.startswith("axial_image_"):
        return (2, param_name)
    if param_name.startswith("spherical_aberration_"):
        return (3, param_name)
    if param_name.startswith("axial_chromatic_"):
        return (4, param_name)
    if param_name.startswith("image_height_"):
        return (5, param_name)
    if param_name.startswith("absolute_distortion_") or param_name.startswith("relative_distortion_"):
        return (6, param_name)
    if param_name.startswith("lateral_chromatic_"):
        return (7, param_name)
    if param_name.startswith("meridional_coma_"):
        return (8, param_name)
    return (9, param_name)


# ═══════════════════════════════════════════════════════════
# Zemax 参考值（保留兼容）
# ═══════════════════════════════════════════════════════════

ZEMAX_REFERENCE: dict = {}

CATEGORY_CN = {"Paraxial": "近轴参数", "Axial": "轴上像差", "Field": "视场像差"}


def _cn(key: str) -> str:
    if key in PARAM_CN:
        return PARAM_CN[key]
    for tmpl, name_tmpl in _PARAM_TEMPLATES.items():
        pattern = _re.escape(tmpl)
        pattern = pattern.replace(r"\{apt\}", r"(full|0|\d+\.\d+)")
        pattern = pattern.replace(r"\{fld\}", r"(full_field|\d+\.\d+_field)")
        m = _re.fullmatch(pattern, key)
        if m:
            groups = m.groups()
            name = name_tmpl
            for g in groups:
                if g in ("full", "1.0"):
                    name = name.replace("{apt}", "全", 1) if "{apt}" in name else name.replace("{apt}", "全孔径", 1)
                elif g == "full_field":
                    name = name.replace("{fld}", "全视场", 1)
                elif "_field" in g:
                    label = g.replace("_field", "")
                    name = name.replace("{fld}", label + " 视场", 1)
                else:
                    name = name.replace("{apt}", g + " 孔径", 1) if "{apt}" in name else name.replace("{fld}", g, 1)
            name = name.replace("{apt}", "?").replace("{fld}", "?")
            return name
    return key


# ═══════════════════════════════════════════════════════════
# Key → Row 解析器（outdata.csv 长表格式）
# ═══════════════════════════════════════════════════════════

def _key_to_row(key: str, value: float) -> dict | None:
    """将结果 key 解析为 (参数, 波长, 视场, 孔径, 数值) 行"""
    row = {"参数": "", "波长": "", "视场": "", "孔径": "", "数值": value}

    # ── 焦距 f' ──
    if key == "f_prime":
        row.update({"参数": "焦距f'", "波长": "d"})
        return row

    # ── 理想像距 l' ──
    if key in ("l_prime", "lF_prime", "lC_prime"):
        wl = {"l_prime": "d", "lF_prime": "F", "lC_prime": "C"}[key]
        row.update({"参数": "理想像距l'（以透镜最后一面为参考）", "波长": wl, "视场": "0", "孔径": "0"})
        return row

    # ── 实际像位置 ──
    m = _re.match(r"axial_image_(full|[0-9.]+)_([dFC])", key)
    if m:
        apt = "1" if m.group(1) == "full" else m.group(1)
        row.update({"参数": "实际像位置（以透镜最后一面为参考）", "波长": m.group(2), "视场": "0", "孔径": apt})
        return row

    # ── 像方主面位置 ──
    if key == "lH_prime":
        row.update({"参数": "像方主面位置lH'（以透镜最后一面为参考）", "波长": "d"})
        return row

    # ── 出瞳距 ──
    if key == "lp_prime":
        row.update({"参数": "出瞳距lp'（以透镜最后一面为参考）", "波长": "d"})
        return row

    # ── 理想像高 y' ──
    if key in ("y0_prime", "y07_prime", "y_full_prime"):
        fld = {"y0_prime": "0", "y07_prime": "0.7", "y_full_prime": "1"}[key]
        row.update({"参数": "理想像高y0'", "波长": "d", "视场": fld, "孔径": "0"})
        return row

    # ── 球差 ──
    m = _re.match(r"spherical_aberration_(full|[0-9.]+)", key)
    if m:
        apt = "1" if m.group(1) == "full" else m.group(1)
        row.update({"参数": "球差", "波长": "d", "视场": "0", "孔径": apt})
        return row

    # ── 位置色差 ──
    m = _re.match(r"axial_chromatic_(full|0|[0-9.]+)", key)
    if m:
        apt = "1" if m.group(1) == "full" else m.group(1)
        row.update({"参数": "位置色差", "波长": "F-C", "视场": "0", "孔径": apt})
        return row

    # ── 场曲 / 像散 ──
    if key in ("xt_prime", "xs_prime", "delta_xts"):
        name = {"xt_prime": "子午场曲xt'", "xs_prime": "弧矢场曲xs'",
                "delta_xts": "像散Δxts'"}[key]
        row.update({"参数": name, "波长": "d", "视场": "1", "孔径": "0"})
        return row

    # ── 实际像高 ──
    m = _re.match(r"image_height_(full_field|[0-9.]+_field)_([dFC])", key)
    if m:
        fld = "1" if m.group(1) == "full_field" else m.group(1).replace("_field", "")
        row.update({"参数": "实际像高", "波长": m.group(2), "视场": fld, "孔径": "0"})
        return row

    # ── 畸变 ──
    m = _re.match(r"(absolute|relative)_distortion_(full_field|[0-9.]+_field)", key)
    if m:
        fld = "1" if m.group(2) == "full_field" else m.group(2).replace("_field", "")
        name = "绝对畸变" if m.group(1) == "absolute" else "相对畸变"
        row.update({"参数": name, "波长": "d", "视场": fld})
        return row

    # ── 倍率色差 ──
    m = _re.match(r"lateral_chromatic_(full_field|[0-9.]+_field)", key)
    if m:
        fld = "1" if m.group(1) == "full_field" else m.group(1).replace("_field", "")
        row.update({"参数": "倍率色差", "波长": "F-C", "视场": fld, "孔径": "0"})
        return row

    # ── 子午慧差 ──
    m = _re.match(r"meridional_coma_(full_field|[0-9.]+_field)_(full|[0-9.]+)_apt", key)
    if m:
        fld = "1" if m.group(1) == "full_field" else m.group(1).replace("_field", "")
        apt = "1" if m.group(2) == "full" else m.group(2)
        row.update({"参数": "子午慧差（不考虑符号，绝对值正确即可）",
                     "波长": "d", "视场": fld, "孔径": apt})
        return row

    # ── 未知 key ──
    row["参数"] = _cn(key)
    return row


# 参数分组排序权重
_PARAM_ORDER = [
    "焦距f'",
    "理想像距l'",
    "实际像位置",
    "像方主面位置lH'",
    "出瞳距lp'",
    "理想像高y0'",
    "球差",
    "位置色差",
    "子午场曲xt'",
    "弧矢场曲xs'",
    "像散Δxts'",
    "实际像高",
    "相对畸变",
    "绝对畸变",
    "倍率色差",
    "子午慧差",
]


def _row_sort_key(row: dict) -> tuple:
    """行排序：按参数分组，组内按波长→视场→孔径"""
    param = row.get("参数", "")
    g = 99
    for i, p in enumerate(_PARAM_ORDER):
        if param.startswith(p) or p.startswith(param.split("（")[0].split("(")[0].rstrip("'")):
            g = i
            break
    wl_order = {"d": 0, "F": 1, "C": 2, "F-C": 3}
    wl = wl_order.get(row.get("波长", ""), 99)

    def _f(s):
        try:
            return float(s) if s else -1
        except ValueError:
            return -1

    return (g, wl, _f(row.get("视场", "")), _f(row.get("孔径", "")))


# ═══════════════════════════════════════════════════════════
# 配置匹配（过滤用）
# ═══════════════════════════════════════════════════════════

def _key_matches_config(key: str, lens_config: dict | None) -> bool:
    """检查 key 是否匹配 lens 配置（同时校验孔径和视场）"""
    if lens_config is None:
        return True
    pup_fracs = lens_config.get("pupil_fractions", [0.0, 0.7, 1.0])
    fld_fracs = lens_config.get("field_fractions", [0.0, 0.7, 1.0])

    # 彗差：同时含视场和孔径
    m = _re.search(r"_((?:full|[0-9.]+)_field)_((?:full|[0-9.]+)_apt)$", key)
    if m:
        fld_val = 1.0 if m.group(1) == "full_field" else float(m.group(1).replace("_field", ""))
        apt_val = 1.0 if m.group(2) == "full_apt" else float(m.group(2).replace("_apt", ""))
        return (any(abs(fld_val - f) < 0.001 for f in fld_fracs) and
                any(abs(apt_val - f) < 0.001 for f in pup_fracs))

    # 轴上像差
    m = _re.search(r"_(?:axial_image|spherical_aberration|axial_chromatic)_([0-9.]+|full)(?:_|$)", key)
    if m:
        apt_val = 1.0 if m.group(1) == "full" else float(m.group(1))
        return any(abs(apt_val - f) < 0.001 for f in pup_fracs)

    # 视场相关
    m = _re.search(r"_(full_field|[0-9.]+_field)(?:_|$)", key)
    if m:
        fld_val = 1.0 if m.group(1) == "full_field" else float(m.group(1).replace("_field", ""))
        return any(abs(fld_val - f) < 0.001 for f in fld_fracs)

    return True


# ═══════════════════════════════════════════════════════════
# 构建输出行
# ═══════════════════════════════════════════════════════════

def _build_output_rows(results: Dict, lens_config: dict | None = None) -> list[dict]:
    """从 results flat dict 构建 outdata.csv 风格的行列表"""
    rows = []
    for key, value in sorted(results.items()):
        if not isinstance(value, (int, float)):
            continue
        if value is None:
            continue
        if lens_config and not _key_matches_config(key, lens_config):
            continue
        row = _key_to_row(key, value)
        if row:
            rows.append(row)

    rows.sort(key=_row_sort_key)

    # 合并参数列：同一参数组的后续行留空
    prev_param = None
    for r in rows:
        if r["参数"] == prev_param:
            r["参数"] = ""
        else:
            prev_param = r["参数"]

    return rows


# ═══════════════════════════════════════════════════════════
# CSV 导出（outdata.csv 长表格式）
# ═══════════════════════════════════════════════════════════

def export_to_csv(results: Dict, metadata: Dict | None = None,
                  lens_config: dict | None = None) -> str:
    """
    导出为 outdata.csv 风格的长表 CSV。

    列：参数 | 波长 | 视场 | 孔径 | 数值
    """
    output = io.StringIO()
    writer = csv.writer(output)

    if metadata:
        writer.writerow(["# OptiCore 计算结果"])
        for mk, mv in metadata.items():
            writer.writerow([f"# {mk}", str(mv)])
        writer.writerow([])

    writer.writerow(["参数", "波长", "视场", "孔径", "数值"])

    rows = _build_output_rows(results, lens_config)
    for r in rows:
        val_str = f"{r['数值']:.8f}" if isinstance(r['数值'], float) else str(r['数值'])
        writer.writerow([r["参数"], r["波长"], r["视场"], r["孔径"], val_str])

    return output.getvalue()


def save_csv(results: Dict, filepath: str, metadata: Dict | None = None,
             lens_config: dict | None = None) -> None:
    """保存 CSV 到磁盘"""
    csv_content = export_to_csv(results, metadata=metadata, lens_config=lens_config)
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(csv_content)


# ═══════════════════════════════════════════════════════════
# 向后兼容
# ═══════════════════════════════════════════════════════════

def format_as_tables(results: Dict, object_distance: str = "infinite") -> Dict[str, list]:
    """向后兼容（已弃用）"""
    return {"近轴参数": [], "轴上像差": [], "视场像差": []}


def _classify_key(key: str) -> str:
    if key in _PARA_KEYWORDS or key in {"xt_prime", "xs_prime", "delta_xts"}:
        return "Paraxial"
    if key.startswith("axial_image_") or key.startswith("spherical_aberration_") or key.startswith("axial_chromatic_"):
        return "Axial"
    return "Field"


# ═══════════════════════════════════════════════════════════
# Streamlit 分表格展示
# ═══════════════════════════════════════════════════════════

def format_detailed_tables(results: Dict,
                            lens_config: dict | None = None) -> list[dict]:
    """
    返回按参数分组的表格列表，行格式按 outdata.csv 风格：
    (参数, 波长, 视场, 孔径, 数值)

    同一参数组的后续行参数列留空（模拟合并单元格）。
    """
    rows = _build_output_rows(results, lens_config)

    # ── 按参数分组 ──
    groups: list[dict] = []
    current_param = None
    current_rows = []

    for r in rows:
        param_full = r["参数"]
        if param_full:
            if current_rows:
                groups.append({"title": current_param or "", "formula": "", "rows": current_rows})
            current_param = param_full
            current_rows = [dict(r)]
        else:
            current_rows.append(dict(r))

    if current_rows:
        groups.append({"title": current_param or "", "formula": "", "rows": current_rows})

    return groups
