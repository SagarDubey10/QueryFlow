import os
import re
import csv
import io
from flask import Flask, render_template, request, Response
import sqlite3
from google import genai
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()

app = Flask(__name__)

# --- Configure Google GenAI Client ---
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client() if api_key else None

# --- Database Setup (Advanced Relational Schema) ---
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 1. Departments Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY, name TEXT NOT NULL, location TEXT)''')
    
    # 2. Employees Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER, salary INTEGER, dept_id INTEGER, FOREIGN KEY (dept_id) REFERENCES departments (id))''')
    
    # 3. Projects Table (NEW)
    cursor.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, budget INTEGER)''')
    
    # 4. Employee_Projects Table (NEW - Many-to-Many Relationship)
    cursor.execute('''CREATE TABLE IF NOT EXISTS employee_projects (emp_id INTEGER, project_id INTEGER, hours_allocated INTEGER, FOREIGN KEY (emp_id) REFERENCES employees (id), FOREIGN KEY (project_id) REFERENCES projects (id), PRIMARY KEY (emp_id, project_id))''')
    
    # Insert Sample Data
    cursor.execute("SELECT count(*) FROM departments")
    if cursor.fetchone()[0] == 0:
        depts = [(1, 'Engineering', 'New York'), (2, 'Sales', 'London'), (3, 'HR', 'Chicago')]
        cursor.executemany("INSERT INTO departments VALUES (?, ?, ?)", depts)
        
        emps = [('Alice', 28, 95000, 1), ('Bob', 35, 80000, 2), ('Charlie', 32, 105000, 1), ('Diana', 40, 75000, 3), ('Evan', 25, 60000, 2), ('Fiona', 29, 110000, 1)]
        cursor.executemany("INSERT INTO employees (name, age, salary, dept_id) VALUES (?, ?, ?, ?)", emps)
        
        projs = [('AI Dashboard', 50000), ('Q3 Marketing', 20000), ('Server Migration', 80000)]
        cursor.executemany("INSERT INTO projects (title, budget) VALUES (?, ?)", projs)
        
        # Link employees to projects
        emp_projs = [(1, 1, 20), (1, 3, 10), (2, 2, 15), (3, 1, 40), (6, 3, 30)]
        cursor.executemany("INSERT INTO employee_projects (emp_id, project_id, hours_allocated) VALUES (?, ?, ?)", emp_projs)
        
        conn.commit()
    conn.close()

init_db()

# --- AI Translation Logic (Updated for Beginners) ---
def convert_nl_to_sql(nl_text):
    if not client: 
        return "ERROR: Gemini API Key is missing. Please check your .env file."
    
    # We changed the persona to an "SQL Tutor"
    prompt = f"""You are an SQL Tutor for beginners using SQLite.

Database schema:
departments(id, name, location)
employees(id, name, age, salary, dept_id)
projects(id, title, budget)
employee_projects(emp_id, project_id, hours_allocated)

Rules:
1. Return ONLY the raw SQL query. No explanations or conversational text.
2. Write the SIMPLEST possible SQL to answer the query. Prefer standard JOINs over complex nested subqueries.
3. ALWAYS format the SQL cleanly with line breaks for readability (e.g., put SELECT, FROM, JOIN, and WHERE on new lines).
4. If the user asks something unrelated to the database, return: ERROR: Unrelated query.

User query: {nl_text}"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt
        )
        sql = response.text.strip()
        match = re.search(r"```(?:sql|sqlite)?\s*(.*?)\s*```", sql, re.DOTALL | re.IGNORECASE)
        if match: sql = match.group(1).strip()
        return sql
    except Exception as e:
        print(f"\n--- API ERROR ---\n{str(e)}\n-----------------\n")
        return "ERROR: Our AI assistant is experiencing issues. Try again."

# --- Security Guardrail ---
def is_safe_query(sql_query):
    upper_sql = sql_query.upper()
    dangerous_keywords = [r'\bDROP\b', r'\bDELETE\b', r'\bUPDATE\b', r'\bINSERT\b', r'\bALTER\b', r'\bTRUNCATE\b', r'\bREPLACE\b']
    for keyword in dangerous_keywords:
        if re.search(keyword, upper_sql): return False
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
        if not is_safe_query(sql_query):
            error_msg = "🛡️ Security Alert: QueryFlow is in Read-Only mode."
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

# --- NEW: Export to CSV Route ---
@app.route('/export', methods=['POST'])
def export_csv():
    sql_query = request.form.get('sql_query')
    
    if not sql_query or not is_safe_query(sql_query):
        return "Invalid or unsafe query", 400

    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()

        # Create a string buffer to write CSV data
        si = io.StringIO()
        writer = csv.writer(si)
        
        if rows:
            # Write headers (column names)
            writer.writerow(rows[0].keys())
            # Write data rows
            for row in rows:
                writer.writerow(row)

        # Return the CSV file as a downloadable response
        output = si.getvalue()
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=queryflow_export.csv"}
        )
    except Exception as e:
        return f"Error generating CSV: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)