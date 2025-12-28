import os
import pypdf
import chromadb
import ollama

def ingest_pdfs():
    # Configuration
    DATA_FOLDER = "data_pdfs"
    DB_PATH = "chroma_db"
    COLLECTION_NAME = "aerostream_docs"
    EMBEDDING_MODEL = "nomic-embed-text"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50

    # Initialize ChromaDB Client
    # This will create the folder 'chroma_db' if it doesn't exist
    print(f"Connecting to ChromaDB at '{DB_PATH}'...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # Create or get collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Check if data folder exists
    if not os.path.exists(DATA_FOLDER):
        print(f"Error: Folder '{DATA_FOLDER}' not found.")
        return

    # List PDF files
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {DATA_FOLDER}.")
        return

    print(f"Found {len(pdf_files)} PDF files. Starting ingestion...")

    for filename in pdf_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        
        try:
            reader = pypdf.PdfReader(file_path)
        except Exception as e:
            print(f"Failed to read {filename}: {e}")
            continue

        file_chunks = []
        file_metadatas = []
        file_ids = []
        file_embeddings = []

        total_chunks_count = 0

        for page_index, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue

            # Sliding window chunking
            start = 0
            text_len = len(text)

            while start < text_len:
                end = min(start + CHUNK_SIZE, text_len)
                chunk_text = text[start:end]

                # Only embed if chunk is not just whitespace
                if chunk_text.strip():
                    try:
                        # Generate embedding using Ollama
                        response = ollama.embeddings(model=EMBEDDING_MODEL, prompt=chunk_text)
                        embedding = response.get('embedding')
                        
                        if embedding:
                            # Create a unique ID for the chunk
                            chunk_id = f"{filename}_p{page_index+1}_{start}"
                            
                            file_chunks.append(chunk_text)
                            file_embeddings.append(embedding)
                            file_ids.append(chunk_id)
                            file_metadatas.append({
                                "source": filename,
                                "page_number": page_index + 1
                            })
                            total_chunks_count += 1
                        else:
                            print(f"Warning: No embedding returned for chunk in {filename} page {page_index+1}")

                    except Exception as e:
                        print(f"Error embedding chunk in {filename}: {e}")
                
                # Break if we reached the end
                if end == text_len:
                    break
                
                # Move window forward, accounting for overlap
                start += (CHUNK_SIZE - CHUNK_OVERLAP)

        # Upsert to Chroma
        if file_chunks:
            collection.upsert(
                ids=file_ids,
                documents=file_chunks,
                embeddings=file_embeddings,
                metadatas=file_metadatas
            )
            print(f"Successfully ingested {filename} - {total_chunks_count} chunks.")
        else:
            print(f"No valid text chunks extracting from {filename}.")

if __name__ == "__main__":
    ingest_pdfs()
