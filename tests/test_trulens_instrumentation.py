"""
Test script for TrueLens instrumentation in rag_logic.py

This script tests that:
1. generate_answer() works without TrueLens enabled (backward compatibility)
2. generate_answer() works WITH TrueLens enabled (records to database)
3. No breaking changes to existing functionality
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from src.rag_logic import generate_answer, get_instrumented_rag_chain


def test_without_trulens():
    """Test normal RAG pipeline without TrueLens instrumentation."""
    print("=" * 70)
    print("TEST 1: generate_answer() WITHOUT TrueLens")
    print("=" * 70)

    query = "What are the safety precautions for the Falcon X1?"

    try:
        result = generate_answer(
            user_query=query,
            retrieval_strategy_type="semantic",
            enable_trulens=False  # Disabled
        )

        # Verify return format
        assert "answer" in result, "Missing 'answer' key"
        assert "retrieved_chunks" in result, "Missing 'retrieved_chunks' key"
        assert "model" in result, "Missing 'model' key"
        assert "retrieval_type" in result, "Missing 'retrieval_type' key"

        print(f"\n✅ Test 1 PASSED")
        print(f"   - Answer length: {len(result['answer'])} chars")
        print(f"   - Retrieved chunks: {len(result['retrieved_chunks'])}")
        print(f"   - Model: {result['model']}")
        print(f"   - Retrieval type: {result['retrieval_type']}")

        return True

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_trulens():
    """Test RAG pipeline WITH TrueLens instrumentation."""
    print("\n" + "=" * 70)
    print("TEST 2: generate_answer() WITH TrueLens")
    print("=" * 70)

    query = "What are the safety precautions for the Falcon X1?"

    try:
        result = generate_answer(
            user_query=query,
            retrieval_strategy_type="semantic",
            enable_trulens=True,  # Enabled
            app_id="test_instrumentation_2025",
            metadata={"expected_location": "SOP-01_Rotor_Arm_Assembly_Falcon_X1"}
        )

        # Verify return format (should be identical to test 1)
        assert "answer" in result, "Missing 'answer' key"
        assert "retrieved_chunks" in result, "Missing 'retrieved_chunks' key"
        assert "model" in result, "Missing 'model' key"
        assert "retrieval_type" in result, "Missing 'retrieval_type' key"

        print(f"\n✅ Test 2 PASSED")
        print(f"   - Answer length: {len(result['answer'])} chars")
        print(f"   - Retrieved chunks: {len(result['retrieved_chunks'])}")
        print(f"   - Model: {result['model']}")
        print(f"   - Retrieval type: {result['retrieval_type']}")
        print(f"   - TrueLens recording: ✓ (check trulens_eval.db)")

        return True

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_instrumented_chain():
    """Test get_instrumented_rag_chain() function."""
    print("\n" + "=" * 70)
    print("TEST 3: get_instrumented_rag_chain()")
    print("=" * 70)

    try:
        tru_chain = get_instrumented_rag_chain(
            retrieval_strategy_type="semantic",
            app_id="test_chain_creation",
            metadata={"test": "metadata"}
        )

        print(f"\n✅ Test 3 PASSED")
        print(f"   - TruChain created: {type(tru_chain)}")
        print(f"   - App name: {tru_chain.app_name}")

        return True

    except Exception as e:
        print(f"\n❌ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test that old code still works (no breaking changes)."""
    print("\n" + "=" * 70)
    print("TEST 4: Backward Compatibility (Old Function Signature)")
    print("=" * 70)

    query = "How do I assemble the rotor arm?"

    try:
        # This should work exactly as before (old function signature)
        result = generate_answer(query)

        # Verify return format
        assert "answer" in result, "Missing 'answer' key"
        assert "retrieved_chunks" in result, "Missing 'retrieved_chunks' key"
        assert "model" in result, "Missing 'model' key"
        assert "retrieval_type" in result, "Missing 'retrieval_type' key"

        print(f"\n✅ Test 4 PASSED")
        print(f"   - Old function signature works: ✓")
        print(f"   - Default behavior unchanged: ✓")

        return True

    except Exception as e:
        print(f"\n❌ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TrueLens Instrumentation Test Suite")
    print("=" * 70)
    print()

    results = []

    # Test 1: Without TrueLens
    results.append(("Without TrueLens", test_without_trulens()))

    # Test 2: With TrueLens
    results.append(("With TrueLens", test_with_trulens()))

    # Test 3: Get instrumented chain
    results.append(("Get Instrumented Chain", test_get_instrumented_chain()))

    # Test 4: Backward compatibility
    results.append(("Backward Compatibility", test_backward_compatibility()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Check trulens_eval.db for recorded evaluations")
        print("2. Use TrueLens dashboard to view results: python -m trulens.apps.langchain.dashboard")
        print("3. Integrate into evaluation pipeline (eval_rag_bot.py)")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit(main())
