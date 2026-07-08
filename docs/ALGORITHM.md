# OptiCore 算法参考手册

> 本文档整合：参数定义、计算公式、Zemax 规范对照、调试记录

---

## 目录

1. [计算流程](#1-计算流程)
2. [坐标与光线定义](#2-坐标与光线定义)
3. [近轴计算](#3-近轴计算)
4. [实际光线追迹](#4-实际光线追迹)
5. [像差计算](#5-像差计算)
6. [场曲与像散（Coddington）](#6-场曲与像散coddington)
7. [全部输出参数](#7-全部输出参数)
8. [Zemax 规范对照](#8-zemax-规范对照)
9. [调试记录](#9-调试记录)

---

## 1. 计算流程

```
                  lens.json
                     │
     ┌───────────────┼───────────────┐
     ▼                               ▼
  无限远物距                      有限物距
     │                               │
     ▼                               ▼
① compute_paraxial()          ① compute_paraxial()
   近轴参数 12 项                 近轴参数 12 项
     │                               │
     ▼                               ▼
② generate_rays()             ② generate_rays()
   3视场×5孔径×3波长=45条         3视场×5孔径×3波长=45条
     │                               │
     ▼                               ▼
③ trace_with_image() ×45      ③ trace_with_image() ×45
   向量 Snell 逐面追迹             向量 Snell 逐面追迹
     │                               │
     ▼                               ▼
④ 像差计算 27 项               ④ 像差计算 27 项
     │                               │
     ▼                               ▼
  39 项输出                     39 项输出
                   │
                   ▼
              78 项汇总
```

### 光线采样

| 视场 | 含义 | 无限远 | 有限物距 |
|------|------|--------|----------|
| 0 (on_axis) | 轴上点 | y=0 | y=0 |
| 0.7 | 0.7 视场 | 0.7×视场角 | 0.7×物高 |
| 1.0 (full) | 全视场 | 全视场角 | 全物高 |

| 孔径 | 入瞳高度 L | 说明 |
|------|-----------|------|
| chief | 0 | 主光线，过入瞳中心 |
| +full | +R_pupil | 上边缘光线 |
| -full | -R_pupil | 下边缘光线 |
| +0.7 | +0.7R | 0.7 带上光线 |
| -0.7 | -0.7R | 0.7 带下光线 |

每条光线包含 d (587.6nm) / F (486.1nm) / C (656.3nm) 三个波长版本。

---

## 2. 坐标与光线定义

### 坐标系（右手系，Zemax 一致）

```
        Y ↑
          |
          |
          O --------→ Z (光传播方向)
```

- +Z：光传播方向
- +Y：像高方向
- 第一面顶点在 z=0
- 曲率半径 R：球心在顶点右侧时 R>0（Zemax 符号）

### 光线表示

```python
Ray(L, U, wavelength)
```

- `L`：光线高度（mm），在 Y-Z 子午面内
- `U`：光线方向角（rad），从 Z 轴起算，逆时针为正
- `wavelength`："d" | "F" | "C"

### 入瞳光线初值

**无限远物距**（视场角 W）：
```
U = atan(y_field / f')          # 同视场所有光线平行
L = 系数 × R_pupil               # 在入瞳平面采样
```

**有限物距**（物距 L₀，物高 y_obj）：
```
L = 系数 × R_pupil               # 在入瞳平面高度
dy = L - y_obj                   # 入瞳高度 − 物高
dz = pupil_z + L₀                # 入瞳 z − 物面 z
U = atan2(dy, dz)               # 从物点到入瞳点的方向
```

### 主光线 (Chief Ray)

通过入瞳中心 (L=0)，经指定视场点。所有横向像差以主光线为参考。

---

## 3. 近轴计算

> 文件：[paraxial.py](../engine/paraxial.py)

### 3.1 近轴光线追迹（L-U 坐标法）

```
折射：n' · u' = n · u − L · (n' − n) / R
传播：L' = L + d · u'
```

追迹一条光线（L₀, U₀）穿过全部 k 个面，返回 (L_k, U_k)。

### 3.2 像方焦距 f'

追迹平行光（U₀=0），从高度 h=R_pupil 入射：
```
f' = −h / U'_last
```

### 3.3 像方截距 l'

无限远物距：追迹 U₀=0 的光线
```
l' = −L_last / U'_last
```

有限物距：追迹从轴上物点发出的光线
```
U₀ = h / L₀        （与内部 tanU≈U 近似一致）
l' = −L_last / U'_last
```

### 3.4 后主面位置 lH'

镜头固有属性，始终从无限远平行光计算：
```
lH' = f' − l'_inf       （Zemax 约定：正值表示主面在最后一面右侧）
```

### 3.5 出瞳位置 lp'

从光阑中心追迹小角度光线，求像方与光轴交点。

### 3.6 近轴像高

追迹主光线（L₀=0，U₀=视场角），在像面落点高度：
```
y' = L_last + l' · U_last
```

无限远：
```
y'_full = f' · tan(W)   （全视场）
y'_0.7 = f' · tan(0.7W) （0.7 视场 = 0.7×视场角）
```

有限物距：
```
y' = |m| · y_obj        （m 为横向放大率）
```

---

## 4. 实际光线追迹

> 文件：[ray_tracer.py](../engine/ray_tracer.py)

### 4.1 球面交点

光线 (z_cur + p·cosU, L_cur + p·sinU) 与球面 (z−zc)² + y² = R² 求交：

```
A = 1
B = 2[(z_cur−zc)·cosU + L_cur·sinU]
C = (z_cur−zc)² + L_cur² − R²
p = (−B − √(B²−4AC)) / 2    取最小正根
```

### 4.2 向量 Snell 折射

```
ŝ  = (cosU, sinU)                   入射方向
N̂  = 从交点指向球心的单位法向量
cosI = ŝ · N̂                        （有符号）

Γ = n'·cosI' − n·cosI               Snell 系数
ŝ' = (n·ŝ + Γ·N̂) / n'              折射方向（向量形式）
U' = atan2(ŝ'_y, ŝ'_x)             折射后光线角
```

> 使用完整向量形式而非标量近似，处理所有入射角（含 cosI<0 的斜入射）。

### 4.3 像面落点

每条光线从最后一面交点传播到近轴像面：
```
dz = last_vertex_z + l' − last_hit_z     实际传播距离
L_image = L_last + dz · tan(U_last)
```

> **关键**：不同光线的 last_hit_z 不同（尤其轴外光线），不能用统一的 l' 传播。

---

## 5. 像差计算

> 文件：[aberration.py](../engine/aberration.py)

所有像差均通过追迹光线 → 像面交点 → 按 Zemax 定义计算。

### 5.1 球差 (Spherical Aberration)

```
δL' = d_cross(实际) − l'(近轴)         Zemax: LSA = z_ray − z_chief
```

- `spherical_aberration_full`：全孔径
- `spherical_aberration_0.7`：0.7 孔径

### 5.2 位置色差 (Longitudinal Chromatic Aberration)

```
Δl'_FC = l'_F(实际) − l'_C(实际)
```

- `axial_chromatic_full`：全孔径
- `axial_chromatic_0.7`：0.7 孔径
- `axial_chromatic_0`：0 孔径（退化为近轴 F−C）

### 5.3 子午彗差 (Meridional Coma)

```
K' = (y'_上光线 + y'_下光线) / 2 − y'_主光线
```

4 项：全视场/0.7视场 × 全孔径/0.7孔径。

### 5.4 实际像高

```
y'_actual = |L_image(主光线)|
```

2 视场 × 3 波长 = 6 项。

### 5.5 畸变 (Distortion)

```
绝对畸变：δy' = |y'_actual| − |y'_ideal|
相对畸变：δy' / |y'_ideal| × 100%
```

理想像高：
- 无限远：`y'_ideal = f' · tan(W)`（全视场）/ `f' · tan(0.7W)`（0.7 视场）
- 有限物距：`y'_ideal = 物高 × 横向放大率`

### 5.6 倍率色差 (Lateral Chromatic Aberration)

```
Δy'_FC = |y'_F| − |y'_C|
```

---

## 6. 场曲与像散（Coddington）

> 文件：[paraxial.py](../engine/paraxial.py) `_coddington_field_curvature()`

采用 **Coddington 细光束方程**沿主光线逐面追迹子午/弧矢焦点。

### Coddington 方程（球面）

**子午（Tangential）：**
```
n'·cos²I' / t' − n·cos²I / t = (n'·cosI' − n·cosI) / R
```

**弧矢（Sagittal）：**
```
n' / s' − n / s = (n'·cosI' − n·cosI) / R
```

其中 I、I' 为主光线在表面的入射角和折射角（锐角），t、s 为沿主光线的物距。

### 初始条件

| 物距 | t₀, s₀ |
|------|--------|
| 无限远 | ∞ |
| 有限物距 | −D_obj（发散光束，负值） |

其中 D_obj = √((pupil_z + L₀)² + (0 − y_obj)²)

### 面间转移

```
t_{k+1} = t'_k − D_k
s_{k+1} = s'_k − D_k
```

D_k 为主光线在面 k 和面 k+1 交点间的实际路径长度。

### 场曲和像散

```
xt' = z_tangential − z_image_plane
xs' = z_sagittal − z_image_plane
Δxts' = xt' − xs'
```

---

## 7. 全部输出参数

按 lensdata.csv 顺序排列，每物距 39 项。

### A. 近轴参数（12 项）

| # | 英文 key | 中文名 | 单位 | 公式 |
|---|----------|--------|------|------|
| 1 | `f_prime` | 像方焦距 f' | mm | −h/U'_last |
| 2 | `l_prime` | 像方截距 l' | mm | −L_last/U'_last |
| 3 | `lC_prime` | C 光近轴像位置 lC' | mm | 用 n_C 追迹 |
| 4 | `lF_prime` | F 光近轴像位置 lF' | mm | 用 n_F 追迹 |
| 5-10 | `axial_image_*` | 实际像点(d/F/C×全/0.7) | mm | 实际光线 d_cross |
| 11 | `lH_prime` | 后主面位置 lH' | mm | f' − l'_inf |
| 12 | `lp_prime` | 出瞳距 lp' | mm | 光阑中心追迹 |
| 13 | `y0_prime` | 0 视场近轴像高 | mm | 0（定义） |
| 14 | `y_full_prime` | 全视场近轴像高 | mm | 主光线落点 |
| 15 | `y07_prime` | 0.7 视场近轴像高 | mm | 主光线落点 |

### B. 轴上像差（11 项）

| # | 英文 key | 中文名 | 公式 |
|---|----------|--------|------|
| 16 | `spherical_aberration_0.7` | 0.7 孔径球差 | d_cross − l' |
| 17 | `spherical_aberration_full` | 全孔径球差 | d_cross − l' |
| 18 | `axial_chromatic_0.7` | 0.7 孔径位置色差 | l'_F − l'_C |
| 19 | `axial_chromatic_full` | 全孔径位置色差 | l'_F − l'_C |
| 20 | `axial_chromatic_0` | 0 孔径位置色差 | lF' − lC'（近轴） |

### C. 视场像差（16 项）

| # | 英文 key | 中文名 | 公式 |
|---|----------|--------|------|
| 21 | `xt_prime` | 子午场曲 xt' | Coddington |
| 22 | `xs_prime` | 弧矢场曲 xs' | Coddington |
| 23 | `delta_xts` | 像散 Δxts' | xt' − xs' |
| 24-29 | `image_height_*` | 实际像高(F/d/C×2视场) | \|L_image(主光线)\| |
| 30-31 | `relative_distortion_*` | 相对畸变 | (实际−理想)/理想×100% |
| 32-33 | `absolute_distortion_*` | 绝对畸变 | 实际−理想 |
| 34-35 | `lateral_chromatic_*` | 倍率色差 | \|y'_F\| − \|y'_C\| |
| 36-39 | `meridional_coma_*` | 子午彗差 | (y'_++y'_-)/2−y'_chief |

---

## 8. Zemax 规范对照

### 符号约定（与 Zemax 对齐）

| 项目 | 约定 |
|------|------|
| 球差 | `d_cross − l'`（实际−近轴） |
| 位置色差 | `l'_F − l'_C` |
| 畸变 | `\|实际\| − \|理想\|` |
| 倍率色差 | `\|y'_F\| − \|y'_C\|` |
| lH' | `f' − l'`（正值=主面在最后一面右侧） |
| 0.7 视场（无限远） | 0.7×视场角 → `f'·tan(0.7W)` |

### 禁止事项

- ❌ 使用理想像面替代实际像面
- ❌ 近轴主光线替代实际主光线
- ❌ 教材三阶像差公式作为最终结果
- ❌ 仅使用二维 L,U 作为最终追迹变量（Zemax 用三维）

### 校对顺序

1. f' 和 l'（基础参照）
2. 出瞳距 lp'
3. d 光实际像高
4. F/C 光实际像高
5. 其他孔径带光线和各像差

---

## 9. 调试记录

### 关键修复（2026-07-07 ~ 2026-07-08）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 实际像高偏差 ~2.4× | 标量 Snell 在 cosI<0 时符号错误 | 改用向量 Snell |
| 2 | 有限物距 l' 错误 | paraxial 忽略有限物距 | 追迹轴上物点光线 |
| 3 | lH' 符号反 | l'−f' vs f'−l' 约定不同 | 改为 f'−l' |
| 4 | SA 符号反 | l'−d_cross vs d_cross−l' | 对齐 Zemax |
| 5 | SA 量大 1.5% | 玻璃折射率（教材值 vs CDGM） | 更新为 CDGM 精确值 |
| 6 | 彗差偏差 ~4.7× | 像面传播距离用统一 l' | 每条光线用实际 dz |
| 7 | 有限物距光线初值偏差 | U 角偏移而非入瞳高度采样 | 改为 L-高度法 |
| 8 | 场曲偏差 >60% | Petzval 近似 | Coddington 细光束追迹 |
| 9 | l' 偏差 0.004mm | atan() vs ratio 与 paraxial 不一致 | 统一用 ratio |
| 10 | 0.7 视场偏差 ~0.05% | 0.7×像高 vs 0.7×视场角 | 改为视场角比例 |

### 校对用镜头（教材第四章）

| 面 | R (mm) | d (mm) | 玻璃 |
|----|--------|--------|------|
| 1 | 62.5 | 4.0 | H-K9L |
| 2 | -43.65 | 2.5 | H-ZF2 |
| 3 | -124.35 | — | Air |

- 入瞳与第一面重合，直径 20mm
- 无限远：半视场角 3°
- 有限物距：500mm，物高 26mm（0.7 视场 18.2mm）
- 玻璃折射率取自 CDGM-ZEMAX 202111 材料库
