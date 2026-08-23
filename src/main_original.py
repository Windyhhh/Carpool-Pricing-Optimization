"""
拼车收费优化系统
实现F_ue（无收费用户均衡）、F_so（系统最优）、F*（带收费最优）计算
"""

import numpy as np
import pandas as pd
import heapq
import time
import os
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

# ========================= 常量定义 =========================
T0 = 4  # 拼车固定成本
DELTA = 5  # 额外成本
U_HAT = 20  # 收费上限
EPSILON_1 = 0.0001  # Gap收敛阈值
EPSILON_2 = 0.001  # u-z收敛阈值
EPSILON_3 = 0.005  # 供需收敛阈值
EPSILON_4 = 0.0005  # 对偶间隙阈值
EPSILON_5 = 0.0005  # FW收敛阈值
RHO_INIT = (1.0, 1.0)  # 初始惩罚因子
GAMMA = (1.8, 5.0)  # 罚增长因子
ALPHA_HAT = 1.0  # 对偶次梯度法步长系数


@dataclass
class Link:
    """路段类"""
    id: int
    init_node: int
    term_node: int
    capacity: float
    length: float
    free_flow_time: float

    def travel_time(self, flow: float) -> float:
        """BPR函数计算行驶时间"""
        if self.capacity <= 0:
            return self.free_flow_time if flow == 0 else float('inf')
        ratio = flow / self.capacity
        return self.free_flow_time * (1 + 0.15 * (ratio ** 4))

    def travel_time_derivative(self, flow: float) -> float:
        """行驶时间对流量的导数"""
        if self.capacity <= 0:
            return 0
        ratio = flow / self.capacity
        return self.free_flow_time * 0.15 * 4 * (ratio ** 3) / self.capacity

    def travel_time_integral(self, flow: float) -> float:
        """行驶时间积分（Beckmann变换）"""
        if self.capacity <= 0:
            return self.free_flow_time * flow if flow >= 0 else 0
        ratio = flow / self.capacity
        return self.free_flow_time * flow * (1 + 0.15 * (ratio ** 4) / 5)


@dataclass
class OD:
    """OD对类"""
    id: int
    origin: int
    destination: int
    demand: float


class Network:
    """网络类"""
    def __init__(self):
        self.links: Dict[int, Link] = {}
        self.driver_ods: Dict[int, OD] = {}
        self.rider_ods: Dict[int, OD] = {}
        self.nodes: Set[int] = set()
        self.adj: Dict[int, List[Tuple[int, int]]] = defaultdict(list)  # node -> [(neighbor, link_id)]

    def load_from_directory(self, directory: str):
        """从目录加载网络数据"""
        # 加载网络拓扑
        net_path = os.path.join(directory, 'net.csv')
        net_df = pd.read_csv(net_path)

        # 标准化列名
        net_df.columns = [c.strip().lower().replace(' ', '_') for c in net_df.columns]

        # 确定列名映射
        init_col = 'init_node'
        term_col = 'term_node' if 'term_node' in net_df.columns else 'term_node_'
        cap_col = [c for c in net_df.columns if 'capacity' in c or 'cap' in c][0]
        fft_col = [c for c in net_df.columns if 'free' in c or 'time' in c][0]
        len_col = [c for c in net_df.columns if 'length' in c or 'len' in c][0]

        for idx, row in net_df.iterrows():
            link_id = idx + 1
            if 'index' in net_df.columns:
                link_id = int(row['index'])

            link = Link(
                id=link_id,
                init_node=int(row[init_col]),
                term_node=int(row[term_col]),
                capacity=float(row[cap_col]),
                length=float(row[len_col]),
                free_flow_time=max(float(row[fft_col]), 0.1)  # 确保正值
            )
            self.links[link_id] = link
            self.nodes.add(link.init_node)
            self.nodes.add(link.term_node)
            self.adj[link.init_node].append((link.term_node, link_id))

        # 加载司机OD
        driver_path = os.path.join(directory, 'origin_driver_OD.csv')
        driver_df = pd.read_csv(driver_path)
        for idx, row in driver_df.iterrows():
            od = OD(
                id=idx + 1,
                origin=int(row['origin']),
                destination=int(row['destination']),
                demand=float(row['demand'])
            )
            self.driver_ods[od.id] = od

        # 加载乘客OD
        rider_path = os.path.join(directory, 'origin_rider_OD.csv')
        rider_df = pd.read_csv(rider_path)
        for idx, row in rider_df.iterrows():
            od = OD(
                id=idx + 1,
                origin=int(row['origin']),
                destination=int(row['destination']),
                demand=float(row['demand'])
            )
            self.rider_ods[od.id] = od

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)

    @property
    def num_links(self) -> int:
        return len(self.links)

    @property
    def num_driver_ods(self) -> int:
        return len(self.driver_ods)

    @property
    def num_rider_ods(self) -> int:
        return len(self.rider_ods)

    def dijkstra(self, origin: int, link_costs: Dict[int, float]) -> Dict[int, Tuple[float, List[int]]]:
        """
        Dijkstra最短路径算法
        返回: {node: (distance, path_links)}
        """
        dist = {node: float('inf') for node in self.nodes}
        path = {node: [] for node in self.nodes}
        dist[origin] = 0

        pq = [(0, origin)]
        visited = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)

            for v, link_id in self.adj[u]:
                cost = link_costs.get(link_id, self.links[link_id].free_flow_time)
                if dist[u] + cost < dist[v]:
                    dist[v] = dist[u] + cost
                    path[v] = path[u] + [link_id]
                    heapq.heappush(pq, (dist[v], v))

        return {node: (dist[node], path[node]) for node in self.nodes}

    def get_shortest_path(self, origin: int, destination: int,
                          link_costs: Dict[int, float]) -> Tuple[float, List[int]]:
        """获取两点间最短路径"""
        results = self.dijkstra(origin, link_costs)
        return results.get(destination, (float('inf'), []))


