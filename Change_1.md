【项目需求变更 — OptiCore 软件功能升级与 UI 重构】

当前程序已能计算 76 项数据并输出 CSV，现需对以下方面进行改造。请基于现有代码架构进行增量修改，不要重写整个项目。

---

## 一、文件输入方式（保持 JSON，扩充字段）

继续保持 JSON 作为唯一输入格式，但需扩充 lens.json 的结构，使其包含完整的系统参数和计算配置。

新的 JSON 结构如下（请按此改造 LensLoader）：

{
  "_comment": "完整光学系统计算配置文件",
  "name": "镜头名称",
  
  "system_parameters": {
    "object_distance": -500.0,          // 物距 (mm)，inf 表示无限远
    "entrance_pupil_radius": 10.0,      // 入瞳半径 (mm)
    "aperture_stop_index": 0,           // 光阑所在面索引，0 表示第一面
    "max_field_height": 12.0            // 最大视场像高 (mm)
  },
  
  "calculation_settings": {
    "wavelengths_selected": ["d", "F", "C"],   // 可选：d, F, C 的一种或多种
    "field_mode": "image_height",              // 三种模式：angle / object_height / image_height
    "field_value": 12.0,                       // 对应的视场数值
    "aperture_angle_deg": 5.0,                 // 孔径角 (度)，用于换算入瞳半径
    "pupil_fractions": [0.0, 0.7, 1.0]         // 需要计算的孔径分数
  },
  
  "surfaces": [
    {"radius": 42.0, "thickness": 6.0, "glass": "H-K9L", "diameter": 25.0},
    {"radius": -50.0, "thickness": 42.0, "glass": "Air", "diameter": 25.0}
  ],
  
  "glass_library": "CDGM-ZEMAX202111.AGF"
}

注意：
- 去掉原来顶层的 wavelengths、field_height、entrance_pupil_radius 等旧字段，全部归入 system_parameters 和 calculation_settings。
- system_parameters 放的是物理系统固有参数（物距、光阑、入瞳等），calculation_settings 放用户本次计算的选择（波长、视场、孔径）。
- object_distance 为 inf 时表示无限远，有限距时输入具体数值（如 -500）。
- field_mode 三种模式：angle（视场角，单位度）、object_height（物高，单位mm）、image_height（线视场/像高，单位mm）。


## 二、JSON 模板下载功能（新增）

为了方便用户填写数据，需在 Streamlit 界面添加一个“下载 JSON 模板”按钮。

### 功能要求
1. 在 Streamlit 界面的文件上传区域旁边，放置一个 **“下载配置模板”** 按钮。
2. 点击后自动下载一个 `template_lens.json` 文件。
3. 模板内容应为完整的 JSON 结构，包含所有必需的字段，并为每个字段填入**示例值/默认值**。
4. 模板中的 `_comment` 字段需包含中文说明，指导用户如何填写各字段。
5. 用户下载后自行修改，再通过现有的文件上传功能上传。

### 模板内容示例（供参考，实际以你的实现为准）

{
  "_comment": "OptiCore 计算配置文件模板 — 请根据实际镜头数据修改",
  "name": "请输入镜头名称，如：双胶合消色差镜头",
  
  "system_parameters": {
    "_comment": "系统物理参数",
    "object_distance": -500.0,
    "_comment_object_distance": "物距(mm)，实物在左侧为负，输入 inf 表示无限远",
    "entrance_pupil_radius": 10.0,
    "_comment_entrance_pupil_radius": "入瞳半径(mm)，必填",
    "aperture_stop_index": 0,
    "_comment_aperture_stop_index": "光阑所在面索引，0表示第一面",
    "max_field_height": 12.0,
    "_comment_max_field_height": "最大视场像高(mm)，全画幅取12"
  },
  
  "calculation_settings": {
    "_comment": "本次计算的选择",
    "wavelengths_selected": ["d", "F", "C"],
    "_comment_wavelengths": "可选 d, F, C 的一种或多种，如 ['d'] 或 ['d', 'F']",
    "field_mode": "image_height",
    "_comment_field_mode": "视场输入模式：angle(度) / object_height(mm) / image_height(mm)",
    "field_value": 12.0,
    "_comment_field_value": "视场数值，与 field_mode 对应",
    "aperture_angle_deg": 5.0,
    "_comment_aperture_angle": "孔径角(度)，程序自动换算入瞳半径",
    "pupil_fractions": [0.0, 0.7, 1.0],
    "_comment_pupil_fractions": "需计算的孔径分数，0为主光线，1为全孔径"
  },
  
  "surfaces": [
    {
      "_comment": "按顺序填写每个光学面，从第一面到像面",
      "radius": 42.0,
      "_comment_radius": "曲率半径(mm)，凸面为正，凹面为负",
      "thickness": 6.0,
      "_comment_thickness": "到下一面的厚度(mm)，最后一面填像面距离",
      "glass": "H-K9L",
      "_comment_glass": "玻璃名称，如 H-K9L、H-ZF2、Air",
      "diameter": 25.0,
      "_comment_diameter": "通光半口径(mm)"
    },
    {
      "radius": -50.0,
      "thickness": 42.0,
      "glass": "Air",
      "diameter": 25.0
    }
  ],
  
  "glass_library": "CDGM-ZEMAX202111.AGF",
  "_comment_glass_library": "AGF玻璃库文件名，如无法获取请使用内置库"
}

