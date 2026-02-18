#!/usr/bin/env python3
"""
Debug script to check Pinecone connection and data structure.
Run this to see why BM25 index is failing to build.
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("Pinecone Diagnostic Script")
print("=" * 80)

# Check environment
api_key = os.getenv("PINECONE_API_KEY")
index_name = os.getenv("PINECONE_INDEX_NAME", "aerostream-docs")

print(f"\n1. Environment Check:")
print(f"   PINECONE_API_KEY: {'✓ Set' if api_key else '✗ Missing'}")
print(f"   PINECONE_INDEX_NAME: {index_name}")

if not api_key:
    print("\n✗ PINECONE_API_KEY not set. Cannot proceed.")
    exit(1)

# Try to import and connect
print(f"\n2. Connecting to Pinecone...")
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=api_key)
    print(f"   ✓ Connected successfully")
except ImportError as e:
    print(f"   ✗ Pinecone not installed: {e}")
    print("   Run: pip install pinecone-client")
    exit(1)
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    exit(1)

# Get index
print(f"\n3. Accessing index '{index_name}'...")
try:
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    print(f"   ✓ Index found")
    print(f"   Total vectors: {stats.total_vector_count}")
    print(f"   Dimension: {stats.dimension}")

    if stats.total_vector_count == 0:
        print(f"\n   ✗ WARNING: Index is EMPTY! No vectors stored.")
        print(f"   Run ingestion first: python scripts/ingest.py")
        exit(1)

except Exception as e:
    print(f"   ✗ Failed: {e}")
    exit(1)

# Check available methods
print(f"\n4. Checking Pinecone API methods...")
has_list_paginated = hasattr(index, 'list_paginated')
has_list = hasattr(index, 'list')
has_query = hasattr(index, 'query')

print(f"   list_paginated(): {'✓ Available' if has_list_paginated else '✗ Not available'}")
print(f"   list(): {'✓ Available' if has_list else '✗ Not available'}")
print(f"   query(): {'✓ Available' if has_query else '✗ Not available'}")

# Try to fetch sample documents
print(f"\n5. Fetching sample documents...")

try:
    # Method 1: Try list_paginated (newer Pinecone)
    if has_list_paginated:
        print(f"   Trying list_paginated()...")
        sample_ids = []
        try:
            for batch in index.list_paginated(limit=5):
                print(f"   Batch type: {type(batch)}")
                print(f"   Batch attributes: {dir(batch)[:10]}...")

                # Try different ways to extract IDs
                if hasattr(batch, 'ids'):
                    batch_ids = batch.ids
                    print(f"   → Has .ids attribute: {batch_ids[:3]}...")
                elif hasattr(batch, '__iter__'):
                    batch_ids = list(batch) if not isinstance(batch, list) else batch
                    print(f"   → Is iterable: {batch_ids[:3]}...")
                else:
                    batch_ids = []
                    print(f"   → Cannot extract IDs from batch")

                sample_ids.extend(batch_ids[:5])
                break  # Just first batch

            if sample_ids:
                print(f"   ✓ Found {len(sample_ids)} IDs via list_paginated()")
            else:
                print(f"   ✗ list_paginated() returned no IDs")

        except Exception as e:
            print(f"   ✗ list_paginated() failed: {e}")
            import traceback
            traceback.print_exc()

    # Method 2: Try query with dummy vector (works on all versions)
    elif has_query:
        print(f"   Trying query() with dummy vector...")
        # Create a dummy query to get some results
        dummy_vector = [0.0] * stats.dimension
        results = index.query(vector=dummy_vector, top_k=5, include_metadata=True)

        sample_ids = [match['id'] for match in results.get('matches', [])]
        if sample_ids:
            print(f"   ✓ Found {len(sample_ids)} IDs via query()")
        else:
            print(f"   ✗ query() returned no results")
    else:
        print(f"   ✗ No suitable method available to list vectors")
        sample_ids = []

    # Fetch and inspect metadata
    if sample_ids:
        print(f"\n6. Inspecting document structure...")
        fetched = index.fetch(ids=sample_ids[:3])

        for vec_id, vec_data in fetched.get('vectors', {}).items():
            print(f"\n   Vector ID: {vec_id}")
            metadata = vec_data.get('metadata', {})
            print(f"   Metadata keys: {list(metadata.keys())}")

            # Check for text field
            if 'text' in metadata:
                text = metadata['text']
                print(f"   ✓ Has 'text' field ({len(text)} chars)")
                print(f"   Sample: {text[:100]}...")
            else:
                print(f"   ✗ No 'text' field in metadata!")
                print(f"   Available: {metadata}")
            break  # Just show first one

    print(f"\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)

except Exception as e:
    print(f"\n   ✗ Error during fetch: {e}")
    import traceback
    traceback.print_exc()