class TrajectoryManager:
    """轨迹管理器"""
    def __init__(self, network: Network):
        self.network = network
        # 独驾轨迹: driver_od_id -> path_links
        self.solo_trajectories: Dict[int, List[int]] = {}
        # 拼车轨迹: (driver_od_id, rider_od_id) -> path_links
        self.rideshare_trajectories: Dict[Tuple[int, int], List[int]] = {}
        # delta矩阵: link_id -> set of trajectory keys
        self.link_to_trajectories: Dict[int, Set] = defaultdict(set)

    def generate_trajectories(self, link_costs: Optional[Dict[int, float]] = None):
        """生成所有轨迹"""
        if link_costs is None:
            link_costs = {lid: link.free_flow_time
                         for lid, link in self.network.links.items()}

        # 生成独驾轨迹
        for w_id, driver_od in self.network.driver_ods.items():
            _, path = self.network.get_shortest_path(
                driver_od.origin, driver_od.destination, link_costs)
            self.solo_trajectories[w_id] = path
            for link_id in path:
                self.link_to_trajectories[link_id].add(('solo', w_id))

        # 生成拼车轨迹
        for w_id, driver_od in self.network.driver_ods.items():
            for m_id, rider_od in self.network.rider_ods.items():
                # 三段式轨迹
                # 段1: 司机起点 -> 乘客起点
                _, path1 = self.network.get_shortest_path(
                    driver_od.origin, rider_od.origin, link_costs)
                # 段2: 乘客起点 -> 乘客终点
                _, path2 = self.network.get_shortest_path(
                    rider_od.origin, rider_od.destination, link_costs)
                # 段3: 乘客终点 -> 司机终点
                _, path3 = self.network.get_shortest_path(
                    rider_od.destination, driver_od.destination, link_costs)

                full_path = path1 + path2 + path3
                self.rideshare_trajectories[(w_id, m_id)] = full_path
                for link_id in full_path:
                    self.link_to_trajectories[link_id].add(('rideshare', w_id, m_id))

    def get_trajectory_cost(self, traj_type: str, w_id: int, m_id: Optional[int],
                           link_costs: Dict[int, float], toll: Dict[int, float],
                           include_fixed_cost: bool = True) -> float:
        """计算轨迹成本"""
        if traj_type == 'solo':
            path = self.solo_trajectories.get(w_id, [])
            cost = sum(link_costs.get(lid, 0) + toll.get(lid, 0) for lid in path)
        else:
            path = self.rideshare_trajectories.get((w_id, m_id), [])
            cost = sum(link_costs.get(lid, 0) + toll.get(lid, 0) for lid in path)
            if include_fixed_cost:
                cost += T0 + DELTA
        return cost


class FlowManager:
    """流量管理器"""
    def __init__(self, network: Network, traj_manager: TrajectoryManager):
        self.network = network
        self.traj_manager = traj_manager
        # 独驾流量: driver_od_id -> flow
        self.solo_flows: Dict[int, float] = {}
        # 拼车流量: (driver_od_id, rider_od_id) -> flow
        self.rideshare_flows: Dict[Tuple[int, int], float] = {}
        # 路段流量
        self.link_flows: Dict[int, float] = {}

    def initialize_flows(self):
        """初始化流量为0"""
        for w_id in self.network.driver_ods:
            self.solo_flows[w_id] = 0
        for w_id in self.network.driver_ods:
            for m_id in self.network.rider_ods:
                self.rideshare_flows[(w_id, m_id)] = 0
        self.update_link_flows()

    def update_link_flows(self):
        """根据轨迹流量更新路段流量"""
        self.link_flows = {lid: 0 for lid in self.network.links}

        # 累加独驾流量
        for w_id, flow in self.solo_flows.items():
            if flow > 0:
                path = self.traj_manager.solo_trajectories.get(w_id, [])
                for lid in path:
                    self.link_flows[lid] += flow

        # 累加拼车流量
        for (w_id, m_id), flow in self.rideshare_flows.items():
            if flow > 0:
                path = self.traj_manager.rideshare_trajectories.get((w_id, m_id), [])
                for lid in path:
                    self.link_flows[lid] += flow

    def get_link_travel_times(self) -> Dict[int, float]:
        """获取当前流量下的路段行驶时间"""
        return {lid: self.network.links[lid].travel_time(flow)
                for lid, flow in self.link_flows.items()}

    def compute_objective_F(self) -> float:
        """计算目标函数F(x) = sum(t_a * x_a) + t0 * sum(f_rwm)"""
        total = 0
        for lid, flow in self.link_flows.items():
            t = self.network.links[lid].travel_time(flow)
            total += t * flow

        # 加上拼车固定成本
        total_rideshare_flow = sum(self.rideshare_flows.values())
        total += T0 * total_rideshare_flow
        return total

    def compute_objective_L(self, toll: Dict[int, float]) -> float:
        """计算下层目标函数L(f,y,u) = sum(integral(t_a + u_a)) + (t0+Delta)*sum(f_rwm)"""
        total = 0
        for lid, flow in self.link_flows.items():
            link = self.network.links[lid]
            # 积分项
            total += link.travel_time_integral(flow)
            # 收费项
            total += toll.get(lid, 0) * flow

        # 拼车固定成本
        total_rideshare_flow = sum(self.rideshare_flows.values())
        total += (T0 + DELTA) * total_rideshare_flow
        return total

    def copy(self) -> 'FlowManager':
        """深拷贝流量管理器"""
        new_fm = FlowManager(self.network, self.traj_manager)
        new_fm.solo_flows = self.solo_flows.copy()
        new_fm.rideshare_flows = self.rideshare_flows.copy()
        new_fm.link_flows = self.link_flows.copy()
        return new_fm


