"""The radar's field signals follow the person's current occupation."""

from src.evidence.signals import Signal
from src.match.radar import _personal_signals
from src.pack import load_pack


def signal(signal_id: str) -> Signal:
    return Signal(
        id=signal_id,
        title=signal_id,
        family="test",
        kind="observed",
        direction="insufficient",
        early_direction=None,
        headline="",
        unit="",
        points=[],
        independent_sources=1,
        note="",
        sources=[],
        evidence=[],
    )


SIGNALS = [
    signal(s)
    for s in (
        "dosm_share_clerical",
        "dosm_share_professionals",
        "aei_43-3031.00_MYS",
        "aei_13-2051.00_GLOBAL",
    )
]


def test_two_current_roles_get_different_field_signals() -> None:
    pack = load_pack()
    clerk = [s.id for s in _personal_signals(pack, "cash_application_analyst", SIGNALS)]
    analyst = [s.id for s in _personal_signals(pack, "financial_analyst", SIGNALS)]
    assert clerk == ["dosm_share_clerical", "aei_43-3031.00_MYS"]  # ISCO 4311 → clerical
    assert analyst == ["dosm_share_professionals", "aei_13-2051.00_GLOBAL"]  # ISCO 2413
    assert _personal_signals(pack, "other", SIGNALS) == []  # no current role: no field focus
