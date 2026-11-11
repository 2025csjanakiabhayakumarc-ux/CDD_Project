from dataclasses import dataclass, field


@dataclass(frozen=True)
class Finding:
    rule_id: str
    row: int | None
    column: str | None
    message: str
    hint: str
    severity: str = "error"  # "error" | "warning" | "info"