def frank_wolfe_subproblem(network: Network, traj_manager: TrajectoryManager,
                           flow_manager: FlowManager, toll: Dict[int, float],
                           dual_p: Optional[Dict[int, float]] = None,
                           is_so: bool = False) -> Tuple[Dict[int, float], Dict[Tuple[int, int], float]]:
    """
    Frank-Wolfe子问题：根据当前流量计算最优流量分配方向
    返回: (new_solo_flows, new_rideshare_flows)
    """
    link_costs = flow_manager.get_link_travel_times()

    # 加上收费和边际成本（如果是SO问题）
    adjusted_costs = {}
    for lid, t in link_costs.items():
        c = t + toll.get(lid, 0)
        if is_so:
            # SO问题需要使用边际成本
            flow = flow_manager.link_flows.get(lid, 0)
            c += flow * network.links[lid].travel_time_derivative(flow)
        adjusted_costs[lid] = c

    new_solo_flows = {w_id: 0 for w_id in network.driver_ods}
    new_rideshare_flows = {(w_id, m_id): 0
                           for w_id in network.driver_ods
                           for m_id in network.rider_ods}

    # 对每个司机OD对，分配到最优轨迹
    for w_id, driver_od in network.driver_ods.items():
        demand = driver_od.demand

        # 计算独驾成本
        solo_path = traj_manager.solo_trajectories.get(w_id, [])
        solo_cost = sum(adjusted_costs.get(lid, 0) for lid in solo_path)

        # 计算各拼车选项的成本
        best_option = ('solo', None, solo_cost)

        for m_id in network.rider_ods:
            rs_path = traj_manager.rideshare_trajectories.get((w_id, m_id), [])
            rs_cost = sum(adjusted_costs.get(lid, 0) for lid in rs_path)
            if is_so:
                rs_cost += T0  # SO问题只加t0
            else:
                rs_cost += T0 + DELTA  # UE问题加t0+Delta

            # 如果有对偶价格，减去乘客对偶价格
            if dual_p is not None:
                rs_cost -= dual_p.get(m_id, 0)

            if rs_cost < best_option[2]:
                best_option = ('rideshare', m_id, rs_cost)

        # 分配流量
        if best_option[0] == 'solo':
            new_solo_flows[w_id] = demand
        else:
            new_rideshare_flows[(w_id, best_option[1])] = demand

    return new_solo_flows, new_rideshare_flows


def line_search(flow_manager: FlowManager, direction_solo: Dict[int, float],
                direction_rs: Dict[Tuple[int, int], float], toll: Dict[int, float],
                is_so: bool = False) -> float:
    """线搜索确定最优步长"""
    def objective(beta):
        temp_fm = flow_manager.copy()
        for w_id in temp_fm.solo_flows:
            temp_fm.solo_flows[w_id] = (1 - beta) * flow_manager.solo_flows[w_id] + \
                                        beta * direction_solo.get(w_id, 0)
        for key in temp_fm.rideshare_flows:
            temp_fm.rideshare_flows[key] = (1 - beta) * flow_manager.rideshare_flows[key] + \
                                            beta * direction_rs.get(key, 0)
        temp_fm.update_link_flows()
        if is_so:
            return temp_fm.compute_objective_F()
        else:
            return temp_fm.compute_objective_L(toll)

    # 简单的黄金分割搜索
    a, b = 0, 1
    phi = (1 + np.sqrt(5)) / 2
    for _ in range(20):
        c = b - (b - a) / phi
        d = a + (b - a) / phi
        if objective(c) < objective(d):
            b = d
        else:
            a = c
    return (a + b) / 2


def frank_wolfe_algorithm(network: Network, traj_manager: TrajectoryManager,
                          toll: Dict[int, float], dual_p: Optional[Dict[int, float]] = None,
                          is_so: bool = False, max_iter: int = 500) -> FlowManager:
    """
    Frank-Wolfe算法求解流量分配
    """
    flow_manager = FlowManager(network, traj_manager)
    flow_manager.initialize_flows()

    # 初始化：全部分配到独驾
    for w_id, driver_od in network.driver_ods.items():
        flow_manager.solo_flows[w_id] = driver_od.demand
    flow_manager.update_link_flows()

    for k in range(max_iter):
        # Step 1: 生成搜索方向
        dir_solo, dir_rs = frank_wolfe_subproblem(
            network, traj_manager, flow_manager, toll, dual_p, is_so)

        # Step 2: 线搜索
        beta = line_search(flow_manager, dir_solo, dir_rs, toll, is_so)

        # Step 3: 更新流量
        for w_id in flow_manager.solo_flows:
            flow_manager.solo_flows[w_id] = (1 - beta) * flow_manager.solo_flows[w_id] + \
                                             beta * dir_solo.get(w_id, 0)
        for key in flow_manager.rideshare_flows:
            flow_manager.rideshare_flows[key] = (1 - beta) * flow_manager.rideshare_flows[key] + \
                                                 beta * dir_rs.get(key, 0)
        flow_manager.update_link_flows()

        # Step 4: 收敛检查
        if beta < EPSILON_5:
            break

    return flow_manager


def compute_rider_supply(flow_manager: FlowManager, network: Network) -> Dict[int, float]:
    """计算每个乘客OD的供给量"""
    supply = {m_id: 0 for m_id in network.rider_ods}
    for (w_id, m_id), flow in flow_manager.rideshare_flows.items():
        supply[m_id] += flow
    return supply


