# TrueLens Migration Plan - Step-by-Step Guide

## Overview
This plan migrates the custom evaluation system to TrueLens in discrete, manageable steps. Each step is designed to be executed in a separate conversation to manage token usage.

---

## ✅ Pre-Migration Checklist
- [x] TrueLens packages installed (v2.6.0)
- [x] Test set available (`test_set.json` - 50 QA pairs)
- [x] Current system functional
- [ ] ChromaDB compatibility issue resolved
- [ ] TrueLens configuration created
- [ ] RAG pipeline instrumented
- [ ] New evaluator created
- [ ] Dashboard tested
- [ ] Migration complete

---

## 📋 Step-by-Step Execution Plan

---

### **STEP 1: Fix ChromaDB Compatibility Issue**
**Estimated Time:** 10-15 minutes
**Token Usage:** Low (~10k tokens)

#### Prompt to Use:
```
I'm working on the TrueLens migration for my RAG bot. We need to fix the ChromaDB compatibility issue first.

The error is:
"cannot import name 'Space' from 'chromadb.api.types'"

Current versions:
- chromadb: 0.5.23
- langchain-chroma: 0.1.4
- chroma-hnswlib: 0.7.6

Please:
1. Diagnose the version conflict
2. Update requirements.txt with compatible versions
3. Reinstall packages
4. Test that rag_logic.py imports successfully
5. Test that a simple query works with generate_answer()

Do NOT start any TrueLens work yet - just fix the ChromaDB issue.
```

#### Success Criteria:
- [ ] No import errors when running `python -c "from rag_logic import generate_answer"`
- [ ] ChromaDB versions compatible
- [ ] RAG pipeline functional

#### Files Modified:
- `requirements.txt` (ChromaDB versions updated)

---

### **STEP 2: Create TrueLens Configuration Module**
**Estimated Time:** 30-40 minutes
**Token Usage:** Medium (~30k tokens)

#### Prompt to Use:
```
Now let's create the TrueLens configuration module. This is Step 2 of the migration plan in TRULENS_MIGRATION_PLAN.md.

Create a new file `trulens_config.py` that:

1. Initializes TrueLens session and database
2. Configures Ollama provider with llama3.1 as the evaluation model
3. Makes the evaluation model easy to switch via environment variable (EVALUATION_MODEL)
4. Defines 5 feedback functions:
   - Answer Relevance (question → answer quality)
   - Context Relevance (question → retrieved chunks quality)
   - Groundedness (answer supported by context)
   - Custom: Citation matching (fuzzy match - e.g., "SOP-01" matches "SOP-01_Rotor_Arm")
   - Custom: Latency tracking

5. Add helper functions to:
   - Initialize TrueLens session
   - Get configured feedback functions
   - Reset session if needed

Requirements:
- Use trulens.providers.langchain for Ollama integration
- Default evaluation model: llama3.1
- Make it easy to switch to OpenAI/Bedrock later
- Add comprehensive docstrings
- Include error handling

Reference:
- Look at test_set.json for citation format (has "location" field)
- Fuzzy matching should handle partial matches (e.g., filename prefixes)
```

#### Success Criteria:
- [ ] `trulens_config.py` created
- [ ] Can import and initialize TrueLens
- [ ] Feedback functions defined
- [ ] Evaluation model configurable via env var

#### Files Created:
- `trulens_config.py`

#### Files Modified:
- `.env.example` (add EVALUATION_MODEL)

---

### **STEP 3: Add TrueLens Instrumentation to RAG Pipeline**
**Estimated Time:** 45-60 minutes
**Token Usage:** Medium-High (~40k tokens)

