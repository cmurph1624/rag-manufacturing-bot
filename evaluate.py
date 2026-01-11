import json
import ollama
import os
import time
from datetime import datetime
from rag_logic import generate_answer, GENERATION_MODEL
from tqdm import tqdm

# Configuration
TEST_SET_PATH = "test_set.json"
JUDGE_MODEL = "llama3.1"  # Using a larger model (8B) for better reasoning as a judge

def load_test_set(path):
    with open(path, 'r') as f:
        data = json.load(f)
    return data["qa_pairs"]

def evaluate_answer(question, bot_answer, gold_answer):
    """
    Uses an LLM to judge if the bot's answer is correct based on the gold answer.
    """
    prompt = f"""
    You are an impartial judge evaluating a chatbot's response.
    
    Question: {question}
    
    Gold Answer: {gold_answer}
    
    Bot Answer: {bot_answer}
    
    Does the Bot Answer contain the information present in the Gold Answer?
    
    Respond 'INCORRECT' if:
    - The bot says "I don't know", "I can't help", or similar.
    - The bot's answer is missing the key facts from the Gold Answer.
    - The bot's answer contradicts the Gold Answer.
    
    Respond 'CORRECT' if:
    - The bot's answer contains the core facts from the Gold Answer (even if phrased differently).
    
    Respond with ONLY 'CORRECT' or 'INCORRECT'.
    """
    
    try:
        response = ollama.chat(model=JUDGE_MODEL, messages=[
            {'role': 'user', 'content': prompt},
        ])
        judgment = response['message']['content'].strip().upper()
        if "CORRECT" in judgment and "INCORRECT" not in judgment:
            return True
        elif "INCORRECT" in judgment:
            return False
        else:
            # Fallback if the model is chatty
            return "CORRECT" in judgment
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        return False

def main():
    print("Loading test set...")
    qa_pairs = load_test_set(TEST_SET_PATH)
    
    print(f"Loaded {len(qa_pairs)} QA pairs.")
    
    correct_count = 0
    results = []
    
    print("Starting evaluation...")
    for item in tqdm(qa_pairs):
        question = item["question"]
        gold_answer = item["answer"]
        expected_location = item.get("location", "N/A")
        
        # Get bot's answer
        start_time = time.time()
        response_data = generate_answer(question)
        end_time = time.time()
        latency = end_time - start_time
        
        bot_answer = response_data["answer"]
        retrieved_chunks = response_data.get("retrieved_chunks", [])
        model_used = response_data.get("model", "unknown")
        
        # Judge the answer
        is_correct = evaluate_answer(question, bot_answer, gold_answer)
        
        if is_correct:
            correct_count += 1
            
        # Check citation
        citation_match = False
        if expected_location != "N/A" and expected_location in bot_answer:
            citation_match = True
        
        results.append({
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "gold_answer": gold_answer,
            "expected_location": expected_location,
            "bot_answer": bot_answer,
            "retrieved_chunks": retrieved_chunks,
            "model_used": model_used,
            "latency_seconds": latency,
            "is_correct": is_correct,
            "citation_match": citation_match
        })
        
    accuracy = (correct_count / len(qa_pairs)) * 100
    print(f"\nEvaluation Complete!")
    print(f"Accuracy: {accuracy:.2f}% ({correct_count}/{len(qa_pairs)})")
    
    # Save detailed results with timestamp
    output_dir = "evaluation_results"
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"evaluation_results_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # Create final output structure
    final_output = {
        "metadata": {
            "model": GENERATION_MODEL,
            "execution_timestamp": timestamp,
            "accuracy": f"{accuracy:.2f}%",
            "total_questions": len(qa_pairs),
            "correct_answers": correct_count
        },
        "results": results
    }

    with open(filepath, "w") as f:
        json.dump(final_output, f, indent=4)
    print(f"Detailed results saved to '{filepath}'")

if __name__ == "__main__":
    main()
