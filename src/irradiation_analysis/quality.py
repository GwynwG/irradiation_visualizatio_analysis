from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from irradiation_analysis.excel_io import ImportResult


@dataclass(frozen=True)
class QualityAssessment:
    score: float
    grade: str
    valid_rate: float
    blocked_rate: float
    duplicate_rate: float
    conflict_rate: float
    warning_count: int
    error_count: int
    issue_counts: tuple[tuple[str, int], ...]
    reasons: tuple[str, ...]


def assess_import_quality(result: ImportResult) -> QualityAssessment:
    summary = result.summary
    raw_rows = max(summary.raw_rows, 0)
    valid_rows = max(summary.valid_rows, 0)
    row_basis = max(raw_rows, 1)
    valid_basis = max(valid_rows, 1)
    issue_counts = Counter(issue.code for issue in result.issues)
    error_count = sum(1 for issue in result.issues if issue.level == "error")
    warning_count = len(result.issues) - error_count

    if raw_rows == 0:
        return QualityAssessment(
            score=0.0,
            grade="不可用",
            valid_rate=0.0,
            blocked_rate=0.0,
            duplicate_rate=0.0,
            conflict_rate=0.0,
            warning_count=warning_count,
            error_count=error_count,
            issue_counts=_issue_counts(issue_counts),
            reasons=("未读取到可评估的数据行。",),
        )

    blocked_rate = summary.blocked_rows / row_basis
    valid_rate = valid_rows / row_basis
    duplicate_rate = summary.exact_duplicate_rows / max(
        summary.valid_rows + summary.exact_duplicate_rows,
        1,
    )
    conflict_rate = summary.conflict_keys / valid_basis
    warning_rate = warning_count / valid_basis

    score = 100.0
    score -= min(blocked_rate * 55.0, 55.0)
    score -= min(conflict_rate * 25.0, 25.0)
    score -= min(duplicate_rate * 10.0, 10.0)
    score -= min(warning_rate * 12.0, 18.0)
    score = round(max(0.0, min(100.0, score)), 1)

    return QualityAssessment(
        score=score,
        grade=_grade(score),
        valid_rate=round(valid_rate, 6),
        blocked_rate=round(blocked_rate, 6),
        duplicate_rate=round(duplicate_rate, 6),
        conflict_rate=round(conflict_rate, 6),
        warning_count=warning_count,
        error_count=error_count,
        issue_counts=_issue_counts(issue_counts),
        reasons=_reasons(
            blocked_rate=blocked_rate,
            conflict_rate=conflict_rate,
            duplicate_rate=duplicate_rate,
            warning_count=warning_count,
            score=score,
        ),
    )


def _grade(score: float) -> str:
    if score >= 90.0:
        return "优"
    if score >= 75.0:
        return "可用"
    if score >= 60.0:
        return "需复核"
    return "不建议分析"


def _issue_counts(counts: Counter[str]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _reasons(
    *,
    blocked_rate: float,
    conflict_rate: float,
    duplicate_rate: float,
    warning_count: int,
    score: float,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if blocked_rate > 0:
        reasons.append(f"阻断行占比 {blocked_rate:.1%}。")
    if conflict_rate > 0:
        reasons.append(f"冲突键占有效记录 {conflict_rate:.1%}。")
    if duplicate_rate > 0:
        reasons.append(f"完全重复行占比 {duplicate_rate:.1%}。")
    if warning_count > 0:
        reasons.append(f"存在 {warning_count} 条提示类质量问题。")
    if not reasons and score >= 90.0:
        reasons.append("未发现明显质量风险，可进入后续分析。")
    return tuple(reasons)
