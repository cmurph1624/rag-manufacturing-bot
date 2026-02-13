import os
import time
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "aerostream-docs")

_pc_client = None
_pc_index = None

def get_pinecone_client():
    """
    Get or create the Pinecone client.
    """
    global _pc_client
    if not PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY not found in environment variables.")
    
    if _pc_client is None:
        _pc_client = Pinecone(api_key=PINECONE_API_KEY)
    return _pc_client

def get_pinecone_index(create_if_missing: bool = False, dimension: int = 768):
    """
    Get the Pinecone index, creating it if it doesn't exist (and create_if_missing is True).
    Default dimension is 768 (for nomic-embed-text).
    """
    global _pc_index
    client = get_pinecone_client()
    
    # Check if index exists
    existing_indexes = [i.name for i in client.list_indexes()]
    
    if PINECONE_INDEX_NAME not in existing_indexes:
        if create_if_missing:
            print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
            client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not client.describe_index(PINECONE_INDEX_NAME).status['ready']:
                time.sleep(1)
            print(f"Index '{PINECONE_INDEX_NAME}' created successfully.")
        else:
            raise ValueError(f"Pinecone index '{PINECONE_INDEX_NAME}' does not exist.")
            
    if _pc_index is None:
        _pc_index = client.Index(PINECONE_INDEX_NAME)
        
    return _pc_index
