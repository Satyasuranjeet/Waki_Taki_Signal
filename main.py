from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app, resources={r"/*": {"origins": "*"}})

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store room information and user sessions
rooms = {}
user_sessions = {}

@app.route('/')
@app.route('/home')
def home():
    return '''
    <h1>WebRTC Signaling Server</h1>
    <p>Server is running successfully!</p>
    <p>Current rooms: {}</p>
    <p>Active users: {}</p>
    '''.format(len(rooms), len(user_sessions))

@socketio.on('connect')
def handle_connect():
    print(f'User connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    # Get user info from session if available
    user_id = request.sid
    user_info = user_sessions.get(user_id)
    
    if user_info:
        username = user_info['username']
        room_id = user_info['room_id']
        
        # Remove user from room
        if room_id in rooms:
            rooms[room_id] = [user for user in rooms[room_id] 
                            if user['id'] != user_id]
            
            # Remove room if empty
            if len(rooms[room_id]) == 0:
                del rooms[room_id]
        
        # Remove user from sessions
        del user_sessions[user_id]
        
        # Notify others in the room
        emit('user-left', {'username': username}, room=room_id)
        print(f'{username} left room {room_id}')
    
    print(f'User disconnected: {user_id}')

@socketio.on('join-room')
def handle_join_room(data):
    room_id = data['roomId']
    username = data['username']
    user_id = request.sid
    
    # Store user info in session
    user_sessions[user_id] = {
        'username': username,
        'room_id': room_id
    }
    
    # Join the room
    join_room(room_id)
    
    # Add user to room tracking
    if room_id not in rooms:
        rooms[room_id] = []
    
    rooms[room_id].append({'id': user_id, 'username': username})
    
    # Notify others in the room
    emit('user-joined', {'username': username}, room=room_id, include_self=False)
    
    print(f'{username} joined room {room_id}')

@socketio.on('offer')
def handle_offer(data):
    user_info = user_sessions.get(request.sid)
    if user_info:
        room_id = user_info['room_id']
        emit('offer', {
            'offer': data['offer'],
            'fromUser': data['fromUser']
        }, room=room_id, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    user_info = user_sessions.get(request.sid)
    if user_info:
        room_id = user_info['room_id']
        emit('answer', {
            'answer': data['answer'],
            'fromUser': data['fromUser']
        }, room=room_id, include_self=False)

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    user_info = user_sessions.get(request.sid)
    if user_info:
        room_id = user_info['room_id']
        emit('ice-candidate', {
            'candidate': data['candidate'],
            'fromUser': data['fromUser']
        }, room=room_id, include_self=False)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f'Signaling server running on port {port}')
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
