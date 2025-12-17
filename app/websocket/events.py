"""
WebSocket Event Handlers for Real-time Task Management
Handles real-time updates for tasks, projects, comments, and user interactions
"""

from flask import session, request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import decode_token, JWTManager
from app import socketio, db
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.models.comment import Comment
from app.models.project_member import ProjectMember
import logging
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store connected users
connected_users = {}
user_rooms = {}


def authenticate_socket_user():
    """Authenticate user from token or session"""
    try:
        # Try JWT token first
        token = request.args.get('token')
        if token:
            try:
                decoded_token = decode_token(token)
                user_id = decoded_token['sub']
                user = User.query.get(user_id)
                if user:
                    return user
            except Exception as e:
                logger.warning(f"JWT token authentication failed: {e}")
        
        # Fallback to session-based auth
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return user
                
        return None
    except Exception as e:
        logger.error(f"Socket authentication error: {e}")
        return None


@socketio.on('connect')
def on_connect():
    """Handle client connection"""
    user = authenticate_socket_user()
    if not user:
        logger.warning("Unauthorized socket connection attempt")
        disconnect()
        return False
    
    # Store user connection
    connected_users[request.sid] = {
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'connected_at': datetime.utcnow(),
        'last_activity': datetime.utcnow()
    }
    
    # Join user to personal room
    join_room(f"user_{user.id}")
    
    # Join user to project rooms they're member of
    user_projects = db.session.query(ProjectMember).filter_by(user_id=user.id).all()
    for project_member in user_projects:
        room_name = f"project_{project_member.project_id}"
        join_room(room_name)
        
        # Track user rooms
        if user.id not in user_rooms:
            user_rooms[user.id] = set()
        user_rooms[user.id].add(room_name)
    
    logger.info(f"User {user.username} connected with session {request.sid}")
    
    # Emit user connected event to project rooms
    for project_member in user_projects:
        socketio.emit('user_connected', {
            'user_id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{project_member.project_id}")
    
    # Send initial connection success
    emit('connected', {
        'message': 'Successfully connected to real-time updates',
        'user_id': user.id,
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection"""
    if request.sid in connected_users:
        user_info = connected_users[request.sid]
        user_id = user_info['user_id']
        username = user_info['username']
        
        # Emit user disconnected event to project rooms
        if user_id in user_rooms:
            for room_name in user_rooms[user_id]:
                socketio.emit('user_disconnected', {
                    'user_id': user_id,
                    'username': username,
                    'timestamp': datetime.utcnow().isoformat()
                }, room=room_name)
            
            # Clean up user rooms
            del user_rooms[user_id]
        
        # Remove from connected users
        del connected_users[request.sid]
        
        logger.info(f"User {username} disconnected")


@socketio.on('join_project')
def on_join_project(data):
    """Join a project room for real-time updates"""
    user = authenticate_socket_user()
    if not user:
        emit('error', {'message': 'Authentication required'})
        return
    
    project_id = data.get('project_id')
    if not project_id:
        emit('error', {'message': 'Project ID required'})
        return
    
    # Verify user has access to project
    project_member = ProjectMember.query.filter_by(
        user_id=user.id, 
        project_id=project_id
    ).first()
    
    if not project_member:
        emit('error', {'message': 'Access denied to project'})
        return
    
    room_name = f"project_{project_id}"
    join_room(room_name)
    
    # Track user rooms
    if user.id not in user_rooms:
        user_rooms[user.id] = set()
    user_rooms[user.id].add(room_name)
    
    emit('joined_project', {
        'project_id': project_id,
        'room': room_name,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    logger.info(f"User {user.username} joined project {project_id}")


@socketio.on('leave_project')
def on_leave_project(data):
    """Leave a project room"""
    user = authenticate_socket_user()
    if not user:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        return
    
    room_name = f"project_{project_id}"
    leave_room(room_name)
    
    # Remove from user rooms tracking
    if user.id in user_rooms and room_name in user_rooms[user.id]:
        user_rooms[user.id].remove(room_name)
    
    emit('left_project', {
        'project_id': project_id,
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('task_created')
def on_task_created(data):
    """Handle task creation event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    task_id = data.get('task_id')
    project_id = data.get('project_id')
    
    if not task_id or not project_id:
        emit('error', {'message': 'Task ID and Project ID required'})
        return
    
    # Get task details
    task = Task.query.get(task_id)
    if not task:
        emit('error', {'message': 'Task not found'})
        return
    
    # Broadcast to project room
    socketio.emit('task_created', {
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'project_id': task.project_id,
            'created_by': task.created_by,
            'assigned_to': task.assigned_to,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat()
        },
        'created_by': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{project_id}")
    
    logger.info(f"Task {task_id} created by {user.username} in project {project_id}")


@socketio.on('task_updated')
def on_task_updated(data):
    """Handle task update event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    task_id = data.get('task_id')
    changes = data.get('changes', {})
    
    if not task_id:
        emit('error', {'message': 'Task ID required'})
        return
    
    # Get task details
    task = Task.query.get(task_id)
    if not task:
        emit('error', {'message': 'Task not found'})
        return
    
    # Broadcast to project room
    socketio.emit('task_updated', {
        'task_id': task_id,
        'changes': changes,
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'project_id': task.project_id,
            'assigned_to': task.assigned_to,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'updated_at': task.updated_at.isoformat()
        },
        'updated_by': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")
    
    logger.info(f"Task {task_id} updated by {user.username}")


@socketio.on('task_status_changed')
def on_task_status_changed(data):
    """Handle task status change event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    task_id = data.get('task_id')
    old_status = data.get('old_status')
    new_status = data.get('new_status')
    
    if not all([task_id, new_status]):
        emit('error', {'message': 'Task ID and new status required'})
        return
    
    # Get task details
    task = Task.query.get(task_id)
    if not task:
        emit('error', {'message': 'Task not found'})
        return
    
    # Broadcast to project room
    socketio.emit('task_status_changed', {
        'task_id': task_id,
        'old_status': old_status,
        'new_status': new_status,
        'task_title': task.title,
        'changed_by': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")
    
    # Send notification to assigned user if different from changer
    if task.assigned_to and task.assigned_to != user.id:
        socketio.emit('notification', {
            'type': 'task_status_changed',
            'message': f'{user.full_name} changed status of "{task.title}" to {new_status}',
            'task_id': task_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{task.assigned_to}")


@socketio.on('task_deleted')
def on_task_deleted(data):
    """Handle task deletion event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    task_id = data.get('task_id')
    project_id = data.get('project_id')
    task_title = data.get('task_title', f'Task {task_id}')
    
    if not task_id or not project_id:
        emit('error', {'message': 'Task ID and Project ID required'})
        return
    
    # Broadcast to project room
    socketio.emit('task_deleted', {
        'task_id': task_id,
        'task_title': task_title,
        'project_id': project_id,
        'deleted_by': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{project_id}")
    
    logger.info(f"Task {task_id} deleted by {user.username}")


@socketio.on('comment_added')
def on_comment_added(data):
    """Handle new comment event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    comment_id = data.get('comment_id')
    task_id = data.get('task_id')
    
    if not comment_id or not task_id:
        emit('error', {'message': 'Comment ID and Task ID required'})
        return
    
    # Get comment and task details
    comment = Comment.query.get(comment_id)
    task = Task.query.get(task_id)
    
    if not comment or not task:
        emit('error', {'message': 'Comment or task not found'})
        return
    
    # Broadcast to project room
    socketio.emit('comment_added', {
        'comment': {
            'id': comment.id,
            'comment_text': comment.comment_text,
            'task_id': comment.task_id,
            'user_id': comment.user_id,
            'author_name': user.full_name,
            'created_at': comment.created_at.isoformat()
        },
        'task': {
            'id': task.id,
            'title': task.title,
            'project_id': task.project_id
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")
    
    # Send notification to task assignee if different from commenter
    if task.assigned_to and task.assigned_to != user.id:
        socketio.emit('notification', {
            'type': 'comment_added',
            'message': f'{user.full_name} commented on "{task.title}"',
            'task_id': task_id,
            'comment_id': comment_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{task.assigned_to}")


@socketio.on('project_updated')
def on_project_updated(data):
    """Handle project update event"""
    user = authenticate_socket_user()
    if not user:
        return
    
    project_id = data.get('project_id')
    changes = data.get('changes', {})
    
    if not project_id:
        emit('error', {'message': 'Project ID required'})
        return
    
    # Get project details
    project = Project.query.get(project_id)
    if not project:
        emit('error', {'message': 'Project not found'})
        return
    
    # Broadcast to project room
    socketio.emit('project_updated', {
        'project_id': project_id,
        'changes': changes,
        'project': {
            'id': project.id,
            'name': project.name,
            'description': project.description,
            'status': getattr(project, 'status', 'active'),
            'updated_at': project.updated_at.isoformat()
        },
        'updated_by': {
            'id': user.id,
            'username': user.username,
            'full_name': user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{project_id}")


@socketio.on('user_typing')
def on_user_typing(data):
    """Handle user typing indicator"""
    user = authenticate_socket_user()
    if not user:
        return
    
    task_id = data.get('task_id')
    is_typing = data.get('is_typing', False)
    
    if not task_id:
        return
    
    # Get task to find project
    task = Task.query.get(task_id)
    if not task:
        return
    
    # Broadcast typing indicator to project room (exclude sender)
    socketio.emit('user_typing', {
        'user_id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'task_id': task_id,
        'is_typing': is_typing,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}", include_self=False)


@socketio.on('get_online_users')
def on_get_online_users(data):
    """Get list of online users in a project"""
    user = authenticate_socket_user()
    if not user:
        return
    
    project_id = data.get('project_id')
    if not project_id:
        emit('error', {'message': 'Project ID required'})
        return
    
    # Verify user has access to project
    project_member = ProjectMember.query.filter_by(
        user_id=user.id, 
        project_id=project_id
    ).first()
    
    if not project_member:
        emit('error', {'message': 'Access denied to project'})
        return
    
    # Get online users in this project
    online_users = []
    room_name = f"project_{project_id}"
    
    for sid, user_info in connected_users.items():
        user_id = user_info['user_id']
        if user_id in user_rooms and room_name in user_rooms[user_id]:
            online_users.append({
                'user_id': user_id,
                'username': user_info['username'],
                'full_name': user_info['full_name'],
                'connected_at': user_info['connected_at'].isoformat(),
                'last_activity': user_info['last_activity'].isoformat()
            })
    
    emit('online_users', {
        'project_id': project_id,
        'users': online_users,
        'count': len(online_users),
        'timestamp': datetime.utcnow().isoformat()
    })


@socketio.on('ping')
def on_ping():
    """Handle ping for keepalive"""
    user = authenticate_socket_user()
    if not user:
        return
    
    # Update last activity
    if request.sid in connected_users:
        connected_users[request.sid]['last_activity'] = datetime.utcnow()
    
    emit('pong', {'timestamp': datetime.utcnow().isoformat()})


# Utility functions for triggering events from API endpoints
def emit_task_created(task, created_by_user):
    """Emit task created event from API"""
    socketio.emit('task_created', {
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'project_id': task.project_id,
            'created_by': task.created_by,
            'assigned_to': task.assigned_to,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'created_at': task.created_at.isoformat()
        },
        'created_by': {
            'id': created_by_user.id,
            'username': created_by_user.username,
            'full_name': created_by_user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")


def emit_task_updated(task, updated_by_user, changes=None):
    """Emit task updated event from API"""
    socketio.emit('task_updated', {
        'task_id': task.id,
        'changes': changes or {},
        'task': {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'project_id': task.project_id,
            'assigned_to': task.assigned_to,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'updated_at': task.updated_at.isoformat()
        },
        'updated_by': {
            'id': updated_by_user.id,
            'username': updated_by_user.username,
            'full_name': updated_by_user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")


def emit_task_deleted(task_id, project_id, task_title, deleted_by_user):
    """Emit task deleted event from API"""
    socketio.emit('task_deleted', {
        'task_id': task_id,
        'task_title': task_title,
        'project_id': project_id,
        'deleted_by': {
            'id': deleted_by_user.id,
            'username': deleted_by_user.username,
            'full_name': deleted_by_user.full_name
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{project_id}")


def emit_comment_added(comment, task, author):
    """Emit comment added event from API"""
    socketio.emit('comment_added', {
        'comment': {
            'id': comment.id,
            'comment_text': comment.comment_text,
            'task_id': comment.task_id,
            'user_id': comment.user_id,
            'author_name': author.full_name,
            'created_at': comment.created_at.isoformat()
        },
        'task': {
            'id': task.id,
            'title': task.title,
            'project_id': task.project_id
        },
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"project_{task.project_id}")


def emit_notification(user_id, notification_type, message, **kwargs):
    """Emit notification to specific user"""
    socketio.emit('notification', {
        'type': notification_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        **kwargs
    }, room=f"user_{user_id}")