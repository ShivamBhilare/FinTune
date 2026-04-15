# FinTune - Automated Personal Finance Optimizer

**Take control of your financial destiny with AI-driven insights, gamified goals, and smart budgeting.**

FinTune is a next-generation personal finance application that blends advanced AI analytics with gamification to verify, track, and optimize your financial health.

---

## 🚀 Key Features

*   **🎙️ Multi-Modal Transaction Input**
    *   Add transactions effortlessly via **Voice** (speech-to-text), **Image** (receipt scanning), or **Manual** entry.
    *   Powered by Google Gemini AI for accurate categorization and extraction.

*   **🎮 Financial Gamification**
    *   Turn saving into a game with **Daily Quests**, **XP**, and **Streaks**.
    *   Complete personalize challenges like "No Outside Food" to level up your financial profile.

*   **🎯 Goal Path Simulator**
    *   Visualize your future with Monte Carlo simulations.
    *   Predict the success probability of your financial goals (e.g., "Buy a Car") based on your risk profile and saving habits.

*   **🔍 AI Pattern Detection**
    *   Uncover hidden spending habits and recurring subscriptions.
    *   Get a personalized "Financial Persona" and actionable insights to curb unnecessary expenses.

*   **🧠 Smart Budget Generator**
    *   Auto-generate budget plans (e.g., 50/30/20 Rule, 70/20/10 Rule and many more) tailored to your income and spending history.

---

## 📸 Visuals

### Dashboard Overview
<img src="static/dashboard.png" width="800" alt="Dashboard Overview">

### Budget Generator
<img src="static/budget.png" width="800" alt="Budget Generator">

### Pattern Detection
<img src="static/pattern.png" width="800" alt="Pattern Detection">

### Goal Simulator
<img src="static/goalpath.png" width="800" alt="Goal Simulator">

### Gamification & Quests
<img src="static/gamification.png" width="800" alt="Gamification & Quests">

---

## 🛠️ Installation

Follow these steps to set up the project locally:

**1. Clone the Repository**
```bash
git clone https://github.com/ShivamBhilare/Nexus_FintTune.git
cd Nexus
```

**2. Create Virtual Environment**
```bash
# Windows
python -m venv env
env\Scripts\activate

# Mac/Linux
python3 -m venv env
source env/bin/activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Run Migrations**
```bash
python manage.py migrate
```

**5. Start the Server**
```bash
python manage.py runserver
```

---

## ⚙️ Configuration

Create a `.env` file in the root directory to store your secrets.

**Example `.env`:**
```ini
# Core Django Security
SECRET_KEY=your_django_secret_key
DEBUG=True

# Database (Optional, uses SQLite by default if empty)
DATABASE_URL=postgres://user:password@localhost:5432/fintune_db

# Google Gemini AI (Required for Voice/Image/Chatbot features)
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## ⚖️ Finance & AI Context

### ⚠️ Disclaimer
**This application is for educational and tracking purposes only.** It does NOT provide professional financial advice. Always consult a certified financial planner for significant investment decisions.

### 🔒 Data Privacy
*   **Your Data, Your Control:** Transaction data is stored securely in your database.
*   **AI Processing:** Voice snippets and receipt images are processed via Google Gemini API solely for extraction purposes and are not used to train public models (subject to Google's API data policy).
*   **No Third-Party Sharing:** We do not sell or share your personal financial data with advertisers.

---

## 💻 Tech Stack

*   **Backend:** Python, Django 5.2.8
*   **Database:** PostgreSQL
*   **AI/ML:** Scikit-Learn, ARIMA Modeling, Google Gemini API (Generative AI)
*   **Frontend:** HTML5, TailwindCSS, Alpine.js, Chart.js
*   **Authentication:** Django Allauth
*   **Icons:** Lucide Icons
