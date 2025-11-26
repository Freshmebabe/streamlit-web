import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
# 【修复1】确保 art3d 被正确引入，即使在不同的 matplotlib 版本中也能兼容
from mpl_toolkits.mplot3d import art3d 
import random 

# --- 中文显示配置 ---
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False 

# --- 物理常数与爆炸参数 ---
R_TANK = 5      # 储罐半径 (m)
H_TANK = 20     # 储罐高度 (m)
LEAK_RATE_KG_S = 0.8  # 泄漏流速 (kg/s)
VCE_EFFICIENCY = 0.03 # VCE爆炸效率 (3%)
COMBUSTION_HEAT_LNG = 50e6 # LNG燃烧热 (J/kg)
EXPLOSION_HEAT_TNT = 4.5e6 # TNT爆炸热 (J/kg)
COMBUSTIBLE_FRACTION = 0.25 # 可燃物质占总泄漏量的比例 (25%)

# --- 页面配置 ---
st.set_page_config(
    page_title="LNG复杂仿真平台 (精致版)",
    page_icon="✨",
    layout="wide"
)

# --- 样式调整 (CSS) ---
st.markdown("""
    <style>
    .main { background-color: #f7f9fc; color: #1f1f1f;}
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); color: #333333;}
    h1, h2, h3, h4 { color: #004085; }
    </style>
    """, unsafe_allow_html=True)

# --- 核心逻辑函数：包含复杂建模过程 ---
def calculate_complex_state(t):
    """根据时间 t (min) 计算当前的物理状态，并进行 TNT 模型计算"""
    t_sec = t * 60
    state = {}
    
    total_leak_kg = LEAK_RATE_KG_S * t_sec
    
    if t <= 1:
        area = 20 * t
    elif t <= 3:
        area = 20 + (400-20) * (t-1)/2
    elif t <= 5:
        area = 400 + (800-400) * (t-3)/2
    elif t <= 10:
        area = 800 + (1200-800) * (t-5)/5
    else:
        area = 1200 
    
    if t < 5:
        H_cloud = 0.5 + 0.5 * t 
    elif t <= 10:
        H_cloud = 3.0 + 0.2 * (t - 5)
    else:
        H_cloud = 4.0 
        
    state['area'] = area
    state['H_cloud'] = H_cloud
    state['total_leak_kg'] = total_leak_kg
    
    if t >= 10:
        M_comb = total_leak_kg * COMBUSTIBLE_FRACTION
        W_tnt = (VCE_EFFICIENCY * M_comb * COMBUSTION_HEAT_LNG) / EXPLOSION_HEAT_TNT
        w_tnt_root = W_tnt ** (1/3)

        R_400kpa = 0.29 * w_tnt_root
        R_100kpa = 0.62 * w_tnt_root
        R_50kpa = 0.98 * w_tnt_root
        
        state['W_tnt'] = W_tnt
        state['R_400kpa'] = R_400kpa
        state['R_100kpa'] = R_100kpa
        state['R_50kpa'] = R_50kpa
        state['status'] = "发生爆炸 (VCE)"
        state['danger_level'] = "极高 (灾难)"
        
    else:
        if t < 3:
            state['max_conc'] = "1%-3%"
            state['danger_level'] = "低 (警示)"
        elif t < 5:
            state['max_conc'] = "5% (LFL)"
            state['danger_level'] = "中 (危险)"
        else:
            state['max_conc'] = "5%-15%"
            state['danger_level'] = "高 (紧急)"
        state['status'] = "泄漏扩散中"
        
    return state