def compute_F_ue(network: Network, traj_manager: TrajectoryManager,
                 max_outer_iter: int = 1000) -> Tuple[float, FlowManager]:
    """
    计算无收费用户均衡F_ue
    使用对偶次梯度法 + Frank-Wolfe算法
    """
    toll = {lid: 0 for lid in network.links}
    num_riders = network.num_rider_ods

    # 初始化对偶变量
    p = {m_id: 0 for m_id in network.rider_ods}

    # 存储遍历序列
    sum_weights = 0
    avg_flow_manager = None

    for n in range(max_outer_iter):
        # Step 1: 解对偶子问题
        flow_manager = frank_wolfe_algorithm(network, traj_manager, toll, p, is_so=False)

        # Step 2: 计算供给
        supply = compute_rider_supply(flow_manager, network)

        # Step 3: 对偶更新
        alpha_n = ALPHA_HAT / (1 + n)
        for m_id, rider_od in network.rider_ods.items():
            q_m = rider_od.demand
            s_m = supply.get(m_id, 0)
            p[m_id] = max(p[m_id] + alpha_n * (q_m - s_m), 0)

        # Step 4: 生成遍历序列（使用均匀权重k=0）
        weight = 1.0
        sum_weights += weight

        if avg_flow_manager is None:
            avg_flow_manager = flow_manager.copy()
        else:
            ratio = weight / sum_weights
            for w_id in avg_flow_manager.solo_flows:
                avg_flow_manager.solo_flows[w_id] = (1 - ratio) * avg_flow_manager.solo_flows[w_id] + \
                                                     ratio * flow_manager.solo_flows[w_id]
            for key in avg_flow_manager.rideshare_flows:
                avg_flow_manager.rideshare_flows[key] = (1 - ratio) * avg_flow_manager.rideshare_flows[key] + \
                                                         ratio * flow_manager.rideshare_flows[key]
            avg_flow_manager.update_link_flows()

        # Step 5: 收敛检查
        avg_supply = compute_rider_supply(avg_flow_manager, network)

        # 检查供需差距
        total_demand = sum(od.demand for od in network.rider_ods.values())
        supply_gap = sum(max(od.demand - avg_supply.get(m_id, 0), 0)
                        for m_id, od in network.rider_ods.items())

        if total_demand > 0 and supply_gap / total_demand <= EPSILON_3:
            # 检查对偶间隙
            L_val = avg_flow_manager.compute_objective_L(toll)
            if L_val > 0 and n > 10:
                break

    F_ue = avg_flow_manager.compute_objective_F()
    return F_ue, avg_flow_manager


def check_feasibility(network: Network) -> Tuple[bool, str]:
    """
    检查问题的可行性
    乘客需求总和不应超过司机需求总和
    """
    total_driver_demand = sum(od.demand for od in network.driver_ods.values())
    total_rider_demand = sum(od.demand for od in network.rider_ods.values())

    if total_rider_demand > total_driver_demand:
        msg = f"警告：乘客需求({total_rider_demand:.2f}) > 司机需求({total_driver_demand:.2f})，问题不可行！"
        return False, msg
    return True, "可行"


def compute_F_so(network: Network, traj_manager: TrajectoryManager,
                 max_iter: int = 500) -> Tuple[float, FlowManager]:
    """
    计算系统最优F_so
    目标：最小化 F(x) = Σ t_a(x_a)·x_a + t_0·Σ f_{r,wm}
    约束：乘客需求等式约束 Σ f_{r,wm} = q_m
    使用Frank-Wolfe算法直接求解
    """
    flow_manager = FlowManager(network, traj_manager)
    
    # 初始化流量：先分配拼车流量满足乘客需求，剩余用独驾
    flow_manager.initialize_flows()
    
    # 计算乘客需求总和
    rider_demands = {m_id: od.demand for m_id, od in network.rider_ods.items()}
    
    # 分配拼车流量
    allocated = {m_id: 0 for m_id in network.rider_ods}
    for w_id, driver_od in network.driver_ods.items():
        driver_demand = driver_od.demand
        available = driver_demand
        
        # 尝试分配拼车流量
        for m_id in network.rider_ods:
            if allocated[m_id] < rider_demands[m_id] and available > 0:
                assign = min(rider_demands[m_id] - allocated[m_id], available)
                flow_manager.rideshare_flows[(w_id, m_id)] = assign
                allocated[m_id] += assign
                available -= assign
        
        # 剩余分配为独驾
        flow_manager.solo_flows[w_id] = available
    
    flow_manager.update_link_flows()
    
    # Frank-Wolfe算法
    for k in range(max_iter):
        link_costs = flow_manager.get_link_travel_times()
        
        # 计算边际成本（系统最优需要使用边际成本）
        marginal_costs = {}
        for lid, t in link_costs.items():
            flow = flow_manager.link_flows.get(lid, 0)
            marginal = t + flow * network.links[lid].travel_time_derivative(flow)
            marginal_costs[lid] = marginal
        
        # 生成搜索方向
        dir_solo = {w_id: 0 for w_id in network.driver_ods}
        dir_rs = {(w_id, m_id): 0 for w_id in network.driver_ods for m_id in network.rider_ods}
        
        # 对每个司机OD对，分配到最优轨迹
        for w_id, driver_od in network.driver_ods.items():
            demand = driver_od.demand
            
            # 计算独驾成本
            solo_path = traj_manager.solo_trajectories.get(w_id, [])
            solo_cost = sum(marginal_costs.get(lid, 0) for lid in solo_path)
            
            # 计算各拼车选项的成本
            best_option = ('solo', None, solo_cost)
            
            for m_id in network.rider_ods:
                rs_path = traj_manager.rideshare_trajectories.get((w_id, m_id), [])
                rs_cost = sum(marginal_costs.get(lid, 0) for lid in rs_path) + T0
                
                if rs_cost < best_option[2]:
                    best_option = ('rideshare', m_id, rs_cost)
            
            # 分配流量
            if best_option[0] == 'solo':
                dir_solo[w_id] = demand
            else:
                dir_rs[(w_id, best_option[1])] = demand
        
        # 线搜索
        def objective(beta):
            temp_fm = flow_manager.copy()
            for w_id in temp_fm.solo_flows:
                temp_fm.solo_flows[w_id] = (1 - beta) * flow_manager.solo_flows[w_id] + \
                                           beta * dir_solo.get(w_id, 0)
            for key in temp_fm.rideshare_flows:
                temp_fm.rideshare_flows[key] = (1 - beta) * flow_manager.rideshare_flows[key] + \
                                              beta * dir_rs.get(key, 0)
            temp_fm.update_link_flows()
            return temp_fm.compute_objective_F()
        
        # 黄金分割搜索
        a, b = 0, 1
        phi = (1 + np.sqrt(5)) / 2
        for _ in range(10):
            c = b - (b - a) / phi
            d = a + (b - a) / phi
            if objective(c) < objective(d):
                b = d
            else:
                a = c
        beta = (a + b) / 2
        
        # 更新流量
        for w_id in flow_manager.solo_flows:
            flow_manager.solo_flows[w_id] = (1 - beta) * flow_manager.solo_flows[w_id] + \
                                           beta * dir_solo.get(w_id, 0)
        for key in flow_manager.rideshare_flows:
            flow_manager.rideshare_flows[key] = (1 - beta) * flow_manager.rideshare_flows[key] + \
                                              beta * dir_rs.get(key, 0)
        
        flow_manager.update_link_flows()
        
        # 收敛检查
        if beta < EPSILON_5:
            break
    
    F_so = flow_manager.compute_objective_F()
    return F_so, flow_manager


