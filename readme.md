# 🌱 EcoLearn: Interactive Environmental Learning Platform

EcoLearn is a **Flask + SQLite based web app** with a modern frontend that helps users learn about **sustainability, renewable energy, and waste management** through interactive lessons and quizzes.  
Users can **register, log in, take quizzes, earn badges, and compete on a leaderboard**.

---

## ✨ Features
- 📚 **Interactive lessons** on sustainability, renewable energy, and waste management  
- 📝 **Quizzes** at the end of each lesson  
- 🏅 **Badges** awarded for scoring 80%+  
- 🏆 **Leaderboard** showcasing top learners  
- 🔐 **User authentication** (register/login/logout with secure password hashing)  
- 💾 **SQLite database** for persistence  

---

## 🛠️ Tech Stack
- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python (Flask, Flask-SQLAlchemy, Flask-Login)  
- **Database:** SQLite  
- **Other:** Flask-CORS for API communication  

---

## 🚀 Setup & Run Locally
1. Clone the repository or unzip the project:
   ```bash
   git clone https://github.com/<your-username>/ecolearn.git
   cd ecolearn


<!-- Create & activate a virtual environment (recommended): -->

python -m venv venv
venv\Scripts\activate   # On Windows
source venv/bin/activate  # On Mac/Linux


<!-- Install dependencies: -->

pip install -r requirements.txt


<!-- Run the app: -->

python app.py


<!-- Open in browser: -->
👉 http://127.0.0.1:5000