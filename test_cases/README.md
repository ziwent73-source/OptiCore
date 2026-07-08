# OptiCore 测试用例

通过 Web 界面左侧上传 JSON 文件加载，或直接修改 `app.py` 中的 `DEMO_LENS_DICT`。

## 用例列表

### 1. cemented_doublet.json — 双胶合消色差透镜

| 参数 | 值 |
|------|-----|
| 结构 | H-K9L (冕牌) + H-ZF2 (火石) 胶合 |
| 焦距 f' | ~45.1 mm |
| 入瞳 | 8 mm (f/5.6) |
| 视场 | ±18 mm (全画幅) |
| 物距 | 无穷远 |
| 波长 | d / F / C（固定） |

**预期性能：**

| 指标 | 值 | 说明 |
|------|-----|------|
| 焦距 f' | 45.1 mm | 接近目标 45mm |
| 全孔径球差 | -0.23 mm | 欠校正，可接受 |
| 全视场彗差 | -0.73 mm | |
| 相对畸变 | 4.4% | |
| 0 孔径位置色差 | 0.009 mm | **消色差效果显著** |
| 倍率色差 | ~0.02 mm | |

> **与单透镜对比**：单透镜位置色差约 −0.68mm，双胶合仅 0.009mm——消色差效果约 **75 倍**。

### 2. textbook_ch4_inf_3deg.json — 教材第四章·无穷远

| 参数 | 值 |
|------|-----|
| 结构 | H-K9L + H-ZF2 双胶合 |
| 焦距 f' | ~99.7 mm |
| 入瞳半径 | 10 mm |
| 视场 | 半视场角 3°（像高 ~5.23mm） |
| 物距 | 无穷远（null） |

> 已与 Zemax OpticStudio 202111 全面校对，全部 39 项误差 <0.06%。

### 3. textbook_ch4_fin_500mm.json — 教材第四章·有限物距

| 参数 | 值 |
|------|-----|
| 结构 | H-K9L + H-ZF2 双胶合 |
| 焦距 f' | ~99.7 mm |
| 入瞳半径 | 10 mm |
| 视场 | 物高 26mm（像高 ~6.46mm） |
| 物距 | 500 mm |

> 已与 Zemax OpticStudio 202111 全面校对，全部参数误差 <0.2%。

## JSON 格式说明（v2.0）

```json
{
  "name": "镜头名称",
  "description": "可选的描述文字",
  "system_parameters": {
    "object_distance": null,
    "entrance_pupil_radius": 10.0,
    "aperture_stop_index": 0,
    "max_field_height": 12.0
  },
  "calculation_settings": {
    "field_mode": "image_height",
    "field_value": 12.0,
    "aperture_angle_deg": 5.0,
    "field_fractions": [0.7],
    "pupil_fractions": [0.7]
  },
  "surfaces": [
    {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
    {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0}
  ],
  "glass_library": "CDGM-ZEMAX202111.AGF"
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `object_distance` | number / null | 物距(mm)，null/inf/0 = 无限远 |
| `entrance_pupil_radius` | number | 入瞳半径(mm) |
| `aperture_stop_index` | int | 光阑所在面索引（0 = 第一面） |
| `max_field_height` | number | 系统最大视场参考值 |
| `field_mode` | string | `"angle"`(度) / `"object_height"`(mm) / `"image_height"`(mm) |
| `field_value` | number | 与 field_mode 对应的数值 |
| `field_fractions` | [number] | 需计算的中间视场分数，0 和 1.0 自动补全 |
| `pupil_fractions` | [number] | 需计算的中间孔径分数，0 和 1.0 自动补全 |
| `glass_library` | string | AGF 玻璃库文件名，空字符串 = 使用内置库 |

> 波长固定为 d / F / C，无需配置。

## 玻璃库

内置 CDGM 常用牌号（加载 AGF 文件时使用精确值）：

| 牌号 | n_d | n_F | n_C | 类型 |
|------|-----|-----|-----|------|
| H-K9L | 1.51680 | 1.52238 | 1.51433 | 冕牌 (低色散) |
| H-ZF2 | 1.67270 | 1.68753 | 1.66662 | 火石 (高色散) |
| H-ZK7 | 1.61300 | 1.61999 | 1.60949 | 重冕 |
| H-LAK7 | 1.71300 | 1.72236 | 1.70886 | 镧冕 |
| H-F4 | 1.62004 | 1.63210 | 1.61498 | 火石 |
| H-ZF10 | 1.68893 | 1.70461 | 1.68193 | 重火石 |
