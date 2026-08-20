# Evaluates judge_node: given the user's keyword criteria and a candidate blob, does
# the LLM judge return EXACTLY the expected set of matching canonical_ids? An exact
# set match scores 1; a single missed or extra id scores 0. The comment lists every
# id that broke the match (expected-but-missed OR produced-but-not-expected).
def judge_node_evaluator(outputs: dict, reference_outputs: dict) -> dict:
    produced = set(outputs.get("canonical_ids") or [])
    expected = set(reference_outputs.get("canonical_ids") or [])

    if produced == expected:
        return {
            "key": "judge_node_correctness",
            "score": 1,
            "comment": "All matched ids equal the expected set.",
        }

    # Either side of the mismatch is a failure: ids the judge should have returned but
    # didn't, and ids it returned but shouldn't have.
    failed = (expected - produced) | (produced - expected)
    comment = "\n".join(f"{i}: this id didn't match the expected ids" for i in sorted(failed))
    return {"key": "judge_node_correctness", "score": 0, "comment": comment}
