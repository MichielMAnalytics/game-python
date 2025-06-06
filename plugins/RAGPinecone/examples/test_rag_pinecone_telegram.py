import os
from typing import TypedDict
import logging
import time
import threading
import requests
from PIL import Image
from io import BytesIO
import json
import re
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import uuid
from flask_cors import CORS
import tempfile
import hashlib

from telegram import Update
from telegram.ext import ContextTypes, filters, MessageHandler

from game_sdk.game.chat_agent import Chat, ChatAgent
from telegram_plugin_gamesdk.telegram_plugin import TelegramPlugin
# Import RAG components
from rag_pinecone_gamesdk.rag_pinecone_plugin import RAGPineconePlugin
from rag_pinecone_gamesdk.rag_pinecone_game_functions import query_knowledge_fn, add_document_fn
from rag_pinecone_gamesdk.search_rag import RAGSearcher
from rag_pinecone_gamesdk.rag_pinecone_game_functions import (
    advanced_query_knowledge_fn, get_relevant_documents_fn
)
from rag_pinecone_gamesdk import DEFAULT_INDEX_NAME, DEFAULT_NAMESPACE
# Import the GameTwitterPlugin instead of TwitterPlugin
from twitter_plugin_gamesdk.game_twitter_plugin import GameTwitterPlugin
from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../telegram/examples')))
from test_telegram_game_functions import send_message_fn, send_media_fn, create_poll_fn, pin_message_fn, unpin_message_fn, delete_message_fn
from dotenv import load_dotenv

# Import functions from populate_knowledge_base
from populate_knowledge_base import download_from_google_drive, RAGPopulator

load_dotenv()

# API Keys
game_api_key = os.environ.get("GAME_API_KEY")
telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
# Add RAG environment variables
pinecone_api_key = os.environ.get("PINECONE_API_KEY")
openai_api_key = os.environ.get("OPENAI_API_KEY")
# Game Twitter access token
game_twitter_access_token = os.environ.get("GAME_TWITTER_ACCESS_TOKEN")

# Print environment variable status
print(f"GAME API Key: {'✓' if game_api_key else '✗'}")
print(f"Telegram Bot Token: {'✓' if telegram_bot_token else '✗'}")
print(f"Pinecone API Key: {'✓' if pinecone_api_key else '✗'}")
print(f"OpenAI API Key: {'✓' if openai_api_key else '✗'}")
print(f"GAME Twitter Access Token: {'✓' if game_twitter_access_token else '✗'}")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

class ActiveUser(TypedDict):
    chat_id: int
    name: str

# Update the prompt to include both RAG capabilities and Twitter interaction with character limit
chat_agent = ChatAgent(
    prompt="""You are Accountable's helpful intern. For both Twitter (X) and Telegram, answer never longer than 250 characters. Use your RAG knowledge to answer questions. Always maintain a professional tone focused on Accountable's services.""",
    api_key=game_api_key,
)

active_users: list[ActiveUser] = []
active_chats: dict[int, Chat] = {}

# Near the top of the file with other global variables
PROCESSED_TWEETS_FILE = "processed_tweets.json"
PROCESSED_DOCUMENTS_FILE = "processed_documents.json"
GDRIVE_URL = "https://drive.google.com/drive/u/2/folders/1R4I59vOL-LQYJGEfFzVB1imAeHcqZHQd"

# Add this near the top of the file with other global variables
processed_tweet_ids = set()
processed_document_ids = set()

# Add this near the top of the file with other global variables
last_documents_check = 0
DOCUMENTS_CHECK_INTERVAL = 30  # Check for new documents every hour (in seconds)

# Add these constants near the top with your other constants
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}
API_PORT = 5001  # You can change this port if needed

# Create Flask app
flask_app = Flask(__name__)
CORS(flask_app)  # Enable CORS for all routes

