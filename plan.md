# OptiCore — 实施方案

> 共轴球面光学系统光线追迹与像差分析工具
> 浙江大学《光学系统设计课程设计》

---

## 0. 当前架构概览

### 设计决策

| 项目 | 决定 |
|------|------|
| 波长 | **固定 d / F / C**（不可配置） |
| 视场分数 | 用户指定中间值，**0 和 1.0 自动补全** |
| 孔径分数 | 用户指定中间值，**0 和 1.0 自动补全** |
| 物距 | 单个物距（无穷远或有限距），JSON 中配置 |
| 输出格式 | **长格式**（参数,波长,视场,孔径,数值） |
| JSON 格式 | **v2.0**（system_parameters + calculation_settings） |
| 折射率 | AGF 玻璃库优先（6-9 位精度），内置库回退 |

### 输出参数分组（16 类，数量动态）

| 类别 | 参数 | 数量 |
|------|------|------|
| 近轴·焦距 | f' | 1 |
| 近轴·像距 | l' (d/F/C) | 3 |
| 轴上·实际像位置 | d/F/C × 各孔径 | 3 × N_apt |
| 近轴·主面位置 | lH' | 1 |
| 近轴·出瞳距 | lp' | 1 |
| 近轴·理想像高 | y'₀ (0.7视场 + 全视场) | 2 × N_fld（非零） |
| 轴上·球差 | 各非零孔径 | N_apt − 1 |
| 轴上·位置色差 | F−C (各孔径含主光线) | N_apt |
| 视场·子午场曲 | xt' | 1 |
| 视场·弧矢场曲 | xs' | 1 |
| 视场·像散 | Δxts' = xt' − xs' | 1 |
| 视场·实际像高 | d/F/C × 各非零视场 | 3 × (N_fld − 1) |
| 视场·相对畸变 | 各非零视场 | N_fld − 1 |
| 视场·绝对畸变 | 各非零视场 | N_fld − 1 |
| 视场·倍率色差 | F−C × 各非零视场 | N_fld − 1 |
| 视场·子午彗差 | 各非零视场 × 各非零孔径 | (N_fld−1) × (N_apt−1) |

> N_fld = 视场分数个数（含 0 和 1.0）  
> N_apt = 孔径分数个数（含 0 和 1.0）  
> 默认 [0.7] → N_fld=3, N_apt=3 → **39 项**

---

## 1. 技术选型

| 层 | 选择 | 理由 |
|------|------|------|
| 计算引擎 | **Python 3** | 科学计算生态完善 |
| Web 界面 | **Streamlit** | 纯 Python，快速迭代 |
| 数据输入 | JSON (v2.0) 文件上传 | 结构化、可版本控制 |
| 数据输出 | CSV 长格式 + 网页表格 | 与 Zemax 输出一致 |
| 绘图 | Matplotlib | 光线轨迹图、镜片填充 |

---

## 2. 项目文件结构

```
OptiCore/
├── app.py                        # Streamlit 网页主入口
├── lens.json                     # 示例镜头（单透镜）
├── template_lens.json            # JSON 配置模板（v2.0）
├── requirements.txt              # 依赖声明
├── README.md                     # 用户文档
├── plan.md                       # 本文件
├── docs/
│   └── ALGORITHM.md              # 算法参考手册
├── engine/                       # 光学计算引擎
│   ├── data_model.py             # Lens, Surface, Ray, Material
│   ├── lens_loader.py            # JSON → Lens（v2.0 + 旧格式兼容）
│   ├── glass_loader.py           # AGF 玻璃库加载
│   ├── ray_generator.py          # ⭐ 入瞳光线采样（动态视场/孔径）
│   ├── paraxial.py               # 近轴计算 + Coddington 场曲
│   ├── ray_tracer.py             # 向量 Snell 折射追迹
│   ├── aberration.py             # 像差计算（全动态）
│   └── file_manager.py           # CSV 导出 + 分组表格（长格式）
├── test_cases/                   # 测试镜头
│   ├── README.md
│   ├── cemented_doublet.json
│   ├── textbook_ch4_inf_3deg.json
│   └── textbook_ch4_fin_500mm.json
└── tests/                        # 测试脚本
    ├── smoke_v2.py               # 动态分数冒烟测试
    ├── debug_aberration.py       # 无穷远 vs Zemax 对比
    └── debug_finite.py           # 有限物距 vs Zemax 对比
```

---