# 绘制圆柱体辅助函数
def plot_cylinder(ax, x0, y0, z0, x1, y1, z1, radius=0.5, color='gray', segments=10):
    v = np.array([x1 - x0, y1 - y0, z1 - z0])
    mag = np.linalg.norm(v)
    if mag == 0: return 
    v = v / mag

    # 确定两个垂直于 v 的向量 n1 和 n2
    not_v = np.array([1, 0, 0])
    if (v == not_v).all(): not_v = np.array([0, 1, 0])

    n1 = np.cross(v, not_v)
    n1 = n1 / np.linalg.norm(n1)
    n2 = np.cross(v, n1)

    # 轴向数据：t 是沿圆柱体长度的方向
    t = np.linspace(0, mag, 2)
    theta = np.linspace(0, 2 * np.pi, segments)

    # 1. 轴向位移（形状: (2, 3)）
    axial_offset = np.outer(t, v) + (x0, y0, z0)
    
    # 2. 圆周位移（形状: (segments, 3) -> (10, 3)）
    radial_offset = radius * (np.outer(np.cos(theta), n1) + np.outer(np.sin(theta), n2))
    
    # 【核心修复】使用 NumPy 的 newaxis 扩展轴向位移的维度，使其形状变为 (2, 1, 3)。
    # 这样就可以与径向位移（形状 (10, 3)，NumPy 自动广播为 (1, 10, 3)）进行广播相加，得到 (2, 10, 3) 的结果。
    points = axial_offset[:, np.newaxis, :] + radial_offset
    
    # Reshape for plot_surface: (2, 10, 3) -> (20, 3)
    # 绘图前，我们需要将其展平或直接使用 (2, 10) 形状的 X, Y, Z
    
    # 提取 X, Y, Z
    X = points[:, :, 0]
    Y = points[:, :, 1]
    Z = points[:, :, 2]
    
    ax.plot_surface(X, Y, Z, color=color, alpha=0.7, rstride=1, cstride=1, antialiased=True)

