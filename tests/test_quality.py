from irradiation_analysis.excel_io import ImportResult, ImportSummary
from irradiation_analysis.models import QualityIssue
from irradiation_analysis.quality import assess_import_quality


def result(
    *,
    raw_rows: int,
    valid_rows: int,
    blocked_rows: int = 0,
    exact_duplicate_rows: int = 0,
    conflict_keys: int = 0,
    issues: list[QualityIssue] | None = None,
) -> ImportResult:
    return ImportResult(
        records=[],
        issues=issues or [],
        summary=ImportSummary(
            file_count=1,
            raw_rows=raw_rows,
            valid_rows=valid_rows,
            blocked_rows=blocked_rows,
            exact_duplicate_rows=exact_duplicate_rows,
            conflict_keys=conflict_keys,
            room_count=0,
            device_count=0,
            monitor_types=(),
        ),
        candidate_sheets={},
    )


def issue(code: str, *, level: str = "warning") -> QualityIssue:
    return QualityIssue(
        level=level,
        code=code,
        message=code,
        source_file="quality.xlsx",
    )


def test_empty_import_is_not_available():
    assessment = assess_import_quality(result(raw_rows=0, valid_rows=0))

    assert assessment.score == 0.0
    assert assessment.grade == "不可用"
    assert assessment.reasons == ("未读取到可评估的数据行。",)


def test_clean_import_gets_excellent_grade():
    assessment = assess_import_quality(result(raw_rows=10, valid_rows=10))

    assert assessment.score == 100.0
    assert assessment.grade == "优"
    assert assessment.valid_rate == 1.0
    assert assessment.blocked_rate == 0.0
    assert assessment.reasons == ("未发现明显质量风险，可进入后续分析。",)


def test_blocked_conflict_duplicate_and_warning_penalties_are_reported():
    assessment = assess_import_quality(
        result(
            raw_rows=10,
            valid_rows=8,
            blocked_rows=2,
            exact_duplicate_rows=1,
            conflict_keys=2,
            issues=[
                issue("invalid_value", level="error"),
                issue("unit_changed"),
                issue("unit_changed"),
                issue("threshold_changed"),
            ],
        )
    )

    assert assessment.score == 77.1
    assert assessment.grade == "可用"
    assert assessment.valid_rate == 0.8
    assert assessment.blocked_rate == 0.2
    assert assessment.duplicate_rate == 0.111111
    assert assessment.conflict_rate == 0.25
    assert assessment.warning_count == 3
    assert assessment.error_count == 1
    assert assessment.issue_counts == (
        ("unit_changed", 2),
        ("invalid_value", 1),
        ("threshold_changed", 1),
    )
    assert any("阻断行占比" in reason for reason in assessment.reasons)