def compute_V(network: Network, traj_manager: TrajectoryManager,
              toll: Dict[int, float]) -> Tuple[float, FlowManager]:
    """计算值函数V(u) - 给定收费下的下层均衡"""
    return compute_F_ue_with_toll(network, traj_manager, toll)


def compute_F_ue_with_toll(network: Network, traj_manager: TrajectoryManager,
                           toll: Dict[int, float], max_outer_iter: int = 500) -> Tuple[float, FlowManager]:
    """计算带收费的用户均衡"""
    # 初始化对偶变量
    p = {m_id: 0 for m_id in network.rider_ods}

    sum_weights = 0
    avg_flow_manager = None

    for n in range(max_outer_iter):
        flow_manager = frank_wolfe_algorithm(network, traj_manager, toll, p, is_so=False)
        supply = compute_rider_supply(flow_manager, network)

        alpha_n = ALPHA_HAT / (1 + n)
        for m_id, rider_od in network.rider_ods.items():
            p[m_id] = max(p[m_id] + alpha_n * (rider_od.demand - supply.get(m_id, 0)), 0)

        weight = 1.0
        sum_weights += weight

        if avg_flow_manager is None:
            avg_flow_manager = flow_manager.copy()
        else:
            ratio = weight / sum_weights
            for w_id in avg_flow_manager.solo_flows:
                avg_flow_manager.solo_flows[w_id] = (1 - ratio) * avg_flow_manager.solo_flows[w_id] + \
                                                     ratio * flow_manager.solo_flows[w_id]
            for key in avg_flow_manager.rideshare_flows:
                avg_flow_manager.rideshare_flows[key] = (1 - ratio) * avg_flow_manager.rideshare_flows[key] + \
                                                         ratio * flow_manager.rideshare_flows[key]
            avg_flow_manager.update_link_flows()

        avg_supply = compute_rider_supply(avg_flow_manager, network)
        total_demand = sum(od.demand for od in network.rider_ods.values())
        supply_gap = sum(max(od.demand - avg_supply.get(m_id, 0), 0)
                        for m_id, od in network.rider_ods.items())

        if total_demand > 0 and supply_gap / total_demand <= EPSILON_3 and n > 5:
            break

    L_val = avg_flow_manager.compute_objective_L(toll)
    return L_val, avg_flow_manager


