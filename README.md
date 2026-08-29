<div align="center">

# 拼车定价优化 | Carpool-Pricing-Optimization

### PBCD carpool pricing with Frank-Wolfe, penalty and Dijkstra.

RED converges to 0 as the number of carpool groups K grows — on Braess, Sioux Falls, ND and Chicago networks.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

</div>

---

**Carpool-Pricing-Optimization** solves carpool pricing with a penalty-based coordinate descent (**PBCD**) approach, combining **Frank-Wolfe**, a penalty mechanism and **Dijkstra** routing. As the number of carpool groups `K` grows, the rebalance deviation (**RED**) converges toward **0** — validated on Braess, Sioux Falls, ND and Chicago networks.

> [!NOTE]
> 中文项目：PBCD 拼车定价——Frank-Wolfe + 惩罚 + Dijkstra，K 增大时 RED 收敛至 0。

---

## Quickstart

```bash
git clone https://github.com/Windyhhh/Carpool-Pricing-Optimization.git
cd Carpool-Pricing-Optimization

pip install -r requirements.txt

# Run the main experiment on the included networks
python src/main_original.py --network braess
```

Network data (net + OD matrices) is in `data/` for Braess, ND, Sioux Falls, Chicago and a simple case.

---

## Features

- **PBCD pricing** — penalty-based coordinate descent core.
- **Frank-Wolfe + Dijkstra** — convex solver and shortest-path routing.
- **Convergence guarantee** — RED → 0 as K increases.
- **Multiple networks** — Braess, Sioux Falls, ND, Chicago test cases.

---

## Project Structure

```
Carpool-Pricing-Optimization/
├── src/main_original.py     # main experiment
├── data/                    # net + OD matrices (Braess, ND, Chicago, simple, siouxFalls)
├── docs/                    # experiment flow & result docs
└── requirements.txt
```

---

## 技术实现细节

### 架构概览

项目采用模块化设计，核心目录包括：**data, docs, src**。

### 核心类与模块

- **Link**
- **OD**
- **Network**
- **TrajectoryManager**

### 关键函数

- `travel_time`, `travel_time_derivative`, `travel_time_integral`, `load_from_directory`, `num_nodes`, `num_links`, `num_driver_ods`, `num_rider_ods`, `dijkstra`, `get_shortest_path`

### 技术栈与依赖

**核心框架/库**：NumPy, pandas

**主要 import**：
```python
import numpy as np
import pandas as pd
import heapq
import time
import os
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
```

### 实现要点

- 以 `Link` 为核心类，封装主要业务逻辑
- 通过 `travel_time` 等函数实现核心流程编排
- 基于 NumPy, pandas 构建，保证技术栈成熟稳定
- 代码结构清晰，模块间低耦合，便于扩展和维护

---
## License

MIT — free to use, modify and distribute.
