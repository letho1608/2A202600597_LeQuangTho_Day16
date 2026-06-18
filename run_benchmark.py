from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
from src.reflexion_lab import llm_runtime

app = typer.Typer(add_completion=False)

@app.command()
def main(

    dataset: str = "data/hotpot_mini.json",
    out_dir: str = "outputs/sample_run",
    reflexion_attempts: int = 3,
    use_llm: bool = typer.Option(
        False, "--use-llm", help="Use real LLM instead of mock runtime"
    ),
    provider: str = typer.Option(
        "gemini", "--provider", help="LLM provider: gemini, openai, anthropic"
    ),
    model: str = typer.Option(None, "--model", help="Specific model name (optional)"),
) -> None:
    if use_llm:
        llm_runtime.init_runtime(provider, model)

    examples = load_dataset(dataset)
    react = ReActAgent(use_llm=use_llm)
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts, use_llm=use_llm)

    print(f"Starting benchmark (use_llm={use_llm})...")

    react_records = []
    for example in examples:
        print(f"Running ReAct for {example.qid}...")
        react_records.append(react.run(example))

    reflexion_records = []
    for example in examples:
        print(f"Running Reflexion for {example.qid}...")
        reflexion_records.append(reflexion.run(example))

    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)

    mode = "llm" if use_llm else "mock"
    report = build_report(all_records, dataset_name=Path(dataset).name, mode=mode)
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))


if __name__ == "__main__":
    app()