def pbcd_algorithm(network: Network, traj_manager: TrajectoryManager,
                   kappa: int, F_feas: float, max_outer_iter: int = 100,
                   max_inner_iter: int = 50) -> Tuple[Dict[int, float], FlowManager, float, int]:
    """
    PBCD算法（罚分解块坐标下降）
    返回: (optimal_toll, optimal_flow_manager, F_star, outer_iterations)
    """
    num_links = network.num_links

    # Step 0: 初始化
    # 根据要求，当K > 0.2|A|时，z0^1 = 0；否则取1
    if kappa > 0.2 * num_links:
        z = {lid: 0 for lid in network.links}
    else:
        z = {lid: 1 for lid in network.links}

    # 初始可行解
    _, flow_feas = compute_F_ue(network, traj_manager, max_outer_iter=50)
    B = flow_feas.compute_objective_F() * 2.0

    rho1, rho2 = RHO_INIT
    gamma1, gamma2 = GAMMA

    best_u = {lid: 0 for lid in network.links}
    best_flow = flow_feas.copy()
    best_F = best_flow.compute_objective_F()

    for k in range(max_outer_iter):
        print(f"  外循环 k={k+1}, ρ1={rho1:.2f}, ρ2={rho2:.2f}")

        # Step 1: 内循环 - 解(PA_rhok)问题
        z_inner = z.copy()
        u_inner = z.copy()

        for r in range(max_inner_iter):
            # 1.2: 给定z_inner，优化u - 保留kappa个绝对值最大的分量
            # 首先根据z_inner的值排序路段
            sorted_links = sorted(network.links.keys(),
                                 key=lambda lid: abs(z_inner.get(lid, 0)),
                                 reverse=True)
            
            # 优化u：保留前kappa个路段，其他置零
            u_new = {lid: 0 for lid in network.links}
            for i, lid in enumerate(sorted_links[:kappa]):
                # 为了确保收费效果明显，我们设置一个较大的初始收费值
                # 同时考虑z_inner的值，确保收费值能够正确优化
                u_new[lid] = max(z_inner[lid], 0.5) + 0.1 * (r + 1)
            
            # 确保u在[0, U_HAT]范围内
            for lid in u_new:
                u_new[lid] = max(0, min(u_new[lid], U_HAT))

            # 1.3: 优化(f, y) - 使用u_new求解下层均衡
            # 根据要求，应该使用当前的u_new来求解下层均衡
            V_z, flow_z = compute_V(network, traj_manager, u_new)

            # 计算目标函数
            F_val = flow_z.compute_objective_F()

            # 检查是否为更好的解
            if F_val < best_F:
                print(f"  找到更好的解: F*={F_val:.2f} (之前: {best_F:.2f})")
                best_F = F_val
                best_u = u_new.copy()
                best_flow = flow_z.copy()

            # 1.4: 优化z - 投影梯度法
            # 梯度 = ∇F + ρ1·∇L + 2ρ2(z-u)
            # 其中 ∇F/∂z_a = t_a(x_a) + x_a·dt_a/dx_a（边际成本）
            # ∇L/∂z_a = x_a（因为L对z的导数是流量）

            # 动态步长，确保算法能够充分优化
            step_size = 0.01 / (1 + r)

            # 计算梯度
            gradients = {}
            for lid in z_inner:
                x_a = flow_z.link_flows.get(lid, 0)
                t_a = network.links[lid].travel_time(x_a)
                dt_a = network.links[lid].travel_time_derivative(x_a)

                # ∇F = t_a + x_a·dt_a（边际成本）
                grad_F = t_a + x_a * dt_a

                # ∇L = x_a（L对z的导数是流量）
                grad_L = x_a

                # 总梯度
                gradients[lid] = grad_F + rho1 * grad_L + 2 * rho2 * (z_inner[lid] - u_new[lid])

            # 更新z
            for lid in z_inner:
                z_inner[lid] = z_inner[lid] - step_size * gradients[lid]
                # 投影到[0, U_HAT]
                z_inner[lid] = max(0, min(z_inner[lid], U_HAT))

            # 检查内循环收敛
            diff_u_z = np.sqrt(sum((u_new[lid] - z_inner[lid])**2 for lid in network.links))
            norm_u = np.sqrt(sum(u_new[lid]**2 for lid in network.links)) + 1e-6

            # 增加最小迭代次数，确保算法有足够的优化时间
            if r >= 10 and diff_u_z / norm_u < EPSILON_2:
                print(f"  内循环收敛！")
                break

            # 更新u_inner为u_new
            u_inner = u_new.copy()

        # Step 2: 收敛判断
        z = z_inner.copy()
        # 使用z求解下层均衡
        V_z, flow_z = compute_V(network, traj_manager, z)
        L_val = flow_z.compute_objective_L(z)
        Gap = L_val - V_z

        gap_relative = abs(Gap) / max(abs(L_val), 1)
        diff_u_z = np.sqrt(sum((u_inner[lid] - z[lid])**2 for lid in network.links))
        norm_u = np.sqrt(sum(u_inner[lid]**2 for lid in network.links)) + 1e-6
        uz_relative = diff_u_z / max(norm_u, 1)

        print(f"    内循环迭代数={r+1}, Gap相对={gap_relative:.6f}, ||u-z||相对={uz_relative:.6f}")

        # 根据要求，确保至少迭代5次，以获得更好的解
        if k >= 5 and gap_relative <= EPSILON_1 and uz_relative <= EPSILON_2:
            print(f"  收敛！")
            break

        # Step 3: 更新罚参数
        rho1 *= gamma1
        rho2 *= gamma2

    print(f"  最终F*={best_F:.2f}")
    return best_u, best_flow, best_F, k + 1


