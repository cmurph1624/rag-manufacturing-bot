import argparse
from ingest.factory import IngestionFactory
from ingest.base import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP

def main():
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB.")
    
    # Generic Args
    parser.add_argument("--reset", action="store_true", help="Reset the database before ingestion")
    parser.add_argument("--strategy", type=str, default="standard", help="Ingestion strategy to use (default: standard)")
    
    # Standard Strategy Args
    parser.add_argument("--chunk_size", type=int, default=DEFAULT_CHUNK_SIZE, help="Size of text chunks (standard)")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="Overlap between chunks (standard)")
    
    # Semantic Strategy Args
    parser.add_argument("--semantic_threshold", type=float, default=0.4, help="Cosine distance threshold for semantic chunking (0.0-1.0)")

    args = parser.parse_args()
    
    print(f"Initializing Ingestion with Strategy: {args.strategy}", flush=True)

    try:
        strategy = IngestionFactory.get_strategy(args.strategy)
        
        # Pass all args as kwargs (strategies will pick what they need)
        strategy.ingest(
            reset=args.reset,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            semantic_threshold=args.semantic_threshold
        )
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)

if __name__ == "__main__":
    main()