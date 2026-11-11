
"""Reusable plain-language hints for DataGuard validation rules."""


def percentage_hint(column: str) -> str:
    return (
        f"Check column '{column}'. Enter a numeric percentage "
        "between 0 and 100."
    )


def date_hint(column: str, expected_format: str) -> str:
    return (
        f"Check column '{column}'. Enter a valid date using "
        f"the format {expected_format}."
    )


def email_hint(column: str) -> str:
    return (
        f"Check column '{column}'. Enter a valid email address, "
        "such as student@example.com."
    )