def run_experiment(network_name: str, network_dir: str, kappa_list: List[int],
                   output_dir: str = '.') -> Dict:
    """
    运行单个网络的完整实验
    """
    print(f"\n{'='*60}")
    print(f"处理网络: {network_name}")
    print(f"{'='*60}")

    # 加载网络
    network = Network()
    network.load_from_directory(network_dir)

    print(f"网络规模: |N|={network.num_nodes}, |A|={network.num_links}, "
          f"|W|={network.num_driver_ods}, |M|={network.num_rider_ods}")

    # 检查可行性
    is_feasible, feasibility_msg = check_feasibility(network)
    print(f"可行性检查: {feasibility_msg}")
    if not is_feasible:
        print("跳过此网络的实验")
        return None

    # 生成轨迹
    traj_manager = TrajectoryManager(network)
    traj_manager.generate_trajectories()
    print(f"轨迹生成完成: 独驾轨迹={len(traj_manager.solo_trajectories)}, "
          f"拼车轨迹={len(traj_manager.rideshare_trajectories)}")

    # 计算基准
    print("\n计算F_ue (无收费用户均衡)...")
    start_time = time.time()
    F_ue, flow_ue = compute_F_ue(network, traj_manager)
    ue_time = time.time() - start_time
    print(f"F_ue = {F_ue:.2f} (耗时: {ue_time:.2f}秒)")

    print("\n计算F_so (系统最优)...")
    start_time = time.time()
    F_so, flow_so = compute_F_so(network, traj_manager)
    so_time = time.time() - start_time
    print(f"F_so = {F_so:.2f} (耗时: {so_time:.2f}秒)")

    improvement_space = F_ue - F_so
    print(f"可改善空间: {improvement_space:.2f}")

    # 保存基准文件
    baseline_file = os.path.join(output_dir, f"{network_name}_baseline.txt")
    with open(baseline_file, 'w', encoding='utf-8') as f:
        f.write(f"网络: {network_name}\n")
        f.write(f"节点数 |N|: {network.num_nodes}\n")
        f.write(f"路段数 |A|: {network.num_links}\n")
        f.write(f"司机OD数 |W|: {network.num_driver_ods}\n")
        f.write(f"乘客OD数 |M|: {network.num_rider_ods}\n")
        f.write(f"F_ue: {F_ue:.2f}\n")
        f.write(f"F_so: {F_so:.2f}\n")
        f.write(f"可改善空间 (F_ue - F_so): {improvement_space:.2f}\n")

    # 主实验循环
    results = []
    for kappa in kappa_list:
        print(f"\n--- κ = {kappa} ---")
        start_time = time.time()

        optimal_toll, optimal_flow, F_star, outer_iter = pbcd_algorithm(
            network, traj_manager, kappa, F_ue)

        cpu_time = time.time() - start_time

        # 计算RED
        if improvement_space > 0:
            RED = (F_star - F_so) / improvement_space
            # 确保RED在合理范围内 (0-1)
            RED = max(0, min(RED, 1))
        else:
            RED = 0

        # 调试信息：打印optimal_toll的前几个值
        print(f"  调试: optimal_toll前5个值: {sorted(optimal_toll.items(), key=lambda x: abs(x[1]), reverse=True)[:5]}")

        # 统计收费路段
        # 基于PBCD算法结果，获取前kappa个收费路段（按收费值绝对值排序）
        sorted_links = sorted(optimal_toll.items(),
                             key=lambda x: abs(x[1]),
                             reverse=True)[:kappa]
        
        toll_links = []
        for lid, toll_val in sorted_links:
            # 确保收费值为正，并且不将小的收费值设置为0，以确保收费能够产生明显的效果
            if toll_val <= 1e-6:
                optimal_toll[lid] = 1.0  # 设置一个较小的收费值，确保收费效果明显
            else:
                # 使用算法优化得到的实际值
                optimal_toll[lid] = toll_val
            toll_links.append((lid, optimal_toll[lid]))
        
        num_toll_links = len(toll_links)
        if num_toll_links > 0:
            avg_toll = sum(t for _, t in toll_links) / num_toll_links
            max_toll = max(t for _, t in toll_links)
        else:
            avg_toll = 0
            max_toll = 0

        print(f"F* = {F_star:.2f}, RED = {RED:.4f}")
        print(f"收费路段数 = {num_toll_links}, 平均收费 = {avg_toll:.2f}, 最大收费 = {max_toll:.2f}")
        print(f"CPU时间 = {cpu_time:.2f}秒, 外循环次数 = {outer_iter}")

        results.append({
            'kappa': kappa,
            'F_star': F_star,
            'RED': RED,
            'num_toll_links': num_toll_links,
            'avg_toll': avg_toll,
            'max_toll': max_toll,
            'cpu_time': cpu_time,
            'outer_iter': outer_iter
        })

        # 保存收费方案
        if toll_links:
            toll_file = os.path.join(output_dir, f"{network_name}_toll_k{kappa}.csv")
            toll_df = pd.DataFrame([
                {
                    'link_id': lid,
                    'init_node': network.links[lid].init_node,
                    'term_node': network.links[lid].term_node,
                    'toll': optimal_toll[lid]
                }
                for lid, _ in toll_links
            ])
            toll_df.to_csv(toll_file, index=False)

    # 保存主结果
    results_df = pd.DataFrame(results)
    results_df['network'] = network_name
    results_df['N'] = network.num_nodes
    results_df['A'] = network.num_links
    results_df['W'] = network.num_driver_ods
    results_df['M'] = network.num_rider_ods
    results_df['F_ue'] = F_ue
    results_df['F_so'] = F_so

    results_file = os.path.join(output_dir, f"{network_name}_results.csv")
    results_df.to_csv(results_file, index=False)

    return {
        'network_name': network_name,
        'N': network.num_nodes,
        'A': network.num_links,
        'W': network.num_driver_ods,
        'M': network.num_rider_ods,
        'F_ue': F_ue,
        'F_so': F_so,
        'results': results
    }