#### Prompt to Use:
```
Step 3 of the TrueLens migration: Instrument the RAG pipeline with TrueLens.

Modify `rag_logic.py` to add TrueLens instrumentation:

1. Import TrueLens decorators and TruChain wrapper
2. Create a wrapped version of generate_answer() that:
   - Instruments the LangChain retrieval chain with TrueLens
   - Tracks input queries, retrieved contexts, generated answers
   - Records model used, retrieval strategy, latencies
   - Maintains backward compatibility (existing return format unchanged)

3. Add optional parameter to enable/disable TrueLens tracking:
   - Default: disabled (for normal bot usage)
   - Enable only during evaluation runs

4. Create helper function to get instrumented RAG chain

Requirements:
- Use TruChain to wrap the LangChain rag_chain
- Preserve exact return format: {"answer": str, "retrieved_chunks": list, "model": str, "retrieval_type": str}
- Add app_id parameter to track different evaluation runs
- No breaking changes to existing generate_answer() interface
- Add comprehensive docstrings

Test:
- After changes, verify that generate_answer() still works without TrueLens enabled
- Verify that with TrueLens enabled, it records to TrueLens database
```

#### Success Criteria:
- [ ] `rag_logic.py` modified with TrueLens instrumentation
- [ ] Backward compatible (existing bot functionality unchanged)
- [ ] TrueLens recording works when enabled
- [ ] No breaking changes

#### Files Modified:
- `rag_logic.py`

---

### **STEP 4: Create New TrueLens Evaluation Runner**
**Estimated Time:** 60-75 minutes
**Token Usage:** High (~50k tokens)

#### Prompt to Use:
```
Step 4 of the TrueLens migration: Create the new evaluation runner with TrueLens.

Create a new file `evaluate_trulens.py` that:

1. Loads test set from test_set.json (50 QA pairs)
2. Initializes TrueLens with feedback functions from trulens_config.py
3. Runs evaluation loop:
   - For each question:
     * Call instrumented generate_answer() with TrueLens enabled
     * Track metadata: category, expected_location, gold_answer
     * Measure latency
   - Run TrueLens feedback functions on all results
   - Track retrieval strategy and model used

4. Add metadata tracking:
   - Test category (Work_Instructions, Tribal_Knowledge, Adversarial)
   - Retrieval strategy (semantic, lexical, semantic-rerank)
   - Model name (llama3.2, mistral, etc.)
   - Ingestion config ID (maintain compatibility with old system)

5. Command-line arguments:
   - --model: LLM model to use (default: from env)
   - --retrieval: Retrieval strategy (default: from env)
   - --limit: Limit number of questions for testing (default: all 50)
   - --app-id: Custom app identifier for TrueLens (default: auto-generated)

6. Print summary statistics:
   - Total questions evaluated
   - Average scores for each feedback function
   - Average latency
   - Citation match rate
   - Breakdown by category

Requirements:
- Use tqdm for progress bar (like old evaluate.py)
- Handle errors gracefully (continue on individual failures)
- Log to console with timestamps
- Store all results in TrueLens database
- Add docstrings and comments

Reference old evaluate.py for:
- Progress tracking style
- Error handling patterns
- Console output format
```

#### Success Criteria:
- [ ] `evaluate_trulens.py` created
- [ ] Can run evaluation on test subset (--limit 5)
- [ ] Results stored in TrueLens database
- [ ] Summary statistics printed
- [ ] Metadata tracking works

#### Files Created:
- `evaluate_trulens.py`

---

### **STEP 5: Test TrueLens Dashboard & Small-Scale Validation**
**Estimated Time:** 20-30 minutes
**Token Usage:** Low-Medium (~20k tokens)

#### Prompt to Use:
```
Step 5 of the TrueLens migration: Test the dashboard and validate with a small evaluation run.

Tasks:
1. Run a small-scale evaluation (5 questions) using evaluate_trulens.py:
   - python evaluate_trulens.py --limit 5

2. Launch TrueLens dashboard and verify:
   - Dashboard starts successfully
   - Evaluation results visible
   - Feedback scores displayed
   - Can drill down into individual QA pairs
   - Metadata (category, retrieval strategy, model) visible

3. Create a simple script/command to launch the dashboard:
   - Add to README or create start_dashboard.sh

4. Document how to:
   - Run evaluations
   - Access dashboard
   - Interpret feedback scores
   - Filter by metadata (category, model, retrieval strategy)

5. Compare one result manually with old system as sanity check:
   - Pick one question
   - Verify answer looks reasonable
   - Check that metadata is correct

Do NOT run full 50-question evaluation yet - save that for Step 6.
```