flask_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit uploads to 16MB

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@flask_app.route('/api/upload-document', methods=['POST'])
def upload_document():
    """API endpoint to handle document uploads and process directly into Pinecone"""
    try:
        logger.info(f"Upload request received: {request.method}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Check if the post request has the file part
        if 'file' not in request.files:
            logger.warning("No file part in the request")
            return jsonify({'error': 'No file part in the request'}), 400
        
        file = request.files['file']
        logger.info(f"File received: {file.filename}")
        
        if file.filename == '':
            logger.warning("Empty filename submitted")
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Create a temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save file to temporary directory
                temp_file_path = os.path.join(temp_dir, secure_filename(file.filename))
                file.save(temp_file_path)
                
                # Initialize RAGPopulator
                populator = RAGPopulator(
                    pinecone_api_key=pinecone_api_key,
                    openai_api_key=openai_api_key,
                    index_name=DEFAULT_INDEX_NAME,
                    namespace=DEFAULT_NAMESPACE,
                    documents_folder=temp_dir
                )
                
                # Process the document
                status, message, results = populator.process_documents_folder()
                
                if status == FunctionResultStatus.DONE:
                    return jsonify({
                        'success': True,
                        'message': f"Document processed successfully: {message}",
                        'results': results
                    }), 200
                else:
                    return jsonify({
                        'error': f"Failed to process document: {message}"
                    }), 500
        else:
            logger.warning(f"Invalid file type: {file.filename}")
            return jsonify({
                'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Add a new endpoint to process Google Drive documents
@flask_app.route('/api/process-drive', methods=['POST'])
def process_drive_documents():
    """API endpoint to process documents from a Google Drive folder"""
    try:
        data = request.get_json()
        if not data or 'folder_url' not in data:
            return jsonify({'error': 'Missing folder_url in request'}), 400
            
        folder_url = data['folder_url']
        
        # Create a temporary directory for downloaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download files from Google Drive
            downloaded_files = download_from_google_drive(folder_url, temp_dir)
            
            if not downloaded_files:
                return jsonify({'error': 'No files were downloaded from Google Drive'}), 400
            
            # Initialize RAGPopulator
            populator = RAGPopulator(
                pinecone_api_key=pinecone_api_key,
                openai_api_key=openai_api_key,
                index_name=DEFAULT_INDEX_NAME,
                namespace=DEFAULT_NAMESPACE,
                documents_folder=temp_dir
            )
            
            # Process all documents
            status, message, results = populator.process_documents_folder()
            
            return jsonify({
                'success': status == FunctionResultStatus.DONE,
                'message': message,
                'results': results
            }), 200 if status == FunctionResultStatus.DONE else 500
            
    except Exception as e:
        logger.error(f"Error processing Google Drive documents: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@flask_app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Accountable Intern Document Upload API'}), 200

@flask_app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to verify API connectivity"""
    return jsonify({
        'status': 'success',
        'message': 'API is working correctly'
    })

def run_flask_server():
    """Run the Flask server in a separate thread"""
    try:
        logger.info(f"Starting Flask server on port {API_PORT}...")
        flask_app.run(host='0.0.0.0', port=API_PORT, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Error starting Flask server: {e}", exc_info=True)

def load_processed_tweets():
    """Load processed tweet IDs from file"""
    try:
        if os.path.exists(PROCESSED_TWEETS_FILE):
            with open(PROCESSED_TWEETS_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logger.error(f"Error loading processed tweets: {e}")
    return set()

def save_processed_tweets():
    """Save processed tweet IDs to file"""
    try:
        with open(PROCESSED_TWEETS_FILE, 'w') as f:
            json.dump(list(processed_tweet_ids), f)
    except Exception as e:
        logger.error(f"Error saving processed tweets: {e}")

def load_processed_documents():
    """Load processed document IDs from file"""
    try:
        if os.path.exists(PROCESSED_DOCUMENTS_FILE):
            with open(PROCESSED_DOCUMENTS_FILE, 'r') as f:
                return set(json.load(f))
    except Exception as e:
        logger.error(f"Error loading processed documents: {e}")
    return set()

def save_processed_documents():
    """Save processed document IDs to file"""
    try:
        with open(PROCESSED_DOCUMENTS_FILE, 'w') as f:
            json.dump(list(processed_document_ids), f)
    except Exception as e:
        logger.error(f"Error saving processed documents: {e}")

# Twitter functions from example_twitter_reaction_module.py
def analyze_image_from_url(image_url: str) -> dict:
    """
    Function to analyse the image colours and brightness
    """
    # Fetch image from URL
    response = requests.get(image_url)
    img = Image.open(BytesIO(response.content))
    # Basic Info
    width, height = img.size
    mode = img.mode  # RGB, Grayscale, etc.
    # Convert to RGB if not already
    img = img.convert("RGB")
    # Get Average Color
    pixels = list(img.getdata())
    avg_color = tuple(sum(x) // len(pixels) for x in zip(*pixels))  # Average RGB
    # Estimate Brightness (0-255)
    brightness = sum(avg_color) // 3  # Simple brightness estimate
    # Format Results
    return {
        "Image Size": f"{width}x{height}", 
        "Image Mode": mode,
        "Average Color (RGB)": avg_color,
        "Brightness Level": brightness
    }

def get_twitter_user_mentions(twitter_plugin, username: str = None) -> list:
    """
    Function to get user mentions for the authenticated Twitter user
    """
    try:
        # Use 'mentions' function directly
        mentions_fn = twitter_plugin.get_function('mentions')
        response = mentions_fn()  # No parameters needed since it gets mentions for authenticated user
        
        # Log the raw response for debugging
        logger.info(f"Raw mentions response: {response}")
        
        # Handle both list and dictionary response formats
        mentions = []
        if isinstance(response, dict):
            # Check if there's a 'data' key that might contain the mentions
            if 'data' in response:
                # Filter out already processed tweets
                mentions = [
                    mention for mention in response['data'] 
                    if mention.get('id') and mention['id'] not in processed_tweet_ids
                ]
                logger.info(f"Retrieved {len(mentions)} new mentions from 'data' key")
            # Check result count in meta
            elif 'meta' in response and response['meta'].get('result_count', 0) == 0:
                logger.info("No mentions found according to meta data")
        elif isinstance(response, list):
            # Filter out already processed tweets
            mentions = [
                mention for mention in response 
                if mention.get('id') and mention['id'] not in processed_tweet_ids
            ]
            logger.info(f"Retrieved {len(mentions)} new mentions as list")
        else:
            logger.warning(f"Unexpected response type: {type(response)}")
        
        return mentions
    except Exception as e:
        logger.error(f"Error getting Twitter mentions: {e}")
        return []

def respond_to_twitter_mention(twitter_plugin, mention, rag_searcher):
    """Process a Twitter mention and respond as the Accountable Intern"""
    try:
        mention_text = mention.get('text', '')
        mention_id = mention.get('id', '')
        
        # Skip if we've already processed this tweet
        if mention_id in processed_tweet_ids:
            logger.info(f"Skipping already processed tweet: {mention_id}")
            return
        
        # Convert mention_id to integer
        tweet_id = int(mention_id) if mention_id else None
        if not tweet_id:
            logger.error("Invalid tweet ID")
            return
        
        # Use RAG to enhance the response
        context = ""
        if mention_text and rag_searcher is not None:  # Check if rag_searcher exists
            try:
                # Get the executable function from the Function object
                query_fn = advanced_query_knowledge_fn(rag_searcher).executable
                # Execute the function with the cleaned mention text
                # Remove mentions and URLs for better RAG matching
                cleaned_text = re.sub(r'@\w+|https?://\S+', '', mention_text).strip()
                status, message, results = query_fn(cleaned_text)
                
                if status == FunctionResultStatus.DONE and message:
                    context = message
                    logger.info(f"RAG context retrieved: {context}")
                else:
                    logger.warning(f"RAG query returned status: {status}")
            except Exception as e:
                logger.error(f"Error querying knowledge base: {e}", exc_info=True)
        else:
            logger.warning(f"Skipping RAG query - {'No mention text' if not mention_text else 'No RAG searcher'}")
        
        # Prepare a response as Accountable Intern
        if context:
            # Find all complete sentences in the context
            sentences = re.split(r'(?<=[.!?])\s+', context)
            response = ""
            suffix = " For more information, visit Accountable.capital"
            
            # Build response by adding sentences until we approach the limit
            for sentence in sentences:
                # Check if adding this sentence plus suffix would exceed Twitter's limit
                if len(response + sentence + suffix) <= 280:
                    if response:
                        response += " " + sentence
                    else:
                        response = sentence
                else:
                    break
            
            # Add the suffix
            response += suffix
            
            logger.info(f"Built response with {len(response)} characters: {response}")
        else:
            # Fallback response
            response = "Thanks for reaching out! As Accountable's intern, I'm here to help. Visit Accountable.capital for more info."
        
        # Truncate response if it's too long for Twitter

        
        logger.info(f"Sending Twitter response: {response}")
        
        # Reply to the tweet
        reply_tweet_fn = twitter_plugin.get_function('reply_tweet')
        reply_tweet_fn(tweet_id=tweet_id, reply=response)
        
        # Add the tweet ID to processed set after successful reply
        processed_tweet_ids.add(mention_id)
        save_processed_tweets()
        logger.info(f"Successfully responded to Twitter mention: {tweet_id}")
        
    except Exception as e:
        logger.error(f"Error responding to Twitter mention: {e}", exc_info=True)

def twitter_monitoring_thread(twitter_plugin, rag_searcher):
    """
    Thread function to periodically check for Twitter mentions and respond to them
    with proper rate limit handling
    """
    # We don't need TWITTER_HANDLE anymore as the 'mentions' function gets mentions for the authenticated user
    base_wait_time = 1 * 30  # 15 minutes in seconds
    current_wait_time = base_wait_time
    max_wait_time = 60 * 60  # 1 hour in seconds
    
    while True:
        try:
            logger.info("Checking for Twitter mentions...")
            mentions = get_twitter_user_mentions(twitter_plugin, None)
            
            if mentions and len(mentions) > 0:
                logger.info(f"Found {len(mentions)} mentions to process")
                # Process each mention
                for mention in mentions:
                    # Check if mention is a proper dictionary with required fields
                    if isinstance(mention, dict) and 'id' in mention and 'text' in mention:
                        respond_to_twitter_mention(twitter_plugin, mention, rag_searcher)
                    else:
                        logger.warning(f"Skipping invalid mention format: {mention}")
                
                # If successful, reset the wait time
                current_wait_time = base_wait_time
            else:
                logger.info("No valid mentions found")
            
            # Wait before checking again
            logger.info(f"Waiting {current_wait_time} seconds before checking Twitter again...")
            time.sleep(current_wait_time)
            
        except Exception as e:
            # If we get a rate limit error, implement exponential backoff
            if "429" in str(e):
                # Double the wait time, but don't exceed the maximum
                current_wait_time = min(current_wait_time * 2, max_wait_time)
                logger.warning(f"Rate limit hit. Backing off for {current_wait_time} seconds.")
                time.sleep(current_wait_time)
            else:
                logger.error(f"Error in Twitter monitoring thread: {e}", exc_info=True)
                # For other errors, wait a minute before trying again
                time.sleep(60)

# Add a function to check and upload new documents
def check_and_upload_documents(rag_plugin):
    """
    Check for new documents in Google Drive and upload them to the vector database
    """
    global rag_searcher, agent_action_space, processed_document_ids
    
    try:
        logger.info("Checking for new documents to upload from Google Drive...")
        google_drive_url = GDRIVE_URL
        
        # Extract folder ID from URL
        folder_id_match = re.search(r'folders/([a-zA-Z0-9_-]+)', google_drive_url)
        if not folder_id_match:
            logger.error(f"Could not extract folder ID from URL: {google_drive_url}")
            return
        
        folder_id = folder_id_match.group(1)
        logger.info(f"Checking Google Drive folder ID: {folder_id}")
        
        # Create a temporary directory for downloaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                import gdown
                
                # Download all files from the folder
                logger.info("Downloading files from Google Drive folder...")
                downloaded_files = gdown.download_folder(
                    url=google_drive_url,
                    output=temp_dir,
                    quiet=False,
                    use_cookies=False
                )
                
                if not downloaded_files:
                    logger.warning("No files were downloaded from Google Drive folder")
                    return
                
                logger.info(f"Downloaded {len(downloaded_files)} files")
                
                # Process only new files based on their content hash
                new_files = []
                for file_path in downloaded_files:
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            if file_hash not in processed_document_ids:
                                new_files.append(file_path)
                                processed_document_ids.add(file_hash)
                                logger.info(f"New file found: {os.path.basename(file_path)}")
                            else:
                                logger.info(f"Skipping already processed file: {os.path.basename(file_path)}")
                                os.remove(file_path)  # Remove duplicate file
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")
                
                if not new_files:
                    logger.info("No new files to process")
                    return
                
                logger.info(f"Found {len(new_files)} new files to process")
                
                # Save the processed IDs immediately
                save_processed_documents()
                
                # Initialize the RAGPopulator with the temporary directory
                populator = RAGPopulator(
                    pinecone_api_key=pinecone_api_key,
                    openai_api_key=openai_api_key,
                    index_name=DEFAULT_INDEX_NAME,
                    namespace=DEFAULT_NAMESPACE,
                    documents_folder=temp_dir
                )
                
                # Process all documents
                status, message, results = populator.process_documents_folder()
                
                # Log the results
                logger.info(f"Status: {status}")
                logger.info(f"Message: {message}")
                logger.info(f"Processed {results.get('total_files', 0)} files, {results.get('successful_files', 0)} successful")
                
                # Count vectors from the results
                total_chunks = 0
                if 'results' in results:
                    for result in results['results']:
                        if result.get('status') == FunctionResultStatus.DONE:
                            # Extract chunk count from message
                            message = result.get('message', '')
                            chunks_match = re.search(r'with (\d+) chunks', message)
                            if chunks_match:
                                total_chunks += int(chunks_match.group(1))
                
                logger.info(f"Total chunks processed: {total_chunks}")
                
                # Print detailed results for each file
                if 'results' in results:
                    logger.info("\nDetailed results:")
                    for result in results['results']:
                        file_path = result.get('file_path', 'Unknown file')
                        status = result.get('status', 'Unknown status')
                        message = result.get('message', 'No message')
                        logger.info(f"File: {os.path.basename(file_path)}")
                        logger.info(f"Status: {status}")
                        logger.info(f"Message: {message}")
                        logger.info("---")
                
                # If we have processed documents and rag_searcher is None, try to initialize it now
                if total_chunks > 0 and rag_searcher is None:
                    try:
                        # Add a delay to ensure vectors are fully indexed
                        logger.info("Waiting for vectors to be indexed before initializing RAG searcher...")
                        time.sleep(10)
                        
                        # Initialize RAG searcher
                        rag_searcher = RAGSearcher(
                            pinecone_api_key=pinecone_api_key,
                            openai_api_key=openai_api_key,
                            index_name=DEFAULT_INDEX_NAME,
                            namespace=DEFAULT_NAMESPACE,
                            llm_model="gpt-4o-mini",
                            temperature=0.0,
                            k=4
                        )
                        
                        logger.info("RAGSearcher initialized successfully after documents were uploaded")
                        
                        # Update action space with advanced RAG functions
                        agent_action_space = [action for action in agent_action_space 
                                            if action.fn_name not in ['advanced_query_knowledge', 'get_relevant_documents']]
                        
                        agent_action_space.extend([
                            advanced_query_knowledge_fn(rag_searcher),
                            get_relevant_documents_fn(rag_searcher),
                        ])
                        
                        logger.info("Updated agent action space with advanced RAG functions")
                        
                    except Exception as e:
                        logger.error(f"Error initializing RAGSearcher after document upload: {e}", exc_info=True)
                        
            except Exception as e:
                logger.error(f"Error processing Google Drive folder: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Error checking and uploading documents: {e}", exc_info=True)

# Update your after_request handler to be more permissive
@flask_app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Requested-With, Authorization, Accept, Origin')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    # Handle preflight OPTIONS requests
    if request.method == 'OPTIONS':
        response.status_code = 200
    return response

# Add explicit handler for OPTIONS requests to the upload endpoint
@flask_app.route('/api/upload-document', methods=['OPTIONS'])
def handle_options():
    return '', 200

def document_monitoring_thread(rag_plugin):
    """Thread function to periodically check for new documents and process them"""
    global last_documents_check
    
    while True:
        try:
            current_time = time.time()
            # Check if enough time has passed since last check
            if current_time - last_documents_check >= DOCUMENTS_CHECK_INTERVAL:
                logger.info("Running scheduled document check...")
                check_and_upload_documents(rag_plugin)
                last_documents_check = current_time
            
            # Sleep for a short interval to prevent busy waiting
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error in document monitoring thread: {e}", exc_info=True)
            # Sleep for a minute before trying again after an error
            time.sleep(60)

if __name__ == "__main__":
    # Start the Flask server FIRST, before other components
    flask_thread = threading.Thread(
        target=run_flask_server,
        daemon=True
    )
    flask_thread.start()
    logger.info("Waiting for Flask server to start...")
    time.sleep(2)  # Give Flask time to start
    
    # Load previously processed documents and tweets
    processed_tweet_ids = load_processed_tweets()
    processed_document_ids = load_processed_documents()
    logger.info(f"Loaded {len(processed_document_ids)} processed document IDs")
    
        
    tg_plugin = TelegramPlugin(bot_token=telegram_bot_token)
    
    # Initialize RAG plugins
    rag_plugin = RAGPineconePlugin(
        pinecone_api_key=pinecone_api_key,
        openai_api_key=openai_api_key,
        index_name=DEFAULT_INDEX_NAME,
        namespace=DEFAULT_NAMESPACE
    )
    
    # Initialize advanced RAG searcher with proper error handling
    try:
        rag_searcher = RAGSearcher(
            pinecone_api_key=pinecone_api_key,
            openai_api_key=openai_api_key,
            index_name=DEFAULT_INDEX_NAME,
            namespace=DEFAULT_NAMESPACE,
            llm_model="gpt-4o-mini",  # You can change this to "gpt-3.5-turbo" for faster, cheaper responses
            temperature=0.0,
            k=4  # Number of documents to retrieve
        )
        logger.info("RAGSearcher initialized successfully")
    except ValueError as e:
        logger.warning(f"Error initializing RAGSearcher: {e}. This may indicate that no documents exist in the database yet.")
        # Create a placeholder RAG searcher that will be updated later when documents are added
        rag_searcher = None
        logger.info("Created placeholder for RAGSearcher")
    except Exception as e:
        logger.error(f"Unexpected error initializing RAGSearcher: {e}", exc_info=True)
        rag_searcher = None
    
    # Initialize GameTwitterPlugin instead of TwitterPlugin
    # Check if GAME_TWITTER_ACCESS_TOKEN exists
    game_twitter_access_token = os.environ.get("GAME_TWITTER_ACCESS_TOKEN")
    
    if not game_twitter_access_token:
        logger.warning("GAME_TWITTER_ACCESS_TOKEN not found. Run 'poetry run twitter-plugin-gamesdk auth -k <GAME_API_KEY>' to get a token.")
        logger.warning("Twitter functionality will be disabled.")
        twitter_plugin = None
    else:
        # Use GameTwitterPlugin with enterprise credentials
        twitter_options = {
            "id": "accountable_twitter_plugin",
            "name": "Accountable Twitter Plugin",
            "description": "Twitter plugin for Accountable Intern.",
            "credentials": {
                "gameTwitterAccessToken": game_twitter_access_token
            },
        }
        twitter_plugin = GameTwitterPlugin(twitter_options)
        # Log the available functions for debugging
        available_functions = [func for func in dir(twitter_plugin) if callable(getattr(twitter_plugin, func)) and not func.startswith("_")]
        logger.info(f"GameTwitterPlugin initialized with enterprise credentials. Available functions: {available_functions}")
        

    # Add RAG and Twitter functions to the action space
    agent_action_space = [
        # Telegram functions
        send_message_fn(tg_plugin),
        send_media_fn(tg_plugin),
        create_poll_fn(tg_plugin),
        pin_message_fn(tg_plugin),
        unpin_message_fn(tg_plugin),
        delete_message_fn(tg_plugin),
        
        # RAG functions
        query_knowledge_fn(rag_plugin),
        add_document_fn(rag_plugin),
    ]
    
    # Only add advanced RAG functions if rag_searcher was successfully initialized
    if rag_searcher:
        agent_action_space.extend([
            advanced_query_knowledge_fn(rag_searcher),
            get_relevant_documents_fn(rag_searcher),
        ])

    if twitter_plugin:
        # Add Twitter functions to action space with correct parameter names
        reply_tweet_fn = twitter_plugin.get_function('reply_tweet')
        agent_action_space.append(Function(
            fn_name="reply_tweet",
            fn_description="Reply to a tweet",
            args=[
                Argument(name="tweet_id", description="ID of the tweet to reply to", type="int"),
                Argument(name="reply", description="Text of the reply", type="str"),
            ],
            executable=reply_tweet_fn
        ))

    # Load previously processed tweets
    processed_tweet_ids = load_processed_tweets()
    
    # Initialize document monitoring by checking once at startup
    check_and_upload_documents(rag_plugin)
    last_documents_check = time.time()
    
    # Start the document monitoring thread
    document_thread = threading.Thread(
        target=document_monitoring_thread,
        args=(rag_plugin,),
        daemon=True
    )
    document_thread.start()
    logger.info("Document monitoring thread started - checking for new documents every 30 seconds")
    
    async def default_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            # Ignore messages from the bot itself
            if update.message.from_user.id == tg_plugin.bot.id:
                logger.info("Ignoring bot's own message.")
                return

            user = update.message.from_user
            chat_id = update.message.chat.id
            chat_type = update.message.chat.type
            bot_username = f"@{tg_plugin.bot.username}"

            logger.info(f"Message received: {update.message.text}")

            # Handle non-text messages
            if update.message.text is None:
                logger.info("Received a non-text message, skipping processing")
                return

            # For group chats, only respond when the bot is mentioned or when it's a direct reply
            if chat_type in ["group", "supergroup"]:
                if (bot_username not in update.message.text and 
                    (update.message.reply_to_message is None or 
                     update.message.reply_to_message.from_user.id != tg_plugin.bot.id)):
                    logger.info("Ignoring group message not mentioning or replying to the bot")
                    return

            try:
                # Try to get existing chat
                chat = active_chats.get(chat_id)
                
                # If no active chat or error occurs, create new one
                if not chat:
                    # Create new active user
                    new_user: ActiveUser = {
                        "chat_id": chat_id,
                        "name": user.first_name
                    }
                    active_users.append(new_user)
                    logger.info(f"Active user added: {user.first_name}")
                    
                    # Create new chat
                    chat = chat_agent.create_chat(
                        partner_id=str(chat_id),  # Convert chat_id to string
                        partner_name=user.first_name,
                        action_space=agent_action_space,
                    )
                    active_chats[chat_id] = chat

                # Process message
                cleaned_message = update.message.text.replace(bot_username, "").strip()
                
                # First try to get context from RAG
                try:
                    query_fn = advanced_query_knowledge_fn(rag_searcher).executable
                    status, rag_context, _ = query_fn(cleaned_message)
                    
                    if status == FunctionResultStatus.DONE and rag_context:
                        # Add RAG context to the message
                        cleaned_message = f"Context from knowledge base: {rag_context}\n\nUser message: {cleaned_message}"
                except Exception as e:
                    logger.error(f"Error querying RAG: {e}", exc_info=True)
                    # Continue without RAG context if there's an error
                
                # Get response from chat agent
                response = chat.next(cleaned_message)

                if response.message:
                    await update.message.reply_text(response.message)

                if response.is_finished:
                    # Clean up finished chat
                    active_chats.pop(chat_id, None)
                    active_users[:] = [u for u in active_users if u["chat_id"] != chat_id]
                    logger.info(f"Chat with {user.first_name} ended.")

            except ValueError as ve:
                # Handle 400 error by creating new chat session
                logger.warning(f"Chat session error, creating new session: {ve}")
                
                # Clean up old session
                active_chats.pop(chat_id, None)
                active_users[:] = [u for u in active_users if u["chat_id"] != chat_id]
                
                # Create new chat session with string chat_id
                chat = chat_agent.create_chat(
                    partner_id=str(chat_id),  # Convert chat_id to string
                    partner_name=user.first_name,
                    action_space=agent_action_space,
                )
                active_chats[chat_id] = chat
                active_users.append({"chat_id": chat_id, "name": user.first_name})
                
                # Try processing message again
                cleaned_message = update.message.text.replace(bot_username, "").strip()
                response = chat.next(cleaned_message)
                
                if response.message:
                    await update.message.reply_text(response.message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await update.message.reply_text("I'm sorry, something went wrong. Please try again.")

    tg_plugin.add_handler(MessageHandler(filters.ALL, default_message_handler))

    # #Start the Twitter monitoring thread only if twitter_plugin is available
    if twitter_plugin:
        twitter_thread = threading.Thread(
            target=twitter_monitoring_thread,
            args=(twitter_plugin, rag_searcher),
            daemon=True
        )
        twitter_thread.start()
        logger.info("Twitter monitoring thread started with GameTwitterPlugin")
    else:
        logger.warning("Twitter functionality disabled due to missing credentials.")

    # Start polling
    print("Starting Telegram bot with RAG capabilities, Twitter monitoring, and document monitoring...")
    tg_plugin.start_polling()

    # Example of executing a function from Telegram Plugin to a chat without polling
    #tg_plugin.send_message(chat_id=829856292, text="Hello! I am a helpful assistant. How can I assist you today?")
