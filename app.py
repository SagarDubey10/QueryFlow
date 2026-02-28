import os
import re
from flask import Flask, render_template, request
import sqlite3
from google import genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

app = Flask(__name__)

# --- Configure Google GenAI Client ---
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client() if api_key else None

# --- Database Setup (Relational Schema) ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create Departments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT
        )
    ''')
    
    # Create Employees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            salary INTEGER,
            dept_id INTEGER,
            FOREIGN KEY (dept_id) REFERENCES departments (id)
        )
    ''')
    
    # Insert Sample Data
    cursor.execute("SELECT count(*) FROM departments")
    if cursor.fetchone()[0] == 0:
        depts = [(1, 'Engineering', 'New York'), (2, 'Sales', 'London'), (3, 'HR', 'Chicago')]
        cursor.executemany("INSERT INTO departments VALUES (?, ?, ?)", depts)
        
        emps = [
            ('Alice', 28, 95000, 1), ('Bob', 35, 80000, 2),
            ('Charlie', 32, 105000, 1), ('Diana', 40, 75000, 3),
            ('Evan', 25, 60000, 2), ('Fiona', 29, 110000, 1),
            ('George', 45, 90000, 2), ('Hannah', 31, 72000, 3)
        ]
        cursor.executemany("INSERT INTO employees (name, age, salary, dept_id) VALUES (?, ?, ?, ?)", emps)
        conn.commit()
        
    conn.close()

init_db()

# --- AI Translation Logic ---
def convert_nl_to_sql(nl_text):
    if not client: 
        return "ERROR: Gemini API Key is missing. Please check your .env file."
    
    prompt = f"""You are a strict SQL generator for SQLite.

Database schema:
departments(id, name, location)
employees(id, name, age, salary, dept_id) -- links to departments.id

Rules:
1. Return ONLY the raw SQL query.
2. NEVER include explanations, greetings, or conversational text.
3. ALWAYS use table aliases when doing JOINs (e.g., SELECT e.name, d.name FROM employees e JOIN departments d ON e.dept_id = d.id).
4. If the user asks something unrelated to the database (like weather, history, etc.), return exactly this text: ERROR: Unrelated query.

User query: {nl_text}"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        sql = response.text.strip()
        
        # Cleanup: Remove markdown (```sql ... ```) if the AI includes it
        match = re.search(r"```(?:sql|sqlite)?\s*(.*?)\s*```", sql, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            
        return sql
        
    except Exception as e:
        # 1. Print the ugly technical error to the terminal for YOU (the developer)
        print(f"\n--- BACKEND ERROR LOG ---")
        print(f"AI Generation Failed: {str(e)}")
        print(f"-------------------------\n")
        
        # 2. Return a clean, professional error to the USER (the frontend)
        return "ERROR: Our AI assistant is currently experiencing connection issues. Please try again in a moment."

# --- Security Guardrail: Read-Only Mode ---
def is_safe_query(sql_query):
    """
    Checks the SQL string for dangerous modification commands.
    Returns True if safe (SELECT only), False if dangerous.
    """
    upper_sql = sql_query.upper()
    
    # List of SQL commands that modify or destroy data
    dangerous_keywords = [
        r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', 
        r'\bINSERT\b', r'\bALTER\b', r'\bTRUNCATE\b', r'\bREPLACE\b'
    ]
    
    for keyword in dangerous_keywords:
        if re.search(keyword, upper_sql):
            return False
            
    return True

# --- Flask Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    nl_input = request.form.get('nl_input')
    sql_query = convert_nl_to_sql(nl_input)
    
    results = []
    error_msg = None
    
    if not sql_query.startswith("ERROR"):
        # --- NEW SECURITY CHECK ---
        if not is_safe_query(sql_query):
            error_msg = "🛡️ Security Alert: QueryFlow is currently in Read-Only mode. Commands that modify or delete data are blocked."
        else:
            try:
                conn = sqlite3.connect('database.db')
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(sql_query)
                results = [dict(row) for row in cursor.fetchall()]
                
                conn.close()
            except Exception as e:
                error_msg = f"SQL Execution Error: {str(e)}"
    else:
        error_msg = sql_query
        
    return render_template('index.html', nl_input=nl_input, sql_query=sql_query, results=results, error=error_msg)

if __name__ == '__main__':
    app.run(debug=True)