## 3. 数据流

```
用户上传 lens.json (v2.0)
        │
        ▼
  LensLoader → Lens 对象
  ├── 解析 system_parameters + calculation_settings
  ├── field_fractions/pupil_fractions 自动补全 0 和 1.0
  └── 加载 AGF 玻璃库（精确折射率）
        │
        ▼
  ParaxialCalculator → 近轴参数
  ├── 焦距 f'（平行光追迹）
  ├── 像距 l' (d/F/C)
  ├── 主面 lH' / 出瞳 lp'
  ├── 近轴像高 y'（主光线追迹）
  └── 场曲 xt'/xs' + 像散 Δxts'（Coddington 细光束）
        │
        ▼
  RayGenerator → 光线集合
  ├── 视场：从 field_fractions 动态生成（0.0 自动 → on_axis）
  ├── 孔径：从 pupil_fractions 动态生成（±分数值）
  └── 波长：固定 d / F / C
        │
        ▼
  RayTracer → 逐面向量 Snell 追迹 → 像面落点
        │
        ▼
  AberrationCalculator → 像差
  ├── 轴上：实际像点、球差、位置色差
  └── 视场：彗差、实际像高、畸变、倍率色差
        │
        ▼
  FileManager → CSV 长格式导出
  ├── _key_to_row(): 键名 → {参数, 波长, 视场, 孔径, 数值}
  ├── _build_output_rows(): 排序 + 合并单元格
  └── format_detailed_tables(): 16 类分组展示
        │
        ▼
  Streamlit UI → KPI 卡片 + 分组表格 + 追迹图 + CSV 下载
```

---

## 4. 核心算法

### 4.1 向量 Snell 折射（`ray_tracer.py`）

```
Γ = n'·cosI' − n·cosI
n'·ŝ' = n·ŝ + Γ·N̂
```

- 处理所有入射角，包括 cosI < 0（凹面、玻璃→空气）
- TIR 检测：sin²I' ≥ 1 时返回 None

### 4.2 Coddington 场曲（`paraxial.py`）

- 精确主光线追迹 → 逐面 Coddington 方程
- 初始波前曲率：无穷远 t=s=∞，有限距 t=s=−D_obj
- 每面：`n' cos²I' / t' = (n' cosI' − n cosI) / R + n cos²I / t`
- 像面参考：与 `compute_paraxial` 一致（有限物距用斜率 h/obj）

### 4.3 动态键名解析（`file_manager.py`）

- 正则匹配 16 类参数组
- 视场/孔径标签区分（`full_field` vs `0.7_field`，`full_apt` vs `0.7_apt`）
- 配置过滤：`_key_matches_config()` 按 field_fractions + pupil_fractions 筛选

---

## 5. 实施历程

### v2.0（当前版本）
- ✅ 波长固定 d/F/C，不可配置
- ✅ 动态视场/孔径分数（0 和 1.0 自动补全）
- ✅ JSON v2.0 格式（system_parameters + calculation_settings）
- ✅ 输出改为长格式（参数,波长,视场,孔径,数值）
- ✅ 16 类参数分组，8 位小数
- ✅ 与 Zemax 全面校对（无穷远 + 有限物距）

### Bug 修复记录
- ✅ **向量 Snell 折射** — 标量公式在 cosI<0 时符号错误，改为完整向量形式
- ✅ **硬编码 f≈45** — 改为近轴计算获取精确 f'
- ✅ **精确视场角** — ray_generator 用 atan 替代小角度近似
- ✅ **Coddington 精度** — 近轴像面与主光线初始角与主流程对齐
- ✅ **像高符号** — 统一取绝对值，与 Zemax 参考一致
- ✅ **键名解析** — 修复视场分数被误匹配为孔径值的正则 bug

---

## 6. 验证标准

| 指标 | 目标 | 实际 |
|------|------|------|
| 焦距误差 | <0.1% | **<0.0001%** |
| 近轴参数 | <0.1% | **<0.001%** |
| 球差 | <0.5% | **<0.03%** |
| 位置色差 | <0.5% | **<0.2%** |
| 场曲/像散 | <1% | **<0.13%** |
| 彗差 | <0.5% | **<0.003%** |
| 畸变 | <0.5% | **<0.004%** |
| 倍率色差 | <0.5% | **<0.004%** |

> 验证基准：Zemax OpticStudio 202111，教材第四章双胶合镜头（H-K9L / H-ZF2）
