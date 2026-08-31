"""Plain-language guide and task examples for advanced Root automation."""

from __future__ import annotations


def _example_paths(invocation_style: str) -> dict[str, str]:
    if invocation_style == "legacy":
        return {
            "position": "examples/grand_second_position.json",
            "historical": "examples/historical_grand_normal_completion.json",
            "multi_step": "examples/grand_second_position.json",
            "preparation": "examples/training_dataset_preparation_known_opponent.json",
            "dataset": "examples/training_dataset_partition_audit.json",
            "statistics": "examples/training_dataset_normal_play.json",
        }
    return {
        "position": "position-request.json",
        "historical": "historical-game.json",
        "multi_step": "position-request.json",
        "preparation": "training-dataset-preparation.json",
        "dataset": "training-dataset.json",
        "statistics": "training-dataset.json",
    }


def build_run_help_epilog(command: str, invocation_style: str) -> str:
    """Builds the advanced concept guide and six task-oriented examples."""

    paths = _example_paths(invocation_style)
    historical_command = (
        f"{command} --input {paths['historical']} --historical-game-review "
        "--output historical-result.json"
    )
    multi_step_command = (
        f"{command} --input {paths['multi_step']} --multi-step 2 "
        "--compare-policies --output comparison-result.json"
    )
    audit_command = (
        f"{command} --input {paths['dataset']} --audit-dataset-partitions "
        "--output partition-audit.json"
    )
    statistics_command = (
        f"{command} --input {paths['statistics']} --aggregate-opponent-statistics "
        "--output aggregation-result.json --export-opponent-statistics "
        "opponent-statistics.json"
    )
    return f"""Concept guide
  Root JSON request
    A portable automation document selecting one of the seven Root workflows. JSON is for
    automation, portability, and reproducibility; normal frontend use does not require JSON.
  Result JSON
    The structured workflow Result. Use --output to retain it in a caller-selected file.
  Samples
    Repeated randomized analysis work. More samples may increase runtime and are not
    calibrated probability.
  Random seed
    A seed makes randomized work reproducible for the same request and implementation.
  Opponent strategy and Policy
    Fixed simulation behavior for opponents, not learned prediction or hidden truth.
  Search budget
    A bounded work limit for Search, not a quality, completeness, or optimality guarantee.
  Provenance
    Field-origin and information-timing evidence, not Confidence, correctness, or proof.
  Quiet mode
    --quiet suppresses successful terminal presentation, but not errors or requested output
    and auxiliary Artifact files.

Task-oriented examples
  Analyze an exported Position request
    Goal: analyze one frontend-exported Position decision.
    Input: a Position Root JSON request in {paths["position"]}.
    Command: {command} --input {paths["position"]} --output position-result.json
    Result: Position analysis Result JSON and normal terminal presentation.
    Output file: --output is optional; when supplied, it writes the exact Result JSON.

  Review a completed Historical Game
    Goal: evaluate recorded decisions in one completed game.
    Input: a Historical Game Root JSON request in {paths["historical"]}.
    Command: {historical_command}
    Result: Historical Game Result JSON with decision-time review when available.
    Output file: --output is optional and does not change the review Result.

  Run Multi-Step Policy Comparison
    Goal: compare supported local Card Policies over bounded simulated steps.
    Input: a Position Root JSON request in {paths["multi_step"]}.
    Command: {multi_step_command}
    Result: Position Result JSON with Multi-Step and Policy Comparison sections.
    Output file: --output is optional; --quiet may suppress only successful presentation.

  Prepare a Training Dataset
    Goal: derive one existing bounded Dataset preparation Result.
    Input: a Training Dataset Preparation Root JSON request in {paths["preparation"]}.
    Command: {command} --input {paths["preparation"]} --output preparation-result.json
    Result: a complete or normally unavailable Training Dataset Preparation Result.
    Output file: --output is optional and writes that unchanged Result state.

  Audit Dataset partitions
    Goal: inspect stable-player membership and overlap under an explicit partition policy.
    Input: a Training Dataset Root JSON request in {paths["dataset"]}.
    Command: {audit_command}
    Result: Dataset partition-audit Result JSON; normal unavailable states remain successful.
    Output file: --output is optional and writes the audit Result.

  Aggregate reusable Opponent Statistics
    Goal: derive reusable observed-behavior statistics from selected Dataset records.
    Input: a Training Dataset Root JSON request in {paths["statistics"]}.
    Command: {statistics_command}
    Result: aggregation Result JSON plus the requested opponent_statistics_input Artifact.
    Output file: both paths are optional; the Artifact is written only when explicitly requested."""
