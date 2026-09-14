"""Common request/result API; GLOBAL execution is supplied by the caller."""

from collections.abc import Callable
from dataclasses import replace
from typing import Protocol

from application.balancing_request import BalancingRequest
from application.results.base_report_result import BaseReportResult
from application.results.report_mode import ReportMode
from configuration.application_config import ApplicationConfig
from configuration.composition_root import (
    BalancingComposition,
    create_balancing_composition,
)
from optimizer.modes.optimization_mode import OptimizationMode


class GlobalRunner(Protocol):
    """Temporary execution seam; the production implementation moves in SCRUM-41."""

    def run(
        self,
        *,
        request: BalancingRequest,
        composition: BalancingComposition,
        warm_start: BaseReportResult,
    ) -> BaseReportResult: ...


class GlobalExecutionUnavailableError(RuntimeError):
    """An optimized GLOBAL request needs an injected execution dependency."""


class BalancingApplication:
    """Use fresh composition per run; return existing report results unchanged.

    A supplied composition factory must also create a fresh graph on each call.
    Player objects and nested metadata values remain caller-owned references.
    """

    def __init__(
        self,
        config: ApplicationConfig,
        global_runner: GlobalRunner | None = None,
        *,
        composition_factory: Callable[
            [ApplicationConfig], BalancingComposition
        ] = create_balancing_composition,
    ) -> None:
        self._config = config
        self._global_runner = global_runner
        self._composition_factory = composition_factory

    def run(self, request: BalancingRequest) -> BaseReportResult:
        config = replace(
            self._config,
            event=replace(self._config.event, number_of_teams=request.number_of_teams),
            optimization_mode=request.optimization_mode,
        )
        composition = self._composition_factory(config)
        balancer = composition.balancer
        global_execution = (
            request.optimization_mode is OptimizationMode.GLOBAL
            and balancer.detect_mode(request.players) is ReportMode.OPTIMIZED
        )
        if global_execution and self._global_runner is None:
            # Fail before spending the STABLE warm-start budget. PREASSIGNED
            # needs no GLOBAL dependency because it never runs optimization.
            raise GlobalExecutionUnavailableError(
                "GLOBAL execution requires an injected GlobalRunner dependency"
            )
        result = balancer.run_players(
            players=request.players,
            number_of_teams=request.number_of_teams,
            title=request.title,
            metadata=dict(request.metadata or {}),
        )
        if global_execution and self._global_runner is not None:
            result = self._global_runner.run(
                request=request,
                composition=composition,
                warm_start=result,
            )
            if not isinstance(result, BaseReportResult):
                raise TypeError("GlobalRunner must return a BaseReportResult")
        return result
