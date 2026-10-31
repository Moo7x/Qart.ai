"""C10 paired-profile check: identical results for the shared synthetic identities, and the check
really fails when a protected fact leaks into the scored text."""

from src.match.engine import Evidence
from src.match.fairness import VARIANTS, paired_profile_check
from src.pack import load_pack

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")


def test_shared_pairs_give_identical_results() -> None:
    result = paired_profile_check(load_pack(), EVIDENCE)
    assert result["pairs"] == len(VARIANTS) - 1
    assert result["identical"] is True
    assert result["max_fit_difference"] == 0.0
    assert result["checked_at"]


def test_a_protected_fact_written_into_free_text_is_caught() -> None:
    # Scrubbing removes labelled lines, not facts inside a sentence (documented limitation);
    # here such a sentence also adds skills, so the results must differ and the check must say so.
    leaky = [
        *VARIANTS[1][:-1],
        "As a Buddhist volunteer I led budget management and variance analysis for the temple.",
        VARIANTS[1][-1],
    ]
    result = paired_profile_check(load_pack(), EVIDENCE, [VARIANTS[0], leaky])
    assert result["identical"] is False
    assert result["max_fit_difference"] > 0