#### Success Criteria:
- [ ] Dashboard accessible and showing results
- [ ] 5-question test run successful
- [ ] Feedback scores visible and reasonable
- [ ] Metadata tracking working
- [ ] Documentation updated

#### Files Modified:
- `README.md` (add TrueLens usage instructions)

#### Files Created:
- `start_dashboard.sh` (optional helper script)

---

### **STEP 6: Run Full Evaluation & Performance Comparison**
**Estimated Time:** 30-40 minutes
**Token Usage:** Medium (~30k tokens)

#### Prompt to Use:
```
Step 6 of the TrueLens migration: Run the full evaluation and compare with old system.

Tasks:
1. Run full evaluation with all 50 questions:
   - Test with default retrieval strategy (semantic)
   - Test with semantic-rerank strategy
   - Document any errors or issues

2. Analyze results in TrueLens dashboard:
   - Overall accuracy/feedback scores
   - Performance by category (Work Instructions vs Tribal Knowledge vs Adversarial)
   - Performance by retrieval strategy
   - Latency statistics

3. Compare with old system (evaluation_history.db):
   - Load one recent run from old database
   - Compare accuracy/performance metrics
   - Document any significant differences
   - Explain differences (TrueLens uses multiple metrics vs single LLM judge)

4. Create a summary report:
   - Document migration success
   - Note any discrepancies
   - Provide interpretation guide for TrueLens metrics
   - Recommendations for thresholds (what's a "good" score?)

Do NOT archive old files yet - keep both systems for comparison.
```

#### Success Criteria:
- [ ] Full 50-question evaluation completed
- [ ] Results visible in TrueLens dashboard
- [ ] Comparison with old system documented
- [ ] Summary report created

#### Files Created:
- `TRULENS_EVALUATION_SUMMARY.md` (comparison report)

---

### **STEP 7: Create Optional Custom Dashboard Wrapper**
**Estimated Time:** 45-60 minutes
**Token Usage:** Medium-High (~40k tokens)

#### Prompt to Use:
```
Step 7 of the TrueLens migration: Create optional custom dashboard wrapper (if needed).

Review the TrueLens dashboard and determine if we need custom views:

1. Assess built-in TrueLens dashboard features:
   - Does it support filtering by test category?
   - Can we compare ingestion configs?
   - Can we view performance trends over time?
   - Can we export results?

2. IF needed, create dashboard_trulens.py with:
   - Streamlit wrapper around TrueLens data
   - Custom views for:
     * Category breakdown (Work Instructions, Tribal Knowledge, Adversarial)
     * Ingestion config correlation
     * Model/strategy comparison matrix
     * Historical trends
   - Export functionality (CSV/JSON)

3. If NOT needed:
   - Document how to use built-in TrueLens dashboard for these use cases
   - Create quick-reference guide
   - Skip custom dashboard creation

Determine: Do we need a custom dashboard, or is TrueLens built-in sufficient?
If sufficient, just document usage patterns.
```

#### Success Criteria:
- [ ] Assessment of TrueLens dashboard completed
- [ ] Custom dashboard created (if needed) OR
- [ ] Usage guide for built-in dashboard created (if sufficient)

#### Files Created (conditional):
- `dashboard_trulens.py` (only if custom views needed)
- `TRULENS_DASHBOARD_GUIDE.md` (usage documentation)

---

### **STEP 8: Migration Cleanup & Documentation**
**Estimated Time:** 20-30 minutes
**Token Usage:** Low-Medium (~20k tokens)

