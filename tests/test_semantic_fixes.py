
import sys
import os
import re

# Mocking the class structure to avoid importing full dependency chain if not needed for split_sentences
class SemanticIngestionStrategy:
    def split_sentences(self, text):
        # NEW Improved regex logic (Corrected)
        sentences = re.split(r'(?<!\d\.)(?<=[.?!])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

def test_split_sentences():
    strategy = SemanticIngestionStrategy()
    
    # 1. Numbered lists
    text_list = "1. First item. 2. Second item."
    sentences = strategy.split_sentences(text_list)
    print(f"Input: '{text_list}'")
    print(f"Output: {sentences}")
    # Expected bad: ['1.', 'First item.', '2.', 'Second item.']
    
    # 2. Measurements
    text_measurement = "Torque to 2.5 Nm."
    sentences = strategy.split_sentences(text_measurement)
    print(f"Input: '{text_measurement}'")
    print(f"Output: {sentences}")
    # Expected bad? Actually 2.5 might not split if no space after dot.
    # User said: "2.5 Nm" -> "2." and "5 Nm" if space? No space in "2.5".
    # User might mean "at a temp of 200. 5 minutes later."? 
    # Or maybe "Version 2.0. Feature X." -> "Version 2.", "0.", "Feature X."?
    
    # 3. Bullet points
    text_bullets = "Required Tools:\n● Hammer\n● Saw"
    sentences = strategy.split_sentences(text_bullets)
    print(f"Input: '{text_bullets}'")
    print(f"Output: {sentences}")
    
    # 4. Part numbers
    text_part = "Use Part #RA-400."
    sentences = strategy.split_sentences(text_part)
    print(f"Input: '{text_part}'")
    print(f"Output: {sentences}")

if __name__ == "__main__":
    print("Testing existing split_sentences logic:")
    test_split_sentences()
