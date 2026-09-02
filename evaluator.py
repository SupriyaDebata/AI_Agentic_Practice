"""evaluator.py — Batch evaluation: 15 questions, accuracy by source type, JSON report."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from chat import answer_question, check_ollama
from retriever import list_collections

TEST_FILE  = Path("test_questions.json")
REPORT_DIR = Path("reports")


def load_test_questions() -> list[dict]:
    if not TEST_FILE.exists():
        raise FileNotFoundError(f"{TEST_FILE} not found. Run from the project root.")
    return json.loads(TEST_FILE.read_text(encoding="utf-8"))["questions"]


def _score_one(item: dict, collection_name: str) -> dict:
    t0 = time.time()
    try:
        result  = answer_question(item["question"], collection_name=collection_name, n_results=5)
        elapsed = time.time() - t0

        keywords    = item.get("expected_keywords", [])
        answer_low  = result["answer"].lower()

        if result["is_refusal"]:
            score = 0.0
        elif not keywords:
            score = 1.0
        else:
            matched = sum(1 for kw in keywords if kw.lower() in answer_low)
            score   = matched / len(keywords)

        return {
            "id":                item["id"],
            "source_type":       item["source_type"],
            "question":          item["question"],
            "answer":            result["answer"][:400],
            "is_refusal":        result["is_refusal"],
            "citations":         result["citations"],
            "expected_keywords": keywords,
            "score":             round(score, 2),
            "passed":            score >= 0.5,
            "elapsed_s":         round(elapsed, 2),
            "error":             None,
        }
    except Exception as exc:
        return {
            "id":                item["id"],
            "source_type":       item["source_type"],
            "question":          item["question"],
            "answer":            "",
            "is_refusal":        False,
            "citations":         [],
            "expected_keywords": item.get("expected_keywords", []),
            "score":             0.0,
            "passed":            False,
            "elapsed_s":         round(time.time() - t0, 2),
            "error":             str(exc),
        }


def score_by_type(results: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list] = {}
    for r in results:
        grouped.setdefault(r["source_type"], []).append(r)

    return {
        stype: {
            "total":    len(items),
            "passed":   sum(1 for i in items if i["passed"]),
            "accuracy": round(sum(1 for i in items if i["passed"]) / len(items), 2),
            "avg_score": round(sum(i["score"] for i in items) / len(items), 2),
            "avg_time_s": round(sum(i["elapsed_s"] for i in items) / len(items), 2),
        }
        for stype, items in grouped.items()
    }


def _print_report(results: list[dict], by_type: dict) -> None:
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    print("\n" + "=" * 64)
    print("  ChatOnDocument — Evaluation Report")
    print("=" * 64)
    print(f"  Overall: {passed}/{total} passed  ({passed/total*100:.0f}%)")
    print()
    print(f"  {'Type':<22} {'Total':>5} {'Pass':>5} {'Acc':>6} {'AvgScr':>7} {'AvgT':>6}")
    print("  " + "-" * 52)
    for stype, s in sorted(by_type.items()):
        print(
            f"  {stype:<22} {s['total']:>5} {s['passed']:>5} "
            f"{s['accuracy']*100:>5.0f}% {s['avg_score']:>7.2f} {s['avg_time_s']:>5.1f}s"
        )
    print()
    print(f"  {'ID':<6} {'Type':<22} {'Pass':>5} {'Score':>6} {'Time':>6}")
    print("  " + "-" * 48)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"  {r['id']:<6} {r['source_type']:<22} {status:>5} "
            f"{r['score']:>6.2f} {r['elapsed_s']:>5.1f}s"
        )
        if r.get("error"):
            print(f"         ERROR: {r['error']}")
    print("=" * 64)


def run_evaluation(collection_name: str = "documents") -> None:
    if not check_ollama():
        print("ERROR: Ollama is not running. Start it with: ollama serve")
        return

    if collection_name not in list_collections():
        print(f"ERROR: Collection '{collection_name}' not found. Ingest documents first.")
        return

    questions = load_test_questions()
    print(f"\nRunning {len(questions)} questions against '{collection_name}'...")
    print("-" * 56)

    results: list[dict] = []
    for i, q in enumerate(questions, 1):
        print(f"[{i:02d}/{len(questions)}] {q['source_type']:<15} {q['question'][:50]}...")
        r = _score_one(q, collection_name)
        results.append(r)
        print(f"         → {'PASS' if r['passed'] else 'FAIL'} score={r['score']} {r['elapsed_s']}s")

    by_type = score_by_type(results)
    _print_report(results, by_type)

    REPORT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report = REPORT_DIR / f"eval_{stamp}.json"
    total = len(results)
    report.write_text(
        json.dumps({
            "timestamp":        datetime.now().isoformat(),
            "collection":       collection_name,
            "overall_accuracy": round(sum(1 for r in results if r["passed"]) / total, 2),
            "total":            total,
            "passed":           sum(1 for r in results if r["passed"]),
            "by_type":          by_type,
            "questions":        results,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"\n  Report saved: {report}")


if __name__ == "__main__":
    col = sys.argv[1] if len(sys.argv) > 1 else "documents"
    run_evaluation(col)
