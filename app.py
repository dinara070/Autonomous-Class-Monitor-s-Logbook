import streamlit as st
from streamlit_cookies_controller import CookieController
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# --- КОНФІГУРАЦІЯ ТА КУКІ ---
st.set_page_config(page_title="Autonomous Class Monitor’s Logbook", layout="centered")
controller = CookieController()

# Список групи для реєстрації/переклички
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
    # Таблиця користувачів
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, full_name TEXT)')
    # Таблиця відвідуваності
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, date TEXT, 
                  period TEXT, subject TEXT, status TEXT, moderator TEXT)''')
    conn.commit()

# --- ЛОГІКА АВТОРИЗАЦІЇ ---
def perform_login(user_data):
    st.session_state['authenticated'] = True
    st.session_state['username'] = user_data[0]
    st.session_state['full_name'] = user_data[2]
    # Зберігаємо логін у кукі надовго
    controller.set('remember_user', user_data[0])
    st.rerun()

def login_register_page():
    st.title("🔐 Access Control")
    tab1, tab2 = st.tabs(["Увійти", "Реєстрація"])
    
    conn = create_connection()
    c = conn.cursor()

    with tab1:
        saved_user = controller.get('remember_user')
        user = st.text_input("Username", value=saved_user if saved_user else "", key="l_user")
        pwd = st.text_input("Password", type='password', key="l_pwd")
        
        # Проста капча
        captcha_code = "7741"
        st.caption(f"Код підтвердження: **{captcha_code}**")
        user_captcha = st.text_input("Введіть код", key="l_cap")

        if st.button("Login", use_container_width=True):
            if user_captcha != captcha_code:
                st.error("Невірний код капчі")
            else:
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
                    controller.set('remember_user', new_user)
                    st.success("Аккаунт створено! Тепер увійдіть.")
                except:
                    st.error("Цей логін вже зайнятий")
            else:
                st.warning("Заповніть всі поля")

# --- ГОЛОВНИЙ ДОДАТОК ---
def main():
    init_db()
    
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_register_page()
        return

    # --- ІНТЕРФЕЙС ЖУРНАЛУ ---
    conn = create_connection()
    st.sidebar.title(f"👤 {st.session_state['full_name']}")
    
    menu = st.sidebar.radio("Навігація", ["Нова перекличка", "Архів", "Статистика"])

    if menu == "Нова перекличка":
        st.subheader("📍 Attendance Check")
        with st.form("att_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            date_now = c1.date_input("Дата", datetime.now())
            subject = c1.text_input("Предмет")
            period = c2.selectbox("Пара", ["1", "2", "3", "4", "5", "6"])
            
            st.divider()
            absent_status = {}
            for student in sorted(MY_GROUP):
                absent_status[student] = st.checkbox(student)

            if st.form_submit_button("Зберегти", use_container_width=True):
                if subject:
                    c = conn.cursor()
                    d_str = date_now.strftime("%Y-%m-%d")
                    for s in MY_GROUP:
                        status = "н" if absent_status[s] else ""
                        c.execute("INSERT INTO attendance (student_name, date, period, subject, status, moderator) VALUES (?,?,?,?,?,?)",
                                  (s, d_str, period, subject, status, st.session_state['username']))
                    conn.commit()
                    st.success("Дані збережено!")
                else:
                    st.error("Вкажіть предмет")

    elif menu == "Архів":
        st.subheader("📂 Records")
        df = pd.read_sql("SELECT * FROM attendance ORDER BY id DESC", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("Download CSV", csv, "report.csv", "text/csv")
        else:
            st.info("Пусто")

    if st.sidebar.button("Вийти 🚪"):
        st.session_state["authenticated"] = False
        st.rerun()

if __name__ == '__main__':
    main()
