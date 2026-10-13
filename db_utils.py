import streamlit as st
from supabase import create_client, Client
import pandas as pd

# Lấy URL và Key từ file .streamlit/secrets.toml
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def insert_data(incident_type, water_level, desc, lat, lon, temp, weather_desc, aqi, address, image_base64):
    data = {
        "incident_type": incident_type,
        "water_level": water_level,
        "description": desc,
        "lat": lat,
        "lon": lon,
        "status": "pending",
        "temperature": temp,
        "weather_desc": weather_desc,
        "aqi": aqi,
        "address": address,
        "image_base64": image_base64  # Thêm dòng lưu trữ ảnh mới
    }
    supabase.table("reports").insert(data).execute()

def clear_all_data():
    # API của Supabase yêu cầu lệnh xóa (delete) phải đi kèm một điều kiện để tránh việc vô tình xóa nhầm toàn bộ bảng.
    # Giải pháp: Xóa tất cả các báo cáo có id > 0 (tương đương với việc xóa sạch toàn bộ dữ liệu trong bảng).
    supabase.table("reports").delete().gt("id", 0).execute()

def load_data():
    # Kéo toàn bộ dữ liệu từ Supabase về
    response = supabase.table("reports").select("*").execute()
    
    # Nếu có dữ liệu thì chuyển thành DataFrame, nếu không thì tạo bảng trống
    if response.data:
        return pd.DataFrame(response.data)
    else:
        return pd.DataFrame(columns=['id', 'incident_type', 'water_level', 'description', 'lat', 'lon', 'status', 'created_at'])

def update_status(report_id, new_status):
    """Cập nhật trạng thái của một báo cáo cụ thể"""
    supabase.table("reports").update({"status": new_status}).eq("id", report_id).execute()

def delete_report(report_id):
    """Xóa một báo cáo cụ thể dựa vào ID"""
    supabase.table("reports").delete().eq("id", report_id).execute()