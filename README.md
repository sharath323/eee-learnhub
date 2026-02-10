# EEE LearnHub 🚀

EEE LearnHub is a **Flask-based learning platform** designed for Electrical and Electronics Engineering (EEE) students. The platform provides structured learning with subjects, topics, downloadable resources, progress tracking, notifications, and admin management — all in one place.

---

## 🌟 Features

### 👨‍💼 Admin Panel

* Admin login authentication
* Add, update, and delete:

  * Subjects
  * Topics
  * Videos and PDFs
  * Interview preparation content
* Send notifications/messages to:

  * All students
  * Individual students
* View total number of students
* View student details (name & email)

### 👨‍🎓 Student Dashboard

* Secure login
* View enrolled subjects
* Topic-wise learning structure
* Watch videos and download PDFs
* Topic-related questions
* Interview preparation cards for each subject
* Progress tracker (percentage-based)
* Notification center (messages from admin)

### 🔔 Notification System

* Admin can broadcast messages
* Users receive notifications in real time
* Read/unread tracking

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Frontend:** HTML, CSS, JavaScript
* **Database:** SQLite (development)
* **ORM:** Flask-SQLAlchemy
* **Version Control:** Git & GitHub

---

## 📂 Project Structure

```
EEE PROJECT/
│
├── app.py
├── eee_learnhub/
│   ├── static/
│   ├── templates/
│   └── __pycache__/
├── login_page/
├── .gitignore
└── README.md
```

---

## ▶️ How to Run Locally

1. **Clone the repository**

   ```bash
   git clone https://github.com/sharath323/eee-learnhub.git
   cd eee-learnhub
   ```

2. **Create a virtual environment (optional but recommended)**

   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask app**

   ```bash
   python app.py
   ```

5. Open browser and go to:

   ```
   http://127.0.0.1:5000/
   ```

---

## 🌍 Deployment

This project is deployment-ready and can be hosted on platforms like:

* Render
* Railway
* PythonAnywhere

(Deployment steps will be added soon.)

---

## 📌 Future Enhancements

* Email notifications
* Quiz & evaluation system
* Certificate generation
* Advanced analytics dashboard
* Role-based permissions

---

## 👤 Author

**Sharath**
EEE Student | Flask Developer

GitHub: [https://github.com/sharath323](https://github.com/sharath323)

---

⭐ If you like this project, don’t forget to star the repository!
Add project README
