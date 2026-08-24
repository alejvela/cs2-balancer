from __future__ import annotations

from html import escape

from exporters.html_v2.report_context import (
    ReportContext,
    TeamReportData,
)
from exporters.html_v2.sections.section import (
    HtmlSection,
)


class SummarySection(HtmlSection):
    """
    Resumen general del informe.

    Funciona tanto para:

        - Optimización automática.
        - Evaluación de equipos preasignados.

    Incluye:

        - Métricas principales.
        - Estado estructural.
        - Comparación entre equipos.
        - Impacto de la actividad.
        - Restricciones del Objective Engine.

    La sección utiliza únicamente ReportContext y no conoce las
    subclases concretas de BaseReportResult.
    """

    @property
    def name(
        self,
    ) -> str:
        return "summary"

    # ========================================================
    # Render
    # ========================================================

    def render(
        self,
        context: ReportContext,
    ) -> str:
        if not isinstance(
            context,
            ReportContext,
        ):
            raise TypeError(
                "context must be a ReportContext instance."
            )

        return f"""
<div class="section summary-section">

    {self._build_heading(context)}

    {self._build_mode_notice(context)}

    {self._build_global_optimization(context)}

    {self._build_primary_metrics(context)}

    {self._build_balance_overview(context)}

    {self._build_team_comparison(context)}

    {self._build_activity_impact(context)}

    {self._build_restriction_overview(context)}

</div>
"""

    # ========================================================
    # Encabezado
    # ========================================================

    @staticmethod
    def _build_heading(
        context: ReportContext,
    ) -> str:
        if context.evaluation_only:
            eyebrow = (
                "EVALUACIÓN ESTADÍSTICA"
            )

            title = (
                "Resumen del equilibrio"
            )

            description = (
                "La composición indicada en el CSV se ha analizado "
                "sin modificar la asignación de ningún jugador."
            )

        else:
            eyebrow = (
                "RESULTADO DEL MOTOR"
            )

            title = (
                "Resumen de la optimización"
            )

            description = (
                "El motor ha generado y evaluado la distribución final "
                "utilizando las restricciones configuradas."
            )

        return f"""
<div class="section-title">

    <div>

        <p class="eyebrow">
            {escape(eyebrow)}
        </p>

        <h2>
            {escape(title)}
        </h2>

        <p class="section-description">
            {escape(description)}
        </p>

    </div>

    <span
        class="
            balance-level
            {escape(context.balance_level)}
        "
    >
        {escape(context.balance_label)}
    </span>

</div>
"""

    # ========================================================
    # Modalidad
    # ========================================================

    @staticmethod
    def _build_mode_notice(
        context: ReportContext,
    ) -> str:
        if context.evaluation_only:
            notice_class = (
                "preassigned"
            )

            notice_title = (
                "Composición conservada"
            )

            notice_text = (
                "Los equipos corresponden exactamente a los valores "
                "de la columna Team. No se han realizado intercambios "
                "ni movimientos entre jugadores."
            )

        else:
            notice_class = (
                "optimized"
            )

            notice_title = (
                "Composición optimizada"
            )

            notice_text = (
                "Los equipos se generaron automáticamente y el motor "
                "aplicó movimientos únicamente cuando aumentaban la "
                "puntuación objetiva."
            )

        icon = (
            "✓"
            if context.is_valid
            else "!"
        )

        return f"""
<div
    class="
        summary-mode-notice
        {escape(notice_class)}
    "
>

    <div
        class="summary-mode-icon"
        aria-hidden="true"
    >
        {icon}
    </div>

    <div>

        <strong>
            {escape(notice_title)}
        </strong>

        <p>
            {escape(notice_text)}
        </p>

    </div>

</div>
"""

    # ========================================================
    # Optimización GLOBAL
    # ========================================================

    @classmethod
    def _build_global_optimization(
        cls,
        context: ReportContext,
    ) -> str:
        if not context.is_global_optimization:
            return ""

        proven = (
            context.global_optimality_proven
        )

        status_class = (
            "proven"
            if proven
            else "unproven"
        )

        status_icon = (
            "✓"
            if proven
            else "…"
        )

        status_title = (
            "Óptimo global demostrado"
            if proven
            else "Mejor solución global encontrada"
        )

        if proven:
            status_text = (
                "La búsqueda Branch & Bound ha agotado el espacio "
                "relevante. No existe otra composición válida con "
                "una puntuación superior según la función objetivo "
                "y las restricciones actuales."
            )
        elif context.global_stopped_by_limit:
            status_text = (
                "La búsqueda global finalizó al alcanzar uno de sus "
                "límites antes de agotar el espacio. La composición "
                "mostrada es la mejor encontrada, pero la optimalidad "
                "global no ha sido demostrada."
            )
        else:
            status_text = (
                "La búsqueda global finalizó sin una demostración "
                "completa de optimalidad. La composición mostrada es "
                "la mejor solución encontrada durante la ejecución."
            )

        cards = (
            cls._global_metric_card(
                label="Incumbent STABLE",
                value=f"{context.global_initial_incumbent_score:.2f}",
                detail="Punto de partida de la búsqueda global",
            ),
            cls._global_metric_card(
                label="Mejora GLOBAL",
                value=f"{context.global_improvement:+.2f}",
                detail="Puntos añadidos sobre STABLE",
                tone=(
                    "positive"
                    if context.global_improvement > 0.0
                    else "neutral"
                ),
            ),
            cls._global_metric_card(
                label="Nodos explorados",
                value=f"{context.global_nodes_visited:,}".replace(",", "."),
                detail="Estados visitados por Branch & Bound",
            ),
            cls._global_metric_card(
                label="Soluciones evaluadas",
                value=(
                    f"{context.global_complete_solutions_evaluated:,}"
                    .replace(",", ".")
                ),
                detail="Composiciones completas evaluadas",
            ),
            cls._global_metric_card(
                label="Ramas podadas",
                value=f"{context.global_pruned_nodes:,}".replace(",", "."),
                detail=(
                    f"{context.global_bound_prunes:,}".replace(",", ".")
                    + " descartadas por bound"
                ),
                tone=(
                    "positive"
                    if context.global_pruned_nodes > 0
                    else "neutral"
                ),
            ),
            cls._global_metric_card(
                label="Tiempo GLOBAL",
                value=cls._format_global_elapsed(
                    context.global_elapsed_seconds
                ),
                detail=cls._global_stop_reason_label(
                    context.global_stop_reason
                ),
            ),
        )

        return f"""
<section class="summary-block global-optimization-block">

    <div class="global-optimization-hero {escape(status_class)}">

        <div class="global-optimization-status-icon" aria-hidden="true">
            {escape(status_icon)}
        </div>

        <div class="global-optimization-copy">
            <p class="eyebrow">
                OPTIMIZACIÓN GLOBAL
            </p>

            <h3>
                {escape(status_title)}
            </h3>

            <p>
                {escape(status_text)}
            </p>
        </div>

        <div class="global-optimization-score">
            <span>Score final</span>
            <strong>{context.global_final_score:.2f}</strong>
            <small>/ 100</small>
        </div>

    </div>

    <div class="global-optimization-metrics">
        {''.join(cards)}
    </div>

</section>
"""

    @staticmethod
    def _global_metric_card(
        label: str,
        value: str,
        detail: str,
        tone: str = "neutral",
    ) -> str:
        return f"""
<article class="global-optimization-metric {escape(tone)}">
    <span>{escape(label)}</span>
    <strong>{escape(value)}</strong>
    <small>{escape(detail)}</small>
</article>
"""

    @staticmethod
    def _format_global_elapsed(
        seconds: float,
    ) -> str:
        value = max(
            0.0,
            float(seconds),
        )

        if value < 60.0:
            return f"{value:.2f} s"

        minutes = int(
            value // 60.0
        )

        remaining = (
            value
            - minutes * 60.0
        )

        return (
            f"{minutes} min "
            f"{remaining:.1f} s"
        )

    @staticmethod
    def _global_stop_reason_label(
        reason: str,
    ) -> str:
        labels = {
            "SEARCH_EXHAUSTED": "Espacio de búsqueda agotado",
            "NODE_LIMIT": "Límite de nodos alcanzado",
            "EVALUATION_LIMIT": "Límite de evaluaciones alcanzado",
            "TIME_LIMIT": "Límite de tiempo alcanzado",
            "PROOF_NOT_COMPLETED": "Demostración no completada",
        }

        normalized = str(
            reason
            or "UNKNOWN"
        ).strip().upper()

        return labels.get(
            normalized,
            normalized.replace(
                "_",
                " ",
            ).title(),
        )

    # ========================================================
    # Métricas principales
    # ========================================================

    def _build_primary_metrics(
        self,
        context: ReportContext,
    ) -> str:
        if context.evaluation_only:

            cards = (
                self._metric_card(
                    label="Equilibrio",
                    value=self._format_number(
                        context.final_score
                    ),
                    detail=context.balance_label,
                    tone=self._score_tone(
                        context.final_score,
                        context.is_valid,
                    ),
                ),

                self._metric_card(
                    label="Penalización estructural",
                    value=self._format_number(
                        context.penalty
                    ),
                    detail=(
                        "Sin incidencias estructurales"
                        if context.penalty <= 0.0
                        else (
                            "La composición contiene incidencias"
                        )
                    ),
                    tone=(
                        "positive"
                        if context.penalty <= 0.0
                        else "negative"
                    ),
                ),

                self._metric_card(
                    label="Equipos",
                    value=str(
                        context.team_count
                    ),
                    detail=(
                        f"{context.player_count} jugadores"
                    ),
                    tone="neutral",
                ),

                self._metric_card(
                    label="Power medio",
                    value=self._format_number(
                        context.average_final_power
                    ),
                    detail="Power efectivo del conjunto",
                    tone="neutral",
                ),

                self._metric_card(
                    label="Actividad media",
                    value=(
                        f"{context.average_activity_factor * 100.0:.1f}%"
                    ),
                    detail=(
                        "Factor medio aplicado al Power"
                    ),
                    tone=self._activity_tone(
                        context.average_activity_factor
                    ),
                ),

                self._metric_card(
                    label="Tiempo de evaluación",
                    value=self._format_time(
                        context.elapsed_ms
                    ),
                    detail="Objective Engine",
                    tone="neutral",
                ),
            )

        else:
            improvement_tone = (
                "positive"
                if context.improvement > 0.0
                else (
                    "negative"
                    if context.improvement < 0.0
                    else "neutral"
                )
            )

            cards = (
                self._metric_card(
                    label="Puntuación inicial",
                    value=self._format_number(
                        context.initial_score
                    ),
                    detail="Antes de optimizar",
                    tone="neutral",
                ),

                self._metric_card(
                    label="Puntuación final",
                    value=self._format_number(
                        context.final_score
                    ),
                    detail=context.balance_label,
                    tone=self._score_tone(
                        context.final_score,
                        context.is_valid,
                    ),
                ),

                self._metric_card(
                    label="Mejora",
                    value=self._format_signed_number(
                        context.improvement
                    ),
                    detail=(
                        "Incremento de puntuación"
                        if context.improvement > 0.0
                        else (
                            "Sin cambios"
                            if context.improvement == 0.0
                            else "Resultado inferior al inicial"
                        )
                    ),
                    tone=improvement_tone,
                ),

                self._metric_card(
                    label="Movimientos",
                    value=str(
                        context.iterations
                    ),
                    detail="Movimientos aceptados",
                    tone="neutral",
                ),

                self._metric_card(
                    label="Evaluaciones",
                    value=str(
                        context.total_evaluations
                    ),
                    detail="Candidatos analizados",
                    tone="neutral",
                ),

                self._metric_card(
                    label="Tiempo",
                    value=self._format_time(
                        context.elapsed_ms
                    ),
                    detail="Optimización completa",
                    tone="neutral",
                ),
            )

        return f"""
<section class="summary-block">

    <div class="summary-block-heading">

        <div>

            <p class="eyebrow">
                MÉTRICAS PRINCIPALES
            </p>

            <h3>
                Resultado general
            </h3>

        </div>

    </div>

    <div class="metric-grid summary-metric-grid">
        {"".join(cards)}
    </div>

</section>
"""

    # ========================================================
    # Estado general
    # ========================================================

    def _build_balance_overview(
        self,
        context: ReportContext,
    ) -> str:
        validity_class = (
            "valid"
            if context.is_valid
            else "invalid"
        )

        validity_title = (
            "Composición estructuralmente válida"
            if context.is_valid
            else (
                "Composición con incidencias estructurales"
            )
        )

        validity_description = (
            "No se han detectado penalizaciones estructurales."
            if context.is_valid
            else (
                "Una o más restricciones han aplicado penalizaciones."
            )
        )

        return f"""
<section class="summary-block">

    <div class="summary-block-heading">

        <div>

            <p class="eyebrow">
                ESTADO GENERAL
            </p>

            <h3>
                Diagnóstico de la composición
            </h3>

        </div>

    </div>

    <div class="summary-overview-grid">

        <article
            class="
                summary-status-card
                {validity_class}
            "
        >

            <span class="summary-card-label">
                Validación estructural
            </span>

            <strong>
                {escape(validity_title)}
            </strong>

            <p>
                {escape(validity_description)}
            </p>

        </article>

        <article class="summary-information-card">

            <span class="summary-card-label">
                Modalidad
            </span>

            <strong>
                {escape(context.mode_label)}
            </strong>

            <p>
                {escape(context.result_description)}
            </p>

        </article>

        <article class="summary-information-card">

            <span class="summary-card-label">
                Configuración
            </span>

            <strong>
                {context.team_count} equipos ·
                {context.player_count} jugadores
            </strong>

            <p>
                {len(context.seeded_players)} cabezas de serie ·
                {len(context.preassigned_players)} con Team asignado
            </p>

        </article>

    </div>

</section>
"""

    # ========================================================
    # Comparación de equipos
    # ========================================================

    def _build_team_comparison(
        self,
        context: ReportContext,
    ) -> str:
        strongest_team = (
            context.strongest_team
        )

        weakest_team = (
            context.weakest_team
        )

        if (
            strongest_team is None
            or weakest_team is None
        ):
            return ""

        return f"""
<section class="summary-block">

    <div class="summary-block-heading">

        <div>

            <p class="eyebrow">
                EQUILIBRIO
            </p>

            <h3>
                Diferencias entre equipos
            </h3>

        </div>

    </div>

    <div class="comparison-grid">

        {self._comparison_card(
            label="Mayor Power",
            name=strongest_team.name,
            primary_value=(
                f"{strongest_team.average_final_power:.2f}"
            ),
            secondary_value=(
                "Power medio efectivo"
            ),
            tone="strongest",
        )}

        {self._comparison_card(
            label="Menor Power",
            name=weakest_team.name,
            primary_value=(
                f"{weakest_team.average_final_power:.2f}"
            ),
            secondary_value=(
                "Power medio efectivo"
            ),
            tone="weakest",
        )}

        {self._comparison_card(
            label="Diferencia de Power",
            name="Dispersión máxima",
            primary_value=(
                f"{context.power_spread:.2f}"
            ),
            secondary_value=(
                "Menor diferencia implica mayor equilibrio"
            ),
            tone=self._spread_tone(
                context.power_spread,
                good_limit=4.0,
                warning_limit=8.0,
            ),
        )}

        {self._comparison_card(
            label="Diferencia ELO",
            name="Medias de equipo",
            primary_value=self._format_optional(
                context.elo_spread,
                decimals=1,
            ),
            secondary_value=(
                "Equipo más alto frente al más bajo"
            ),
            tone=self._spread_tone(
                context.elo_spread,
                good_limit=80.0,
                warning_limit=150.0,
            ),
        )}

        {self._comparison_card(
            label="Diferencia KD",
            name="Medias de equipo",
            primary_value=self._format_optional(
                context.kd_spread,
                decimals=3,
            ),
            secondary_value=(
                "Equipo más alto frente al más bajo"
            ),
            tone=self._spread_tone(
                context.kd_spread,
                good_limit=0.05,
                warning_limit=0.10,
            ),
        )}

    </div>

</section>
"""

    # ========================================================
    # Impacto de actividad
    # ========================================================

    def _build_activity_impact(
        self,
        context: ReportContext,
    ) -> str:
        if not context.teams:
            return ""

        teams = tuple(
            context.teams
        )

        most_penalized = max(
            teams,
            key=self._team_activity_penalty,
        )

        least_penalized = min(
            teams,
            key=self._team_activity_penalty,
        )

        global_base_power = (
            context.average_base_power
        )

        global_final_power = (
            context.average_final_power
        )

        global_loss = max(
            0.0,
            (
                global_base_power
                - global_final_power
            ),
        )

        rows = "\n".join(
            self._build_activity_team_row(
                team=team,
            )
            for team in teams
        )

        return f"""
<section class="summary-block">

    <div class="summary-block-heading">

        <div>

            <p class="eyebrow">
                ACTIVIDAD COMPETITIVA
            </p>

            <h3>
                Impacto sobre los equipos
            </h3>

            <p class="section-description">
                Comparación entre el Power estadístico base y el Power
                efectivo después de aplicar el factor de actividad.
            </p>

        </div>

    </div>

    <div class="activity-impact-highlight-grid">

        {self._activity_highlight_card(
            label="Power base global",
            value=f"{global_base_power:.2f}",
            detail="Antes del ajuste de actividad",
            tone="neutral",
        )}

        {self._activity_highlight_card(
            label="Power efectivo global",
            value=f"{global_final_power:.2f}",
            detail="Valor utilizado por el balanceador",
            tone="positive",
        )}

        {self._activity_highlight_card(
            label="Pérdida media",
            value=f"-{global_loss:.2f}",
            detail="Power perdido por actividad",
            tone=(
                "positive"
                if global_loss <= 0.50
                else (
                    "warning"
                    if global_loss <= 3.0
                    else "negative"
                )
            ),
        )}

        {self._activity_highlight_card(
            label="Equipo más penalizado",
            value=most_penalized.name,
            detail=(
                f"-{self._team_activity_penalty(most_penalized):.2f} "
                "Power medio"
            ),
            tone=(
                "negative"
                if self._team_activity_penalty(
                    most_penalized
                ) > 0.0
                else "positive"
            ),
        )}

        {self._activity_highlight_card(
            label="Equipo menos penalizado",
            value=least_penalized.name,
            detail=(
                f"-{self._team_activity_penalty(least_penalized):.2f} "
                "Power medio"
            ),
            tone="positive",
        )}

    </div>

    <div class="table-panel activity-impact-table-panel">

        <div class="table-toolbar">

            <div>

                <strong>
                    Actividad por equipo
                </strong>

                <span>
                    Base frente a Power efectivo
                </span>

            </div>

        </div>

        <div class="table-scroll">

            <table class="data-table activity-impact-table">

                <thead>

                    <tr>

                        <th>
                            Equipo
                        </th>

                        <th class="numeric-cell">
                            Power base
                        </th>

                        <th class="numeric-cell">
                            Actividad
                        </th>

                        <th class="numeric-cell">
                            Pérdida
                        </th>

                        <th class="numeric-cell">
                            Power final
                        </th>

                        <th class="numeric-cell">
                            Jugadores penalizados
                        </th>

                    </tr>

                </thead>

                <tbody>
                    {rows}
                </tbody>

            </table>

        </div>

    </div>

</section>
"""

    def _build_activity_team_row(
        self,
        team: TeamReportData,
    ) -> str:
        penalty = (
            self._team_activity_penalty(
                team
            )
        )

        penalized_players = sum(
            1
            for player in team.players
            if player.activity_factor < 0.999
        )

        activity_class = (
            self._activity_css_class(
                team.average_activity_factor
            )
        )

        penalty_class = (
            "positive-value"
            if penalty <= 0.005
            else "negative-value"
        )

        return f"""
<tr>

    <td>
        <strong>
            {escape(team.name)}
        </strong>
    </td>

    <td class="numeric-cell">
        {team.average_base_power:.2f}
    </td>

    <td class="numeric-cell">

        <strong class="{escape(activity_class)}">
            {team.average_activity_factor * 100.0:.1f}%
        </strong>

    </td>

    <td
        class="
            numeric-cell
            {penalty_class}
        "
    >
        -{penalty:.2f}
    </td>

    <td class="numeric-cell">

        <strong class="final-power-value">
            {team.average_final_power:.2f}
        </strong>

    </td>

    <td class="numeric-cell">
        {penalized_players}
        /
        {team.player_count}
    </td>

</tr>
"""

    @staticmethod
    def _team_activity_penalty(
        team: TeamReportData,
    ) -> float:
        return max(
            0.0,
            (
                team.average_base_power
                - team.average_final_power
            ),
        )

    # ========================================================
    # Restricciones
    # ========================================================

    def _build_restriction_overview(
        self,
        context: ReportContext,
    ) -> str:
        restrictions = tuple(
            context.restrictions.values()
        )

        if not restrictions:
            return """
<section class="summary-block">

    <div class="empty-panel">
        No existen restricciones disponibles para esta evaluación.
    </div>

</section>
"""

        penalized = tuple(
            restriction
            for restriction in restrictions
            if restriction.penalty > 0.0
        )

        weakest = min(
            restrictions,
            key=lambda restriction: (
                restriction.score,
                -restriction.penalty,
            ),
        )

        best = max(
            restrictions,
            key=lambda restriction: (
                restriction.score,
                -restriction.penalty,
            ),
        )

        return f"""
<section class="summary-block">

    <div class="summary-block-heading">

        <div>

            <p class="eyebrow">
                OBJECTIVE ENGINE
            </p>

            <h3>
                Resumen de restricciones
            </h3>

        </div>

    </div>

    <div class="restriction-summary-grid">

        {self._restriction_card(
            label="Restricciones",
            value=str(
                len(restrictions)
            ),
            detail="Métricas evaluadas",
            tone="neutral",
        )}

        {self._restriction_card(
            label="Penalizadas",
            value=str(
                len(penalized)
            ),
            detail=(
                "Sin penalizaciones"
                if not penalized
                else "Requieren revisión"
            ),
            tone=(
                "positive"
                if not penalized
                else "negative"
            ),
        )}

        {self._restriction_card(
            label="Métrica más débil",
            value=f"{weakest.score:.2f}",
            detail=weakest.name,
            tone=self._score_tone(
                weakest.score,
                weakest.penalty <= 0.0,
            ),
        )}

        {self._restriction_card(
            label="Métrica más fuerte",
            value=f"{best.score:.2f}",
            detail=best.name,
            tone="positive",
        )}

    </div>

</section>
"""

    # ========================================================
    # Componentes
    # ========================================================

    @staticmethod
    def _metric_card(
        label: str,
        value: str,
        detail: str,
        tone: str,
    ) -> str:
        return f"""
<article
    class="
        metric-card
        summary-metric-card
        {escape(tone)}
    "
>

    <span class="metric-label">
        {escape(label)}
    </span>

    <strong class="metric-value">
        {escape(value)}
    </strong>

    <small>
        {escape(detail)}
    </small>

</article>
"""

    @staticmethod
    def _comparison_card(
        label: str,
        name: str,
        primary_value: str,
        secondary_value: str,
        tone: str,
    ) -> str:
        return f"""
<article class="comparison-card {escape(tone)}">

    <span class="summary-card-label">
        {escape(label)}
    </span>

    <strong class="comparison-team-name">
        {escape(name)}
    </strong>

    <span class="comparison-value">
        {escape(primary_value)}
    </span>

    <small>
        {escape(secondary_value)}
    </small>

</article>
"""

    @staticmethod
    def _activity_highlight_card(
        label: str,
        value: str,
        detail: str,
        tone: str,
    ) -> str:
        return f"""
<article
    class="
        activity-impact-highlight
        {escape(tone)}
    "
>

    <span>
        {escape(label)}
    </span>

    <strong>
        {escape(value)}
    </strong>

    <small>
        {escape(detail)}
    </small>

</article>
"""

    @staticmethod
    def _restriction_card(
        label: str,
        value: str,
        detail: str,
        tone: str,
    ) -> str:
        return f"""
<article
    class="
        restriction-summary-card
        {escape(tone)}
    "
>

    <span class="summary-card-label">
        {escape(label)}
    </span>

    <strong>
        {escape(value)}
    </strong>

    <p>
        {escape(detail)}
    </p>

</article>
"""

    # ========================================================
    # Formato
    # ========================================================

    @staticmethod
    def _format_number(
        value: float | int | None,
        decimals: int = 2,
    ) -> str:
        if value is None:
            return "N/A"

        try:
            numeric = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return "N/A"

        return (
            f"{numeric:.{decimals}f}"
        )

    @staticmethod
    def _format_optional(
        value: float | int | None,
        decimals: int = 2,
    ) -> str:
        return (
            SummarySection._format_number(
                value=value,
                decimals=decimals,
            )
        )

    @staticmethod
    def _format_signed_number(
        value: float | int,
        decimals: int = 2,
    ) -> str:
        return (
            f"{float(value):+.{decimals}f}"
        )

    @staticmethod
    def _format_time(
        elapsed_ms: float,
    ) -> str:
        value = max(
            0.0,
            float(elapsed_ms),
        )

        if value < 1000.0:
            return (
                f"{value:.2f} ms"
            )

        seconds = (
            value / 1000.0
        )

        if seconds < 60.0:
            return (
                f"{seconds:.2f} s"
            )

        minutes = int(
            seconds // 60.0
        )

        remaining = (
            seconds
            - minutes * 60.0
        )

        return (
            f"{minutes} min "
            f"{remaining:.1f} s"
        )

    # ========================================================
    # Clasificaciones visuales
    # ========================================================

    @staticmethod
    def _score_tone(
        score: float,
        valid: bool,
    ) -> str:
        if not valid:
            return "negative"

        if score >= 85.0:
            return "positive"

        if score >= 70.0:
            return "warning"

        return "negative"

    @staticmethod
    def _spread_tone(
        value: float | None,
        good_limit: float,
        warning_limit: float,
    ) -> str:
        if value is None:
            return "neutral"

        if value <= good_limit:
            return "positive"

        if value <= warning_limit:
            return "warning"

        return "negative"

    @staticmethod
    def _activity_tone(
        factor: float,
    ) -> str:
        if factor >= 0.95:
            return "positive"

        if factor >= 0.85:
            return "warning"

        return "negative"

    @staticmethod
    def _activity_css_class(
        factor: float,
    ) -> str:
        if factor >= 0.95:
            return "activity-high"

        if factor >= 0.85:
            return "activity-medium"

        return "activity-low"

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r})"
        )
