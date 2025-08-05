import streamlit as st
import folium
from streamlit_folium import folium_static
from folium import plugins
import time

# 页面配置
st.set_page_config(
    page_title="重庆应急设备路径地图",
    page_icon="🚒",
    layout="wide"
)

# 标题与说明
st.title("重庆应急设备调配路径地图")
st.write("实时路径规划工具，输入起始点、目的地和途经点")

# 使用会话状态保存用户输入的点位
if 'locations' not in st.session_state:
    st.session_state.locations = {
        "设备EQP_0457": [29.5723, 106.5343],
        "灾点": [29.5491, 106.5765]
    }
if 'route_coords' not in st.session_state:
    st.session_state.route_coords = []

# 输入侧边栏 - 新增实时输入功能
with st.sidebar:
    st.header("设备信息")
    st.info("""
    - **编号**：EQP_0457  
    - **类型**：应急救援车  
    - **状态**：已调度  
    - **速度**：60 km/h  
    """)
    
    st.header("实时路径规划")
    
    # 起始点输入
    start_lat = st.number_input("起点纬度", value=29.5723, key="start_lat")
    start_lng = st.number_input("起点经度", value=106.5343, key="start_lng")
    if st.button("添加起点"):
        st.session_state.locations["设备EQP_0457"] = [start_lat, start_lng]
        st.experimental_rerun()
    
    # 终点输入
    end_lat = st.number_input("终点纬度", value=29.5491, key="end_lat")
    end_lng = st.number_input("终点经度", value=106.5765, key="end_lng")
    if st.button("添加终点"):
        st.session_state.locations["灾点"] = [end_lat, end_lng]
        st.experimental_rerun()
    
    # 途经点输入
    st.subheader("添加途经点")
    wp_name = st.text_input("途经点名称", key="wp_name", placeholder="如:长江大桥")
    wp_lat = st.number_input("途经点纬度", key="wp_lat", value=29.5618)
    wp_lng = st.number_input("途经点经度", key="wp_lng", value=106.5522)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("添加途经点"):
            if wp_name:
                st.session_state.locations[wp_name] = [wp_lat, wp_lng]
                st.experimental_rerun()
            else:
                st.warning("请先输入途经点名称")
    
    with col2:
        if st.button("清除所有途经点"):
            keys_to_remove = [key for key in st.session_state.locations if key not in ["设备EQP_0457", "灾点"]]
            for key in keys_to_remove:
                st.session_state.locations.pop(key)
            st.experimental_rerun()
    
    st.header("路径详情")
    if st.session_state.route_coords:
        distance = len(st.session_state.route_coords) * 1.2  # 模拟距离计算
        st.success(f"""
        - **总距离**：{distance:.1f}公里  
        - **预计用时**：{distance*1.2:.1f}分钟  
        - **途经点数量**：{len(st.session_state.locations) - 2}  
        """)
    
    st.header("灾点信息")
    st.warning("""
    - **灾情等级**：二级应急事件  
    - **需求**：救援设备及3名工作人员  
    - **联系人**：李主任 (138****1234)  
    """)

# 计算路径（模拟路径规划算法）
def calculate_route():
    if "设备EQP_0457" not in st.session_state.locations or "灾点" not in st.session_state.locations:
        st.warning("请先添加起点和终点！")
        return []
    
    # 按顺序收集除起点和终点外的所有点位
    waypoints = [coord for name, coord in st.session_state.locations.items() 
                if name != "设备EQP_0457" and name != "灾点"]
    
    # 按纬度排序（简单排序算法模拟路径规划）
    waypoints.sort(key=lambda x: x[0])
    
    route = [
        st.session_state.locations["设备EQP_0457"],
        *waypoints,
        st.session_state.locations["灾点"]
    ]
    return route

# 生成模拟的动态轨迹点
def generate_animation_points(start, end, waypoints):
    if not waypoints:
        return [start, end]
    
    points = [start]
    
    # 在起点和第一个途经点之间生成中间点
    for i in range(len(waypoints)):
        prev = waypoints[i-1] if i > 0 else start
        current = waypoints[i]
        
        # 生成5个中间点
        for j in range(1, 6):
            lat = prev[0] + (current[0] - prev[0]) * j/6
            lng = prev[1] + (current[1] - prev[1]) * j/6
            points.append([lat, lng])
    
    # 在最后一个途经点和终点之间生成中间点
    last_wp = waypoints[-1]
    for j in range(1, 6):
        lat = last_wp[0] + (end[0] - last_wp[0]) * j/6
        lng = last_wp[1] + (end[1] - last_wp[1]) * j/6
        points.append([lat, lng])
    
    points.append(end)
    return points

# 计算中心位置
start = st.session_state.locations["设备EQP_0457"]
end = st.session_state.locations["灾点"]
center_lat = (start[0] + end[0]) / 2
center_lng = (start[1] + end[1]) / 2

