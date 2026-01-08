import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- КОНФІГУРАЦІЯ ---
st.set_page_config(page_title="Autonomous Class Monitor’s Logbook", layout="centered")

# Пароль для доступу (тільки для тебе)
ACCESS_PASSWORD = "your_secret_password" 

# Список твоєї групи (можна додати/змінити)
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

# --- БАЗА ДАНИХ ---
def init_db():
    conn = sqlite3.connect('attendance_private.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attendance
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  student_name TEXT,
                  date TEXT,
                  period TEXT,
                  subject TEXT,
                  status TEXT)''')
    conn.commit()
    return conn

# --- ЛОГІКА ВХОДУ ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 Вхід у журнал")
    pwd = st.text_input("Введіть пароль доступу:", type="password")
    if st.button("Увійти"):
        if pwd == ACCESS_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Невірний пароль!")
    st.stop()

# --- ОСНОВНИЙ ІНТЕРФЕЙС ---
conn = init_db()
st.title("📝 Робочий журнал старости")

menu = st.sidebar.radio("Меню", ["Нова перекличка", "Архів та Експорт", "Статистика"])

if menu == "Нова перекличка":
    st.subheader("📍 Відмітка на парі")
    
    col1, col2 = st.columns(2)
    with col1:
        date_now = st.date_input("Дата", datetime.now())
        subject = st.text_input("Назва предмета", placeholder="напр. Математичний аналіз")
    with col2:
        period = st.selectbox("Номер пари", ["1 пара", "2 пара", "3 пара", "4 пара", "5 пара"])
        
    st.divider()
    st.write("### Список групи")
    st.caption("Позначте тих, хто **ВІДСУТНІЙ** (поставте галочку)")

    # Створюємо словник для зберігання стану (True = відсутній)
    absent_list = []
    
    # Відображення списку чекбоксами
    for student in sorted(MY_GROUP):
        if st.checkbox(student, key=student):
            absent_list.append(student)

    if st.button("💾 Зберегти дані в журнал", use_container_width=True, type="primary"):
        if not subject:
            st.error("Будь ласка, введіть назву предмета!")
        else:
            c = conn.cursor()
            date_str = date_now.strftime("%Y-%m-%d")
            
            # Записуємо всіх: присутніх ("") та відсутніх ("н")
            for student in MY_GROUP:
                status = "н" if student in absent_list else ""
                c.execute("INSERT INTO attendance (student_name, date, period, subject, status) VALUES (?,?,?,?,?)",
                          (student, date_str, period, subject, status))
            conn.commit()
            st.success(f"Дані за {date_str} ({subject}) успішно збережені!")
            st.balloons()

elif menu == "Архів та Експорт":
    st.subheader("📂 Перегляд записів")
    
    df = pd.read_sql("SELECT * FROM attendance ORDER BY id DESC", conn)
    
    if not df.empty:
        # Фільтр для швидкого пошуку
        search_date = st.date_input("Фільтр за датою", value=None)
        if search_date:
            df = df[df['date'] == search_date.strftime("%Y-%m-%d")]
            
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Кнопка для завантаження в Excel
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="⬇️ Завантажити звіт для деканату (CSV)",
            data=csv,
            file_name=f"attendance_report_{datetime.now().strftime('%d_%m')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Журнал поки що порожній.")

elif menu == "Статистика":
    st.subheader("📊 Аналіз пропусків")
    df = pd.read_sql("SELECT student_name, status FROM attendance WHERE status='н'", conn)
    
    if not df.empty:
        stats = df['student_name'].value_counts()
        st.bar_chart(stats)
        st.write("#### Кількість пропусків поіменно:")
        st.table(stats)
    else:
        st.info("Пропусків не зафіксовано. Всі молодці!")

# --- ВИХІД ---
if st.sidebar.button("Вийти з системи"):
    st.session_state["authenticated"] = False
    st.rerun()
