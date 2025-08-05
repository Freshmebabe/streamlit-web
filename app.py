import streamlit as st
import folium
from streamlit_folium import folium_static
from folium import plugins

# 页面配置
st.set_page_config(
    page_title="重庆应急设备路径地图",
    page_icon="🚒",
    layout="wide"
)

# 标题与说明
st.title("重庆应急设备调配路径地图")
st.write("设备 EQP_0457 到灾点的路径展示（含动态轨迹与导航工具）")

# 坐标数据
locations = {
    "设备EQP_0457": [29.5723, 106.5343],
    "长江大桥": [29.5618, 106.5522],
    "红旗路": [29.5562, 106.5648],
    "灾点": [29.5491, 106.5765]
}

# 路径点
route_coords = [
    locations["设备EQP_0457"],
    locations["长江大桥"],
    locations["红旗路"],
    locations["灾点"]
]

# 初始化地图（含比例尺）
m = folium.Map(
    location=[(locations["设备EQP_0457"][0] + locations["灾点"][0]) / 2,
              (locations["设备EQP_0457"][1] + locations["灾点"][1]) / 2],
    zoom_start=14,
    tiles='CartoDB positron',
    control_scale=True
)

# 添加起点标记
folium.Marker(
    location=locations["设备EQP_0457"],
    tooltip="设备EQP_0457",
    popup="设备编号：EQP_0457<br>状态：待命",
    icon=folium.Icon(color='green', icon='truck', prefix='fa')
).add_to(m)

# 添加灾点标记
folium.Marker(
    location=locations["灾点"],
    tooltip="灾点",
    popup="灾情等级：二级<br>需求：应急救援设备",
    icon=folium.Icon(color='red', icon='exclamation-circle', prefix='fa')
).add_to(m)

# 添加中间途经点标记
for name, coord in locations.items():
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

# 添加静态 PolyLine（可选）
folium.PolyLine(
    route_coords,
    color='orange',
    weight=6,
    opacity=0.7,
    tooltip="设备运输路线"
).add_to(m)

# 添加动态轨迹（AntPath）
plugins.AntPath(
    locations=route_coords,
    dash_array=[10, 20],
    delay=800,
    color='red',
    pulse_color='orange',
    weight=5
).add_to(m)

# 添加路径信息标签
middle_idx = len(route_coords) // 2
folium.Marker(
    location=route_coords[middle_idx],
    icon=folium.DivIcon(
        html="""
        <div style="background-color:white; padding:6px; border-radius:4px; 
                    box-shadow:0 1px 4px rgba(0,0,0,0.3); font-size:12px">
            <b>路径信息</b><br/>
            距离：9.6公里<br/>
            预计时间：15分钟
        </div>
        """
    )
).add_to(m)

# 添加测距控件
plugins.MeasureControl(
    position='topright',
    primary_length_unit='kilometers'
).add_to(m)

# 添加小地图
plugins.MiniMap(toggle_display=True).add_to(m)

# 添加全屏控件
plugins.Fullscreen().add_to(m)

# 显示地图
folium_static(m, width=1000, height=600)

# 侧边栏
with st.sidebar:
    st.header("设备信息")
    st.info("""
    - **编号**：EQP_0457  
    - **类型**：应急救援车  
    - **当前位置**：江北区  
    - **状态**：已调度  
    - **出发时间**：09:30  
    """)

    st.header("路径详情")
    st.success("""
    - **总距离**：9.6公里  
    - **预计到达**：10:00  
    - **途经路线**：  
      1. 起点 → 长江大桥  
      2. 长江大桥 → 红旗路  
      3. 红旗路 → 灾点  
    - **路况**：良好  
    """)

    st.header("灾点信息")
    st.warning("""
    - **位置**：渝中区  
    - **灾情**：二级应急事件  
    - **需求**：救援设备及3名工作人员  
    - **报告时间**：09:20  
    """)
