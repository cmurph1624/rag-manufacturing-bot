#!/usr/bin/env python3
"""
Quick test script to verify BM25 lexical search is working.
"""
import os
import sys

# Set retrieval to lexical
os.environ['RETRIEVAL_STRATEGY'] = 'lexical'
os.environ['VECTOR_DB'] = 'pinecone'

from src.retrieval.factory import RetrievalFactory

print("=" * 80)
print("Testing BM25 Lexical Search")
print("=" * 80)

# Create lexical retriever
print("\n1. Creating lexical retriever...")
retriever = RetrievalFactory.get_strategy("lexical")
print(f"✓ Created: {type(retriever)}")

# Test queries
test_queries = [
    "Loctite type for rotor arm",
    "3mm Hex Key tool",
    "Solid Red LED E-500",
    "maximum temperature charging"
]

for query in test_queries:
    print(f"\n2. Testing query: '{query}'")
    print("-" * 80)

    try:
        results = retriever.invoke(query)
        print(f"✓ Found {len(results)} results")

        if results:
            for i, doc in enumerate(results[:3]):  # Show first 3
                print(f"\n  Result {i+1}:")
                content = doc.page_content[:150].replace('\n', ' ')
                print(f"    Content: {content}...")
                print(f"    Source: {doc.metadata.get('source', 'Unknown')}")
        else:
            print("  ✗ No results found (BM25 may need debugging)")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