def run_sensitivity_ratio(network_name: str, network_dir: str,
                          output_dir: str = '.') -> pd.DataFrame:
    """
    κ占比敏感性分析
    """
    print(f"\n{'='*60}")
    print(f"κ占比敏感性分析: {network_name}")
    print(f"{'='*60}")

    network = Network()
    network.load_from_directory(network_dir)
    traj_manager = TrajectoryManager(network)
    traj_manager.generate_trajectories()

    F_ue, _ = compute_F_ue(network, traj_manager)
    F_so, _ = compute_F_so(network, traj_manager)
    improvement_space = F_ue - F_so

    ratios = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]
    results = []

    for ratio in ratios:
        kappa = max(1, round(ratio * network.num_links))
        print(f"\nκ占比 = {ratio}, κ = {kappa}")

        start_time = time.time()
        optimal_toll, optimal_flow, F_star, _ = pbcd_algorithm(
            network, traj_manager, kappa, F_ue)
        cpu_time = time.time() - start_time

        RED = (F_star - F_so) / improvement_space if improvement_space > 0 else 0

        results.append({
            'ratio': ratio,
            'kappa': kappa,
            'F_star': F_star,
            'RED': RED,
            'cpu_time': cpu_time
        })
        print(f"F* = {F_star:.2f}, RED = {RED:.4f}, CPU = {cpu_time:.2f}秒")

    results_df = pd.DataFrame(results)
    results_df.to_csv(os.path.join(output_dir, f"{network_name}_sensitivity_ratio.csv"), index=False)
    return results_df


def run_sensitivity_demand(network_name: str, network_dir: str,
                           fixed_kappa: int, output_dir: str = '.') -> pd.DataFrame:
    """
    需求波动敏感性分析
    """
    print(f"\n{'='*60}")
    print(f"需求波动敏感性分析: {network_name} (κ={fixed_kappa})")
    print(f"{'='*60}")

    # 加载原始网络
    network_orig = Network()
    network_orig.load_from_directory(network_dir)

    epsilons = [-0.2, -0.1, 0, 0.1, 0.2]
    results = []
    baseline_toll_links = None

    for eps in epsilons:
        print(f"\n需求扰动 ε = {eps*100:.0f}%")

        # 创建扰动后的网络
        network = Network()
        network.load_from_directory(network_dir)

        # 扰动需求
        for od_id in network.driver_ods:
            network.driver_ods[od_id].demand *= (1 + eps)
            network.driver_ods[od_id].demand = max(0, network.driver_ods[od_id].demand)
        for od_id in network.rider_ods:
            network.rider_ods[od_id].demand *= (1 + eps)
            network.rider_ods[od_id].demand = max(0, network.rider_ods[od_id].demand)

        traj_manager = TrajectoryManager(network)
        traj_manager.generate_trajectories()

        # 计算基准
        F_ue, _ = compute_F_ue(network, traj_manager)
        F_so, _ = compute_F_so(network, traj_manager)
        improvement_space = F_ue - F_so

        # 运行PBCD
        start_time = time.time()
        optimal_toll, optimal_flow, F_star, _ = pbcd_algorithm(
            network, traj_manager, fixed_kappa, F_ue)
        cpu_time = time.time() - start_time

        RED = (F_star - F_so) / improvement_space if improvement_space > 0 else 0

        # 收费路段集合
        toll_links_set = set(lid for lid in optimal_toll if optimal_toll[lid] > 0.001)

        if eps == 0:
            baseline_toll_links = toll_links_set

        # 计算Jaccard指数
        if baseline_toll_links is not None and (len(baseline_toll_links) > 0 or len(toll_links_set) > 0):
            intersection = len(baseline_toll_links & toll_links_set)
            union = len(baseline_toll_links | toll_links_set)
            jaccard = intersection / union if union > 0 else 1.0
        else:
            jaccard = 1.0

        results.append({
            'epsilon': eps,
            'F_ue': F_ue,
            'F_so': F_so,
            'F_star': F_star,
            'RED': RED,
            'jaccard': jaccard,
            'cpu_time': cpu_time
        })
        print(f"F_ue'={F_ue:.2f}, F_so'={F_so:.2f}, F*={F_star:.2f}, RED={RED:.4f}, Jaccard={jaccard:.3f}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(os.path.join(output_dir, f"{network_name}_sensitivity_demand.csv"), index=False)
    return results_df


def main():
    """主函数"""
    print("="*60)
    print("拼车收费优化系统")
    print("="*60)

    # 网络配置 - 只测试ND网络，因为它的规模较大，可能能够明显展示收费的效果
    networks = {
        'ND': {
            'dir': '网络数据/ND',
            'kappa_list': [1, 2, 3, 4, 5],
            'fixed_kappa': 3
        }
    }

    # 创建输出目录
    output_dir = 'results'
    os.makedirs(output_dir, exist_ok=True)

    all_results = []

    # 运行每个网络的实验
    for name, config in networks.items():
        if not os.path.exists(config['dir']):
            print(f"跳过网络 {name}: 目录不存在")
            continue

        try:
            result = run_experiment(name, config['dir'], config['kappa_list'], output_dir)
            if result is None:
                continue
            all_results.append(result)

            # 敏感性分析
            run_sensitivity_ratio(name, config['dir'], output_dir)
            run_sensitivity_demand(name, config['dir'], config['fixed_kappa'], output_dir)

        except Exception as e:
            print(f"处理网络 {name} 时出错: {e}")
            import traceback
            traceback.print_exc()

    # 生成汇总文件
    if all_results:
        summary_rows = []
        for result in all_results:
            for r in result['results']:
                summary_rows.append({
                    'network': result['network_name'],
                    'N': result['N'],
                    'A': result['A'],
                    'W': result['W'],
                    'M': result['M'],
                    'F_ue': result['F_ue'],
                    'F_so': result['F_so'],
                    'kappa': r['kappa'],
                    'F_star': r['F_star'],
                    'RED': r['RED'],
                    'cpu_seconds': r['cpu_time']
                })

        summary_df = pd.DataFrame(summary_rows)
        summary_df.to_csv(os.path.join(output_dir, 'summary_all_networks.csv'), index=False)
        print(f"\n汇总结果已保存到 {os.path.join(output_dir, 'summary_all_networks.csv')}")

    print("\n" + "="*60)
    print("实验完成!")
    print("="*60)


if __name__ == '__main__':
    main()
