# 🌊 QueryFlow

> **An intelligent, AI-powered database dashboard that safely translates natural language into complex, executable SQL queries in real-time.**

QueryFlow bridges the gap between non-technical users and complex data structures. By integrating Google's Gemini AI with a custom Flask backend, this platform allows users to ask questions in plain English and instantly receive accurate data tables, syntax-highlighted SQL code, and downloadable reports.

## ✨ Key Features

* **Natural Language Processing:** Translates plain English into accurate SQLite queries using the Gemini 2.5 Flash API.
* **Robust Security Guardrails:** Implements a custom Regex-based SQL Interceptor that parses and actively blocks destructive DDL/DML commands (`DROP`, `DELETE`, `UPDATE`), ensuring a strict, secure **Read-Only** environment.
* **Complex Database Architecture:** Designed around a fully normalized **3NF relational schema** handling Many-to-Many relationships via junction tables.
* **Premium UX/UI:** Built with a custom "Soft UI" aesthetic, featuring state-managed Dark/Light mode (via `localStorage`), CSS hardware-accelerated animations, and instant IDE-style syntax highlighting.
* **Business-Ready Exports:** Includes a backend data-stream generator allowing users to instantly download their query results as clean CSV files.

## 🛠️ Technology Stack

* **Backend:** Python 3, Flask
* **Database:** SQLite3
* **AI Engine:** Google GenAI SDK (Gemini API)
* **Frontend:** HTML5, CSS3 (Variables, Animations), Vanilla JavaScript

## 📊 Database Schema (3NF)

The application queries a highly structured relational database designed to simulate a real-world company environment, utilizing a junction table to handle many-to-many relationships:

1. `departments` (id, name, location)
2. `employees` (id, name, age, salary, dept_id) *— One-to-Many with departments*
3. `projects` (id, title, budget)
4. `employee_projects` (emp_id, project_id, hours_allocated) *— Junction table linking employees and projects*



## 🚀 Local Installation & Setup

To run QueryFlow locally on your machine, follow these steps:

**1. Clone the repository**
`bash
git clone https://github.com/SagarDubey10/QueryFlow.git
cd QueryFlow
`

**2. Create a virtual environment (Recommended)**
`bash
python -m venv venv
# On Windows use: venv\Scripts\activate
# On macOS/Linux use: source venv/bin/activate
`

**3. Install dependencies**
`bash
pip install flask google-genai python-dotenv
`

**4. Set up your Environment Variables**
Create a `.env` file in the root directory and add your Google Gemini API key:
`text
GEMINI_API_KEY=your_actual_api_key_here
`
*(Note: Ensure your `.env` file is added to your `.gitignore` to prevent leaking your API key!)*

**5. Run the Application**
`bash
python app.py
`
The application will automatically generate the `database.db` file and populate it with sample data on its first run. Open your browser and navigate to `http://127.0.0.1:5000`.

## 🛡️ Security Note
This project features an application-layer security interceptor. If a user attempts a SQL Injection or asks the AI to delete data (e.g., *"Fire all employees"*), the AI may generate a `DELETE` command, but the backend Python validator will intercept the query and return a Security Alert without executing it, protecting the database integrity.