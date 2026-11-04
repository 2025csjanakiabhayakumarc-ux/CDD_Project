from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One validation failure returned by any rule check() function.

    Every rule module must return List[Finding] from its check().
    An empty list means the CSV passed that rule.
    """
    rule: str       # rule identifier, e.g. "required_columns"
    message: str    # human-readable description of the failure
    hint: str = ""  # plain-language fix suggestion (populated by Member 4's hint module)
