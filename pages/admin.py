import streamlit as st
import pandas as pd
import plotly.express as px
import db_utils
import time
import json

st.set_page_config(page_title="Dashboard Quản trị Nâng cao", layout="wide")

ADMIN_PASSWORD = "123"

if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False

st.title("📊 Hệ thống Quản trị Báo cáo (CMS)")

if not st.session_state['is_admin']:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("Vui lòng đăng nhập để truy cập Dashboard Hệ thống.")
        pwd_input = st.text_input("Nhập mật khẩu Admin:", type="password")
        if st.button("Đăng nhập", type="primary"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state['is_admin'] = True
                st.rerun()
            else:
                st.error("Sai mật khẩu!")
else:
    # Nút Đăng xuất đặt gọn góc phải
    col_title, col_logout = st.columns([8, 1])
    with col_logout:
        if st.button("Đăng xuất"):
            st.session_state['is_admin'] = False
            st.rerun()
        
    st.divider()
    
    # Kéo dữ liệu từ Cloud
    raw_df = db_utils.load_data()
    
    if raw_df.empty:
        st.warning("Chưa có dữ liệu báo cáo nào trong hệ thống.")
    else:
        # 1. BỘ LỌC DỮ LIỆU NÂNG CAO (Advanced Filters)
        with st.expander("🔍 Bộ lọc Dữ liệu", expanded=True):
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            
            # Lọc theo loại sự cố
            incident_options = ["Tất cả"] + list(raw_df['incident_type'].dropna().unique())
            selected_type = filter_col1.selectbox("Loại sự cố", incident_options)
            
            # Lọc theo trạng thái
            status_options = ["Tất cả", "pending", "resolved"]
            selected_status = filter_col2.selectbox("Trạng thái xử lý", status_options)
            
            # Áp dụng logic lọc vào DataFrame
            df = raw_df.copy()
            if selected_type != "Tất cả":
                df = df[df['incident_type'] == selected_type]
            if selected_status != "Tất cả":
                df = df[df['status'] == selected_status]
                
            filter_col3.metric("Số lượng kết quả", len(df))

        # 2. CHỈ SỐ TỔNG QUAN (KPIs) - Tự động nhảy số theo bộ lọc
        st.subheader("📌 Chỉ số Hiện tại")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        total_reports = len(df)
        resolved_reports = len(df[df['status'] == 'resolved']) if 'status' in df.columns else 0
        pending_reports = total_reports - resolved_reports
        top_incident = df['incident_type'].mode()[0] if not df['incident_type'].empty else "N/A"
        
        kpi1.metric("Tổng số sự cố (Đã lọc)", total_reports)
        kpi2.metric("Đã xử lý (Màu xanh)", resolved_reports)
        kpi3.metric("Đang chờ duyệt (Màu đỏ/cam)", pending_reports)
        kpi4.metric("Sự cố phổ biến nhất", top_incident)
        
        st.divider()
        
        # 3. PHÂN TÍCH & TRỰC QUAN HÓA (Plotly)
        if not df.empty:
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                incident_counts = df['incident_type'].value_counts().reset_index()
                incident_counts.columns = ['Loại sự cố', 'Số lượng']
                fig_pie = px.pie(incident_counts, values='Số lượng', names='Loại sự cố', title='Tỷ lệ Cơ cấu Sự cố', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with chart_col2:
                # Phân tích theo trạng thái
                status_counts = df['status'].value_counts().reset_index()
                status_counts.columns = ['Trạng thái', 'Số lượng']
                # Đổi tên cho dễ hiểu trên biểu đồ
                status_counts['Trạng thái'] = status_counts['Trạng thái'].replace({'pending': 'Đang chờ', 'resolved': 'Đã xử lý'})
                fig_bar = px.bar(status_counts, x='Trạng thái', y='Số lượng', title='Tiến độ Xử lý', color='Trạng thái', text_auto=True, color_discrete_map={'Đang chờ': 'red', 'Đã xử lý': 'green'})
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        
        # 4. QUẢN LÝ VÀ DUYỆT BÁO CÁO (Tương tác trực tiếp)
        st.subheader("🛠️ Duyệt & Quản lý Sự cố")
        
        # Tạo Tabs để Admin dễ phân loại công việc
        tab1, tab2 = st.tabs(["📋 Chế độ Bảng & Xuất File", "🖼️ Chế độ Thẻ (Duyệt/Xóa từng mục)"])
        
        with tab1:
            st.dataframe(df.drop(columns=['image_base64'], errors='ignore'), use_container_width=True)
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                # NÚT XUẤT CSV CŨ
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Tải xuống (CSV)", data=csv, file_name='DuLieu.csv', mime='text/csv', type="primary", use_container_width=True)
            
            with col_dl2:
                # TÍNH NĂNG MỚI: XUẤT GEOJSON CHUẨN GIS
                geojson = {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": "Point", "coordinates": [row['lon'], row['lat']]},
                            "properties": {k: str(v) for k, v in row.items() if k != 'image_base64'}
                        } for _, row in df.iterrows()
                    ]
                }
                st.download_button("🌍 Tải xuống Không gian (GeoJSON)", data=json.dumps(geojson), file_name='DuLieu_GIS.geojson', mime='application/geo+json', type="primary", use_container_width=True)

        with tab2:
            if df.empty:
                st.info("Không có dữ liệu phù hợp với bộ lọc hiện tại.")
            else:
                cols = st.columns(3)
                for i, (_, row) in enumerate(df.iterrows()):
                    col_index = i % 3
                    with cols[col_index]:
                        # Thiết kế dạng Card
                        with st.container(border=True):
                            # Hiển thị ảnh (Đã dùng use_container_width=True để không bị cảnh báo)
                            if 'image_base64' in row and pd.notna(row['image_base64']) and row['image_base64']:
                                st.image(row['image_base64'], use_container_width=True)
                            
                            st.markdown(f"**[{row['id']}] {row['incident_type']}**")
                            st.caption(f"📍 {row.get('address', 'Chưa rõ địa chỉ')}")
                            st.write(f"📝 {row['description']}")
                            
                            # Hiển thị trạng thái hiện tại
                            if row['status'] == 'pending':
                                st.error("Trạng thái: Đang chờ")
                            else:
                                st.success("Trạng thái: Đã xử lý")
                            
                            # Các nút thao tác (Nằm trên cùng 1 hàng)
                            btn_col1, btn_col2, btn_col3 = st.columns(3)
                            with btn_col1:
                                if row['status'] == 'pending':
                                    if st.button("✅ Duyệt", key=f"resolve_{row['id']}"):
                                        db_utils.update_status(row['id'], "resolved")
                                        st.rerun()
                            with btn_col2:
                                if st.button("🗑️ Xóa", key=f"del_{row['id']}"):
                                    db_utils.delete_report(row['id'])
                                    st.rerun()
                            with btn_col3:
                                # TÍNH NĂNG MỚI: CHỈ ĐƯỜNG GOOGLE MAPS
                                maps_url = f"https://www.google.com/maps/dir/?api=1&destination={row['lat']},{row['lon']}"
                                st.link_button("🗺️ Chỉ đường", maps_url)
                                    
        # Khu vực cực kỳ nguy hiểm (Xóa toàn bộ)
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.expander("⚠️ Cài đặt Hệ thống (Danger Zone)"):
            st.warning("Hành động này sẽ xóa vĩnh viễn toàn bộ dữ liệu trong cơ sở dữ liệu Supabase.")
            if st.button("Xóa toàn bộ dữ liệu hệ thống", type="primary"):
                db_utils.clear_all_data()
                st.success("Đã xóa sạch cơ sở dữ liệu.")
                time.sleep(1.5)
                st.rerun()