# 计算路径
st.session_state.route_coords = calculate_route()

# 初始化地图
m = folium.Map(
    location=[center_lat, center_lng],
    zoom_start=13,
    tiles='CartoDB positron',
    control_scale=True
)

# 添加起点标记
folium.Marker(
    location=start,
    tooltip="设备EQP_0457",
    popup="设备编号：EQP_0457<br>状态：已调度",
    icon=folium.Icon(color='green', icon='truck', prefix='fa')
).add_to(m)

# 添加灾点标记
folium.Marker(
    location=end,
    tooltip="灾点",
    popup="灾情等级：二级<br>需求：应急救援设备",
    icon=folium.Icon(color='red', icon='exclamation-circle', prefix='fa')
).add_to(m)

# 添加途经点标记
for name, coord in st.session_state.locations.items():
    if name not in ["设备EQP_0457", "灾点"]:
        folium.CircleMarker(
            location=coord,
            radius=8,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.6,
            tooltip=name,
            popup=name
        ).add_to(m)

# 添加静态路径线
if st.session_state.route_coords:
    # 添加静态 PolyLine
    folium.PolyLine(
        st.session_state.route_coords,
        color='orange',
        weight=6,
        opacity=0.7,
        tooltip="设备运输路线"
    ).add_to(m)
    
    # 生成动画点
    animation_points = generate_animation_points(
        st.session_state.route_coords[0],
        st.session_state.route_coords[-1],
        st.session_state.route_coords[1:-1]
    )
    
    # 添加动态轨迹
    plugins.AntPath(
        locations=animation_points,
        dash_array=[10, 20],
        delay=800,
        color='red',
        pulse_color='orange',
        weight=5
    ).add_to(m)
    
    # 添加路径信息标签
    if len(st.session_state.route_coords) > 2:
        middle_idx = len(st.session_state.route_coords) // 2
        distance = len(st.session_state.route_coords) * 1.2
        folium.Marker(
            location=st.session_state.route_coords[middle_idx],
            icon=folium.DivIcon(
                html=f"""
                <div style="background-color:white; padding:6px; border-radius:4px; 
                            box-shadow:0 1px 4px rgba(0,0,0,0.3); font-size:12px">
                    <b>路径信息</b><br/>
                    距离：{distance:.1f}公里<br/>
                    预计用时：{distance*1.2:.1f}分钟
                </div>
                """
            )
        ).add_to(m)

# 添加地图控件
plugins.MeasureControl(
    position='topright',
    primary_length_unit='kilometers'
).add_to(m)

plugins.MiniMap(toggle_display=True).add_to(m)
plugins.Fullscreen().add_to(m)

# 显示地图
folium_static(m, width=1000, height=600)

# 当前路径点显示
with st.expander("当前路径点"):
    st.info(f"**起点**: {start[0]}, {start[1]}")
    st.info(f"**终点**: {end[0]}, {end[1]}")
    if st.session_state.locations:
        for name, coord in st.session_state.locations.items():
            if name not in ["设备EQP_0457", "灾点"]:
                st.success(f"**途经点 {name}**: {coord[0]}, {coord[1]}")

# 实时移动效果动画
if st.button("开始模拟移动"):
    st.write("设备移动中...")
    
    # 使用进度条
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 生成动画点
    animation_points = generate_animation_points(
        st.session_state.route_coords[0],
        st.session_state.route_coords[-1],
        st.session_state.route_coords[1:-1]
    )
    
    # 创建临时地图用于动画
    temp_map = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='CartoDB positron'
    )
    
    # 临时地图容器
    map_placeholder = st.empty()
    
    for i, point in enumerate(animation_points):
        # 更新进度
        progress = int((i + 1) / len(animation_points) * 100)
        progress_bar.progress(progress)
        status_text.text(f"移动进度: {progress}%")
        
        # 清空临时地图
        temp_map = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles='CartoDB positron'
        )
        
        # 添加起点和终点
        folium.Marker(
            location=st.session_state.locations["设备EQP_0457"],
            icon=folium.Icon(color='green', icon='truck', prefix='fa')
        ).add_to(temp_map)
        
        folium.Marker(
            location=st.session_state.locations["灾点"],
            icon=folium.Icon(color='red', icon='exclamation-circle', prefix='fa')
        ).add_to(temp_map)
        
        # 添加当前设备位置
        folium.Marker(
            location=point,
            icon=folium.Icon(color='blue', icon='truck', prefix='fa')
        ).add_to(temp_map)
        
        # 添加路径
        folium.PolyLine(
            st.session_state.route_coords,
            color='orange',
            weight=3
        ).add_to(temp_map)
        
        # 显示临时地图
        map_placeholder.empty()
        with map_placeholder.container():
            folium_static(temp_map, width=1000, height=400)
        
        # 延迟以创建动画效果
        time.sleep(0.2)
    
    # 完成提示
    st.balloons()
    st.success("设备已到达目的地！")