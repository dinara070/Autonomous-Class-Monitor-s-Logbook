import streamlit as st
from streamlit_cookies_controller import CookieController
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime
import io

# --- КОНФІГУРАЦІЯ ТА КУКІ ---
st.set_page_config(page_title="Autonomous Class Monitor’s Logbook", layout="wide")

# Ініціалізація контролера кукі
if 'controller' not in st.session_state:
    st.session_state.controller = CookieController()
controller = st.session_state.controller

# Список вашої групи
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
    # Користувачі
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT, full_name TEXT)')
    # Відвідуваність
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT, date TEXT, 
                  period TEXT, subject TEXT, status TEXT, moderator TEXT)''')
    
    # ПЕРЕВІРКА ТА ОНОВЛЕННЯ СТРУКТУРИ (Migration)
    # Перевіряємо, чи є колонка semester. Якщо немає - додаємо.
    try:
        c.execute("SELECT semester FROM attendance LIMIT 1")
    except sqlite3.OperationalError:
        st.warning("Оновлення бази даних... Додавання підтримки семестрів.")
        c.execute("ALTER TABLE attendance ADD COLUMN semester TEXT DEFAULT '2025-2'")
    
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
        st.title("🎓 Logbook Access")
        tab1, tab2 = st.tabs(["🔑 Увійти", "📝 Реєстрація"])
        conn = create_connection()
        c = conn.cursor()

        with tab1:
            saved_user = controller.get('remember_user')
            user = st.text_input("Логін", value=saved_user if saved_user else "", key="l_user")
            pwd = st.text_input("Пароль", type='password', key="l_pwd")
            if st.button("Увійти", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=?', (user,))
                data = c.fetchone()
                if data and check_hashes(pwd, data[1]):
                    perform_login(data)
                else:
                    st.error("Невірний логін або пароль")

        with tab2:
            new_user = st.text_input("Придумайте логін", key="r_user")
            new_full_name = st.text_input("Ваше ПІБ", key="r_name")
            new_pwd = st.text_input("Придумайте пароль", type='password', key="r_pwd")
            if st.button("Зареєструватися", use_container_width=True):
                if new_user and new_pwd and new_full_name:
                    try:
                        c.execute('INSERT INTO users VALUES (?,?,?)', (new_user, make_hashes(new_pwd), new_full_name))
                        conn.commit()
                        st.success("Аккаунт створено!")
                    except:
                        st.error("Цей логін вже зайнятий")

# --- ГОЛОВНИЙ ДОДАТОК ---
def main():
    init_db()
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_register_page()
        return

    conn = create_connection()
    st.sidebar.title(f"👤 {st.session_state['full_name']}")
    
    # Вибір семестру
    current_sem = st.sidebar.selectbox("Семестр", ["2025-1", "2025-2", "2026-1", "2026-2"], index=1)
    
    menu = st.sidebar.radio("Меню", ["Нова перекличка", "Архів та Експорт", "Імпорт", "Статистика"])

    if menu == "Нова перекличка":
        st.subheader(f"📅 Перекличка ({current_sem})")
        # Використовуємо форму для уникнення помилок Node
        with st.form("att_check_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            date_now = col1.date_input("Дата", datetime.now())
            subject = col1.text_input("Назва предмета")
            period = col2.selectbox("Пара", ["1", "2", "3", "4", "5", "6"])
            
            st.divider()
            st.write("Відмітьте **ВІДСУТНІХ**:")
            
            absent_status = {}
            # Виводимо список у два стовпчики для компактності
            c_list1, c_list2 = st.columns(2)
            for i, student in enumerate(sorted(MY_GROUP)):
                target_col = c_list1 if i % 2 == 0 else c_list2
                absent_status[student] = target_col.checkbox(student, key=f"ch_{student}")

            if st.form_submit_button("💾 Зберегти дані", use_container_width=True):
                if subject:
                    c = conn.cursor()
                    d_str = date_now.strftime("%Y-%m-%d")
                    for s in MY_GROUP:
                        status = "н" if absent_status[s] else ""
                        c.execute("INSERT INTO attendance (student_name, date, period, subject, status, moderator, semester) VALUES (?,?,?,?,?,?,?)",
                                  (s, d_str, period, subject, status, st.session_state['username'], current_sem))
                    conn.commit()
                    st.success("Запис успішно додано!")
                else:
                    st.error("Введіть назву предмета!")

    elif menu == "Архів та Експорт":
        st.subheader("📂 Журнал записів")
        try:
            df = pd.read_sql(f"SELECT * FROM attendance WHERE semester='{current_sem}' ORDER BY id DESC", conn)
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Експорт у CSV", csv, f"attendance_{current_sem}.csv", use_container_width=True)
            else:
                st.info("Дані за цей семестр відсутні.")
        except Exception as e:
            st.error(f"Помилка завантаження: {e}")

    elif menu == "Імпорт":
        st.subheader("📥 Імпорт файлів")
        up_file = st.file_uploader("Завантажте CSV або Excel", type=['csv', 'xlsx'])
        if up_file:
            try:
                df_imp = pd.read_csv(up_file) if up_file.name.endswith('.csv') else pd.read_excel(up_file)
                if st.button("🚀 Почати імпорт"):
                    df_imp.to_sql('attendance', conn, if_exists='append', index=False)
                    st.success("Дані додано!")
            except Exception as e:
                st.error(f"Помилка: {e}")

    elif menu == "Статистика":
        st.subheader("📊 Аналіз прогулів")
        try:
            query = f"SELECT student_name FROM attendance WHERE status='н' AND semester='{current_sem}'"
            df_s = pd.read_sql(query, conn)
            if not df_s.empty:
                counts = df_s['student_name'].value_counts()
                st.bar_chart(counts)
                st.table(counts)
            else:
                st.success("Прогулів немає!")
        except:
            st.info("Статистика поки не доступна.")

    if st.sidebar.button("Logout 🚪"):
        st.session_state["authenticated"] = False
        st.rerun()

if __name__ == '__main__':
    main()
