import streamlit as st
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import pandas as pd
import requests
from streamlit_geolocation import streamlit_geolocation
from PIL import Image  # Thư viện xử lý ảnh (thường đi kèm với streamlit)
import io
import base64
import db_utils

st.set_page_config(page_title="Trang chủ - Báo cáo Sự cố", layout="wide")

st.markdown("""
    <style>
    /* 1. Tạo kiểu dáng Thẻ (Card) cho các thông số Khí tượng (Metrics) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 2px 6px 15px rgba(0,0,0,0.1);
    }
    
    /* 2. Làm mịn các đường viền Form nhập liệu */
    div[data-testid="stForm"] {
        border-radius: 12px;
        border: none;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.05);
        padding: 20px;
    }
    
    /* 3. Tùy chỉnh Nút bấm Lưu báo cáo */
    button[kind="primary"] {
        border-radius: 8px;
        font-weight: bold;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

OWM_API_KEY = st.secrets["OWM_API_KEY"]

# HÀM MỚI: Nén và chuyển đổi ảnh thành dạng Base64 siêu nhẹ
def process_and_convert_to_base64(file_obj):
    if file_obj is None:
        return None
    try:
        img = Image.open(file_obj)
        # Chuyển đổi hệ màu RGB nếu cần
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Nén nhỏ kích thước tối đa 300px để không làm nặng Database
        img.thumbnail((300, 300))
        
        buffered = io.BytesIO()
        # Lưu dưới dạng JPEG, chất lượng 70% để dung lượng chỉ khoảng 10-20KB
        img.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None

@st.cache_data(ttl=600)
def get_environmental_data(lat, lon):
    try:
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric&lang=vi"
        weather_res = requests.get(weather_url).json()
        temp = weather_res['main']['temp']
        desc = weather_res['weather'][0]['description']
        
        aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OWM_API_KEY}"
        aqi_res = requests.get(aqi_url).json()
        aqi_val = aqi_res['list'][0]['main']['aqi']
        aqi_dict = {1: "Tốt", 2: "Khá", 3: "Trung bình", 4: "Kém", 5: "Rất kém"}
        aqi_status = aqi_dict.get(aqi_val, "Không xác định")
        return temp, desc.capitalize(), aqi_status
    except Exception as e:
        return None, None, None

@st.cache_data(ttl=600)
def get_address(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'GIS_Incident_App/1.0'}
        response = requests.get(url, headers=headers).json()
        return response.get('display_name', 'Không xác định được địa chỉ')
    except Exception as e:
        return "Không thể tải địa chỉ"

st.title("🗺️ Hệ thống Cảnh báo Sự cố & Giám sát Môi trường")
with st.expander("📖 Hướng dẫn sử dụng hệ thống", expanded=False):
    st.markdown("""
    1. **Sử dụng GPS:** Bấm nút *Định vị tự động* để hệ thống tự tìm vị trí của bạn (Khuyên dùng trên thiết bị di động).
    2. **Click thủ công:** Di chuyển bản đồ và click vào điểm xảy ra sự cố.
    3. Điền thông tin chi tiết, đính kèm hình ảnh và nhấn **Lưu Báo cáo**.
    """)

col1, col2 = st.columns([2, 1])

try:
    df = db_utils.load_data()
except Exception as e:
    st.error(f"Không thể kết nối Supabase: {e}")
    df = pd.DataFrame()

with col1:
    st.subheader("Bản đồ Sự cố")
    view_mode = st.radio(
        "Chế độ hiển thị:",
        options=["Marker (Chi tiết từng điểm)", "Heatmap (Bản đồ nhiệt)"],
        horizontal=True
    )
    m = folium.Map(location=[10.7626, 106.6601], zoom_start=12)
    
    if not df.empty:
        if view_mode == "Marker (Chi tiết từng điểm)":
            for idx, row in df.iterrows():
                color = "green" if row.get('status') == 'resolved' else ("orange" if row['incident_type'] == "Ngập lụt" else "red")
                water_info = f"<br><b>Mức ngập:</b> {row['water_level']}" if pd.notna(row.get('water_level')) and row['water_level'] else ""
                
                # HTML POPUP CHỨA ẢNH
                popup_html = f"<h4>{row['incident_type']}</h4><p>{row['description']}</p>{water_info}<br><b>Trạng thái:</b> {row.get('status', 'pending')}"
                
                # Nếu có ảnh, chèn thẻ img vào Popup bản đồ
                if 'image_base64' in row and pd.notna(row['image_base64']) and row['image_base64']:
                    popup_html += f'<br><img src="{row["image_base64"]}" width="180px" style="border-radius: 8px; margin-top:5px;">'
                
                folium.Marker(
                    [row['lat'], row['lon']], 
                    popup=folium.Popup(popup_html, max_width=250),
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(m)
        else:
            heat_data = [[row['lat'], row['lon']] for index, row in df.iterrows()]
            HeatMap(heat_data, radius=25, blur=15, max_zoom=1, gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}).add_to(m)
            
    map_data = st_folium(m, width=700, height=500)

with col2:
    st.subheader("Thông tin Khu vực & Báo cáo")
    st.markdown("**Lấy vị trí tự động (GPS)**")
    location = streamlit_geolocation()
    
    clicked_lat, clicked_lon = None, None
    temp, env_desc, aqi_status = None, None, None 
    address = "" 
    
    if location['latitude'] is not None and location['longitude'] is not None:
        clicked_lat = location['latitude']
        clicked_lon = location['longitude']
        st.success(f"📡 Đã định vị GPS: {clicked_lat:.4f}, {clicked_lon:.4f}")
    elif map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lon = map_data["last_clicked"]["lng"]
        st.success(f"📍 Tọa độ click: {clicked_lat:.4f}, {clicked_lon:.4f}")
    
    if clicked_lat is not None and clicked_lon is not None:
        address = get_address(clicked_lat, clicked_lon)
        st.info(f"🏠 Địa chỉ: {address}")
        
        temp, env_desc, aqi_status = get_environmental_data(clicked_lat, clicked_lon)
        if temp is not None:
            env_col1, env_col2 = st.columns(2)
            env_col1.metric(label="Thời tiết", value=f"{temp}°C", delta=env_desc, delta_color="off")
            if aqi_status in ["Tốt", "Khá"]:
                env_col2.metric(label="Chỉ số AQI", value=aqi_status)
            else:
                env_col2.metric(label="Chỉ số AQI", value=aqi_status, delta="Cảnh báo", delta_color="inverse")
            st.divider()
    else:
        st.info("Bấm nút định vị hoặc click vào bản đồ để chọn vị trí.")

    # FORM BÁO CÁO VÀ CHỤP/TẢI ẢNH
    incident_type = st.selectbox("Loại sự cố", ["Ngập lụt", "Ổ gà / Hư hỏng đường", "Cây đổ", "Tai nạn", "Khác"])
    
    water_level = None
    if incident_type == "Ngập lụt":
        water_level = st.selectbox("Mức ngập", ["Nhẹ (Dưới mắt cá chân)", "Vừa (Nửa bánh xe)", "Sâu (Ngập ống xả)"])
        
    description = st.text_area("Mô tả chi tiết")
    
    # Giao diện chọn hình thức thêm ảnh
    st.markdown("**📷 Hình ảnh hiện trường**")
    photo_source = st.radio("Chọn phương thức", ["Chụp ảnh từ camera", "Chọn file từ thư viện ảnh"], horizontal=True)
    
    image_file = None
    if photo_source == "Chụp ảnh từ camera":
        image_file = st.camera_input("Chụp ảnh")
    else:
        image_file = st.file_uploader("Tải file ảnh lên", type=["png", "jpg", "jpeg"])
    
    if st.button("Lưu Báo cáo", type="primary"):
        if clicked_lat is None or clicked_lon is None:
            st.toast("Vui lòng định vị hoặc click chọn vị trí!", icon="⚠️")
        elif description.strip() == "":
            st.toast("Vui lòng nhập mô tả sự cố.", icon="⚠️")
        else:
            with st.spinner('Đang nén ảnh và đẩy dữ liệu lên Cloud...'):
                image_base64 = process_and_convert_to_base64(image_file)
                db_utils.insert_data(
                    incident_type, water_level, description, 
                    clicked_lat, clicked_lon, 
                    temp, env_desc, aqi_status, address,
                    image_base64
                )
            
            # Chỉ giữ lại thông báo Toast tinh tế góc màn hình
            st.toast("Đã gửi báo cáo thành công!", icon="✅")
            
            import time
            time.sleep(1.5)
            st.rerun()
