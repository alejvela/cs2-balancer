"""
Application result models.

The package intentionally avoids eager re-exports.

Import result classes directly from their modules to prevent circular
dependencies between the application layer and optimization services.

Examples:

    from application.results.base_report_result import BaseReportResult

    from application.results.optimization_result import (
        OptimizationResult,
    )

    from application.results.evaluation_result import (
        EvaluationResult,
    )

    from application.results.report_mode import (
        ReportMode,
    )
"""

__all__ = ()
