import sqlite3

conn = sqlite3.connect('students.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    name TEXT NOT NULL,
    program TEXT NOT NULL,
    year INTEGER NOT NULL,
    section TEXT NOT NULL
)
''')

cursor.execute("DELETE FROM students")

students = [
    ('24-00290', 'April Joy Catagena', 'BSIT', 3, 'A'),
    ('26-1524', 'Ferry Jhon Debaja', 'BSIT', 2, 'A'),
    ('24-00331', 'Jiza Mae Gubac', 'BSIT', 3, 'B'),
    ('24-00085', 'John Alfred Santos', 'BSIT', 3, 'C'),
    ('24-00115', 'Jero Paca-oncis', 'BSIT', 3, 'B')
]

cursor.executemany('''
INSERT INTO students (student_id, name, program, year, section)
VALUES (?, ?, ?, ?, ?)
''', students)

conn.commit()
conn.close()

print("Database created successfully.")