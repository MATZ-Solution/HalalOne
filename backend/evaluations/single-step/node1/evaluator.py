# Evaluator

def correct_classification(outputs: dict, reference_outputs: dict) -> bool:
    """Check if the agent chose the correct route."""
    return outputs["classification"] == reference_outputs["classification"]
