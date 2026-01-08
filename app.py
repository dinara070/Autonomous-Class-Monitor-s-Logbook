import streamlit as st
from streamlit_cookies_controller import CookieController
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import io

# --- КОНФІГУРАЦІЯ ТА КУКІ ---
st.set_page_config(page_title="Autonomous Class Monitor’s Logbook", layout="wide")
controller = CookieController()

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

# --- БЕЗПЕКА ТА БД ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def create_connection():
    return sqlite3.connect('attendance_private.db', check_same_thread=False)

def init_db():
    conn = create_connection()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, full_name TEXT)')
    # Додано колонку semester для майбутнього сортування
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  student_name TEXT, 
                  date TEXT, 
                  period TEXT, 
                  subject TEXT, 
                  status TEXT, 
                  moderator TEXT,
                  semester TEXT)''')
    conn.commit()

# --- ЛОГІКА АВТОРИЗАЦІЇ ---
def perform_login(user_data):
    st.session_state['authenticated'] = True
    st.session_state['username'] = user_data[0]
    st.session_state['full_name'] = user_data[2]
    controller.set('remember_user', user_data[0])
    st.rerun()

def login_register_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Access Control")
        tab1, tab2 = st.tabs(["Увійти", "Реєстрація"])
        conn = create_connection()
        c = conn.cursor()

        with tab1:
            saved_user = controller.get('remember_user')
            user = st.text_input("Username", value=saved_user if saved_user else "", key="l_user")
            pwd = st.text_input("Password", type='password', key="l_pwd")
            if st.button("Login", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=?', (user,))
                data = c.fetchone()
                if data and check_hashes(pwd, data[1]):
                    perform_login(data)
                else:
                    st.error("Невірний логін або пароль")

        with tab2:
            new_user = st.text_input("Username", key="r_user")
            new_full_name = st.text_input("Повне ПІБ", key="r_name")
            new_pwd = st.text_input("Password", type='password', key="r_pwd")
            if st.button("Sign Up", use_container_width=True):
                if new_user and new_pwd and new_full_name:
                    try:
                        c.execute('INSERT INTO users VALUES (?,?,?)', (new_user, make_hashes(new_pwd), new_full_name))
                        conn.commit()
                        st.success("Аккаунт створено! Увійдіть.")
                    except:
                        st.error("Цей логін вже зайнятий")

# --- ОСНОВНИЙ ДОДАТОК ---
def main():
    init_db()
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_register_page()
        return

    conn = create_connection()
    st.sidebar.title(f"👤 {st.session_state['full_name']}")
    
    # Вибір семестру для роботи
    current_sem = st.sidebar.selectbox("Поточний семестр", ["2025-1", "2025-2", "2026-1", "2026-2"], index=2)
    
    menu = st.sidebar.radio("Навігація", ["Нова перекличка", "Архів та Експорт", "Імпорт даних", "Статистика"])

    if menu == "Нова перекличка":
        st.subheader(f"📍 Перекличка — Семестр {current_sem}")
        with st.form("att_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            date_now = c1.date_input("Дата", datetime.now())
            subject = c1.text_input("Предмет")
            period = c2.selectbox("Пара", ["1", "2", "3", "4", "5", "6"])
            
            st.divider()
            absent_status = {}
            for student in sorted(MY_GROUP):
                absent_status[student] = st.checkbox(student)

            if st.form_submit_button("Зберегти запис", use_container_width=True):
                if subject:
                    c = conn.cursor()
                    d_str = date_now.strftime("%Y-%m-%d")
                    for s in MY_GROUP:
                        status = "н" if absent_status[s] else ""
                        c.execute("INSERT INTO attendance (student_name, date, period, subject, status, moderator, semester) VALUES (?,?,?,?,?,?,?)",
                                  (s, d_str, period, subject, status, st.session_state['username'], current_sem))
                    conn.commit()
                    st.success("Дані збережено успішно!")
                else:
                    st.error("Потрібно вказати назву предмета")

    elif menu == "Архів та Експорт":
        st.subheader("📂 Архів записів")
        
        # Фільтр за семестром в архіві
        df = pd.read_sql(f"SELECT * FROM attendance WHERE semester='{current_sem}' ORDER BY id DESC", conn)
        
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            
            # Блок Експорту
            st.divider()
            st.write("### 📤 Експорт даних")
            col_ex1, col_ex2 = st.columns(2)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            col_ex1.download_button("Завантажити у CSV", csv, f"attendance_sem_{current_sem}.csv", "text/csv", use_container_width=True)
            
            # Експорт в Excel через буфер
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Attendance')
            col_ex2.download_button("Завантажити у Excel", buffer.getvalue(), f"attendance_sem_{current_sem}.xlsx", use_container_width=True)
        else:
            st.info(f"В семестрі {current_sem} ще немає записів.")

    elif menu == "Імпорт даних":
        st.subheader("📥 Імпорт зовнішніх даних")
        st.warning("Увага: Формат файлу повинен збігатися з форматом експорту (CSV або Excel)")
        
        uploaded_file = st.file_uploader("Оберіть файл для імпорту", type=['csv', 'xlsx'])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    imp_df = pd.read_csv(uploaded_file)
                else:
                    imp_df = pd.read_excel(uploaded_file)
                
                st.write("Попередній перегляд даних:")
                st.dataframe(imp_df.head())
                
                if st.button("🚀 Підтвердити імпорт у базу"):
                    imp_df.to_sql('attendance', conn, if_exists='append', index=False)
                    st.success("Дані успішно додані до вашого журналу!")
            except Exception as e:
                st.error(f"Помилка при зчитуванні файлу: {e}")

    elif menu == "Статистика":
        st.subheader(f"📊 Аналіз пропусків — Семестр {current_sem}")
        df_stat = pd.read_sql(f"SELECT student_name FROM attendance WHERE status='н' AND semester='{current_sem}'", conn)
        if not df_stat.empty:
            counts = df_stat['student_name'].value_counts()
            st.bar_chart(counts)
            st.table(counts)
        else:
            st.info("Немає даних для аналізу.")

    if st.sidebar.button("Вийти 🚪"):
        st.session_state["authenticated"] = False
        st.rerun()

if __name__ == '__main__':
    main()
