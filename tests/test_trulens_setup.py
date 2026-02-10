"""
Standalone test script for TrueLens configuration.
Tests that trulens_config can be imported and initialized correctly.
"""

import sys

print("=" * 60)
print("TrueLens Configuration Test")
print("=" * 60)

# Test 1: Import core TrueLens components
print("\n[Test 1] Importing TrueLens core components...")
try:
    from trulens.core import Feedback, TruSession
    from trulens.providers.langchain import Langchain
    from trulens.apps.langchain.tru_chain import TruChain
    print("✅ All TrueLens core imports successful")
except ImportError as e:
    print(f"❌ TrueLens import failed: {e}")
    sys.exit(1)

# Test 2: Import trulens_config module
print("\n[Test 2] Importing trulens_config module...")
try:
    from trulens_config import TrueLensConfig, initialize_trulens
    print("✅ trulens_config imported successfully")
except ImportError as e:
    print(f"❌ trulens_config import failed: {e}")
    sys.exit(1)

# Test 3: Create TrueLensConfig instance
print("\n[Test 3] Creating TrueLensConfig instance...")
try:
    config = TrueLensConfig(
        database_path="/tmp/test_trulens.db",
        evaluation_model="llama3.1"
    )
    print(f"✅ TrueLensConfig created")
    print(f"   - Database: {config.database_path}")
    print(f"   - Evaluation model: {config.evaluation_model}")
except Exception as e:
    print(f"❌ TrueLensConfig creation failed: {e}")
    sys.exit(1)

# Test 4: Initialize session
print("\n[Test 4] Initializing TrueLens session...")
try:
    session = config.initialize_session(reset=False)
    print(f"✅ Session initialized successfully")
except Exception as e:
    print(f"❌ Session initialization failed: {e}")
    sys.exit(1)

# Test 5: Get provider
print("\n[Test 5] Initializing evaluation provider...")
try:
    provider = config.get_provider()
    print(f"✅ Provider initialized successfully")
except Exception as e:
    print(f"❌ Provider initialization failed: {e}")
    sys.exit(1)

# Test 6: Get feedback functions
print("\n[Test 6] Getting feedback functions...")
try:
    feedbacks = config.get_feedback_functions()
    print(f"✅ Got {len(feedbacks)} feedback functions:")
    for fb in feedbacks:
        print(f"   - {fb.name}")
except Exception as e:
    print(f"❌ Feedback function retrieval failed: {e}")
    sys.exit(1)

# Test 7: Test initialize_trulens helper
print("\n[Test 7] Testing initialize_trulens helper...")
try:
    session2, feedbacks2 = initialize_trulens(
        database_path="/tmp/test_trulens2.db",
        evaluation_model="llama3.1"
    )
    print(f"✅ Helper function works: {len(feedbacks2)} feedbacks")
except Exception as e:
    print(f"❌ Helper function failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("=" * 60)
print("\nNext steps:")
print("1. Instrument RAG pipeline with TrueLens (Step 3)")
print("2. Create evaluation runner (Step 4)")
print("3. Test with small dataset (Step 5)")
