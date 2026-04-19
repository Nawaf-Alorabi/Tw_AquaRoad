import streamlit as st
import cv2
from ultralytics import YOLO
import numpy as np
import requests
import datetime
import time
import urllib.parse
import sqlite3

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="AQUA-ROAD | Autonomous Monitoring",
    layout="wide"
)

# --- 2. Interface Customization (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #FAF9F6; }
    [data-testid="stSidebar"] { background-color: #003527 !important; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h3 {
        color: white !important;
    }
    .main-title {
        font-family: 'Manrope', sans-serif;
        font-weight: 800;
        color: #003527 !important;
        text-transform: uppercase;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-left: 5px solid #003527;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 15px;
    }
    .details-text { color: #474747 !important; font-size: 13px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Database Management ---
def init_db():
    conn = sqlite3.connect('aqua_road.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, time TEXT, source TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def save_report_to_db(source, status):
    conn = sqlite3.connect('aqua_road.db')
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO reports (date, time, source, status) VALUES (?, ?, ?, ?)",
              (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), source, status))
    conn.commit()
    conn.close()

init_db()

# --- 4. Alert Function & Session State ---
def send_telegram_alert(source_option, time_now):
    token = "8524001645:AAFCZbanUp8kJVKxoV0SGkMWYSVGw1kD9Wo"
    chat_id = "954637036"
    raw_message = f"Latest Report Sent:\nSource: {source_option}\nTime: {time_now}"
    url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={urllib.parse.quote(raw_message)}"
    try:
        requests.get(url, timeout=5)
    except:
        pass

if 'last_alert_time' not in st.session_state:
    st.session_state.last_alert_time = 0

# 
if 'last_report_html' not in st.session_state:
    st.session_state.last_report_html = ""

# --- 5. Model Loading ---
@st.cache_resource
def load_model():
    return YOLO('best.pt')

model = load_model()

# --- 6. Top Header ---
st.markdown('<h1 class="main-title">🌊 AQUA-ROAD</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #003527; font-size: 14px; margin-top:-10px; font-weight:bold;">Automated Water Accumulation Monitoring System</p>', unsafe_allow_html=True)
st.divider()

# --- 7. Sidebar ---
with st.sidebar:
    st.markdown('<h3>⚙️ SETTINGS</h3>', unsafe_allow_html=True)
    input_type = st.sidebar.radio("INPUT TYPE", ("Live Video", "Upload Image"))
    source_option = st.sidebar.selectbox("CHOOSE SOURCE", ("Camera #402", "Camera #105", "Trial Stream"))
    threshold = st.sidebar.slider("CONFIDENCE", 0.0, 1.0, 0.5)
    iou_val = st.sidebar.slider("IoU THRESHOLD", 0.0, 1.0, 0.45)

# --- 8. Main Content ---
col_video, col_info = st.columns([2, 1])

with col_video:
    if input_type == "Live Video":
        st.markdown('<p style="font-weight:bold; color:#5E5E5E;">Live Monitoring Feed</p>', unsafe_allow_html=True)
        st_frame = st.empty()
    else:
        st.markdown('<p style="font-weight:bold; color:#5E5E5E;">Image Analysis</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
        st_frame = st.empty()

with col_info:
    st.markdown('<p style="font-weight:bold; color:#5E5E5E;">Control & Monitoring Panel</p>', unsafe_allow_html=True)
    status_indicator = st.empty()
    
    if source_option == "Camera #402":
        location_name, coordinates = "Al-Hada District, Riyadh", "24.71°N, 46.67°E"
        video_source = 0  # Local camera
    elif source_option == "Camera #105":
        location_name, coordinates = "Al-Malqa District, Riyadh", "24.82°N, 46.61°E"
        video_source = 0  # Local camera
    else:
        location_name, coordinates = "Test Zone, Riyadh", "00.00°N, 00.00°E"
        # Using a sample video URL for testing (you can replace with your own)
        video_source = "https://commondatastorage.googleapis.com/gtv-videos-library/sample/ForBiggerBlazes.mp4"

    st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 10px; color: gray; font-weight: bold; text-transform: uppercase;">Exact Location</div>
            <div style="font-weight:bold; font-size:14px; color:#1A1C1A;">{location_name}</div>
            <div style="font-size: 11px; color: #474747;">{coordinates}</div>
        </div>
    """, unsafe_allow_html=True)
    
    alert_log_placeholder = st.empty()

def handle_detection(results, source_option):
    current_labels = [model.names[int(box.cls[0])].lower() for box in results[0].boxes]
    is_danger = any(label in current_labels for label in ["pond", "water", "flood", "puddle"])

    if is_danger:
        status_indicator.error("🚨 ALERT: Water Accumulation Detected")
        current_time = time.time()
        if current_time - st.session_state.last_alert_time > 600:
            time_now = datetime.datetime.now().strftime('%H:%M:%S')
            send_telegram_alert(source_option, time_now)
            save_report_to_db(source_option, "Detected")
            st.session_state.last_alert_time = current_time
            st.session_state.last_report_html = f"""
                <div class="metric-card" style="border-left-color: #ba1a1a;">
                    <b style="color:#ba1a1a;">📅 Latest Archived Report:</b><br>
                    <span class="details-text">Source: {source_option}</span><br>
                    <span class="details-text">Time: {time_now}</span><br>
                    <span style="color:green; font-weight:bold; font-size:13px;">✓ Reported & Saved Successfully</span>
                </div>
            """
            st.toast(f'Alert Saved: {source_option}')
    else:
        status_indicator.success("✔️ SYSTEM STATUS: Road is Clear")

    if st.session_state.last_report_html:
        alert_log_placeholder.markdown(st.session_state.last_report_html, unsafe_allow_html=True)


if input_type == "Live Video":
    try:
        cap = cv2.VideoCapture(video_source)
        if not cap.isOpened():
            st.error("❌ خطأ: لا يمكن الاتصال بمصدر الفيديو")
            st.info("💡 للاستخدام المحلي: تأكد من توصيل الكاميرا")
        else:
            frame_count = 0
            max_frames = 300
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                frame = cv2.resize(frame, (640, 480))
                results = model.predict(frame, conf=threshold, iou=iou_val)
                st_frame.image(cv2.cvtColor(results[0].plot(), cv2.COLOR_BGR2RGB), use_container_width=True)
                handle_detection(results, source_option)
                frame_count += 1
            cap.release()
            st.success(f"✅ تمت معالجة {frame_count} إطار")
    except Exception as e:
        st.error(f"❌ خطأ: {str(e)}")

else:  # Upload Image
    if uploaded_file is not None:
        try:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            image = cv2.imdecode(file_bytes, 1)
            image = cv2.resize(image, (640, 480))
            results = model.predict(image, conf=threshold, iou=iou_val)
            st_frame.image(cv2.cvtColor(results[0].plot(), cv2.COLOR_BGR2RGB), use_container_width=True)
            handle_detection(results, source_option)
        except Exception as e:
            st.error(f"❌ خطأ في معالجة الصورة: {str(e)}")
    else:
        st.info("📤 يرجى رفع صورة للبدء في التحليل")