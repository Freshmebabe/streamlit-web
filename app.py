import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import random 
import os
import platform
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties  # 导入字体属性类

# ========== 第一步：先调用set_page_config（必须是第一个Streamlit命令） ==========
st.set_page_config(
    page_title="LNG仿真平台",
    page_icon="⚛️",
    layout="wide"
)

# --- 中文显示配置（本地+云端双适配，移除内部Streamlit命令）---
def setup_chinese_font():
    """
    自动适配本地/云端环境的中文配置：
    1. 本地优先使用系统自带中文字体（Windows: SimHei/Microsoft YaHei；Mac: PingFang SC；Linux: WenQuanYi Zen Hei）
    2. 云端使用预装字体
    返回：字体配置状态信息（用于后续显示）
    """
    status_msg = ""
    try:
        # ===== 第一步：检测系统类型，定位本地中文字体路径 =====
        system = platform.system()
        local_font_paths = []
        
        if system == "Windows":
            # Windows默认字体路径（必存在）
            font_dir = "C:/Windows/Fonts/"
            # 优先尝试的中文字体文件（黑体/微软雅黑/宋体）
            local_font_files = ["simhei.ttf", "msyh.ttc", "simsun.ttc"]
            local_font_paths = [os.path.join(font_dir, f) for f in local_font_files if os.path.exists(os.path.join(font_dir, f))]
            
        elif system == "Darwin":  # MacOS
            font_dir = "/System/Library/Fonts/"
            local_font_files = ["PingFang.ttc", "Heiti.ttc"]
            local_font_paths = [os.path.join(font_dir, f) for f in local_font_files if os.path.exists(os.path.join(font_dir, f))]
            
        elif system == "Linux":  # Linux/Streamlit云端
            font_dir = "/usr/share/fonts/truetype/"
            local_font_files = ["wqy-zenhei/wqy-zenhei.ttc"]
            local_font_paths = [os.path.join(font_dir, f) for f in local_font_files if os.path.exists(os.path.join(font_dir, f))]
        
        # ===== 第二步：本地有字体则优先加载 =====
        if local_font_paths:
            # 注册本地字体
            font_path = local_font_paths[0]  # 取第一个可用的中文字体
            fm.fontManager.addfont(font_path)
            # 获取字体名称
            font_prop = fm.FontProperties(fname=font_path)
            font_name = font_prop.get_name()
            # 设置Matplotlib字体
            plt.rcParams['font.sans-serif'] = [font_name, 'sans-serif']
            #status_msg = f"✅ 本地字体加载成功：{font_name} (路径：{font_path})"
        
        # ===== 第三步：本地无字体则用云端适配逻辑 =====
        else:
            # 云端常见中文字体列表
            chinese_fonts = [
                'WenQuanYi Zen Hei', 'SimHei','DejaVu Sans', 'Arial Unicode MS',
                'Microsoft YaHei', 'PingFang SC'
            ]
            available_fonts = set([f.name for f in fm.fontManager.ttflist])
            for font in chinese_fonts:
                if font in available_fonts:
                    plt.rcParams['font.sans-serif'] = [font, 'sans-serif']
                    # status_msg = f"⚠️ 本地无中文字体，使用兼容字体：{font}"
                    break
            else:
                plt.rcParams['font.sans-serif'] = ['sans-serif']
                # status_msg = "⚠️ 未找到可用中文字体，中文可能显示异常"
        
        # 关键：解决负号显示问题
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 10  # 基础字体大小
        
    except Exception as e:
        status_msg = f"❌ 字体配置失败：{str(e)}"
        plt.rcParams['font.sans-serif'] = ['sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
    
    return status_msg  # 返回状态信息，后续再用st显示

# 初始化中文配置（此时还未调用任何st命令，仅返回状态）
font_status = setup_chinese_font()

# --- 物理常数与爆炸参数 ---
R_TANK = 5      # 储罐半径 (m)
H_TANK = 20     # 储罐高度 (m)
LEAK_RATE_KG_S = 0.8  # 泄漏流速 (kg/s)
VCE_EFFICIENCY = 0.03 # VCE爆炸效率 (3%)
COMBUSTIBLE_FRACTION = 0.25 # 可燃物质占总泄漏量的比例 (25%)
COMBUSTION_HEAT_LNG = 50e6 # LNG燃烧热 (J/kg)
EXPLOSION_HEAT_TNT = 4.5e6 # TNT爆炸热 (J/kg)

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
    
    # 1. 源项与泄漏量
    total_leak_kg = LEAK_RATE_KG_S * t_sec
    
    # 2. 扩散模型 (面积插值与高度模型)
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
    
    # 简化重气模型：云团高度 (H_cloud)
    if t < 5:
        H_cloud = 0.5 + 0.5 * t 
    elif t <= 10:
        H_cloud = 3.0 + 0.2 * (t - 5)
    else:
        H_cloud = 4.0 
        
    state['area'] = area
    state['H_cloud'] = H_cloud
    state['total_leak_kg'] = total_leak_kg
    
    # 3. 爆炸模型 (仅在爆炸发生时计算)
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

# --- 复杂 3D 绘图函数 ---
def draw_complex_3d_simulation_plot(t, state):
    # 设置高DPI（适配本地/云端显示）
    plt.rcParams['figure.dpi'] = 150
    plt.rcParams['savefig.dpi'] = 150
    
    fig = plt.figure(figsize=(12, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # 从 mpl_toolkits.mplot3d 引入 art3d
    from mpl_toolkits.mplot3d import art3d 
    
    ax.set_xlim(-70, 70)
    ax.set_ylim(-70, 70)
    ax.set_zlim(0, 35) 
    
    # 轴标签设置（加粗、大号字体，确保中文显示）
    ax.set_xlabel('East-west direction (m)', fontsize=12, fontweight='bold')
    ax.set_ylabel('North-south direction (m)', fontsize=12, fontweight='bold')
    ax.set_zlabel('height (m)', fontsize=12, fontweight='bold')
    
    # 刻度标签加粗
    ax.tick_params(colors='#333333', labelsize=10, width=1.5)

    # --- 1. 绘制地面 ---
    x_ground = np.linspace(-70, 70, 2)
    y_ground = np.linspace(-70, 70, 2)
    X_ground, Y_ground = np.meshgrid(x_ground, y_ground)
    Z_ground = np.zeros_like(X_ground)
    ax.plot_surface(X_ground, Y_ground, Z_ground, color='#a0d8b3', alpha=0.5)

    # --- 2. 绘制 LNG 储罐 (中心) ---
    z_tank = np.linspace(0, H_TANK, 50)
    theta_tank = np.linspace(0, 2*np.pi, 50)
    theta_grid, z_grid = np.meshgrid(theta_tank, z_tank)
    x_tank = R_TANK * np.cos(theta_grid)
    y_tank = R_TANK * np.sin(theta_grid)
    ax.plot_surface(x_tank, y_tank, z_grid, color='#666666', alpha=0.8) 
    ax.text(0, 0, H_TANK + 2, "T-101", color='black', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # --- 3. 绘制厂区其他元素：BOG 压缩机房 ---
    room_x, room_y, room_z_base = 20, -15, 0 
    room_width, room_depth, room_height = 10, 10, 8
    
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
    ax.add_collection3d(art3d.Poly3DCollection(room_faces, facecolor='#b0c4de', edgecolor='black', alpha=0.7, label='BOG Compressor room'))
    ax.text(room_x + room_width/2, room_y + room_depth/2, room_z_base + room_height + 1, "BOG room", color='black', ha='center', fontsize=9, fontweight='bold')

    # 绘制管道 (简化)
    pipe_color = '#7f8c8d'
    ax.plot([R_TANK*np.cos(np.pi/4), room_x+room_width/2], [R_TANK*np.sin(np.pi/4), room_y+room_depth/2], [1, 1], color=pipe_color, linewidth=3, label='Pipeline')
    ax.plot([-30, -30], [-70, 70], [2, 2], color=pipe_color, linewidth=3)
    ax.plot([30, 30], [-70, 70], [2, 2], color=pipe_color, linewidth=3)

    # --- 4. 动态场景分歧：爆炸前 vs 爆炸后 ---
    if t < 10:
        # --- 泄漏扩散阶段 (3D 云团) ---
        ax.set_title(f"3D simulation of leakage and diffusion (T={t:.1f} min) | Cloud mass height: {state['H_cloud']:.1f} m", fontsize=16, fontweight='bold')
        
        if state['area'] > 1:
            radius_base = np.sqrt(state['area'] / np.pi) * 0.8
            num_points = int(state['area'] * 2)
            leak_x_source, leak_y_source, leak_z_source = R_TANK, 0, 0
            
            # 扩散区
            xs_diff = np.random.normal(leak_x_source + radius_base/2, radius_base/2, num_points)
            ys_diff = np.random.normal(leak_y_source + radius_base/2, radius_base/2, num_points) 
            zs_diff = np.random.uniform(0.1, state['H_cloud'] * 0.7, num_points)
            
            # 高浓度积聚区 (靠近爆炸中心)
            xs_hot = np.random.normal(5, 3, num_points//5) 
            ys_hot = np.random.normal(-5, 3, num_points//5)
            zs_hot = np.random.uniform(0.1, 2, num_points//5)
            
            ax.scatter(xs_diff, ys_diff, zs_diff, c='cyan', alpha=0.3, s=10, label='low-concentration vapor cloud')
            ax.scatter(xs_hot, ys_hot, zs_hot, c='#ff7f0e', alpha=0.6, s=20, label='high-concentration accumulation area')

    else:
        # --- 爆炸阶段 (3D 伤害半球 & 火焰) ---
        ax.set_title(f"3D simulation of explosion consequences  (T={t:.1f} min)", fontsize=16, color='#dc3545', fontweight='bold') 
        
        center_exp = (5, -5, 0)
        
        def plot_blast_hemisphere(radius, color, alpha, label_text):
            u = np.linspace(0, 2 * np.pi, 50)
            v = np.linspace(0, np.pi / 2, 30)
            x = radius * np.outer(np.cos(u), np.sin(v)) + center_exp[0]
            y = radius * np.outer(np.sin(u), np.sin(v)) + center_exp[1]
            z = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + center_exp[2]
            ax.plot_wireframe(x, y, z, color=color, alpha=alpha, linewidth=1.0)
            ax.text(center_exp[0] + radius*0.8, center_exp[1] - radius*0.3, 15, 
                    f"{label_text}: {radius:.1f}m", color=color, fontsize=9, horizontalalignment='center', fontweight='bold')
        
        plot_blast_hemisphere(state['R_400kpa'], '#cc0000', 0.8, '0.4MPa')
        plot_blast_hemisphere(state['R_100kpa'], '#ff9900', 0.5, '0.1MPa')
        plot_blast_hemisphere(state['R_50kpa'], '#00b33c', 0.3, '0.05MPa')
        
        ax.scatter(center_exp[0], center_exp[1], center_exp[2], marker='*', s=800, c='yellow', edgecolors='red', zorder=10)
        
        # 模拟爆炸后的火焰 (在爆心周围)
        fire_x = np.random.normal(center_exp[0], 3, 100)
        fire_y = np.random.normal(center_exp[1], 3, 100)
        fire_z = np.random.uniform(0.1, 8, 100)
        ax.scatter(fire_x, fire_y, fire_z, c='red', marker='^', s=np.random.uniform(50, 200, 100), alpha=0.6)
        ax.scatter(fire_x, fire_y, fire_z*0.5, c='orange', marker='^', s=np.random.uniform(30, 150, 100), alpha=0.8)

        # BOG机房损坏提示
        ax.text(room_x + room_width/2, room_y + room_depth/2, room_z_base + room_height + 3, 
                "BOG机房 (损毁)", color='darkred', ha='center', va='center', fontsize=11, fontweight='bold')
        
        ax.view_init(elev=20, azim=-60)
    
    # 图例加粗（通过FontProperties）
    legend_prop = FontProperties(size=10, weight='bold')
    ax.legend(
        loc='upper right', 
        prop=legend_prop,
        framealpha=0.9
    ) 
    
    # 调整布局，避免标签被截断
    plt.tight_layout()
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
        st.metric(r"🔴 $0.4\text{ MPa}$ (设备全毁)", f"{state['R_400kpa']:.1f} m", help="包括储罐外罐、BOG机房内核心设备")
        st.metric(r"🟠 $0.1\text{ MPa}$ (致死/管道变形)", f"{state['R_100kpa']:.1f} m", help="波及管廊、大部分区域人员")
        st.metric(r"🟢 $0.05\text{ MPa}$ (仪表/玻璃损坏)", f"{state['R_50kpa']:.1f} m", help="厂区边界、中控室玻璃")
        
        st.markdown("##### 🚒 应急指挥指导：")
        st.markdown("* **首要任务：** 隔离并扑灭次生火灾（如 BOG 机房区域）。")
        st.markdown("* **BOG 机房：** 已被爆炸严重损毁，立即评估二次泄漏风险。")

# --- 主界面布局 ---
def main():
    # 显示字体配置状态（在set_page_config之后）
    if "✅" in font_status:
        st.success(font_status)
    elif "⚠️" in font_status:
        st.warning(font_status)
    else:
        st.error(font_status)
    
    st.title("⚛️ LNG储罐泄漏事故 3D 复杂仿真平台")
    st.markdown("---")
    st.markdown("#### 基于物理模型：TNT当量法、重气扩散近似")
    
    # --- 侧边栏：控制面板 ---
    st.sidebar.header("🕹️ 模拟控制台")
    sim_time = st.sidebar.slider("模拟时间进程 (分钟)", 0.0, 15.0, 0.0, 0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 建模参数设定")
    st.sidebar.metric("泄漏流率 (固定)", f"{LEAK_RATE_KG_S} kg/s")
    st.sidebar.metric(r"VCE 爆炸效率 ($\eta$)", f"{VCE_EFFICIENCY*100:.1f} %") # 使用 r-string
    
    # --- 计算当前状态 ---
    current_state = calculate_complex_state(sim_time)

    # --- 顶部：关键指标看板 (KPI) ---
    st.header("实时关键指标 (KPI)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric(label="当前状态", value=current_state['status'])
    kpi2.metric(label="累计泄漏量", value=f"{current_state['total_leak_kg']:.1f} kg")
    kpi3.metric(label=r"蒸汽云覆盖面积 ($m^2$)", value=f"{current_state['area']:.0f}") # 使用 r-string
    
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
        col_plot, col_analysis = st.columns([2, 1])

        with col_plot:
            fig = draw_complex_3d_simulation_plot(sim_time, current_state)
            st.pyplot(fig, clear_figure=True)
            
        with col_analysis:
            render_dynamic_analysis(sim_time, current_state)
            
        with st.expander("图例说明"):
            st.markdown("""
            * **灰色圆柱：** LNG储罐 T-101。
            * **浅蓝色方块：** BOG压缩机房 (东南侧，靠近爆心)。
            * **灰色直线：** 厂区主要管道/管廊。
            * **泄漏阶段：** 青色/橙色散点模拟贴地重气云团扩散。
            * **爆炸阶段：** 同心网格半球体代表超压波及范围（由内向外：$0.4\text{ MPa}, 0.1\text{ MPa}, 0.05\text{ MPa}$），红色/橙色散点模拟火灾。
            """)

    with tab2:
        st.subheader("推荐应急处置流程 (SOP)")
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