# --- 精致化 3D 绘图函数 ---
def draw_complex_3d_simulation_plot(t, state):
    fig = plt.figure(figsize=(14, 12)) 
    ax = fig.add_subplot(111, projection='3d')
    
    ax.view_init(elev=25, azim=-45) 

    ax.set_xlim(-70, 70)
    ax.set_ylim(-70, 70)
    ax.set_zlim(0, 40) 
    ax.set_xlabel('东-西方向 (m)', color='#333333')
    ax.set_ylabel('南-北方向 (m)', color='#333333')
    ax.set_zlabel('高度 (m)', color='#333333')
    ax.tick_params(colors='#333333')
    ax.set_facecolor('lightgrey') 
    
    ax.grid(False) 
    
    # --- 1. 绘制地面 (增加纹理感) ---
    x_ground = np.linspace(-70, 70, 100)
    y_ground = np.linspace(-70, 70, 100)
    X_ground, Y_ground = np.meshgrid(x_ground, y_ground)
    Z_ground = np.zeros_like(X_ground)
    ax.plot_surface(X_ground, Y_ground, Z_ground, color='#c2e6d1', alpha=0.8, antialiased=False, rstride=10, cstride=10)
    
    # 绘制道路 (示例)
    ax.plot([-70, 70], [-50, -50], [0.01, 0.01], color='#6e7e85', linewidth=5)
    ax.plot([-70, 70], [50, 50], [0.01, 0.01], color='#6e7e85', linewidth=5)
    ax.text(0, -50, 1, "主干道", color='white', ha='center', va='bottom', fontsize=8)

    # --- 2. 绘制 LNG 储罐 (更平滑，有光泽感) ---
    num_segments = 100
    z_tank = np.linspace(0, H_TANK, num_segments)
    theta_tank = np.linspace(0, 2*np.pi, num_segments)
    theta_grid, z_grid = np.meshgrid(theta_tank, z_tank)
    x_tank = R_TANK * np.cos(theta_grid)
    y_tank = R_TANK * np.sin(theta_grid)
    
    # 侧面
    ax.plot_surface(x_tank, y_tank, z_grid, color='#8ba4c7', alpha=0.9, rstride=5, cstride=5, antialiased=True) 
    
    # 【修复】储罐顶部：创建独立且正确的二维网格
    # 顶部需要使用 x, y 的一维数组进行网格化，然后 Z 坐标填充为常量 H_TANK
    x_circle = R_TANK * np.cos(theta_tank)
    y_circle = R_TANK * np.sin(theta_tank)
    
    # 创建一个简单的二维网格来绘制顶部
    X_top, Y_top = np.meshgrid(x_circle, x_circle) # 这里实际上只需要一个简单的网格，我们使用极坐标的方式
    
    # 采用更标准的绘制圆柱体顶盖的方法：使用网格化
    theta_top = np.linspace(0, 2 * np.pi, 100)
    r_top = np.linspace(0, R_TANK, 2)
    R_top, Theta_top = np.meshgrid(r_top, theta_top)
    
    X_cap = R_top * np.cos(Theta_top)
    Y_cap = R_top * np.sin(Theta_top)
    Z_cap = np.full_like(X_cap, H_TANK)
    
    # 绘制顶部表面
    ax.plot_surface(X_cap, Y_cap, Z_cap, color='#5a718c', alpha=1.0) 

    ax.text(0, 0, H_TANK + 2, "LNG 储罐 T-101", color='darkblue', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # --- 3. 绘制厂区其他元素：BOG 压缩机房 ---
    room_x, room_y, room_z_base = 20, -15, 0 
    room_width, room_depth, room_height = 12, 10, 8 
    
    room_verts = [
        [room_x, room_y, room_z_base], [room_x + room_width, room_y, room_z_base],
        [room_x + room_width, room_y + room_depth, room_z_base], [room_x, room_y + room_depth, room_z_base],
        [room_x, room_y, room_z_base + room_height], [room_x + room_width, room_y, room_z_base + room_height],
        [room_x + room_width, room_y + room_depth, room_z_base + room_height], [room_x, room_y + room_depth, room_z_base + room_height]
    ]
    room_faces = [
        [room_verts[0], room_verts[1], room_verts[2], room_verts[3]], 
        [room_verts[4], room_verts[5], room_verts[6], room_verts[7]], 
        [room_verts[0], room_verts[1], room_verts[5], room_verts[4]], 
        [room_verts[1], room_verts[2], room_verts[6], room_verts[5]], 
        [room_verts[2], room_verts[3], room_verts[7], room_verts[6]], 
        [room_verts[3], room_verts[0], room_verts[4], room_verts[7]]
    ]
    ax.add_collection3d(art3d.Poly3DCollection(room_faces, facecolor='#dbe4ee', edgecolor='#5f7c9e', alpha=0.8, linewidth=0.8))
    ax.text(room_x + room_width/2, room_y + room_depth/2, room_z_base + room_height + 1, "BOG 压缩机房", color='#333333', ha='center', fontsize=8, fontweight='bold')

    # 绘制管道 (使用辅助函数)
    pipe_color = '#7a8a9a'
    plot_cylinder(ax, R_TANK * np.cos(np.pi/4), R_TANK * np.sin(np.pi/4), 1.5, 
                  room_x + room_width/2 - 2, room_y + room_depth/2 + 2, 1.5, radius=0.7, color=pipe_color)
    plot_cylinder(ax, room_x + room_width/2 - 2, room_y + room_depth/2 + 2, 1.5, 
                  room_x + room_width/2 - 2, room_y + room_depth/2 + 2, 4.0, radius=0.7, color=pipe_color)

    pipe_color_light = '#9db8c7'
    plot_cylinder(ax, -30, -70, 2, -30, 70, 2, radius=0.4, color=pipe_color_light)
    plot_cylinder(ax, 30, -70, 2, 30, 70, 2, radius=0.4, color=pipe_color_light)
    ax.text(-30, 70, 3, "主管廊", color='#333333', ha='center', fontsize=8)


    # --- 4. 动态场景分歧：爆炸前 vs 爆炸后 ---
    
    if t < 10:
        # --- 泄漏扩散阶段 (更具层次感的云团) ---
        ax.set_title(f"泄漏扩散 3D 模拟 (T={t:.1f} min) | 云团高度: {state['H_cloud']:.1f} m", fontsize=16)
        
        if state['area'] > 1:
            radius_base = np.sqrt(state['area'] / np.pi) * 0.9 
            num_points_total = int(state['area'] * 3) 

            leak_x_source, leak_y_source, leak_z_source = R_TANK * np.cos(np.pi/4), R_TANK * np.sin(np.pi/4), 0.5
            
            # 低浓度外层
            xs_outer = np.random.normal(leak_x_source + radius_base*0.5, radius_base, num_points_total)
            ys_outer = np.random.normal(leak_y_source + radius_base*0.5, radius_base, num_points_total) 
            zs_outer = np.random.uniform(0.1, state['H_cloud'] * 0.9, num_points_total)
            ax.scatter(xs_outer, ys_outer, zs_outer, c='skyblue', alpha=0.1, s=15, label='稀释蒸汽云')

            # 中浓度层
            xs_mid = np.random.normal(leak_x_source + radius_base*0.3, radius_base*0.7, num_points_total // 2)
            ys_mid = np.random.normal(leak_y_source + radius_base*0.3, radius_base*0.7, num_points_total // 2)
            zs_mid = np.random.uniform(0.1, state['H_cloud'] * 0.6, num_points_total // 2)
            ax.scatter(xs_mid, ys_mid, zs_mid, c='cadetblue', alpha=0.2, s=20)

            # 高浓度积聚区
            xs_hot = np.random.normal(room_x + room_width/2 - 5, 4, num_points_total // 5) 
            ys_hot = np.random.normal(room_y + room_depth/2 + 5, 4, num_points_total // 5)
            zs_hot = np.random.uniform(0.1, 2.5, num_points_total // 5)
            ax.scatter(xs_hot, ys_hot, zs_hot, c='#ff7f0e', alpha=0.7, s=30, label='高浓度积聚区')
            

    else:
        # --- 爆炸阶段 (3D 伤害半球 & 爆炸火球 & 碎片) ---
        ax.set_title(f"爆炸后果 3D 模拟 (T={t:.1f} min)", fontsize=16, color='#dc3545', fontweight='bold') 
        
        center_exp = (20 + room_width/2 - 5, -15 + room_depth/2 + 5, 0) 
        
        def plot_blast_hemisphere(radius, color, alpha, label_text):
            u = np.linspace(0, 2 * np.pi, 50)
            v = np.linspace(0, np.pi / 2, 30)
            x = radius * np.outer(np.cos(u), np.sin(v)) + center_exp[0]
            y = radius * np.outer(np.sin(u), np.sin(v)) + center_exp[1]
            z = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + center_exp[2]
            ax.plot_wireframe(x, y, z, color=color, alpha=alpha, linewidth=1.5, antialiased=True) 
            ax.text(center_exp[0] + radius*0.8, center_exp[1] - radius*0.3, 15, 
                    f"{label_text}: {radius:.1f}m", color=color, fontsize=8, horizontalalignment='center')
        
        plot_blast_hemisphere(state['R_400kpa'], '#ff0000', 0.8, '0.4MPa') 
        plot_blast_hemisphere(state['R_100kpa'], '#ff8c00', 0.6, '0.1MPa') 
        plot_blast_hemisphere(state['R_50kpa'], '#32cd32', 0.4, '0.05MPa') 
        
        # 模拟爆炸中心火球 
        fireball_radius = 8 
        u_fire = np.linspace(0, 2 * np.pi, 30)
        v_fire = np.linspace(0, np.pi, 30)
        x_fire = fireball_radius * np.outer(np.cos(u_fire), np.sin(v_fire)) + center_exp[0]
        y_fire = fireball_radius * np.outer(np.sin(u_fire), np.sin(v_fire)) + center_exp[1]
        z_fire = fireball_radius * np.outer(np.ones(np.size(u_fire)), np.cos(v_fire)) + center_exp[2] + fireball_radius 
        ax.plot_surface(x_fire, y_fire, z_fire, color='yellow', alpha=0.7, rstride=2, cstride=2, antialiased=True)
        ax.plot_surface(x_fire, y_fire, z_fire, color='red', alpha=0.4, rstride=2, cstride=2, antialiased=True)
        
        # 模拟爆炸后的次生火点
        fire_x = np.random.normal(center_exp[0], 5, 200)
        fire_y = np.random.normal(center_exp[1], 5, 200)
        fire_z = np.random.uniform(0.1, 10, 200)
        ax.scatter(fire_x, fire_y, fire_z, c='red', marker='^', s=np.random.uniform(50, 300, 200), alpha=0.6, label='火灾')
        ax.scatter(fire_x, fire_y, fire_z*0.5, c='orange', marker='^', s=np.random.uniform(30, 200, 200), alpha=0.8)

        # 模拟碎片/烟雾
        smoke_x = np.random.normal(center_exp[0], 10, 300)
        smoke_y = np.random.normal(center_exp[1], 10, 300)
        smoke_z = np.random.uniform(0.1, 20, 300)
        ax.scatter(smoke_x, smoke_y, smoke_z, c='grey', marker='o', s=np.random.uniform(10, 100, 300), alpha=0.2, label='烟雾/碎片')


        # BOG机房损坏提示
        ax.text(room_x + room_width/2, room_y + room_depth/2, room_z_base + room_height + 3, 
                "BOG机房 (完全损毁)", color='darkred', ha='center', va='center', fontsize=12, fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        
    return fig

# --- 动态分析面板函数 ---
def render_dynamic_analysis(t, state):
    st.markdown("#### ⚙️ 实时事故分析与指导")
    st.markdown("---")

    if t < 10:
        st.metric("📏 **当前云团高度**", f"{state['H_cloud']:.1f} m", help="基于重气效应模型近似计算")
        
        if t < 3:
            st.info("🟢 【T < 3 min】泄漏初期：云团高度低，主要在液池上方。**BOG机房安全。**")
        elif t < 5:
            st.warning("🟡 【T < 5 min】LFL 临界：云团开始加速扩散和抬升，爆炸风险显著增加。**BOG机房被蒸汽云波及，风险中等。**")
        else:
            st.error("🟠 【T < 10 min】高风险积聚：云团高度接近最大值。**BOG机房位于高浓度积聚区，爆炸风险极高！**")
            
    elif t >= 10:
        st.balloons()
        st.subheader("💥 爆炸模型评估结果")
        st.error(f"🔴 **计算当量：** {state['W_tnt']:.1f} kg TNT")
        st.markdown("---")
        
        st.markdown("#### 冲击波超压波及范围 (TNT 模型)")
        # 【修复 SyntaxWarning】使用 r-string
        st.metric(r"🔴 $0.4\text{ MPa}$ (设备全毁)", f"{state['R_400kpa']:.1f} m", help="包括储罐外罐、BOG机房内核心设备")
        st.metric(r"🟠 $0.1\text{ MPa}$ (致死/管道变形)", f"{state['R_100kpa']:.1f} m", help="波及管廊、大部分区域人员")
        st.metric(r"🟢 $0.05\text{ MPa}$ (仪表/玻璃损坏)", f"{state['R_50kpa']:.1f} m", help="厂区边界、中控室玻璃")
        
        st.markdown("##### 🚒 应急指挥指导：")
        st.markdown("* **首要任务：** 隔离并扑灭次生火灾（如 BOG 机房区域）。")
        st.markdown("* **BOG 机房：** 已被爆炸严重损毁，立即评估二次泄漏风险。")

# --- 主界面布局 ---
def main():
    st.title("✨ LNG储罐泄漏事故 3D 复杂仿真平台 (精致版)")
    st.markdown("---")
    st.markdown("#### 基于物理模型：TNT当量法、重气扩散近似")
    
    # --- 侧边栏：控制面板 ---
    st.sidebar.header("🕹️ 模拟控制台")
    sim_time = st.sidebar.slider("模拟时间进程 (分钟)", 0.0, 15.0, 0.0, 0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 建模参数设定")
    st.sidebar.metric("泄漏流率 (固定)", f"{LEAK_RATE_KG_S} kg/s")
    # 【修复 SyntaxWarning】使用 r-string
    st.sidebar.metric(r"VCE 爆炸效率 ($\eta$)", f"{VCE_EFFICIENCY*100:.1f} %")
    
    # --- 计算当前状态 ---
    current_state = calculate_complex_state(sim_time)

    # --- 顶部：关键指标看板 (KPI) ---
    st.header("实时关键指标 (KPI)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric(label="当前状态", value=current_state['status'])
    kpi2.metric(label="累计泄漏量", value=f"{current_state['total_leak_kg']:.1f} kg")
    # 【修复 SyntaxWarning】使用 r-string
    kpi3.metric(label=r"蒸汽云覆盖面积 ($m^2$)", value=f"{current_state['area']:.0f}")
    
    if sim_time >= 10:
        kpi4.metric("💥 爆炸危险等级", current_state['danger_level'], delta="立即采取行动", delta_color="inverse")
    elif sim_time >= 5:
        kpi4.metric("⚠️ 泄漏危险等级", current_state['danger_level'], delta="快速处理", delta_color="inverse")
    else:
        kpi4.metric("✅ 泄漏危险等级", current_state['danger_level'])


    # --- 主要内容区 ---
    st.markdown("---")
    tab1, tab2 = st.tabs(["🌎 3D 物理模型视图 & 分析", "🛠️ 应急处置SOP"])

    with tab1:
        st.subheader("实时 3D 扩散/爆炸后果模拟")
        st.markdown("您可拖动右侧 3D 视图自由旋转视角。")
        col_plot, col_analysis = st.columns([2, 1])

        with col_plot:
            fig = draw_complex_3d_simulation_plot(sim_time, current_state)
            st.pyplot(fig, clear_figure=True)
            
        with col_analysis:
            render_dynamic_analysis(sim_time, current_state)
            
        with st.expander("图例说明"):
            # 【修复 SyntaxWarning】使用 r-string
            st.markdown(r"""
            * **LNG储罐 T-101：** 略带蓝色的金属感圆柱体。
            * **BOG压缩机房：** 浅灰蓝色方块，有边框。
            * **管道/管廊：** 灰色圆柱体。
            * **泄漏阶段：**
                * **稀释蒸汽云 (淡蓝色散点)：** 扩散范围广，透明度高。
                * **高浓度积聚区 (橙色散点)：** 密度高，位于爆炸中心区域。
            * **爆炸阶段：**
                * **冲击波半球：** 由内向外分别为 $0.4\text{ MPa}$ (红色), $0.1\text{ MPa}$ (橙色), $0.05\text{ MPa}$ (绿色) 伤害范围。
                * **爆炸火球：** 黄色/红色渐变球体。
            """)

    with tab2:
        st.subheader("推荐应急处置流程 (SOP)")
        # 【修复 SyntaxWarning】使用 r-string
        st.markdown(r"""
        #### 1. 自动与人工切断 (T < 3min)
        * **目标：** 在蒸汽云达到 LFL 之前（即 $\mathbf{T<3min}$）完成切断。
        * **行动：** 立即触发 **ESD（紧急切断）** 按钮，切断储罐底部根部阀。
        
        #### 2. 工艺隔离与消防覆盖 (T < 5min)
        * **行动：** 关闭 T-101 出液总阀及回气阀，启动**水喷淋系统**稀释蒸汽云浓度。
        
        #### 3. 人员疏散与管制 (T < 10min)
        * **行动：** 广播通知全厂撤离，重点疏散处于**下风向（北侧）** 和 **低洼区域（东南侧，BOG机房区域）** 的人员。
        * **避难方向：** 撤离至**上风向**或指定抗爆区。
        
        #### 4. 爆炸后处置 (T $\ge 10\text{min}$)
        * **行动：** 立即报告，启动消防救援。隔离爆炸中心区域，扑灭次生火灾（尤其是 BOG 机房区域）。
        * **重点：** 评估 $0.1\text{ MPa}$ 范围内人员伤亡情况，启动紧急救援。
        """)

if __name__ == "__main__":
    main()