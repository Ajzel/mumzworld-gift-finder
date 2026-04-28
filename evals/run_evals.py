# evals/run_evals.py
import json
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.gift_finder import run


def load_cases():
    path = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate(case: dict) -> dict:
    result = {
        "id": case["id"],
        "description": case["description"],
        "query": case["query"],
        "passed": False,
        "failures": [],
        "recs": 0,
        "no_match_reason": None,
    }

    try:
        response = run(case["query"])
    except Exception as e:
        result["failures"].append(f"Pipeline error: {e}")
        return result

    recs = response.recommendations
    result["recs"] = len(recs)
    result["no_match_reason"] = response.no_match_reason

    expect_match = case.get("expect_match", None)

    if expect_match is True and len(recs) == 0:
        result["failures"].append("Expected recommendations but got none")
    if expect_match is False and len(recs) > 0:
        result["failures"].append(f"Expected no match but got {len(recs)} recommendations")

    if "expect_language" in case:
        if response.intent.query_language != case["expect_language"]:
            result["failures"].append(
                f"Language: expected {case['expect_language']}, "
                f"got {response.intent.query_language}"
            )

    if "expect_max_price" in case:
        for rec in recs:
            if rec.price_aed > case["expect_max_price"]:
                result["failures"].append(
                    f"Budget breach: {rec.name_en} costs {rec.price_aed} AED "
                    f"(max {case['expect_max_price']})"
                )

    if case.get("expect_is_for_mom"):
        if not response.intent.is_for_mom:
            result["failures"].append("Expected is_for_mom=True but got False")

    for rec in recs:
        if not rec.reason_ar or len(rec.reason_ar.strip()) < 10:
            result["failures"].append(f"Arabic reason too short for {rec.name_en}")

    result["passed"] = len(result["failures"]) == 0
    return result


def main():
    cases = load_cases()
    results = []
    print(f"\nRunning {len(cases)} eval cases...\n")

    for i, case in enumerate(cases):
        print(f"[{i+1}/{len(cases)}] {case['id']}: {case['description'][:50]}...")
        r = evaluate(case)
        results.append(r)
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"  {status} | Recs: {r['recs']}", end="")
        if r["failures"]:
            print(f" | Issues: {'; '.join(r['failures'])}")
        else:
            print()
        time.sleep(5)  # avoid per-minute rate limit

    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"\n{'='*50}")
    print(f"RESULTS: {passed}/{total} passed ({int(passed/total*100)}%)")
    print(f"{'='*50}\n")

    out_path = os.path.join(os.path.dirname(__file__), "eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Full results saved to {out_path}")


if __name__ == "__main__":
    main()