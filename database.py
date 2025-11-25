import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')

    # Enable foreign key support
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    # Drop existing tables if they exist (for development simplicity)
    c.execute('DROP TABLE IF EXISTS projects;')
    c.execute('DROP TABLE IF EXISTS expenses;')
    c.execute('DROP TABLE IF EXISTS messages;')
    c.execute('DROP TABLE IF EXISTS attendance;')
    c.execute('DROP TABLE IF EXISTS donations;')
    c.execute('DROP TABLE IF EXISTS events;')
    c.execute('DROP TABLE IF EXISTS members;')
    c.execute('DROP TABLE IF EXISTS users;')
    c.execute('DROP TABLE IF EXISTS churches;')

    # Create churches table
    c.execute('''
        CREATE TABLE churches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_id INTEGER,
            FOREIGN KEY (parent_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create users table
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL, -- e.g., 'main_church', 'branch_admin'
            associated_church_id INTEGER NOT NULL,
            FOREIGN KEY (associated_church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create members table
    c.execute('''
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            church_id INTEGER NOT NULL,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create events table
    c.execute('''
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            church_id INTEGER NOT NULL,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create donations table
    c.execute('''
        CREATE TABLE donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            donor_name TEXT,
            date TEXT NOT NULL,
            type TEXT, -- e.g., 'tithe', 'offering'
            church_id INTEGER NOT NULL,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create attendance table
    c.execute('''
        CREATE TABLE attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            member_count INTEGER NOT NULL,
            date TEXT NOT NULL,
            church_id INTEGER NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create projects table
    c.execute('''
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            church_id INTEGER NOT NULL,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create expenses table
    c.execute('''
        CREATE TABLE expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            project_id INTEGER,
            church_id INTEGER NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE SET NULL,
            FOREIGN KEY (church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    # Create messages table for instant messaging
    c.execute('''
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_church_id INTEGER NOT NULL,
            receiver_church_id INTEGER NOT NULL,
            message_content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_church_id) REFERENCES churches (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_church_id) REFERENCES churches (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
