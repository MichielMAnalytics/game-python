from flask import Blueprint, request, jsonify, current_app, session
import uuid
from services.agent_service import AgentService
import subprocess
import os
import re
import time
from werkzeug.local import LocalProxy
import threading
import sys
from db.database import (
    store_token, get_token, get_user_info, update_user_info, 
    remove_token, store_api_key, get_api_key, register_user, login_user, get_db_connection, debug_users, check_user_auth_status
)
import json

# Initialize blueprint
api_bp = Blueprint('api', __name__)

# Initialize agent service
agent_service = AgentService()

# In-memory storage for auth process (replace with a proper database in production)
auth_sessions = {}
twitter_tokens = {}

# Add a lock for auth processes
auth_lock = threading.Lock()

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0'
    })

@api_bp.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint that processes messages through the agent"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = data.get('user_id', str(uuid.uuid4()))
        message = data.get('message')
        has_enhanced_data = data.get('has_enhanced_data', False)
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Log the incoming request to see what we're getting
        current_app.logger.info(f"Chat request from user {user_id}")
        current_app.logger.info(f"Has enhanced data: {has_enhanced_data}")
        
        # Only log partial messages to avoid filling logs with large texts
        log_message = message
        if len(log_message) > 100:
            log_message = log_message[:100] + "..."
        current_app.logger.info(f"Message (truncated): {log_message}")
        
        # Handle enhanced messages
        if has_enhanced_data:
            try:
                # Parse the JSON message
                message_data = json.loads(message)
                
                # Extract components
                visible_text = message_data.get('visibleText', message)
                full_text = message_data.get('fullQuotedText')
                source_url = message_data.get('sourceUrl')
                
                # Log the components for debugging
                current_app.logger.info(f"Enhanced message detected:")
                current_app.logger.info(f"  Visible text: {visible_text[:100] + '...' if len(visible_text) > 100 else visible_text}")
                if full_text:
                    current_app.logger.info(f"  Has full text: {len(full_text)} characters")
                if source_url:
                    current_app.logger.info(f"  Source URL: {source_url}")
                
                # Reconstruct a message that includes all the information for the AI
                if full_text or source_url:
                    ai_message = visible_text
                    
                    if full_text:
                        ai_message += f"\n\nFull quoted text: {full_text}"
                    
                    if source_url:
                        ai_message += f"\n\nSource: {source_url}"
                    
                    # Use this enhanced message for the AI
                    message = ai_message
            except json.JSONDecodeError:
                # If parsing fails, just use the original message
                current_app.logger.warning("Failed to parse enhanced message JSON")
                pass
        
        # Try to get API key from database
        api_key = get_api_key(user_id)
        if api_key:
            # Set it in agent service
            agent_service.api_key = api_key
            os.environ["GAME_API_KEY"] = api_key
        
        # Process the message through agent service
        response = agent_service.process_message(user_id, message)
        
        return jsonify(response)
    
    except Exception as e:
        current_app.logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/reset', methods=['POST'])
