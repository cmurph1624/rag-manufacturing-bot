import json
import os

def migrate_test_set(filepath):
    print(f"Loading '{filepath}'...")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return

    if not isinstance(data, dict) or "qa_pairs" not in data:
        print("Error: JSON structure not as expected (must have key 'qa_pairs').")
        return

    qa_pairs = data["qa_pairs"]
    print(f"Found {len(qa_pairs)} items. Adding IDs...")

    for index, item in enumerate(qa_pairs):
        # Add 'id' field, 1-indexed
        item["id"] = index + 1
        
        # Move 'id' to the front if possible (aesthetic only, dictionary order is insertion based in modern python)
        # Reconstruct dict to force order: id, category, question, answer, location, etc.
        new_item = {"id": item["id"]}
        for k, v in item.items():
            if k != "id":
                new_item[k] = v
        qa_pairs[index] = new_item

    data["qa_pairs"] = qa_pairs
    
    print(f"Writing updated data back to '{filepath}'...")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        
    print("Migration complete!")

if __name__ == "__main__":
    target_file = "tests/test_set.json"
    migrate_test_set(target_file)
