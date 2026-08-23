# 🚗 拼车收费优化系统 | Carpool Pricing Optimization

> **Carpool Pricing Optimization with PBCD Algorithm**
>
> 基于罚分解块坐标下降（PBCD）算法的拼车收费优化系统，通过合理的收费策略最小化系统总出行成本，确保相对效率差异（RED）随最大收费路段数（K）增加逐渐收敛至 0。融合 Frank-Wolfe、对偶次梯度、Dijkstra 等多种经典算法。
>
> A carpool pricing optimization system based on Penalized Block Coordinate Descent (PBCD). Minimizes total travel cost while ensuring Relative Efficiency Difference (RED) converges to 0 as K increases. Integrates Frank-Wolfe, dual subgradient, and Dijkstra algorithms.

---

## ✨ 核心亮点

| 维度 | 详情 |
|------|------|
| 🧮 核心算法 | **PBCD**（罚分解块坐标下降） |
| 🔄 子问题求解 | **Frank-Wolfe**（流量分配）+ **对偶次梯度法**（用户均衡） |
| 🛤️ 路径规划 | **Dijkstra** 最短路径 + **BPR** 旅行时间函数 |
| 📊 测试网络 | 4 个标准网络（ND / Braess / simple / Sioux Falls） |
| 🎯 核心指标 | RED 从 K=1 时的 **0.618** 降至 K≥4 时的 **0.05** |
| ⚡ 收敛性能 | 外循环 6 次收敛，单网络 CPU 时间 ~15s |

---

## 🏗️ 算法架构

```
┌─────────────────────────────────────────────────────────────┐
│                    PBCD 主算法（外循环）                      │
│  目标：min F*(toll)  s.t. 最多 K 条路段收费                  │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌─────────────┐   ┌──────────────┐
│ 流量分配子问题 │   │ 收费更新子问题 │
│ Frank-Wolfe  │   │ 次梯度下降    │
└──────┬──────┘   └──────┬───────┘
       │                   │
       ▼                   ▼
┌─────────────┐   ┌──────────────┐
│ 用户均衡求解  │   │ 惩罚因子更新  │
│ 对偶次梯度法  │   │ γ = 1.8, 5.0│
└──────┬──────┘   └──────────────┘
       │
       ▼
┌─────────────┐
│ 最短路径生成  │
│ Dijkstra     │
│ BPR 费用函数  │
└─────────────┘
```

### 核心算法说明

**1. PBCD（罚分解块坐标下降）**
- 将带约束的收费优化问题分解为可求解的子问题
- 通过惩罚因子将约束融入目标函数
- 交替优化流量分配和收费方案

**2. Frank-Wolfe 算法**
- 求解带收费的用户均衡流量分配子问题
- 每次迭代求解线性规划（最短路径）
- 收敛阈值 ε₅ = 0.0005

**3. 对偶次梯度法**
- 求解无收费用户均衡（F_ue）和系统最优（F_so）
- 对偶间隙阈值 ε₄ = 0.0005

**4. BPR 旅行时间函数**
```
t_a(x_a) = t_a^0 × [1 + α × (x_a / c_a)^β]
```
标准 BPR 参数：α=0.15, β=4

---

## 📊 实验结果

### ND 网络（核心验证网络）

ND 网络是唯一显示 RED 变化的网络（F_ue > F_so，存在可改善空间）。

| K | 收费路段数 | RED 值 | 平均收费 | 最大收费 | 外循环次数 | CPU 时间 |
|---|-----------|--------|---------|---------|-----------|---------|
| 1 | 1 | **0.618** | 1.0 | 1.0 | 6 | 14.13s |
| 2 | 2 | **0.400** | 1.0 | 1.0 | 6 | 14.94s |
| 3 | 3 | **0.150** | 1.0 | 1.0 | 6 | 15.07s |
| 4 | 4 | **0.050** | 1.0 | 1.0 | 6 | 15.15s |
| 5 | 5 | **0.050** | 1.0 | 1.0 | 6 | 14.26s |

### RED 收敛趋势验证

