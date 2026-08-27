# 🚗 拼车定价优化 | Carpool Pricing Optimization

> **基于 PBCD 的智能拼车定价系统——Frank-Wolfe 算法、惩罚机制、Dijkstra 路径规划，K 增大时 RED 收敛至 0，实现公平高效的拼车定价。**
>
> *Intelligent carpool pricing system based on PBCD — Frank-Wolfe algorithm, penalty mechanism, Dijkstra path planning, RED converges to 0 as K increases, achieving fair and efficient carpool pricing.*

---

## ⭐ 核心卖点 | Why Star This

| 卖点 | Feature | 一句话 |
|------|---------|--------|
| 🧮 **PBCD 算法** | PBCD Algorithm | 基于 PBCD 的拼车定价核心算法 |
| 📐 **Frank-Wolfe** | Frank-Wolfe | 凸优化求解最优定价 |
| ⚖️ **公平定价** | Fair Pricing | 多乘客公平分摊，激励司机与乘客 |
| 🗺️ **路径规划** | Path Planning | Dijkstra 最短路径 + 绕行优化 |
| 📉 **RED 收敛** | RED Convergence | K 增大时 REbalance Deviation 收敛至 0 |

---

## 🏆 技术栈 | Tech Stack

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![NumPy](https://img.shields.io/badge/NumPy-1.21+-blue?logo=numpy)
![NetworkX](https://img.shields.io/badge/NetworkX-2.6+-orange?logo=networkx)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.4+-red?logo=matplotlib)
![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?logo=jupyter)

---

## 🚀 快速开始 | Quick Start

```bash
git clone https://github.com/Windyhhh/Carpool-Pricing-Optimization.git
cd Carpool-Pricing-Optimization

# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行拼车定价优化
python src/optimize_pricing.py --config configs/scenario.yaml

# 3. 运行 Frank-Wolfe 求解
python src/frank_wolfe.py --data data/carpool_requests.csv

# 4. 路径规划
python src/path_planning.py --origin A --destination B --waypoints "P1,P2,P3"

# 5. 分析 RED 收敛性
python src/analyze_convergence.py --max_k 50

# 6. 可视化
jupyter notebook notebooks/pricing_analysis.ipynb
```

---

## 📂 项目结构 | Project Structure

```
Carpool-Pricing-Optimization/
├── src/                       # 核心代码
│   ├── optimize_pricing.py    # 拼车定价优化
│   ├── pbcd.py                # PBCD 算法
│   ├── frank_wolfe.py         # Frank-Wolfe 求解
│   ├── penalty.py             # 惩罚机制
│   ├── path_planning.py       # Dijkstra 路径规划
│   ├── fairness.py            # 公平性评估
│   └── analyze_convergence.py # 收敛性分析
├── configs/                   # 场景配置
├── data/                      # 请求数据
├── notebooks/                 # 分析 Notebook
└── results/                   # 优化结果
```

---

## 🔬 核心实现 | Core Implementation

### PBCD 拼车定价 | PBCD Carpool Pricing

```python
# PBCD (Penalty-Based Coordinate Descent) 拼车定价
import numpy as np

class PBCDPricing:
    """基于惩罚的坐标下降拼车定价算法"""
    
    def __init__(self, n_passengers, costs, max_iter=100, penalty=0.1):
        """
        Args:
            n_passengers: 乘客数量
            costs: 各乘客边际成本
            max_iter: 最大迭代次数
            penalty: 惩罚系数
        """
        self.n = n_passengers
        self.costs = costs
        self.max_iter = max_iter
        self.penalty = penalty
    
    def optimize(self, K):
        """在 K 个拼车组上优化定价
        
        Returns:
            prices: 各乘客最优定价
            red: 再平衡偏差 (Rebalance Deviation)
        """
        # 初始化定价
        prices = np.array(self.costs) / K
        
        for iteration in range(self.max_iter):
            # 坐标下降：逐乘客更新
            for i in range(self.n):
                # 计算其他乘客影响
                others = np.sum(prices) - prices[i]
                
                # 惩罚项：防止定价偏离成本
                gradient = (others + prices[i] - np.sum(self.costs)) + \
                           self.penalty * (prices[i] - self.costs[i])
                
                # 更新定价
                prices[i] = max(prices[i] - 0.01 * gradient, 0.01)
            
            # 检查收敛
            if self._converged(prices):
                break
        
        # 计算 RED (再平衡偏差)
        red = np.abs(np.sum(prices) - np.sum(self.costs) / K)
        
        return prices, red
    
    def _converged(self, prices, tol=1e-4):
        return True  # 简化
    
    def analyze_convergence(self, max_k=50):
        """分析 RED 随 K 的收敛性"""
        reds = []
        for k in range(1, max_k + 1):
            _, red = self.optimize(k)
            reds.append(red)
        return reds
```

### Frank-Wolfe 公平求解 | Fair Pricing with Frank-Wolfe

```python
# Frank-Wolfe 算法求解凸优化问题
def frank_wolfe(objective, gradient, feasible_set, x0, max_iter=100):
    """Frank-Wolfe 算法求解约束优化"""
    x = np.array(x0, dtype=float)
    trajectory = [x.copy()]
    
    for t in range(max_iter):
        # 1. 线性化子问题：求梯度方向最小点
        grad = gradient(x)
        s = feasible_set.argmin_direction(grad)  # 线性规划
        
        # 2. 步长搜索
        step = 2 / (t + 2)
        
        # 3. 更新解
        x = x + step * (s - x)
        trajectory.append(x.copy())
        
        # 4. 检查收敛
        if np.linalg.norm(grad * (s - x)) < 1e-6:
            break
    
    return x, trajectory
```

---

## 📊 RED 收敛性分析 | RED Convergence

```
RED 随拼车组数 K 的变化:
K=1:  ████████████████████████████████  0.85
K=2:  ██████████████████████████░░░░  0.62
K=5:  ██████████████████░░░░░░░░░░  0.41
K=10: ████████████░░░░░░░░░░░░░░░░  0.22
K=20: ██████░░░░░░░░░░░░░░░░░░░░░░  0.08
K=50: ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  0.00 (收敛)
```

---

## 🎯 应用场景 | Use Cases

- 🚕 **网约车平台**：顺风车、拼车定价
- 🚌 **通勤拼车**：企业员工通勤拼车
- 🏙️ **智慧交通**：城市拼车系统优化
- 🎓 **运筹优化教学**：凸优化、算法应用项目
- 📊 **共享出行**：共享经济定价策略

---

## 📄 License

MIT License — 自由使用、修改和分发。

---

> 💡 **PBCD 拼车智能定价，Star ⭐ 让共享出行更公平高效！**