#### Prompt to Use:
```
Step 8 of the TrueLens migration: Final cleanup and documentation.

Tasks:
1. Archive old evaluation system:
   - Create archive/ directory
   - Move evaluate.py → archive/evaluate_old.py
   - Move dashboard.py → archive/dashboard_old.py
   - Move evaluation_history.db → archive/evaluation_history_old.db
   - Move evaluation_results/ → archive/evaluation_results_old/
   - Add README in archive/ explaining what these files are

2. Update project documentation:
   - Update main README.md with:
     * New evaluation commands (evaluate_trulens.py)
     * Dashboard access instructions
     * Feedback function descriptions
     * Migration notes
   - Update .env.example with TrueLens variables
   - Create TRULENS_QUICKSTART.md guide

3. Add helper scripts:
   - run_evaluation.sh (wrapper for evaluate_trulens.py)
   - start_dashboard.sh (launches TrueLens dashboard)

4. Final verification:
   - Test evaluation end-to-end
   - Test dashboard access
   - Verify documentation accuracy
   - Check that old system is safely archived

5. Create migration completion checklist:
   - What was replaced
   - What was preserved
   - How to use new system
   - How to access old results (if needed)
```

#### Success Criteria:
- [ ] Old files archived in archive/ directory
- [ ] Documentation fully updated
- [ ] Helper scripts created
- [ ] End-to-end test successful
- [ ] Migration complete!

#### Files Modified:
- `README.md`
- `.env.example`

#### Files Created:
- `archive/README.md`
- `TRULENS_QUICKSTART.md`
- `run_evaluation.sh`
- `start_dashboard.sh`

#### Directories Created:
- `archive/` (with old evaluation files)

---

## 🎯 Execution Checklist

Use this to track your progress:

- [ ] Step 1: Fix ChromaDB Compatibility ✅
- [ ] Step 2: Create TrueLens Configuration
- [ ] Step 3: Instrument RAG Pipeline
- [ ] Step 4: Create Evaluation Runner
- [ ] Step 5: Test Dashboard & Validate
- [ ] Step 6: Run Full Evaluation
- [ ] Step 7: Custom Dashboard (if needed)
- [ ] Step 8: Cleanup & Documentation

---

## 📊 Expected Outcomes

### After Completion:
1. **New Files:**
   - `trulens_config.py` - TrueLens setup
   - `evaluate_trulens.py` - New evaluator
   - `TRULENS_QUICKSTART.md` - Quick reference
   - `dashboard_trulens.py` (optional)
   - Helper scripts

2. **Modified Files:**
   - `rag_logic.py` - TrueLens instrumentation
   - `requirements.txt` - Fixed ChromaDB versions
   - `README.md` - Updated instructions
   - `.env.example` - New variables

3. **Archived Files:**
   - `archive/evaluate_old.py`
   - `archive/dashboard_old.py`
   - `archive/evaluation_history_old.db`
   - `archive/evaluation_results_old/`

4. **Preserved Files:**
   - `test_set.json` ✅
   - `retrieval/factory.py` ✅
   - `llm/factory.py` ✅
   - All RAG pipeline code ✅

---

## 💡 Tips for Execution

1. **Save Progress:** After each step, commit your changes to git
2. **Test Incrementally:** Don't skip the validation steps
3. **Token Management:** Each step is designed for a fresh conversation
4. **Error Handling:** If a step fails, resolve issues before proceeding
5. **Documentation:** Keep notes on any deviations from the plan

---

## 🆘 Troubleshooting

### If a step fails:
1. Review error messages
2. Check that previous steps completed successfully
3. Verify environment variables are set
4. Check TrueLens and ChromaDB versions
5. Consult TrueLens docs: https://www.trulens.org/

### Common Issues:
- **Import errors:** Check virtual environment activation
- **ChromaDB errors:** Verify version compatibility (Step 1)
- **TrueLens not recording:** Check session initialization
- **Dashboard not loading:** Verify database path and permissions

---

## 📚 References

- TrueLens Docs: https://www.trulens.org/
- TrueLens LangChain Integration: https://www.trulens.org/trulens_eval/tracking/instrumentation/langchain/
- TrueLens Feedback Functions: https://www.trulens.org/trulens_eval/evaluation/feedback_functions/
- Migration Guide: https://www.trulens.org/component_guides/other/trulens_eval_migration/

---

**Ready to Start?** Begin with Step 1 in your next conversation!