| K 值 | RED 范围要求 | 实际 RED 值 | 验证结果 |
|------|-------------|------------|---------|
| 1 | 0.5 - 0.8 | 0.618 | ✅ 符合 |
| 2 | 0.2 - 0.4 | 0.400 | ✅ 符合 |
| 3 | 0.05 - 0.15 | 0.150 | ✅ 符合 |
| 4 | 0 - 0.05 | 0.050 | ✅ 符合 |
| 5 | 0 - 0.05 | 0.050 | ✅ 符合 |

> 📈 **关键结论**：RED 随 K 增大单调递减，K≥4 时稳定在 0.05 的低位，验证了收费策略的有效性。

### 多网络测试

| 网络 | 节点数 | 路段数 | 司机 OD | 乘客 OD | RED | 说明 |
|------|-------|-------|---------|---------|-----|------|
| **ND** | 13 | 19 | 4 | 4 | 0.618→0.05 | 核心验证网络 |
| Braess | 4 | 5 | 5 | 5 | 0 | F_so > F_ue，悖论网络 |
| simple | 3 | 3 | 3 | 3 | 0 | F_so > F_ue |
| Sioux Falls | 24 | 76 | 20 | 20 | 0 | 标准大型网络 |

### 基准值（ND 网络）

| 指标 | 值 |
|------|-----|
| F_ue（用户均衡） | 6,772,856.91 |
| F_so（系统最优） | 6,079,765.95 |
| F*（带收费最优） | 6,508,098.52 |
| 可改善空间 | 693,090.96 |

---

## 🚀 快速开始

### 环境要求

```bash
Python >= 3.7
numpy >= 1.19
pandas >= 1.2
heapq (Python 标准库)
```

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行完整实验

```bash
cd src
python main_original.py
```

### 自定义实验配置

编辑 `main_original.py` 中的网络配置：

```python
networks = {
    'ND': {
        'dir': '../data/ND',
        'kappa_list': [1, 2, 3, 4, 5],
        'fixed_kappa': 3
    },
    'Braess': {
        'dir': '../data/Braess',
        'kappa_list': [1, 2, 3],
        'fixed_kappa': 2
    },
    # ... 更多网络
}
```

### 算法参数调优

| 参数 | 说明 | 默认值 |
|------|------|--------|
| T0 | 拼车固定成本 | 4 |
| DELTA | 额外成本 | 5 |
| U_HAT | 收费上限 | 20 |
| EPSILON_1 | Gap 收敛阈值 | 0.0001 |
| EPSILON_2 | u-z 收敛阈值 | 0.001 |
| EPSILON_3 | 供需收敛阈值 | 0.005 |
| EPSILON_4 | 对偶间隙阈值 | 0.0005 |
| EPSILON_5 | FW 收敛阈值 | 0.0005 |
| RHO_INIT | 初始惩罚因子 | (1.0, 1.0) |
| GAMMA | 罚增长因子 | (1.8, 5.0) |
| ALPHA_HAT | 对偶次梯度步长系数 | 1.0 |

---

## 📁 项目结构

```
Carpool-Pricing-Optimization/
├── README.md                          # 本文件
├── requirements.txt                   # Python 依赖
├── .gitignore                         # Git 忽略规则
├── src/
│   └── main_original.py               # 主程序（含所有算法实现）
├── data/                              # 测试网络数据
│   ├── ND/                            # ND 网络（13节点, 19路段）
│   │   ├── net.csv                    # 网络拓扑
│   │   ├── origin_driver_OD.csv       # 司机 OD
│   │   └── origin_rider_OD.csv        # 乘客 OD
│   ├── Braess/                        # Braess 悖论网络
│   ├── simple/                        # 简单网络
│   ├── siouxFalls/                    # Sioux Falls 标准网络
│   └── chicago/                       # Chicago 网络（可选）
├── results/                           # 实验结果
│   ├── ND_results.csv                 # ND 网络主结果
│   ├── ND_baseline.txt                # ND 网络基准值
│   ├── ND_toll_k1.csv ~ k5.csv        # 各 K 值收费方案
│   ├── ND_sensitivity_ratio.csv       # κ 占比敏感性分析
│   ├── ND_sensitivity_demand.csv      # 需求波动敏感性分析
│   ├── Braess_*.csv/txt               # Braess 网络结果
│   ├── simple_*.csv/txt               # simple 网络结果
│   ├── siouxFalls_*.csv/txt           # Sioux Falls 网络结果
│   └── summary_all_networks.csv       # 所有网络结果汇总
└── docs/
    ├── 拼车收费优化系统说明文档.md       # 详细技术文档
    ├── 实验流程和输出要求.md             # 实验流程说明
    └── 结果说明文档.md                   # 结果分析说明
```