def reset_chat():
    """Reset a user's chat session"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        success = agent_service.reset_chat(user_id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Chat session reset'})
        else:
            return jsonify({'status': 'not_found', 'message': 'No active chat session found'}), 404
    
    except Exception as e:
        current_app.logger.error(f"Error in reset endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/auth/initiate', methods=['POST'])
def initiate_auth():
    """Start the OAuth process with Twitter"""
    try:
        # Use a lock to prevent concurrent auth processes
        if not auth_lock.acquire(blocking=False):
            return jsonify({'error': 'Another authentication process is already in progress'}), 429
        
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            user_id = data.get('user_id', str(uuid.uuid4()))
            use_stored_key = data.get('use_stored_key', False)
            
            # Verify that the user exists in the database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT email FROM users WHERE user_id = ?', (user_id,))
            user_result = cursor.fetchone()
            user_exists = user_result is not None
            conn.close()
            
            if not user_exists:
                auth_lock.release()
                return jsonify({'error': 'User not found. Please log in again.'}), 404
            
            # If use_stored_key is True, try to get the API key from the database
            if use_stored_key or not api_key:
                stored_api_key = get_api_key(user_id)
                if stored_api_key:
                    api_key = stored_api_key
                    current_app.logger.info(f"Using stored API key for user {user_id}")
                else:
                    auth_lock.release()
                    return jsonify({'error': 'No API key stored for this user'}), 400
            
            if not api_key:
                auth_lock.release()
                return jsonify({'error': 'API key is required'}), 400
            
            # Store API key in environment for this session
            os.environ["GAME_API_KEY"] = api_key
            
            # Also update the agent service if needed
            agent_service.api_key = api_key
            
            # Always store the API key in the database
            store_api_key(user_id, api_key)
            
            # Check if user already has a valid token
            existing_token = get_token(user_id)
            if existing_token:
                # Token exists, set it and return success
                os.environ["GAME_TWITTER_ACCESS_TOKEN"] = existing_token
                auth_lock.release()
                return jsonify({
                    'session_id': user_id,
                    'already_authenticated': True,
                    'message': 'Already authenticated'
                })
            
            # Generate a unique session ID
            session_id = user_id
            auth_sessions[session_id] = {
                'api_key': api_key,
                'status': 'initiated',
                'timestamp': time.time()
            }
            
            # Run the Twitter auth command
            try:
                # Create a process to run the command
                process = subprocess.Popen(
                    ['poetry', 'run', 'twitter-plugin-gamesdk', 'auth', '-k', api_key],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Read the output to find the auth URL
                auth_url = None
                stderr_output = ""
                for line in process.stdout:
                    if 'Visit the following URL to authenticate:' in line:
                        # The next line should contain the URL
                        try:
                            auth_url = next(process.stdout).strip()
                            break
                        except StopIteration:
                            # Handle case where there's no more output
                            break
                
                # If we couldn't get the URL from stdout, check stderr
                if not auth_url:
                    stderr_output = process.stderr.read()
                    current_app.logger.error(f"Error in subprocess: {stderr_output}")
                    return jsonify({'error': 'Failed to get auth URL. API key may be invalid.'}), 500
                
                # Store the process for later access
                auth_sessions[session_id]['process'] = process
                
                # Create a logger for the thread to avoid using current_app
                import logging
                thread_logger = logging.getLogger('auth_thread')
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                thread_logger.addHandler(handler)
                thread_logger.setLevel(logging.INFO)
                
                # Create a thread to monitor the process output
                def monitor_process(session_id, process, logger):
                    access_token = None
                    for line in process.stdout:
                        if "Here's your access token:" in line:
                            # The next line should contain the token
                            try:
                                access_token = next(process.stdout).strip()
                                break
                            except StopIteration:
                                break
                    
                    if access_token:
                        # Save the token in encrypted database
                        store_token(session_id, access_token)
                        
                        # Update session status
                        auth_sessions[session_id]['status'] = 'completed'
                        
                        # Set the token in environment variable
                        os.environ["GAME_TWITTER_ACCESS_TOKEN"] = access_token
                        
                        # Try to get Twitter user info once we have the token
                        try:
                            # We need to import here to avoid circular imports
                            try:
                                # First try direct relative import
                                from services.chat_agent import initialize_twitter_plugin, get_twitter_user_info
                            except ImportError:
                                logger.error("Could not import chat_agent functions. Twitter user info will not be saved.")
                                
                                
                            
                            # Initialize Twitter plugin with new token
                            global_twitter_plugin = initialize_twitter_plugin()
                            
                            if global_twitter_plugin:
                                # Get user info
                                twitter_id, twitter_name = get_twitter_user_info()
                                
                                # Store user info with the token if available
                                if twitter_id and twitter_name:
                                    user_info = {
                                        'id': twitter_id,
                                        'name': twitter_name
                                    }
                                    update_user_info(session_id, user_info)
                        except Exception as e:
                            logger.error(f"Error getting Twitter user info: {str(e)}")
                    else:
                        auth_sessions[session_id]['status'] = 'failed'
                        logger.error("Could not extract access token from output")
                
                # Start the monitoring thread
                import threading
                thread = threading.Thread(target=monitor_process, args=(session_id, process, thread_logger))
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    'session_id': session_id,
                    'auth_url': auth_url,
                    'browser_opened': True,
                    'message': 'Authentication initiated'
                })
                
            except subprocess.SubprocessError as e:
                current_app.logger.error(f"Subprocess error: {str(e)}")
                return jsonify({'error': 'Failed to run auth command'}), 500
        finally:
            # Always release the lock
            auth_lock.release()
            
    except Exception as e:
        current_app.logger.error(f"Error in initiate_auth: {str(e)}")
        # Make sure to release the lock if we got an exception
        if auth_lock.locked():
            auth_lock.release()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@api_bp.route('/auth/status', methods=['GET'])
def check_auth_status():
    """Check the status of the auth process"""
    # Get user_id from query parameters
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({
            'authenticated': False,
            'message': 'User ID is required'
        }), 400
    
    # Check if this is a valid user in our database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT email FROM users WHERE user_id = ?', (user_id,))
    user_result = cursor.fetchone()
    conn.close()
    
    if not user_result:
        return jsonify({
            'authenticated': False,
            'message': 'User not found'
        }), 404
    
    # Try to get the API key from the database first
    api_key = get_api_key(user_id)
    has_api_key = api_key is not None
    
    # Try to get the token from the database
    token = get_token(user_id)
    has_token = token is not None
    
    # Set them in the environment if available
    if api_key:
        os.environ["GAME_API_KEY"] = api_key
        agent_service.api_key = api_key
    
    if token:
        os.environ["GAME_TWITTER_ACCESS_TOKEN"] = token
    
    # Check for user_info which indicates Twitter auth
    user_info = get_user_info(user_id)
    
    # Log the actual status
    current_app.logger.info(f"Auth status check for user {user_id}:")
    current_app.logger.info(f"  Email: {user_result[0]}")
    current_app.logger.info(f"  API key present: {has_api_key}")
    current_app.logger.info(f"  Token present: {has_token}")
    current_app.logger.info(f"  User info present: {user_info is not None}")
    
    if token:
        # Set the token as an environment variable for the session
        os.environ["GAME_TWITTER_ACCESS_TOKEN"] = token
        
        return jsonify({
            'authenticated': True,
            'api_key_stored': has_api_key,
            'token_stored': True,
            'message': 'Authentication successful',
            'user_info': user_info,
            'email': user_result[0]
        })
    
    # User has API key but no Twitter token
    return jsonify({
        'authenticated': False,
        'api_key_stored': has_api_key,
        'token_stored': False,
        'message': 'Twitter authentication needed',
        'user_exists': True,
        'email': user_result[0]
    })

@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    """Log out a user without clearing stored tokens and API keys"""
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Debug users before logout
    current_app.logger.info(f"Logging out user: {user_id}")
    
    # Mark user as logged out but preserve tokens for future logins
    success = remove_token(user_id)
    
    # Clear environment variables for this session
    if 'GAME_TWITTER_ACCESS_TOKEN' in os.environ:
        del os.environ['GAME_TWITTER_ACCESS_TOKEN']
    
    if 'GAME_API_KEY' in os.environ:
        del os.environ['GAME_API_KEY']
    
    current_app.logger.info(f"User {user_id} logged out successfully, tokens preserved")
    
    return jsonify({
        'success': success,
        'message': 'Logged out successfully. Tokens preserved for future login.'
    })

@api_bp.route('/auth/callback', methods=['GET'])
def auth_callback():
    """Handle OAuth callback directly"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return jsonify({'error': 'Invalid callback parameters'}), 400
    
    # Process the callback (you may need to implement this based on your OAuth flow)
    # This is just a placeholder
    return jsonify({'success': True, 'message': 'Authentication processed'})

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password (at least 8 chars)
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400
        
        current_app.logger.info(f"Registering new user with email: {email}")
        
        # Show users before registration
        debug_users()
        
        # Register the user
        user_id, error = register_user(email, password)
        
        if error:
            current_app.logger.error(f"Registration failed: {error}")
            return jsonify({'error': error}), 400
        
        # Show users after registration to verify
        current_app.logger.info(f"Registration succeeded for user_id: {user_id}")
        debug_users()
        
        # Store the user ID in the response for the client
        return jsonify({
            'success': True,
            'user_id': user_id,
            'message': 'User registered successfully'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in register: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login a user"""
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Log login attempt (without capturing passwords)
        current_app.logger.info(f"Login attempt for email: {email}")
        
        # Debug: List all users in the database
        debug_users()
        
        # Authenticate the user
        user_id, error = login_user(email, password)
        
        if error:
            current_app.logger.warning(f"Login failed for email {email}: {error}")
            return jsonify({'error': error}), 401
        
        # Check if user has GAME API key stored - use more direct check
        api_key = get_api_key(user_id)
        has_api_key = api_key is not None
        
        # Check if user has Twitter token - use more direct check
        token = get_token(user_id)
        has_twitter = token is not None
        
        # Set the token in the environment if available
        if token:
            os.environ["GAME_TWITTER_ACCESS_TOKEN"] = token
        
        # Set the API key in the environment if available
        if api_key:
            os.environ["GAME_API_KEY"] = api_key
            agent_service.api_key = api_key
        
        # Get user info if available
        user_info = get_user_info(user_id)
        
        # Log additional debug info
        current_app.logger.info(f"Login successful for user: {user_id}")
        current_app.logger.info(f"  Has API key: {has_api_key}")
        current_app.logger.info(f"  Has Twitter token: {has_twitter}")
        current_app.logger.info(f"  User info: {user_info}")
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'has_api_key': has_api_key,
            'has_twitter_auth': has_twitter,
            'user_info': user_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in login: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@api_bp.route('/auth/debug_status', methods=['GET'])
def debug_auth_status():
    """Debug endpoint to check user auth status"""
    # Get user_id from query parameters
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Check user status
    status = check_user_auth_status(user_id)
    
    # Also check if we can decrypt tokens
    if status['has_api_key']:
        api_key = get_api_key(user_id)
        status['api_key_decryptable'] = api_key is not None
    
    if status['has_token']:
        token = get_token(user_id)
        status['token_decryptable'] = token is not None
    
    return jsonify(status) 