### 实现要点
- 使用 Streamlit 的 `st.download_button` 实现下载。
- 模板中每个字段的注释用 `_comment_xxx` 方式嵌入，方便用户理解和修改。
- 模板的 JSON 格式必须完全正确，用户下载后可直接上传使用。


## 三、核心计算层改造

### 1. 波长
- 当前：固定三光同时计算。
- 改为：只计算 wavelengths_selected 中选中的波长。
- 要求：未选中的波长不参与任何计算，对应的色差项（位置色差、倍率色差）自动跳过，不显示也不输出。

### 2. 视场
- 当前：固定 0、0.7、1.0 三个视场。
- 改为：根据 field_mode 和 field_value 换算目标视场，只计算目标视场 + 0 视场（轴上点作为基准）。
- 要求：0 视场始终作为基准计算，但结果显示时只显示用户选中的目标视场。

### 3. 孔径
- 当前：通过入瞳半径固定值控制。
- 改为：根据 aperture_angle_deg（用户输入的孔径角）和物距换算出入瞳半径。
- 要求：按 pupil_fractions 中的分数生成各孔径光线（如 [0.0, 0.7, 1.0] 生成 0孔径、0.7孔径、全孔径三条光线）。

### 4. 折射率（玻璃库）
- 当前：硬编码 H-K9L 和 H-ZF2 的折射率。
- 改为：从 CDGM-ZEMAX202111.AGF 文件中读取玻璃数据。
- 要求：
  - 程序在启动时读取 AGF 文件，按玻璃名称和波长索引折射率。
  - 如果 AGF 文件不存在或解析失败，程序报错提示并回退到内置常用玻璃库（H-K9L、H-ZF2、Air 的 d/F/C 折射率）。
  - 如果以上都无法解决，提供手动输入折射率的输入框作为最终备选。

### 5. 物距
- 当前：无限远和有限距两组同时计算。
- 改为：只计算 system_parameters.object_distance 中指定的单个物距。
- 要求：输入 inf 或 0 视为无限远，输入正数视为有限距（注意物距符号遵循光学符号规则，实物在左侧为负）。


## 四、结果显示精度升级

- 所有数值输出（界面显示 + CSV 导出）统一保留 8 位小数。
- 请在代码中设置 NumPy 的 set_printoptions(precision=8) 和 Pandas 的 pd.set_option('display.precision', 8)。


## 五、UI 界面重构（Streamlit）

### 1. 动态结果显示
- 只显示用户选择的参数所对应的计算结果。
- 逻辑示例：
  - 波长只选 d 光 → 不显示 F/C 相关的像位、色差列。
  - 视场只选 0.7 → 不显示全视场的畸变、彗差、像高。
  - 孔径只选 0.7 → 不显示全孔径的球差、彗差。

### 2. 结果按像差类别分表格显示
- 用 st.expander 分别展示以下独立表格：
  - 近轴数据表（f', l', lH', lp', 入瞳/出瞳位置，y0'，等）
  - 球差表（各孔径、各波长的球差值）
  - 位置色差表（各孔径的位置色差值）
  - 子午彗差表（各视场、各孔径的彗差值）
  - 实际像高表（各视场、各波长的实际像高）
  - 畸变表（各视场的绝对畸变和相对畸变）
  - 倍率色差表（各视场的倍率色差值）
- 每个表格上方显示该像差类别的计算公式（字符串即可）。

### 3. 模板下载按钮位置
- 在文件上传区域（st.file_uploader）旁边或下方，放置 st.download_button。
- 按钮文字：“📄 下载 JSON 配置模板”。


## 六、文件存取功能保留

- 保留 JSON 输入和 CSV 导出。
- 导出 CSV 时，表头需包含当前计算的所有配置参数（波长、视场、物距、孔径角），便于溯源。
- 导出文件名自动生成，如 OptiCore_results_20260107_143022.csv。


## 七、开发顺序（请按此执行，每步完成后停下来等我测试）

Step 1：改造 lens.json 结构 + 修改 LensLoader 适配新字段。
Step 2：在 Streamlit 界面添加“下载 JSON 模板”按钮。
Step 3：实现 AGF 玻璃库读取（含 fallback 机制）。
Step 4：改造核心计算层（波长/视场/孔径/物距变量化）。
Step 5：升级输出精度到 8 位小数。
Step 6：重构 Streamlit UI（动态显示 + 分表格展示）。
Step 7：适配 CSV 导出功能。


## 八、特别提醒

1. 请先确认 CDGM-ZEMAX202111.AGF 文件的解析是否可行。如果不可行，请告诉我，我会提供内置玻璃库的替代方案。
2. 现有的单球面测试功能请保留，不要删除。
3. 所有新增字段的默认值请设置为合理的数值（如波长默认选 d、F、C，视场默认 12mm，孔径角默认 5°）。
4. 模板下载功能要优先实现，方便用户（特别是小组其他成员）快速上手填写数据。

---

请从 Step 1 开始执行。