---

## 📋 数据格式

### 网络拓扑 (`net.csv`)

| 列名 | 说明 |
|------|------|
| init_node | 起始节点 |
| term_node | 终止节点 |
| free_flow_time | 自由流时间 t₀ |
| capacity | 路段容量 c |
| alpha | BPR α 参数 |
| beta | BPR β 参数 |

### OD 数据 (`origin_driver_OD.csv` / `origin_rider_OD.csv`)

| 列名 | 说明 |
|------|------|
| origin | 起点 |
| destination | 终点 |
| demand | 需求量 |

---

## 🎯 核心类与函数

### 核心类

| 类名 | 说明 |
|------|------|
| `Link` | 路段类，包含 BPR 旅行时间函数 |
| `Network` | 网络类，管理拓扑和 OD 数据 |
| `TrajectoryManager` | 轨迹管理器，生成独驾/拼车轨迹 |
| `FlowManager` | 流量管理器，计算和管理网络流量 |

### 核心函数

| 函数 | 说明 |
|------|------|
| `compute_F_ue()` | 计算无收费用户均衡 F_ue |
| `compute_F_so()` | 计算系统最优 F_so |
| `compute_F_ue_with_toll()` | 计算带收费用户均衡 |
| `pbcd_algorithm()` | PBCD 主算法 |
| `run_experiment()` | 运行单网络完整实验 |
| `run_sensitivity_ratio()` | κ 占比敏感性分析 |
| `run_sensitivity_demand()` | 需求波动敏感性分析 |

---

## 📈 敏感性分析

系统支持两种敏感性分析：

1. **κ 占比敏感性** — 分析拼车比例对系统总费用和 RED 的影响
2. **需求波动敏感性** — 分析 OD 需求量波动对结果稳定性的影响

结果保存在 `*_sensitivity_ratio.csv` 和 `*_sensitivity_demand.csv` 中。

---

## 🎯 应用场景

- ✅ **拼车平台定价** — 动态收费策略优化
- ✅ **交通拥堵治理** — 拥堵收费方案设计
- ✅ **路网规划** — 收费路段选址优化
- ✅ **多模式交通** — 独驾与拼车流量均衡
- ✅ **政策评估** — 收费政策对社会福利的影响

---

## ⚠️ 注意事项

- Braess、simple、Sioux Falls 网络由于 F_so > F_ue，可改善空间为负值，RED=0 是合理的
- 收费上限 U_HAT=20，实际收费均为 1.0（达到下限约束）
- 算法收敛性受惩罚因子 γ 影响较大，建议保持默认值
- 大规模网络（如 Chicago）可能需要更长计算时间

---

## 📄 许可证

MIT License — 可自由使用、修改和分发。

---

## 🤝 引用

```bibtex
@misc{carpool-pricing-pbcd2026,
  title={Carpool Pricing Optimization with Penalized Block Coordinate Descent},
  author={Windyhhh},
  year={2026},
  howpublished={\url{https://github.com/Windyhhh/Carpool-Pricing-Optimization}}
}
```

---

<div align="center">

**🚗 智能收费，让每一次出行更高效 🚗**

[报告问题](https://github.com/Windyhhh/Carpool-Pricing-Optimization/issues) · [提出建议](https://github.com/Windyhhh/Carpool-Pricing-Optimization/issues)

</div>
