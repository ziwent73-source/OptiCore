# OptiCore — 共轴球面光学系统计算工具

> Python + Streamlit 实现的光线追迹与像差分析软件  
> 浙江大学《光学系统设计课程设计》

## 功能

- **两种输入方式**：上传 JSON 文件（传统方式）/ 页面上直接填写表单（新增），调用同一计算引擎
- **近轴计算**：焦距 f'、像距 l'、主面位置 lH'、出瞳距 lp'、近轴像高、场曲、像散
- **实际光线追迹**：逐面 Snell 折射（向量形式），固定 d / F / C 三波长
- **像差分析**：球差、位置色差、子午彗差、实际像高、畸变（绝对/相对）、倍率色差
- **细光束场曲**：Coddington 方程计算子午/弧矢场曲及像散
- **动态分数**：视场分数和孔径分数由用户指定中间值，0 和 1.0 自动补全
- **数据导出**：CSV 结果下载（长格式，8 位小数）

## 快速开始

### 方式一：双击运行（推荐，无需命令行）

1. **首次使用**：双击 **`run.bat`** → 自动检测 Python + 安装依赖库（约 1-2 分钟）
2. **之后每次**：双击 **`launch.bat`** → 启动程序，浏览器自动打开

> `%~dp0` 相对路径，放在任何目录都能运行。需提前安装 Python 3.10+ 并勾选 "Add Python to PATH"。

### 方式二：命令行启动

```bash
cd OptiCore
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 `http://localhost:8501`

### 使用步骤

**📂 JSON 文件模式：**
1. 顶部选择「📂 上传 JSON 文件」
2. 左侧上传 `lens.json`，或点击 **「示例镜头」** 加载演示数据
3. 点击 **「开始计算」** 执行光线追迹
4. 查看 KPI 卡片 + 分组详细表格 + 追迹路径表 + 下载 CSV

**✏️ 手动填写模式：**
1. 顶部选择「✏️ 手动填写参数」
2. 在表单中填写系统参数、计算设置、光学面数据
3. 可动态添加/删除光学面，每面独立填写曲率半径、厚度、玻璃、口径
4. 点击 **「开始计算」** → 结果展示与 JSON 模式完全一致
5. 点 **「重新填写」** 可返回编辑

## 项目结构

```
OptiCore/
├── app.py                        # Streamlit Web 界面（含表单输入 + JSON 上传）
├── run.bat                       # 一键环境检测 + 依赖安装（首次使用）
├── launch.bat                    # 一键启动程序（日常使用）
├── lens.json                     # 示例镜头（单透镜 f'≈45mm）
├── template_lens.json            # JSON 配置模板（v2.0 格式）
├── requirements.txt              # 依赖：streamlit, numpy, pandas, matplotlib
├── README.md                     # 本文件
├── plan.md                       # 项目实施方案
├── docs/
│   └── ALGORITHM.md              # 算法参考手册
├── engine/                       # 光学计算引擎
│   ├── data_model.py             # Lens, Surface, Ray, Material 数据结构
│   ├── lens_loader.py            # JSON → Lens（v2.0 + 旧格式兼容）
│   ├── glass_loader.py           # AGF 玻璃库加载
│   ├── ray_generator.py          # ⭐ 入瞳光线采样（动态视场/孔径）
│   ├── paraxial.py               # 近轴计算 + Coddington 场曲/像散
│   ├── ray_tracer.py             # 向量 Snell 实际追迹
│   ├── aberration.py             # 像差计算（动态分数）
│   └── file_manager.py           # CSV 导出 + 分组表格（长格式）
├── test_cases/                   # 测试镜头
│   ├── README.md
│   ├── cemented_doublet.json                # 双胶合 f'≈45mm
│   ├── textbook_ch4_inf_3deg.json           # 教材第四章·无穷远·3°视场角
│   └── textbook_ch4_fin_500mm.json          # 教材第四章·有限物距500mm·物高26mm
└── tests/                        # 测试脚本
    ├── smoke_v2.py               # 动态分数冒烟测试
    ├── debug_aberration.py       # 无穷远 vs Zemax 对比
    ├── debug_finite.py           # 有限物距 vs Zemax 对比
    └── ...
```

