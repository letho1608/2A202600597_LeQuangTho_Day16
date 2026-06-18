import json
import os
from src.reflexion_lab.schemas import QAExample, ContextChunk


def convert_hotpot_raw(input_path: str, output_path: str, limit: int = 150):
    print(f"Loading raw HotpotQA data from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Converting first {limit} examples...")
    converted = []
    for i, item in enumerate(data[:limit]):
        # Map context
        context_chunks = []
        for title, sentences in item["context"]:
            text = " ".join(sentences)
            context_chunks.append(ContextChunk(title=title, text=text))

        # Create QAExample
        # Note: hotpot uses 'level' while our schema uses 'difficulty'
        example = QAExample(
            qid=item["_id"],
            difficulty=item["level"],
            question=item["question"],
            gold_answer=item["answer"],
            context=context_chunks,
        )
        converted.append(example.model_dump())

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2)

    print(f"Successfully saved {len(converted)} examples to {output_path}")


if __name__ == "__main__":
    raw_path = "data/hotpot_dev_distractor_v1.json"
    processed_path = "data/hotpot_processed.json"
    if os.path.exists(raw_path):
        convert_hotpot_raw(raw_path, processed_path)
    else:
        print(f"Error: {raw_path} not found.")
