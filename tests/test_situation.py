"""The person's situation is read from the CV: a finance role named as the current job wins."""

from src.intake.extract import situation_from


def test_a_finance_role_means_working_whatever_the_model_says() -> None:
    assert situation_from("cash_application_analyst", 6, "switcher")[0] == "working"


def test_the_model_decides_between_student_and_switcher() -> None:
    assert situation_from("other", None, "student")[0] == "student"
    assert situation_from("other", 5, "switcher")[0] == "switcher"


def test_without_a_model_no_experience_means_student() -> None:
    assert situation_from("other", None, None)[0] == "student"
    assert situation_from("other", 4, None)[0] == "switcher"
    assert all(situation_from("other", y, None)[1] for y in (None, 4))  # always a stated reason
