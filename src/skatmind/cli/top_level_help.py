"""Lightweight Product-oriented top-level CLI help text."""

from skatmind.cli.onboarding_contracts import (
    ADVANCED_COMMAND_FAMILIES,
    PRODUCT_TOP_LEVEL_AREAS,
)

_AREA_DESCRIPTIONS = (
    "Enter visible decision information and receive a bounded Card recommendation.",
    "Review recorded decisions using only information available at each decision.",
    "Create or resume a private step-by-step record of one Skat game.",
    "Create or resume a private local fixed three-player 36-game Match.",
    "Use selected Match snapshots for cross-game summaries and Coaching evidence.",
    "See the version, license, local operation, and managed-storage information.",
)

_COMMAND_DESCRIPTIONS = (
    "Open the complete private local browser application explicitly.",
    "Run advanced Root JSON automation with reproducible file inputs and outputs.",
    "Use the direct explicit Session-file automation interface.",
    "Use the direct explicit Match Workspace interface.",
    "Use the direct explicit Learning Corpus interface.",
)


def build_top_level_description(command: str) -> str:
    """Builds the ordered Product discovery sections before common options."""

    areas = "\n".join(
        f"  {name}\n    {description}"
        for name, description in zip(
            PRODUCT_TOP_LEVEL_AREAS,
            _AREA_DESCRIPTIONS,
            strict=True,
        )
    )
    commands = "\n".join(
        f"  {name:<8} {description}"
        for name, description in zip(
            ADVANCED_COMMAND_FAMILIES,
            _COMMAND_DESCRIPTIONS,
            strict=True,
        )
    )
    return (
        "Product introduction\n"
        "  SkatMind is a private local Skat analysis, review, capture, and learning tool.\n\n"
        "Start here\n"
        f"  {command}\n"
        "    With no arguments, opens the complete private local browser application.\n"
        "    Normal frontend use does not require JSON, filesystem paths, or technical options.\n\n"
        "What the local application includes\n"
        f"{areas}\n\n"
        "Advanced commands\n"
        f"{commands}"
    )


def build_top_level_epilog(command: str) -> str:
    """Builds the final ordered help-discovery section."""

    return (
        "More help\n"
        f"  {command} app --help\n"
        f"  {command} run --help\n"
        f"  {command} session --help\n"
        f"  {command} capture --help\n"
        f"  {command} corpus --help"
    )
