"""
OptiCore — 共轴球面光学系统计算工具
Streamlit Web 界面

运行: python -m streamlit run app.py
"""

import json
import math
import os
import shutil
import sys
import streamlit as st
import numpy as np

from engine.data_model import Lens, Surface
from engine.aberration import compute_system
from engine.file_manager import export_to_csv, format_detailed_tables
from engine.ray_generator import generate_rays
from engine.ray_tracer import trace_single_ray

# ═══════════════════════════════════════════════════════════
# 全局精度设置（Change_1.md 第四章要求 8 位小数）
# ═══════════════════════════════════════════════════════════
np.set_printoptions(precision=8, suppress=True)
try:
    import pandas as pd
    pd.set_option('display.precision', 8)
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════
# 波长配置：始终使用 d, F, C 三波长，不做变量选择
# ═══════════════════════════════════════════════════════════
FIXED_WAVELENGTHS = ["d", "F", "C"]

WL_DISPLAY = {
    "d": "d 光 (587.6nm, 氦黄线)",
    "F": "F 光 (486.1nm, 氢蓝线)",
    "C": "C 光 (656.3nm, 氢红线)",
}

# ═══════════════════════════════════════════════════════════
# 示例镜头（v2.0 格式）
# ═══════════════════════════════════════════════════════════
DEMO_LENS_DICT = {
    "_comment": "OptiCore 示例镜头 — 单透镜 f'≈45mm",
    "name": "Demo Singlet — f'~45mm",
    "system_parameters": {
        "object_distance": None,
        "entrance_pupil_radius": 10.0,
        "aperture_stop_index": 0,
        "max_field_height": 18.0,
    },
    "calculation_settings": {
        "field_mode": "image_height",
        "field_value": 18.0,
        "aperture_angle_deg": 5.0,
        "field_fractions": [0.7],
        "pupil_fractions": [0.7],
    },
    "surfaces": [
        {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
        {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0},
    ],
    "glass_library": "CDGM-ZEMAX202111.AGF",
}

# ═══════════════════════════════════════════════════════════
# JSON 配置模板（含中文注释）
# ═══════════════════════════════════════════════════════════
TEMPLATE_JSON = json.dumps({
    "_comment": "OptiCore 计算配置文件模板 — 请根据实际镜头数据修改",
    "name": "请输入镜头名称，如：双胶合消色差镜头",
    "system_parameters": {
        "_comment": "系统物理参数",
        "object_distance": None,
        "_comment_object_distance": "物距(mm)，null/inf=无限远，正数=有限距(实物在左为负时取绝对值)",
        "entrance_pupil_radius": 10.0,
        "_comment_entrance_pupil_radius": "入瞳半径(mm)，必填",
        "aperture_stop_index": 0,
        "_comment_aperture_stop_index": "光阑所在面索引，0表示第一面",
        "max_field_height": 12.0,
        "_comment_max_field_height": "最大视场像高(mm)，全画幅取12",
    },
    "calculation_settings": {
        "_comment": "本次计算的选择（波长固定为 d, F, C 三光全选，无需配置）",
        "field_fractions": [0.7],
        "_comment_field_fractions": "需计算的中间视场分数，0(轴上)和1(全视场)自动补全",
        "field_mode": "image_height",
        "_comment_field_mode": "视场输入模式：angle(度) / object_height(mm) / image_height(mm)",
        "field_value": 12.0,
        "_comment_field_value": "视场数值，与 field_mode 对应",
        "aperture_angle_deg": 5.0,
        "_comment_aperture_angle": "孔径角(度)，程序自动换算入瞳半径",
        "pupil_fractions": [0.7],
        "_comment_pupil_fractions": "需计算的中间孔径分数，0(主光线)和1(全孔径)自动补全",
    },
    "surfaces": [
        {
            "_comment": "按顺序填写每个光学面，从第一面到像面",
            "radius": 42.0,
            "_comment_radius": "曲率半径(mm)，凸面(R>0)为正值，凹面(R<0)为负值",
            "thickness": 6.0,
            "_comment_thickness": "到下一面的厚度(mm)，最后一面填像面距离",
            "glass": "H-K9L",
            "_comment_glass": "玻璃名称，如 H-K9L、H-ZF2、Air",
            "diameter": 25.0,
            "_comment_diameter": "通光半口径(mm)",
        },
        {
            "radius": -50.0,
            "thickness": 42.0,
            "glass": "Air",
            "diameter": 25.0,
        },
    ],
    "glass_library": "CDGM-ZEMAX202111.AGF",
    "_comment_glass_library": "AGF玻璃库文件名，如无法获取请使用内置库",
}, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# Lens 构建函数
# ═══════════════════════════════════════════════════════════
def build_lens(data: dict) -> Lens:
    """从字典构建 Lens 对象，加载 AGF 玻璃库，固定使用 d/F/C 三波长"""
    from engine.lens_loader import load_lens_from_dict
    from engine.glass_loader import load_glass_catalog

    lens = load_lens_from_dict(data)

    # 始终使用 d, F, C 三波长（用户要求：不设为变量）
    lens.wavelengths = list(FIXED_WAVELENGTHS)
    lens.wavelengths_selected = list(FIXED_WAVELENGTHS)

    # 尝试加载 AGF 玻璃库
    if lens.glass_library:
        load_glass_catalog(lens)

    return lens


# ═══════════════════════════════════════════════════════════
# 辅助函数：光线表格
# ═══════════════════════════════════════════════════════════
FIELD_CN = {
    "on_axis": "0 视场（轴上）",
    "0.7_field": "0.7 视场",
    "full_field": "全视场",
}


def _apt_cn(label: str) -> str:
    """将孔径标签转为中文显示"""
    if label == "chief":
        return "主光线 (0 孔径)"
    # e.g. "full_plus" → "全孔径(+)"  or "0.7_minus" → "0.7 孔径(-)"
    base = label.replace("_plus", "").replace("_minus", "")
    sign = "(+)" if "_plus" in label else "(-)"
    if base == "full" or base == "1.0":
        return f"全孔径 {sign}"
    return f"{base} 孔径 {sign}"


def _wl_cn(wl: str) -> str:
    return WL_DISPLAY.get(wl, wl)


def build_incident_ray_table(lens: Lens, object_distance: float,
                              focal_length: float | None = None) -> list[dict]:
    """返回所有入射光线的 (L, U) 初始坐标"""
    bundles = generate_rays(lens, object_distance, focal_length=focal_length)
    rows = []
    for b in bundles:
        rows.append({
            "视场": FIELD_CN.get(b.field_label, b.field_label),
            "孔径": _apt_cn(b.aperture_label),
            "波长": _wl_cn(b.ray.wavelength),
            "L (mm)": f"{b.ray.L:.4f}",
            "U (rad)": f"{b.ray.U:.8f}",
        })
    return rows


def build_trace_path_table(lens: Lens, object_distance: float,
                            focal_length: float | None = None) -> list[dict]:
    """返回每条 d 光光线在每个面后的 (L', U')"""
    bundles = generate_rays(lens, object_distance, focal_length=focal_length)
    rows = []
    for b in bundles:
        if b.ray.wavelength != "d":
            continue
        result = trace_single_ray(lens, b.ray, object_distance)
        if result is None:
            continue
        for p in result["path"]:
            rows.append({
                "视场": FIELD_CN.get(b.field_label, b.field_label),
                "孔径": _apt_cn(b.aperture_label),
                "面号": p["surface_index"] + 1,
                "z_hit (mm)": f"{p['z_hit']:.4f}",
                "L' (mm)": f"{p['L']:.6f}",
                "U' (rad)": f"{p['U']:.8f}",
            })
    return rows


# ═══════════════════════════════════════════════════════════
# 页面设置
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="OptiCore — 光学系统计算",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 OptiCore — 共轴球面光学系统计算")
st.caption("近轴计算 · 实际光线追迹 · 像差分析 · d/F/C 三波长")

# ═══════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════
if "lens" not in st.session_state:
    st.session_state.lens = None
if "lens_label" not in st.session_state:
    st.session_state.lens_label = ""
if "results" not in st.session_state:
    st.session_state.results = None


# ═══════════════════════════════════════════════════════════
# 侧边栏 — 文件输入
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("📁 输入设置")

    # ── 文件上传 ──
    uploaded_file = st.file_uploader(
        "上传 lens.json",
        type=["json"],
        help="镜头参数配置文件（JSON 格式）",
    )

    # ── 示例镜头 + 模板下载 并排 ──
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("📦 示例镜头", use_container_width=True,
                     help="加载单透镜示例（f'≈45mm）"):
            st.session_state.lens = build_lens(DEMO_LENS_DICT)
            st.session_state.lens_label = "示例镜头（单透镜，f'≈45mm）"
            st.session_state.results = None
    with col_b:
        st.download_button(
            label="📄 下载模板",
            data=TEMPLATE_JSON,
            file_name="template_lens.json",
            mime="application/json",
            use_container_width=True,
            help="下载 JSON 配置模板，修改后上传",
        )

    # ── 处理上传 ──
    if uploaded_file is not None:
        try:
            content = uploaded_file.read()
            data = json.loads(content.decode("utf-8"))
            st.session_state.lens = build_lens(data)
            st.session_state.lens_label = uploaded_file.name
            st.session_state.results = None
        except json.JSONDecodeError as e:
            st.error(f"JSON 解析失败: {e}")
        except Exception as e:
            st.error(f"加载失败: {e}")

    st.divider()

    # ── 清除缓存 ──
    if st.button("🧹 清除缓存并重载", use_container_width=True,
                 help="删除 __pycache__ + 清除模块缓存，解决代码更新后报错"):
        count = 0
        project_root = os.path.dirname(os.path.abspath(__file__))
        for root, dirs, _files in os.walk(project_root):
            if "__pycache__" in dirs:
                cache_path = os.path.join(root, "__pycache__")
                shutil.rmtree(cache_path, ignore_errors=True)
                count += 1
        to_remove = [k for k in sys.modules if k.startswith("engine")]
        for k in to_remove:
            del sys.modules[k]
        st.success(f"✅ 已清除 {count} 个缓存 + {len(to_remove)} 个模块，正在重载…")
        import time as _t
        _t.sleep(0.3)
        st.rerun()

    st.caption("OptiCore v2.0 | Python + Streamlit")


# ═══════════════════════════════════════════════════════════
# 主内容区
# ═══════════════════════════════════════════════════════════
lens = st.session_state.lens

if lens is None:
    st.info("👈 请上传 lens.json 或点击「📦 示例镜头」开始")
    st.stop()

# ── 镜头概览 ──
st.success(f"✅ 已加载: **{st.session_state.lens_label}**")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("镜片数", lens.num_surfaces - 1)
col2.metric("入瞳半径", f"{lens.entrance_pupil_radius:.1f} mm")
obj_label = "无限远 (∞)" if lens.is_infinite else f"{lens.object_distance:.0f} mm"
col3.metric("物距", obj_label)

FM_MAP = {"angle": "视场角 (°)", "object_height": "物高 (mm)", "image_height": "像高 (mm)"}
col4.metric("视场模式", FM_MAP.get(lens.field_mode, lens.field_mode))
col5.metric(f"视场值", f"{lens.field_value:.3f}")

# 波长信息（固定 d/F/C）
wl_info = " | ".join(WL_DISPLAY[w] for w in FIXED_WAVELENGTHS)
st.caption(f"📍 计算波长（固定全部选中）：{wl_info}")

# ── 镜头面参数表 ──
with st.expander("📋 镜头面参数", expanded=False):
    surface_data = []
    for i, s in enumerate(lens.surfaces):
        r_display = f"{s.radius:.2f}" if abs(s.radius) < 1e8 else "∞ (平面)"
        surface_data.append({
            "面号": i + 1,
            "曲率半径 R (mm)": r_display,
            "厚度 d (mm)": f"{s.thickness:.3f}",
            "材料": s.glass,
            "口径 (mm)": f"{s.diameter:.1f}",
        })
    st.dataframe(surface_data, use_container_width=True, hide_index=True)

# ── 入射光线初始坐标 ──
with st.expander("🔍 入射光线初始坐标 (L, U)", expanded=False):
    st.caption("按照要求，先求出所需计算的入射光线的初始坐标（L, U）")
    from engine.paraxial import compute_paraxial as _cp
    _pp = _cp(lens, lens.object_distance)
    inc_rays = build_incident_ray_table(lens, lens.object_distance,
                                         focal_length=_pp.get("f_prime"))
    st.dataframe(inc_rays, use_container_width=True, hide_index=True, height=350)
    st.caption(f"共 {len(inc_rays)} 条光线 · "
               f"{len(set(r['视场'] for r in inc_rays))} 视场 × "
               f"{len(set(r['孔径'] for r in inc_rays))} 孔径 × "
               f"{len(set(r['波长'] for r in inc_rays))} 波长")

st.divider()

# ── 计算按钮 ──
if st.button("🚀 开始计算", type="primary", use_container_width=True):
    with st.spinner("正在追迹光线并计算像差…"):
        try:
            st.session_state.results = compute_system(lens)
        except Exception as e:
            st.error(f"计算出错: {e}")
            import traceback
            st.code(traceback.format_exc())

# ── 结果展示 ──
results = st.session_state.results

if results is not None:
    n_items = len([v for v in results.values() if isinstance(v, (int, float))])
    st.success(f"✅ 计算完成！共 **{n_items}** 项数据")

    # ── KPI 指标卡 ──
    def _v(key, default=0.0):
        val = results.get(key)
        return val if isinstance(val, (int, float)) and val is not None else default

    kpi_cols = st.columns(5)
    kpi_cols[0].metric("焦距 f'", f"{_v('f_prime'):.8f} mm")
    kpi_cols[1].metric("像距 l'", f"{_v('l_prime'):.8f} mm")
    kpi_cols[2].metric("全孔径球差", f"{_v('spherical_aberration_full'):.8f} mm")
    kpi_cols[3].metric("全视场彗差", f"{_v('meridional_coma_full_field_full_apt'):.8f} mm")
    kpi_cols[4].metric("全视场畸变", f"{_v('relative_distortion_full_field'):.6f} %")

    # ── 分表格详细展示 ──
    st.divider()
    lens_cfg = {
        "pupil_fractions": getattr(lens, "pupil_fractions", [0.0, 0.7, 1.0]),
        "field_fractions": getattr(lens, "field_fractions", [0.0, 0.7, 1.0]),
        "field_mode": lens.field_mode,
        "field_value": lens.field_value,
    }
    detailed_tables = format_detailed_tables(results, lens_config=lens_cfg)

    for tbl in detailed_tables:
        with st.expander(tbl["title"], expanded=(tbl["title"].startswith("📐"))):
            st.caption(tbl["formula"])
            if tbl["rows"]:
                st.dataframe(tbl["rows"], use_container_width=True, hide_index=True)
            else:
                st.caption("（无匹配数据）")

    # ── 光线追迹轨迹 ──
    with st.expander("📈 光线追迹轨迹 (L', U') — d 光各面出射坐标", expanded=False):
        st.caption("进行光线追迹，分别得到各条出射光线的坐标（L', U'）")
        from engine.paraxial import compute_paraxial as _cp2
        _pp2 = _cp2(lens, lens.object_distance)
        trace_rows = build_trace_path_table(lens, lens.object_distance,
                                             focal_length=_pp2.get("f_prime"))
        st.dataframe(trace_rows, use_container_width=True, hide_index=True, height=400)
        st.caption(f"共 {len(trace_rows)} 条记录 · d 光 · {lens.num_surfaces} 个面")

    # ── CSV 导出（含配置元数据）──
    from datetime import datetime
    csv_meta = {
        "镜头名称": getattr(lens, "name", "") or st.session_state.lens_label,
        "物距": "无限远 (∞)" if lens.is_infinite else f"{lens.object_distance:.3f} mm",
        "波长": ", ".join(FIXED_WAVELENGTHS),
        "视场模式": FM_MAP.get(lens.field_mode, lens.field_mode),
        "视场值": f"{lens.field_value:.3f}",
        "入瞳半径": f"{lens.entrance_pupil_radius:.3f} mm",
        "孔径分数": str(getattr(lens, 'pupil_fractions', [0.0, 0.7, 1.0])),
        "导出时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    csv_data = export_to_csv(results, metadata=csv_meta, lens_config=lens_cfg)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.divider()
    st.download_button(
        label="📥 下载 CSV 结果文件",
        data=csv_data,
        file_name=f"OptiCore_results_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
    )

else:
    st.info("👆 点击上方「🚀 开始计算」按钮执行光线追迹与像差分析")

st.divider()
st.caption(
    "OptiCore v2.0 — 基于 Snell 折射定律的向量光线追迹 · "
    "d/F/C 三波长 · 多视场多孔径 · 像差分析 · 8 位小数精度"
)
