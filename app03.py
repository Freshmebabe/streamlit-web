import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# --- 中文显示配置 ---
# 确保所有字体都支持中文
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS'] 
plt.rcParams['axes.unicode_minus'] = False 

# --- 页面配置 ---
st.set_page_config(
    page_title="LNG储罐泄漏事故 3D 仿真平台",
    page_icon="🧊",
    layout="wide"
)

# --- 样式调整 (CSS) ---
st.markdown("""
    <style>
    /* 优化整体布局和背景色，保证深色字体在浅色背景上清晰显示 */
    .main {
        background-color: #f7f9fc; /* 极浅灰蓝背景 */
        color: #1f1f1f; /* 确保主体字体为深色 */
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        color: #333333; /* 确保Metric内的字体为深色 */
    }
    h1, h2, h3, h4 {
        color: #004085; /* 深蓝色标题 */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 核心逻辑函数 (保持不变) ---
def calculate_state(t):
    """根据时间 t (min) 计算当前的物理状态"""
    state = {}
    
    # 面积插值
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
    
    state['area'] = area
    
    # 累计泄漏量
    leak_rate = 0.8 * 60 # kg/min
    if t <= 10:
        total_leak = leak_rate * t
        state['is_leaking'] = True
        state['status'] = "泄漏扩散中"
    else:
        total_leak = leak_rate * 10
        state['is_leaking'] = False
        state['status'] = "发生爆炸 (VCE)"
        
    state['total_leak_kg'] = total_leak
    
    # 浓度与危险判定
    if t < 3:
        state['max_conc'] = "1%-3%"
        state['danger_level'] = "低 (警示)"
    elif t < 5:
        state['max_conc'] = "5% (LFL)"
        state['danger_level'] = "中 (危险)"
    elif t < 10:
        state['max_conc'] = "5%-15%"
        state['danger_level'] = "高 (紧急)"
    else:
        state['max_conc'] = ">12% (爆燃)"
        state['danger_level'] = "极高 (灾难)"
        
    return state

# --- 核心 3D 绘图函数 ---
def draw_3d_simulation_plot(t, state):
    """绘制 3D 动态模拟图"""
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 1. 设置轴标签和范围
    ax.set_xlim(-60, 60)
    ax.set_ylim(-60, 60)
    ax.set_zlim(0, 30)
    ax.set_xlabel('东-西方向 (m)', color='#333333')
    ax.set_ylabel('南-北方向 (m)', color='#333333')
    ax.set_zlabel('高度 (m)', color='#333333')
    ax.tick_params(colors='#333333') # 坐标轴数字颜色
    
    # 2. 绘制储罐 (圆柱体)
    R_tank, H_tank = 5, 20
    z_tank = np.linspace(0, H_tank, 50)
    theta_tank = np.linspace(0, 2*np.pi, 50)
    theta_grid, z_grid = np.meshgrid(theta_tank, z_tank)
    x_tank = R_tank * np.cos(theta_grid)
    y_tank = R_tank * np.sin(theta_grid)
    ax.plot_surface(x_tank, y_tank, z_grid, color='#8c8c8c', alpha=0.8) # 深灰色储罐
    
    # 3. 场景分歧：爆炸前 vs 爆炸后
    if t < 10:
        # --- 泄漏扩散阶段 (3D 云团) ---
        ax.set_title(f"泄漏扩散 3D 模拟 T={t:.1f} min", fontsize=16)
        
        if state['area'] > 1:
            radius = np.sqrt(state['area'] / np.pi) * 0.8
            cloud_height = 5 + (t / 10) * 10
            
            # 绘制重气云 (散点模拟)
            num_points = int(state['area'] * 2)
            xs = np.random.normal(2, radius/2, num_points)
            ys = np.random.normal(radius/2, radius/2, num_points) 
            zs = np.random.uniform(0.1, cloud_height * 0.7, num_points)
            
            # 东南侧高浓度积聚 (模拟爆心位置)
            xs_hot = np.random.normal(5, 3, num_points//5)
            ys_hot = np.random.normal(-5, 3, num_points//5)
            zs_hot = np.random.uniform(0.1, 2, num_points//5)
            
            ax.scatter(xs, ys, zs, c='cyan', alpha=0.3, s=10, label='低浓度蒸汽云')
            ax.scatter(xs_hot, ys_hot, zs_hot, c='#ff7f0e', alpha=0.6, s=20, label='高浓度积聚区(LFL以上)')

    else:
        # --- 爆炸阶段 (3D 伤害半球) ---
        ax.set_title(f"爆炸后果 3D 模拟 (T={t:.1f} min)", fontsize=16, color='#dc3545') # 红色标题
        
        center_exp = (5, -5, 0)
        
        def plot_blast_hemisphere(radius, color, alpha, label):
            u = np.linspace(0, 2 * np.pi, 50)
            v = np.linspace(0, np.pi / 2, 30)
            x = radius * np.outer(np.cos(u), np.sin(v)) + center_exp[0]
            y = radius * np.outer(np.sin(u), np.sin(v)) + center_exp[1]
            z = radius * np.outer(np.ones(np.size(u)), np.cos(v)) + center_exp[2]
            ax.plot_wireframe(x, y, z, color=color, alpha=alpha, label=label, linewidth=1.0)
        
        plot_blast_hemisphere(10, '#cc0000', 0.8, '10m: 重度破坏 (0.4-0.8MPa)')
        plot_blast_hemisphere(30, '#ff9900', 0.5, '30m: 致命区 (0.1-0.4MPa)')
        plot_blast_hemisphere(50, '#00b33c', 0.3, '50m: 轻度破坏 (0.05MPa)')
        
        ax.scatter(center_exp[0], center_exp[1], center_exp[2], marker='*', s=800, c='yellow', edgecolors='red', zorder=10)
        
        # 调整视角
        ax.view_init(elev=20, azim=-60)
        
    ax.legend(loc='upper right', fontsize=10)
    return fig

# --- 动态分析面板函数 ---
def render_dynamic_analysis(t, state):
    """根据当前时间和状态，提供动态的实时分析和指导。"""
    st.markdown("#### ⚙️ 实时事故分析与指导")
    st.markdown("---")

    if t < 1:
        st.info("🟢 【T < 1 min】泄漏初期：")
        st.markdown(f"**状态：** LNG在罐底形成液池（约 $20 m^2$）。蒸汽云浓度仅 **{state['max_conc']}**，远低于爆炸下限（LFL）。")
        st.markdown("* **建议：** 现场人员快速确认泄漏源，准备隔离措施。")

    elif t < 3:
        st.warning("🟡 【T < 3 min】LFL 临界警告：")
        st.markdown(f"**状态：** 蒸汽云扩散范围 **$400 m^2$**，局部浓度已达 **5% (LFL)**，开始形成可燃区域。")
        st.markdown("* **操作：** **立即执行紧急切断 (ESD)**，同时启动水喷淋稀释云团。")

    elif t < 10:
        st.error("🟠 【T < 10 min】爆炸风险极高：")
        st.markdown(f"**状态：** 蒸汽云已扩散至 **{state['area']:.0f} $m^2$**，东南侧低洼地带浓度高达 **{state['max_conc']}**。")
        st.markdown("* **危险：** **已达到爆炸极限！** 任何火花、静电或违规动火将引发 VCE 爆炸。")
        st.metric("🚨 **当前主要风险**", "低洼高浓度积聚", delta="立即疏散点火源", delta_color="inverse")

    elif t >= 10:
        st.balloons()
        st.subheader("💥 爆炸后果评估 - T+10.1 min")
        st.error("🔴 **灾难已发生！** 最大超压 $0.8 MPa$。")
        st.markdown("---")
        
        st.markdown("#### 伤害区域划分")
        col_dmg1, col_dmg2 = st.columns(2)
        col_dmg1.metric("🔴 核心重灾区 ($R<10m$)", "设备完全损毁", delta="超压 0.4 - 0.8 MPa")
        col_dmg2.metric("🟠 致命区 ($R<30m$)", "人员死亡率100%", delta="超压 0.1 - 0.4 MPa")
        
        st.markdown("##### 🚒 应急指挥指导：")
        st.markdown("* **首要任务：** 隔离并扑灭次生火灾，评估储罐外罐结构完整性。")
        st.markdown("* **救援：** 立即启动伤亡人员搜索和抢救工作，重点关注 $30m \sim 50m$ 区域的烧伤和重伤人员。")

# --- 主界面布局 ---
def main():
    st.title("🏭 LNG储罐区泄漏爆炸事故 3D 仿真平台")
    st.markdown("---")
    st.markdown("#### 场景：储罐底部管道泄漏引发蒸汽云爆炸 (VCE)")
    
    # --- 侧边栏：控制面板 ---
    st.sidebar.header("🕹️ 模拟控制台")
    
    sim_time = st.sidebar.slider("模拟时间进程 (分钟)", 0.0, 15.0, 0.0, 0.1)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 场景参数设定")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("泄漏孔径", "50 mm")
    col2.metric("管道压力", "0.6 MPa")
    st.sidebar.metric("泄漏流速", "0.8 kg/s")
    st.sidebar.info("提示：拖动滑块至 10.0 分钟以上，将触发爆炸事件。")

    # --- 计算当前状态 ---
    current_state = calculate_state(sim_time)

    # --- 顶部：关键指标看板 (KPI) ---
    st.header("实时关键指标 (KPI)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    kpi1.metric(label="当前状态", value=current_state['status'])
    kpi2.metric(label="累计泄漏量 (LNG)", value=f"{current_state['total_leak_kg']:.1f} kg")
    kpi3.metric(label="蒸汽云覆盖面积", value=f"{current_state['area']:.0f} $m^2$", delta=f"{current_state['area']/1200*100:.1f}% (最大范围)")
    
    if sim_time >= 10:
        kpi4.metric("💥 爆炸危险等级", current_state['danger_level'], delta="立即采取行动", delta_color="inverse")
        st.toast('🚨 爆炸警报：危险等级极高！请立即参考 SOP!', icon='🔥')
    elif sim_time >= 5:
        kpi4.metric("⚠️ 泄漏危险等级", current_state['danger_level'], delta="快速处理", delta_color="inverse")
    else:
        kpi4.metric("✅ 泄漏危险等级", current_state['danger_level'])


    # --- 主要内容区：分栏显示 ---
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["🌎 3D 模拟视图 & 分析", "📝 详细事故报告", "🛠️ 应急处置SOP"])

    with tab1:
        st.subheader("实时 3D 扩散/爆炸后果模拟")
        
        # 使用两栏布局：左侧图表，右侧分析
        col_plot, col_analysis = st.columns([2, 1])

        with col_plot:
            fig = draw_3d_simulation_plot(sim_time, current_state)
            st.pyplot(fig, clear_figure=True)
            
        with col_analysis:
            # 渲染动态分析面板
            render_dynamic_analysis(sim_time, current_state)
            
        with st.expander("图例说明"):
            st.markdown("""
            * **泄漏阶段：** 灰色圆柱为储罐；青色/橙色散点模拟贴地重气云团。橙色区域代表高浓度积聚区（爆炸隐患）。
            * **爆炸阶段：** 同心网格半球体代表超压波及范围（颜色越深，破坏性越强）。
            """)

    with tab2:
        st.subheader("事故模拟演练评估报告")
        
        # 模拟生成数据表格
        data = {
            "时间节点": ["T+1 min", "T+3 min", "T+5 min", "T+10 min", "T+10.1 min"],
            "事件": ["液池形成", "达到爆炸下限", "波及BOG机房", "积聚主干道", "蒸汽云爆炸"],
            "覆盖面积($m^2$)": [20, 400, 800, 1200, "N/A"],
            "最高浓度": ["3% (安全)", "5% (LFL)", "8% (危险)", "12% (极危)", "N/A"],
            "后果": ["无直接伤害", "形成可燃区", "波及设备", "报警未处置", "3死2重伤 (预估)"]
        }
        df_report = pd.DataFrame(data)
        st.dataframe(df_report.set_index("时间节点"), use_container_width=True)

        st.markdown("""
        #### 💣 爆炸后果评估摘要
        * **核心爆轰区 ($R<5m$):** 最大超压 $0.8 MPa$，储罐外罐混凝土结构严重破损。
        * **死亡/重度破坏区 ($R<30m$):** 超压 $0.1-0.8 MPa$，人员伤亡率 $100\%$。BOG 压缩机等设备全毁。
        """)

    with tab3:
        st.subheader("推荐应急处置流程 (SOP)")
        st.markdown("""
        #### 1. 自动与人工切断 (T < 3min)
        * **目标：** 在蒸汽云达到 LFL 之前（即 $\mathbf{T<3min}$）完成切断。
        * **行动：** 立即触发 **ESD（紧急切断）** 按钮，切断储罐底部根部阀。
        
        #### 2. 工艺隔离与消防覆盖 (T < 5min)
        * **行动：** 关闭 T-101 出液总阀及回气阀，启动**水喷淋系统**稀释蒸汽云浓度。
        
        #### 3. 人员疏散与管制 (T < 10min)
        * **行动：** 广播通知全厂撤离，重点疏散处于**下风向（北侧）** 和 **低洼区域（东南侧）** 的人员。
        * **避难方向：** 撤离至**上风向**或指定抗爆区。**严禁**在储罐区附近进行任何火工作业。
        """)

if __name__ == "__main__":
    main()