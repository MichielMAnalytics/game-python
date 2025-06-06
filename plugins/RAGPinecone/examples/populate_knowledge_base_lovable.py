import os
import logging
import tempfile
import requests
import re
import time
from dotenv import load_dotenv
import gdown
from langchain_unstructured import UnstructuredLoader

from rag_pinecone_gamesdk.populate_rag import RAGPopulator
from rag_pinecone_gamesdk import DEFAULT_INDEX_NAME, DEFAULT_NAMESPACE
from game_sdk.game.custom_types import FunctionResultStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def download_from_google_drive(folder_url, download_folder):
    """
    Download all files from a Google Drive folder
    
    Args:
        folder_url: URL of the Google Drive folder
        download_folder: Local folder to download files to
        
    Returns:
        List of downloaded file paths
    """
    logger.info(f"Downloading files from Google Drive folder: {folder_url}")
    
    # Extract folder ID from URL
    folder_id_match = re.search(r'folders/([a-zA-Z0-9_-]+)', folder_url)
    if not folder_id_match:
        logger.error(f"Could not extract folder ID from URL: {folder_url}")
        return []
    
    folder_id = folder_id_match.group(1)
    logger.info(f"Folder ID: {folder_id}")
    
    # Create download folder if it doesn't exist
    os.makedirs(download_folder, exist_ok=True)
    
    # Download all files in the folder
    try:
        # Use gdown to download all files in the folder
        downloaded_files = gdown.download_folder(
            id=folder_id,
            output=download_folder,
            quiet=False,
            use_cookies=False
        )
        
        if not downloaded_files:
            logger.warning("No files were downloaded from Google Drive")
            return []
        
        logger.info(f"Downloaded {len(downloaded_files)} files from Google Drive")
        return downloaded_files
    
    except Exception as e:
        logger.error(f"Error downloading files from Google Drive: {str(e)}")
        return []

def load_documents():
    # Use absolute directory path
    documents_path = "/Users/michi/L-Documents/The Application Layer/AGENT_VIRTUALS/game-python/plugins/RAGPinecone/Documents"
    
    # Get all files from the directory
    documents = []
    loaded_files = []
    for file in os.listdir(documents_path):
        if file.endswith(('.pdf', '.txt', '.doc', '.docx')):  # Add or modify extensions as needed
            file_path = os.path.join(documents_path, file)
            try:
                loader = UnstructuredLoader(file_path)
                file_docs = loader.load()
                documents.extend(file_docs)
                loaded_files.append(file)
                logger.info(f"Successfully loaded file: {file} - split into {len(file_docs)} segments")
            except Exception as e:
                logger.error(f"Error loading file {file}: {e}")
    
    logger.info(f"Total files processed: {len(loaded_files)}")
    return documents

def main():
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    pinecone_api_key = os.environ.get("PINECONE_API_KEY")
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not pinecone_api_key:
        logger.error("PINECONE_API_KEY environment variable is not set")
        return
    
    if not openai_api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        return
    
    # Use absolute path instead of relative path
    documents_path = "/Users/michi/L-Documents/The Application Layer/AGENT_VIRTUALS/game-python/plugins/RAGPinecone/Documents"
    
    # Check if the directory exists
    if not os.path.exists(documents_path):
        logger.error(f"Documents directory {documents_path} doesn't exist.")
        return
    
    # Initialize the RAGPopulator with the local documents path
    logger.info("Initializing RAGPopulator...")
    populator = RAGPopulator(
        pinecone_api_key=pinecone_api_key,
        openai_api_key=openai_api_key,
        index_name=DEFAULT_INDEX_NAME,
        namespace=DEFAULT_NAMESPACE,
        documents_folder=documents_path,  # Use the local directory
    )
    
    # Process all documents in the local folder
    logger.info(f"Processing documents from: {documents_path}")
    status, message, results = populator.process_documents_folder()
    
    # Log the results
    logger.info(f"Status: {status}")
    logger.info(f"Message: {message}")
    logger.info(f"Processed {results.get('total_files', 0)} files, {results.get('successful_files', 0)} successful")
    
    # Count vectors from the results instead of using fetch_all_ids()
    total_chunks = 0
    if 'results' in results:
        for result in results['results']:
            if result.get('status') == FunctionResultStatus.DONE:
                # Extract chunk count from message (assuming format: "... with XX chunks")
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

# Add this method to the RAGPopulator class
def process_document(self, file_path):
    """
    Process a single document and add it to the vector database
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Tuple of (status, message, result)
    """
    try:
        # Load the document
        logger.info(f"Loading document: {file_path}")
        loader = UnstructuredLoader(file_path)
        documents = loader.load()
        
        if not documents:
            return FunctionResultStatus.ERROR, f"No content extracted from {os.path.basename(file_path)}", {}
        
        # Process the document
        logger.info(f"Splitting document into chunks and creating embeddings")
        document_id = os.path.basename(file_path)
        
        # Call the process_and_store method
        vector_count = self.process_and_store(documents, document_id)
        
        if vector_count > 0:
            result = {
                'file_path': file_path,
                'status': FunctionResultStatus.DONE,
                'message': f"Successfully processed {os.path.basename(file_path)} with {vector_count} chunks",
                'vectors_count': vector_count
            }
            return FunctionResultStatus.DONE, f"Successfully processed {os.path.basename(file_path)} with {vector_count} chunks", result
        else:
            result = {
                'file_path': file_path,
                'status': FunctionResultStatus.ERROR,
                'message': f"No vectors created for {os.path.basename(file_path)}"
            }
            return FunctionResultStatus.ERROR, f"No vectors created for {os.path.basename(file_path)}", result
            
    except Exception as e:
        logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
        result = {
            'file_path': file_path,
            'status': FunctionResultStatus.ERROR,
            'message': f"Error: {str(e)}"
        }
        return FunctionResultStatus.ERROR, f"Failed to process {os.path.basename(file_path)}: {str(e)}", result

if __name__ == "__main__":
    main()
