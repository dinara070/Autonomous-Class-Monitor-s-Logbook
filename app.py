import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Ініціалізація стану повинна бути першою
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# --- КОНФІГУРАЦІЯ СТОРІНКИ ---
st.set_page_config(page_title="Autonomous Class Monitor’s Logbook", layout="centered")

# Пароль (зміни на свій)
ACCESS_PASSWORD = "your_secret_password" 

# Список твоєї групи
MY_GROUP = [
    "Адамлюк Владислав Романович", "Бичко Дар'я Юріївна", "Бугрова Юлія Вікторівна", 
    "Бурейко Володимир Омелянович", "Гончарук Ангеліна Сергіївна", "Гріщенко Світлана Василівна", 
    "Гунько Іван Романович", "Дорош Руслан Миколайович", "Журавель Альона Олександрович", 
    "Зінченко Максим Олександрович", "Калінін Євген Олексійович", "Кисіль Яна Юріївна", 
    "Киця Ярослав Володимирович", "Кравчук Юлія Юріївна", "Мартинюк Діана Сергіївна", 
    "Назарук Діана Володимирівна", "Пасічник Софія Назарівна", "Пустовіт Анастасія Дмитрівна", 
    "Пучкова Валерія Ігорівна", "Сичук Ангеліна Олександрівна", "Слободянюк Вікторія Вікторівна", 
    "Стаськова Валентина Анатоліївна", "Харкевич Руслан Сергійович", 
    "Черешня Станіслав Сергійович", "Чорна Єлизавета Миколаївна"
]

# --- БАЗА ДАНИХ (Оптимізовано) ---
@st.cache_resource
def get_connection():
    return sqlite3.connect('attendance_private.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_name TEXT,
                  date TEXT,
                  period TEXT,
                  subject TEXT,
                  status TEXT)''')
    conn.commit()

# --- ЛОГІКА ВХОДУ ---
if not st.session_state["authenticated"]:
    st.title("🔐 Login to Logbook")
    with st.form("login_form"):
        pwd = st.text_input("Enter password:", type="password")
        if st.form_submit_button("Login"):
            if pwd == ACCESS_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong password!")
    st.stop()

# --- ОСНОВНИЙ ІНТЕРФЕЙС ---
init_db()
conn = get_connection()

st.title("📝 Autonomous Class Monitor’s Logbook")

# Використовуємо sidebar з чіткими ключами
menu = st.sidebar.radio("Navigation", ["New Attendance", "History & Export", "Stats"], key="main_menu")

if menu == "New Attendance":
    st.subheader("📍 Attendance Check")
    
    with st.form("check_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_now = st.date_input("Date", datetime.now(), key="entry_date")
            subject = st.text_input("Subject", placeholder="e.g. Calculus", key="entry_sub")
        with col2:
            period = st.selectbox("Period", ["1", "2", "3", "4", "5", "6"], key="entry_period")
            
        st.divider()
        st.write("### Mark Absent Students:")
        
        absent_data = {}
        for student in sorted(MY_GROUP):
            absent_data[student] = st.checkbox(student, key=f"abs_{student}")

        if st.form_submit_button("💾 Save Attendance"):
            if not subject:
                st.error("Please enter the subject name!")
            else:
                c = conn.cursor()
                date_str = date_now.strftime("%Y-%m-%d")
                for student in MY_GROUP:
                    status = "н" if absent_data[student] else ""
                    c.execute("INSERT INTO attendance (student_name, date, period, subject, status) VALUES (?,?,?,?,?)",
                              (student, date_str, period, subject, status))
                conn.commit()
                st.success("Successfully saved!")
                st.balloons()

elif menu == "History & Export":
    st.subheader("📂 Records Archive")
    df = pd.read_sql("SELECT * FROM attendance ORDER BY id DESC", conn)
    
    if not df.empty:
        filter_date = st.date_input("Filter by date", value=None, key="filter_date")
        if filter_date:
            df = df[df['date'] == filter_date.strftime("%Y-%m-%d")]
            
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ Download CSV Report", csv, "attendance.csv", "text/csv", key="btn_csv")
    else:
        st.info("Logbook is empty.")

elif menu == "Stats":
    st.subheader("📊 Absenteeism Stats")
    df = pd.read_sql("SELECT student_name FROM attendance WHERE status='н'", conn)
    
    if not df.empty:
        stats = df['student_name'].value_counts()
        st.bar_chart(stats)
        st.table(stats)
    else:
        st.info("No absences recorded yet.")

# --- ВИХІД ---
st.sidebar.divider()
if st.sidebar.button("Logout 🚪", key="btn_logout"):
    st.session_state["authenticated"] = False
    st.rerun()