## JSON 配置格式（v2.0）

```json
{
  "name": "镜头名称",
  "system_parameters": {
    "object_distance": null,
    "entrance_pupil_radius": 10.0,
    "aperture_stop_index": 0,
    "max_field_height": 12.0
  },
  "calculation_settings": {
    "field_fractions": [0.7],
    "field_mode": "image_height",
    "field_value": 12.0,
    "aperture_angle_deg": 5.0,
    "pupil_fractions": [0.7]
  },
  "surfaces": [
    {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
    {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0}
  ],
  "glass_library": "CDGM-ZEMAX202111.AGF"
}
```

> `object_distance`: `null` / `"inf"` / `0` = 无限远，正数 = 有限物距（取绝对值）  
> `field_fractions` / `pupil_fractions`: 只需填中间值，0 和 1.0 自动补全  
> `field_mode`: `"angle"`（视场角·度）/ `"object_height"`（物高·mm）/ `"image_height"`（像高·mm）

## 测试用例

| 文件 | 场景 | 焦距 | 说明 |
|------|------|------|------|
| `lens.json` | 单透镜 H-K9L | ~45mm | 演示用 |
| `cemented_doublet.json` | H-K9L + H-ZF2 胶合 | ~45mm | 消色差 |
| `textbook_ch4_inf_3deg.json` | H-K9L + H-ZF2 胶合 | ~99.7mm | **无穷远·3°视场角** |
| `textbook_ch4_fin_500mm.json` | H-K9L + H-ZF2 胶合 | ~99.7mm | **有限物距500mm·物高26mm** |

## 玻璃库

内置 CDGM 常用牌号（AGF 文件优先）：

| 牌号 | n_d | n_F | n_C | 阿贝数 ν |
|------|-----|-----|-----|-----------|
| H-K9L | 1.51680 | 1.52238 | 1.51433 | ~64 |
| H-ZF2 | 1.67270 | 1.68753 | 1.66662 | ~32 |
| H-ZK7 | 1.61300 | 1.61999 | 1.60949 | ~60 |
| H-F4 | 1.62004 | 1.63210 | 1.61498 | ~37 |
| Air | 1.00000 | 1.00000 | 1.00000 | — |

> 加载 `CDGM-ZEMAX202111.AGF` 时使用数据库精确值（6-9 位小数），上表为近似值。

## 输出格式

CSV 采用长格式（与 Zemax 输出一致）：

```csv
参数,波长,视场,孔径,数值
焦距f',d,,,45.17187531
理想像距l'（以透镜最后一面为参考）,d,0,0,42.97318397
,F,0,0,42.50557331
,C,0,0,43.18343219
...
子午慧差（不考虑符号，绝对值正确即可）,d,0.7,0.7,1.60717115
```

- 同一参数组的后续行参数列留空（合并单元格效果）
- 数值统一 8 位小数
- 参数按 16 个类别分组排序

## 校对精度

与 Zemax OpticStudio 教材第四章双胶合镜头（H-K9L / H-ZF2）对比：

| 参数类别 | 无穷远·3° | 有限物距·500mm |
|----------|-----------|----------------|
| 近轴参数 (f', l', lH', lp') | **<0.001%** | **<0.001%** |
| 近轴像高 (y'₀, y'₀.₇) | **<0.001%** | **<0.001%** |
| 球差 | **<0.03%** | **<0.004%** |
| 位置色差 | **<0.06%** | **<0.2%** |
| 子午场曲 xt' | **<0.02%** | **<0.07%** |
| 弧矢场曲 xs' | **<0.001%** | **<0.001%** |
| 像散 Δxts' | **<0.03%** | **<0.13%** |
| 子午彗差 | **<0.003%** | **<0.001%** |
| 畸变（绝对/相对） | **<0.002%** | **<0.003%** |
| 倍率色差 | **<0.003%** | **<0.004%** |

## 依赖

```
streamlit >= 1.28
numpy >= 1.24
pandas >= 2.0
matplotlib >= 3.7
```
