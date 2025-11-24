from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# User registration
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    church_name = data['church_name']
    email = data['email']
    password = data['password']

    hashed_password = generate_password_hash(password)

    conn = sqlite3.connect('database.db')
    # Enable foreign key support
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        # First, create the church entry
        c.execute("INSERT INTO churches (name) VALUES (?)", (church_name,))
        church_id = c.lastrowid # Get the ID of the newly created church

        # Then, create the user with role 'main_church' and link to the created church
        c.execute("INSERT INTO users (email, password, role, associated_church_id) VALUES (?, ?, ?, ?)",
                  (email, hashed_password, 'main_church', church_id))
        conn.commit()
        return jsonify({'message': 'Main Church registered successfully!'})
    except sqlite3.IntegrityError as e:
        # Handle cases where email might already exist or other integrity constraints
        if "UNIQUE constraint failed: users.email" in str(e):
            return jsonify({'error': 'Email already exists!'}), 400
        else:
            return jsonify({'error': 'Database integrity error: ' + str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    finally:
        conn.close()

# Endpoint to create a new branch church (by main_church user)
@app.route('/churches', methods=['POST'])
def create_church():
    # Rudimentary Authorization: Check user_id and user_role from headers
    user_id = request.headers.get('User-Id')
    user_role = request.headers.get('User-Role')
    associated_church_id = request.headers.get('Associated-Church-Id') # This is the main church's ID

    if not user_id or not user_role or not associated_church_id:
        return jsonify({'error': 'Authentication headers missing!'}), 401

    if user_role != 'main_church':
        return jsonify({'error': 'Only main church users can create branches!'}), 403

    data = request.get_json()
    church_name = data.get('name')

    if not church_name:
        return jsonify({'error': 'Church name is required!'}), 400

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        # Check if the main church exists and the associated_church_id is valid
        c.execute("SELECT id FROM churches WHERE id = ?", (associated_church_id,))
        if not c.fetchone():
            return jsonify({'error': 'Main church not found!'}), 404

        c.execute("INSERT INTO churches (name, parent_id) VALUES (?, ?)", (church_name, associated_church_id))
        new_church_id = c.lastrowid
        conn.commit()
        return jsonify({'message': 'Branch church created successfully!', 'church_id': new_church_id}), 201
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    finally:
        conn.close()

# Endpoint to get all branch churches for a main church (by main_church user)
@app.route('/churches', methods=['GET'])
def get_churches():
    user_id = request.headers.get('User-Id')
    user_role = request.headers.get('User-Role')
    associated_church_id = request.headers.get('Associated-Church-Id')

    if not user_id or not user_role or not associated_church_id:
        return jsonify({'error': 'Authentication headers missing!'}), 401

    if user_role != 'main_church':
        return jsonify({'error': 'Only main church users can view branches!'}), 403

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        c.execute("SELECT id, name FROM churches WHERE parent_id = ?", (associated_church_id,))
        branches = c.fetchall()
        
        # Format results into a list of dictionaries
        branches_list = []
        for branch in branches:
            branches_list.append({"id": branch[0], "name": branch[1]})
            
        return jsonify(branches_list), 200
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    finally:
        conn.close()

# Endpoint to create a branch admin (by main_church user)
@app.route('/users', methods=['POST'])
def create_user():
    # Authorization: Check user_id and user_role from headers
    main_church_user_id = request.headers.get('User-Id')
    main_church_user_role = request.headers.get('User-Role')
    main_church_id = request.headers.get('Associated-Church-Id')

    if not main_church_user_id or not main_church_user_role or not main_church_id:
        return jsonify({'error': 'Authentication headers missing!'}), 401

    if main_church_user_role != 'main_church':
        return jsonify({'error': 'Only main church users can create branch admins!'}), 403
    
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    branch_church_id = data.get('branch_church_id')

    if not email or not password or not branch_church_id:
        return jsonify({'error': 'Email, password, and branch_church_id are required!'}), 400

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        # Security check: Verify the branch church belongs to the main church
        c.execute("SELECT id FROM churches WHERE id = ? AND parent_id = ?", (branch_church_id, main_church_id))
        if not c.fetchone():
            return jsonify({'error': 'Branch church not found or does not belong to your main church!'}), 404

        hashed_password = generate_password_hash(password)

        # Create the user with role 'branch_admin'
        c.execute("INSERT INTO users (email, password, role, associated_church_id) VALUES (?, ?, ?, ?)",
                  (email, hashed_password, 'branch_admin', branch_church_id))
        conn.commit()
        return jsonify({'message': 'Branch admin registered successfully!'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email already exists!'}), 400
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred: ' + str(e)}), 500
    finally:
        conn.close()

# User login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required!'}), 400

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;') # Enable foreign key support
    c = conn.cursor()

    # Select id, email, password, role, associated_church_id
    c.execute("SELECT id, email, password, role, associated_church_id FROM users WHERE email = ?", (email,))
    user = c.fetchone() # user is now (id, email, password, role, associated_church_id)

    conn.close()

    if user and check_password_hash(user[2], password): # user[2] is the hashed password
        return jsonify({
            'message': 'Login successful!',
            'user_id': user[0],
            'email': user[1],
            'role': user[3],
            'associated_church_id': user[4]
        })
    else:
        return jsonify({'error': 'Invalid credentials!'}), 401

# --- Helper for Authorization ---
def check_auth(request):
    user_id = request.headers.get('User-Id')
    user_role = request.headers.get('User-Role')
    associated_church_id = request.headers.get('Associated-Church-Id')
    if not user_id or not user_role or not associated_church_id:
        return None, None, None, jsonify({'error': 'Authentication headers missing!'}), 401
    return user_id, user_role, associated_church_id, None, None

# --- Members Endpoints ---
@app.route('/members', methods=['GET', 'POST'])
def manage_members():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            if user_role == 'main_church':
                # Main church sees all members from its branches (recursive query or simple check if we assume 1 level)
                # For simplicity V1: Main church sees members of the church linked to the request (which might be a branch if they are viewing a branch details)
                # But the requirement says "Main church has access to all data".
                # Let's allow filtering by church_id query param.
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    # Verify this church belongs to main church hierarchy
                    c.execute("SELECT id FROM churches WHERE id = ? AND (parent_id = ? OR id = ?)", (target_church_id, associated_church_id, associated_church_id))
                    if not c.fetchone():
                        return jsonify({'error': 'Unauthorized access to this church data'}), 403
                    c.execute("SELECT * FROM members WHERE church_id = ?", (target_church_id,))
                else:
                    # Get all members of main church AND its branches
                    c.execute("SELECT * FROM members WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
            else:
                # Branch admin sees only their members
                c.execute("SELECT * FROM members WHERE church_id = ?", (associated_church_id,))
            
            rows = c.fetchall()
            members = [{"id": r[0], "name": r[1], "phone": r[2], "address": r[3], "church_id": r[4]} for r in rows]
            return jsonify(members), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        address = data.get('address')
        # If main church is creating, they might specify which church it is for
        target_church_id = data.get('church_id', associated_church_id)

        if user_role == 'main_church' and str(target_church_id) != str(associated_church_id):
             # Verify target church
             c.execute("SELECT id FROM churches WHERE id = ? AND parent_id = ?", (target_church_id, associated_church_id))
             if not c.fetchone():
                 conn.close()
                 return jsonify({'error': 'Invalid target church'}), 403
        elif user_role != 'main_church':
            target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO members (name, phone, address, church_id) VALUES (?, ?, ?, ?)", (name, phone, address, target_church_id))
            conn.commit()
            return jsonify({'message': 'Member added', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

# --- Events Endpoints ---
@app.route('/events', methods=['GET', 'POST'])
def manage_events():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            if user_role == 'main_church':
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    c.execute("SELECT * FROM events WHERE church_id = ?", (target_church_id,))
                else:
                    c.execute("SELECT * FROM events WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
            else:
                c.execute("SELECT * FROM events WHERE church_id = ?", (associated_church_id,))
            
            rows = c.fetchall()
            events = [{"id": r[0], "title": r[1], "date": r[2], "description": r[3], "church_id": r[4]} for r in rows]
            return jsonify(events), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        target_church_id = data.get('church_id', associated_church_id)
        if user_role != 'main_church': target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO events (title, date, description, church_id) VALUES (?, ?, ?, ?)", 
                      (data['title'], data['date'], data.get('description'), target_church_id))
            conn.commit()
            return jsonify({'message': 'Event created', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

# --- Donations Endpoints ---
@app.route('/donations', methods=['GET', 'POST', 'DELETE'])
def manage_donations():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            if user_role == 'main_church':
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    c.execute("SELECT * FROM donations WHERE church_id = ?", (target_church_id,))
                else:
                    c.execute("SELECT * FROM donations WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
            else:
                c.execute("SELECT * FROM donations WHERE church_id = ?", (associated_church_id,))
            
            rows = c.fetchall()
            donations = [{"id": r[0], "amount": r[1], "donor_name": r[2], "date": r[3], "type": r[4], "church_id": r[5]} for r in rows]
            return jsonify(donations), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        target_church_id = data.get('church_id', associated_church_id)
        if user_role != 'main_church': target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO donations (amount, donor_name, date, type, church_id) VALUES (?, ?, ?, ?, ?)", 
                      (data['amount'], data.get('donor_name'), data['date'], data.get('type'), target_church_id))
            conn.commit()
            return jsonify({'message': 'Donation recorded', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
            
    elif request.method == 'DELETE':
        if user_role != 'main_church':
            conn.close()
            return jsonify({'error': 'Branch admins cannot delete donations!'}), 403
        
        donation_id = request.args.get('id')
        if not donation_id:
            conn.close()
            return jsonify({'error': 'Donation ID required'}), 400
            
        try:
            c.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
            conn.commit()
            return jsonify({'message': 'Donation deleted'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

# --- Attendance Endpoints ---
@app.route('/attendance', methods=['GET', 'POST'])
def manage_attendance():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            if user_role == 'main_church':
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    c.execute("SELECT * FROM attendance WHERE church_id = ?", (target_church_id,))
                else:
                    c.execute("SELECT * FROM attendance WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
            else:
                c.execute("SELECT * FROM attendance WHERE church_id = ?", (associated_church_id,))
            
            rows = c.fetchall()
            attendance = [{"id": r[0], "event_id": r[1], "member_count": r[2], "date": r[3], "church_id": r[4]} for r in rows]
            return jsonify(attendance), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        target_church_id = data.get('church_id', associated_church_id)
        if user_role != 'main_church': target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO attendance (event_id, member_count, date, church_id) VALUES (?, ?, ?, ?)", 
                      (data['event_id'], data['member_count'], data['date'], target_church_id))
            conn.commit()
            return jsonify({'message': 'Attendance recorded', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

# --- Stats Endpoint ---
@app.route('/stats', methods=['GET'])
def get_stats():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    if user_role != 'main_church':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    try:
        # Count total branches
        c.execute("SELECT COUNT(id) FROM churches WHERE parent_id = ?", (associated_church_id,))
        total_branches = c.fetchone()[0]

        # Count total members (main church + all branches)
        c.execute("SELECT COUNT(id) FROM members WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
        total_members = c.fetchone()[0]
        
        conn.close()

        return jsonify({
            'total_branches': total_branches,
            'total_members': total_members
        })
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# --- Finances Endpoints (Main Church) ---
@app.route('/finances/total', methods=['GET'])
def get_total_finances():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    if user_role != 'main_church':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    try:
        search_term = request.args.get('search_term')
        
        # Get all churches belonging to the main church's hierarchy
        # Include main church itself and its branches
        query = "SELECT id, name FROM churches WHERE id = ? OR parent_id = ?"
        params = (associated_church_id, associated_church_id)

        if search_term:
            query += " AND name LIKE ?"
            params += ('%' + search_term + '%',)

        c.execute(query, params)
        churches = c.fetchall()

        results = []
        for church_id, church_name in churches:
            # Calculate total donations for this church
            c.execute("SELECT SUM(amount) FROM donations WHERE church_id = ?", (church_id,))
            total_donations = c.fetchone()[0] or 0.0

            # Calculate total expenses for this church
            c.execute("SELECT SUM(amount) FROM expenses WHERE church_id = ?", (church_id,))
            total_expenses = c.fetchone()[0] or 0.0

            total_balance = total_donations - total_expenses
            results.append({
                'church_id': church_id,
                'church_name': church_name,
                'total_balance': total_balance
            })
        
        conn.close()
        return jsonify(results), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

# --- Projects Endpoints ---
@app.route('/projects', methods=['GET', 'POST'])
def manage_projects():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            if user_role == 'main_church':
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    c.execute("SELECT * FROM projects WHERE church_id = ?", (target_church_id,))
                else:
                    c.execute("SELECT * FROM projects WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)", (associated_church_id, associated_church_id))
            else:
                c.execute("SELECT * FROM projects WHERE church_id = ?", (associated_church_id,))
            
            rows = c.fetchall()
            projects = [{"id": r[0], "name": r[1], "budget": r[2], "church_id": r[3]} for r in rows]
            return jsonify(projects), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        budget = data.get('budget')
        target_church_id = data.get('church_id', associated_church_id)

        if not name or not budget:
            return jsonify({'error': 'Project name and budget are required!'}), 400

        if user_role == 'main_church' and str(target_church_id) != str(associated_church_id):
             c.execute("SELECT id FROM churches WHERE id = ? AND parent_id = ?", (target_church_id, associated_church_id))
             if not c.fetchone():
                 conn.close()
                 return jsonify({'error': 'Invalid target church'}), 403
        elif user_role != 'main_church':
            target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO projects (name, budget, church_id) VALUES (?, ?, ?)", (name, budget, target_church_id))
            conn.commit()
            return jsonify({'message': 'Project added', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/projects/<int:project_id>', methods=['PUT', 'DELETE'])
def manage_single_project(project_id):
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        c.execute("SELECT church_id FROM projects WHERE id = ?", (project_id,))
        project_church_id = c.fetchone()
        if not project_church_id:
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
        project_church_id = project_church_id[0]

        is_authorized = False
        if user_role == 'main_church':
            # Main church can manage projects of its own and its branches
            c.execute("SELECT id FROM churches WHERE id = ? AND (parent_id = ? OR id = ?)", (project_church_id, associated_church_id, associated_church_id))
            if c.fetchone():
                is_authorized = True
        elif user_role == 'branch_admin' and str(project_church_id) == str(associated_church_id):
            is_authorized = True

        if not is_authorized:
            conn.close()
            return jsonify({'error': 'Unauthorized to manage this project!'}), 403

        if request.method == 'PUT':
            data = request.get_json()
            name = data.get('name')
            budget = data.get('budget')

            if not name or not budget:
                return jsonify({'error': 'Project name and budget are required!'}), 400

            c.execute("UPDATE projects SET name = ?, budget = ? WHERE id = ?", (name, budget, project_id))
            conn.commit()
            return jsonify({'message': 'Project updated'}), 200
        
        elif request.method == 'DELETE':
            c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return jsonify({'message': 'Project deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Expenses Endpoints ---
@app.route('/expenses', methods=['GET', 'POST'])
def manage_expenses():
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    if request.method == 'GET':
        try:
            query = "SELECT * FROM expenses WHERE church_id = ?"
            params = [associated_church_id]
            
            project_id = request.args.get('project_id')
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)

            if user_role == 'main_church':
                target_church_id = request.args.get('church_id')
                if target_church_id:
                    # Verify this church belongs to main church hierarchy
                    c.execute("SELECT id FROM churches WHERE id = ? AND (parent_id = ? OR id = ?)", (target_church_id, associated_church_id, associated_church_id))
                    if not c.fetchone():
                        return jsonify({'error': 'Unauthorized access to this church data'}), 403
                    query = query.replace("WHERE church_id = ?", "WHERE church_id = ?") # Replace to use target_church_id
                    params[0] = target_church_id # Update the church_id in params
                else:
                    # Get all expenses of main church AND its branches
                    query = "SELECT * FROM expenses WHERE church_id = ? OR church_id IN (SELECT id FROM churches WHERE parent_id = ?)"
                    params = (associated_church_id, associated_church_id)
                    if project_id:
                        query += " AND project_id = ?"
                        params += (project_id,)
            
            c.execute(query, params)
            rows = c.fetchall()
            expenses = [{"id": r[0], "description": r[1], "amount": r[2], "date": r[3], "project_id": r[4], "church_id": r[5]} for r in rows]
            return jsonify(expenses), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

    elif request.method == 'POST':
        data = request.get_json()
        description = data.get('description')
        amount = data.get('amount')
        date = data.get('date')
        project_id = data.get('project_id')
        target_church_id = data.get('church_id', associated_church_id)

        if not description or not amount or not date:
            return jsonify({'error': 'Description, amount, and date are required!'}), 400

        if user_role == 'main_church' and str(target_church_id) != str(associated_church_id):
             c.execute("SELECT id FROM churches WHERE id = ? AND parent_id = ?", (target_church_id, associated_church_id))
             if not c.fetchone():
                 conn.close()
                 return jsonify({'error': 'Invalid target church'}), 403
        elif user_role != 'main_church':
            target_church_id = associated_church_id

        try:
            c.execute("INSERT INTO expenses (description, amount, date, project_id, church_id) VALUES (?, ?, ?, ?, ?)", (description, amount, date, project_id, target_church_id))
            conn.commit()
            return jsonify({'message': 'Expense added', 'id': c.lastrowid}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/expenses/<int:expense_id>', methods=['PUT', 'DELETE'])
def manage_single_expense(expense_id):
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    conn.execute('PRAGMA foreign_keys = ON;')
    c = conn.cursor()

    try:
        c.execute("SELECT church_id FROM expenses WHERE id = ?", (expense_id,))
        expense_church_id = c.fetchone()
        if not expense_church_id:
            conn.close()
            return jsonify({'error': 'Expense not found'}), 404
        expense_church_id = expense_church_id[0]

        is_authorized = False
        if user_role == 'main_church':
            c.execute("SELECT id FROM churches WHERE id = ? AND (parent_id = ? OR id = ?)", (expense_church_id, associated_church_id, associated_church_id))
            if c.fetchone():
                is_authorized = True
        elif user_role == 'branch_admin' and str(expense_church_id) == str(associated_church_id):
            is_authorized = True

        if not is_authorized:
            conn.close()
            return jsonify({'error': 'Unauthorized to manage this expense!'}), 403

        if request.method == 'PUT':
            data = request.get_json()
            description = data.get('description')
            amount = data.get('amount')
            date = data.get('date')
            project_id = data.get('project_id')

            if not description or not amount or not date:
                return jsonify({'error': 'Description, amount, and date are required!'}), 400

            c.execute("UPDATE expenses SET description = ?, amount = ?, date = ?, project_id = ? WHERE id = ?", (description, amount, date, project_id, expense_id))
            conn.commit()
            return jsonify({'message': 'Expense updated'}), 200
        
        elif request.method == 'DELETE':
            c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            return jsonify({'message': 'Expense deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Finances Balance Endpoint ---
@app.route('/finances/balance/<int:church_id>', methods=['GET'])
def get_church_balance(church_id):
    user_id, user_role, associated_church_id, error_response, status_code = check_auth(request)
    if error_response: return error_response, status_code

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    try:
        # Verify authorization
        is_authorized = False
        if user_role == 'main_church':
            # Main church can view balance of its own church or any of its branches
            c.execute("SELECT id FROM churches WHERE id = ? AND (parent_id = ? OR id = ?)", (church_id, associated_church_id, associated_church_id))
            if c.fetchone():
                is_authorized = True
        elif user_role == 'branch_admin' and church_id == associated_church_id:
            # Branch admin can only view balance of their associated church
            is_authorized = True

        if not is_authorized:
            conn.close()
            return jsonify({'error': 'Unauthorized to view this church balance!'}), 403

        c.execute("SELECT name FROM churches WHERE id = ?", (church_id,))
        church_name_row = c.fetchone()
        if not church_name_row:
            conn.close()
            return jsonify({'error': 'Church not found'}), 404
        church_name = church_name_row[0]

        # Calculate total donations for this church
        c.execute("SELECT SUM(amount) FROM donations WHERE church_id = ?", (church_id,))
        total_donations = c.fetchone()[0] or 0.0

        # Calculate total expenses for this church
        c.execute("SELECT SUM(amount) FROM expenses WHERE church_id = ?", (church_id,))
        total_expenses = c.fetchone()[0] or 0.0

        total_balance = total_donations - total_expenses
        
        conn.close()
        return jsonify({
            'church_id': church_id,
            'church_name': church_name,
            'total_balance': total_balance
        }), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='10.130.236.214', port=8888)
