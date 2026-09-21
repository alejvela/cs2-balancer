"""Construct HTML/console scoring collaborators without composing an engine."""

from dataclasses import dataclass

from configuration.application_config import ApplicationConfig
from configuration.scoring_factory import create_scoring_model
from exporters.html_v2.html_exporter import HtmlExporterV2
from scoring.scoring_model import ScoringModel


@dataclass(frozen=True, slots=True)
class ReportingComponents:
    scoring_model: ScoringModel
    exporter: HtmlExporterV2


def create_reporting_components(config: ApplicationConfig) -> ReportingComponents:
    """Use the same scoring configuration as execution, with fresh report state."""
    scoring = create_scoring_model(config.scoring)
    return ReportingComponents(
        scoring, HtmlExporterV2(scoring_model=scoring, title=config.event.report_title)
    )
