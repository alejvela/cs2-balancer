from __future__ import annotations

from html import escape
from typing import Any

from exporters.html_v2.report_context import (
    PlayerReportData,
    ReportContext,
)
from exporters.html_v2.sections.section import (
    HtmlSection,
)


class RankingSection(HtmlSection):
    """
    Ranking individual de jugadores.

    La sección utiliza exclusivamente ReportContext y los componentes
    visuales existentes en ReportStyles.

    El orden del ranking viene determinado por:

        context.ranking

    que actualmente ordena por:

        1. Power final.
        2. Power base.
        3. ELO.
        4. Nick.

    El Power final representa la fuerza utilizada realmente por el
    modelo después de aplicar, cuando corresponda, el ajuste de
    actividad.

    La sección funciona tanto para:

        - Optimización automática.
        - Evaluación de equipos preasignados.

    No conoce OptimizationResult ni EvaluationResult.
    """

    @property
    def name(
        self,
    ) -> str:
        return "ranking"

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

        if not context.ranking:
            return self._build_empty_state(
                context
            )

        return f"""
<div class="section ranking-section">

    {self._build_heading(context)}

    {self._build_highlights(context)}

    {self._build_table(context)}

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
                "ANÁLISIS INDIVIDUAL"
            )

            title = (
                "Ranking de jugadores"
            )

            description = (
                "Clasificación individual ordenada por Power final. "
                "Los equipos mostrados corresponden exactamente a "
                "la asignación definida mediante la columna Team."
            )

        else:
            eyebrow = (
                "POWER RANKING"
            )

            title = (
                "Ranking individual"
            )

            description = (
                "Clasificación de los jugadores utilizando el Power "
                "final empleado por el motor de balanceo."
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

    <span class="section-counter">
        {context.player_count} jugadores
    </span>
</div>
"""

    # ========================================================
    # Highlights
    # ========================================================

    def _build_highlights(
        self,
        context: ReportContext,
    ) -> str:
        ranking = context.ranking

        strongest = (
            ranking[0]
        )

        weakest = (
            ranking[-1]
        )

        average_power = (
            sum(
                player.final_power
                for player in ranking
            )
            / len(ranking)
        )

        return f"""
<div class="ranking-highlight-grid">

    {self._build_highlight_card(
        label="Mayor Power",
        badge="TOP 1",
        player=strongest.nickname,
        value=f"{strongest.final_power:.2f}",
        detail=self._player_highlight_detail(
            strongest
        ),
        danger=False,
    )}

    {self._build_highlight_card(
        label="Power medio",
        badge=f"{len(ranking)} jugadores",
        player="Promedio del ranking",
        value=f"{average_power:.2f}",
        detail=(
            "Media del Power final de todos "
            "los jugadores analizados."
        ),
        danger=False,
    )}

    {self._build_highlight_card(
        label="Menor Power",
        badge=f"#{len(ranking)}",
        player=weakest.nickname,
        value=f"{weakest.final_power:.2f}",
        detail=self._player_highlight_detail(
            weakest
        ),
        danger=True,
    )}

</div>
"""

    @staticmethod
    def _build_highlight_card(
        label: str,
        badge: str,
        player: str,
        value: str,
        detail: str,
        danger: bool,
    ) -> str:
        value_class = (
            "highlight-value danger"
            if danger
            else "highlight-value"
        )

        return f"""
<article class="ranking-highlight-card">

    <div class="highlight-card-top">
        <span class="highlight-label">
            {escape(label)}
        </span>

        <span class="highlight-badge">
            {escape(badge)}
        </span>
    </div>

    <strong class="highlight-player">
        {escape(player)}
    </strong>

    <span class="{value_class}">
        {escape(value)}
    </span>

    <small>
        {escape(detail)}
    </small>

</article>
"""

    # ========================================================
    # Tabla
    # ========================================================

    def _build_table(
        self,
        context: ReportContext,
    ) -> str:
        rows = "\n".join(
            self._build_player_row(
                position=position,
                player=player,
                context=context,
            )
            for position, player in enumerate(
                context.ranking,
                start=1,
            )
        )

        team_csv_header = ""

        if context.evaluation_only:
            team_csv_header = """
<th>
    Team CSV
</th>
"""

        return f"""
<div class="table-panel">

    <div class="table-toolbar">
        <div>
            <strong>
                Clasificación completa
            </strong>

            <span>
                Ordenada por Power final
            </span>
        </div>

        <div>
            <strong>
                {context.player_count}
            </strong>

            <span>
                jugadores
            </span>
        </div>
    </div>

    <div class="table-scroll">

        <table class="data-table ranking-data-table">

            <thead>
                <tr>
                    <th>
                        #
                    </th>

                    <th>
                        Jugador
                    </th>

                    <th>
                        Equipo
                    </th>

                    {team_csv_header}

                    <th class="numeric-cell">
                        Power final
                    </th>

                    <th class="numeric-cell">
                        Power base
                    </th>

                    <th>
                        Actividad
                    </th>

                    <th class="numeric-cell">
                        ELO
                    </th>

                    <th class="numeric-cell">
                        Nivel
                    </th>

                    <th class="numeric-cell">
                        KD
                    </th>

                    <th class="numeric-cell">
                        ADR
                    </th>

                    <th class="numeric-cell">
                        Rating
                    </th>

                    <th class="numeric-cell">
                        Winrate
                    </th>

                    <th>
                        Seed
                    </th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>

        </table>

    </div>

</div>
"""

    # ========================================================
    # Fila
    # ========================================================

    def _build_player_row(
        self,
        position: int,
        player: PlayerReportData,
        context: ReportContext,
    ) -> str:
        delta = (
            player.final_power
            - player.base_power
        )

        team_csv_cell = ""

        if context.evaluation_only:
            team_csv_cell = f"""
<td>
    {
        self._build_team_pill(
            player.assigned_team_number
        )
    }
</td>
"""

        return f"""
<tr>

    <td>
        {self._build_position(position)}
    </td>

    <td>
        {self._build_player_identity(player)}
    </td>

    <td>
        <span class="team-pill">
            {escape(player.team_name)}
        </span>
    </td>

    {team_csv_cell}

    <td class="numeric-cell">
        <strong class="final-power-value">
            {player.final_power:.2f}
        </strong>

        {self._build_power_delta(delta)}
    </td>

    <td class="numeric-cell">
        {player.base_power:.2f}
    </td>

    <td>
        {self._build_activity(player)}
    </td>

    <td class="numeric-cell">
        {self._format_optional(
            player.elo,
            decimals=0,
        )}
    </td>

    <td class="numeric-cell">
        {self._format_optional(
            player.level,
            decimals=0,
        )}
    </td>

    <td class="numeric-cell">
        {self._format_optional(
            player.kd,
            decimals=2,
        )}
    </td>

    <td class="numeric-cell">
        {self._format_optional(
            player.adr,
            decimals=1,
        )}
    </td>

    <td class="numeric-cell">
        {self._format_optional(
            player.rating,
            decimals=2,
        )}
    </td>

    <td class="numeric-cell">
        {self._format_percentage(
            player.winrate
        )}
    </td>

    <td>
        {self._build_seed(player)}
    </td>

</tr>
"""

    # ========================================================
    # Posición
    # ========================================================

    @staticmethod
    def _build_position(
        position: int,
    ) -> str:
        if position == 1:
            return """
<span
    class="micro-badge warning"
    title="Primera posición"
>
    #1
</span>
"""

        if position == 2:
            return """
<span
    class="micro-badge neutral"
    title="Segunda posición"
>
    #2
</span>
"""

        if position == 3:
            return """
<span
    class="micro-badge neutral"
    title="Tercera posición"
>
    #3
</span>
"""

        return f"""
<span class="muted-value">
    #{position}
</span>
"""

    # ========================================================
    # Jugador
    # ========================================================

    @staticmethod
    def _build_player_identity(
        player: PlayerReportData,
    ) -> str:
        metadata: list[str] = []

        if player.role:
            metadata.append(
                f"""
<span class="micro-badge neutral">
    {escape(player.role)}
</span>
"""
            )

        if (
            player.seed
            is not None
        ):
            metadata.append(
                f"""
<span class="micro-badge warning">
    Seed {player.seed}
</span>
"""
            )

        profile = ""

        if player.profile_url:
            profile = f"""
<a
    href="{escape(
        player.profile_url,
        quote=True,
    )}"
    target="_blank"
    rel="noopener noreferrer"
    class="player-profile-link"
>
    Ver perfil
</a>
"""

        meta_html = ""

        if metadata:
            meta_html = f"""
<div class="player-meta-line">
    {"".join(metadata)}
</div>
"""

        return f"""
<div class="ranking-player">

    <strong>
        {escape(player.nickname)}
    </strong>

    {meta_html}

    {profile}

</div>
"""

    # ========================================================
    # Equipo
    # ========================================================

    @staticmethod
    def _build_team_pill(
        team_number: int | None,
    ) -> str:
        if team_number is None:
            return """
<span class="muted-value">
    —
</span>
"""

        return f"""
<span class="team-pill">
    Team {team_number}
</span>
"""

    # ========================================================
    # Seed
    # ========================================================

    @staticmethod
    def _build_seed(
        player: PlayerReportData,
    ) -> str:
        if player.seed is None:
            return """
<span class="muted-value">
    —
</span>
"""

        return f"""
<span class="seed-badge">
    {player.seed}
</span>
"""

    # ========================================================
    # Actividad
    # ========================================================

    def _build_activity(
        self,
        player: PlayerReportData,
    ) -> str:
        activity_class = (
            self._activity_class(
                player.activity_factor
            )
        )

        percentage = (
            player.activity_percentage
        )

        matches_text = (
            self._activity_matches_text(
                player
            )
        )

        progress_width = max(
            0.0,
            min(
                100.0,
                percentage,
            ),
        )

        return f"""
<div class="activity-cell compact">

    <div class="activity-value-line">
        <strong class="{activity_class}">
            {percentage:.0f}%
        </strong>
    </div>

    <div class="mini-progress">
        <span
            class="{activity_class}"
            style="
                width:
                {progress_width:.2f}%;
            "
        ></span>
    </div>

    <small class="muted-value">
        {escape(matches_text)}
    </small>

</div>
"""

    @staticmethod
    def _activity_class(
        activity_factor: float,
    ) -> str:
        if activity_factor >= 0.90:
            return "activity-high"

        if activity_factor >= 0.75:
            return "activity-medium"

        return "activity-low"

    @staticmethod
    def _activity_matches_text(
        player: PlayerReportData,
    ) -> str:
        if not player.has_activity_data:
            return "Sin historial"

        matches = (
            player.total_matches_90_days
        )

        if matches is None:
            return "Historial disponible"

        if matches == 0:
            return "0 partidas / 90d"

        if matches == 1:
            return "1 partida / 90d"

        return (
            f"{matches} partidas / 90d"
        )

    # ========================================================
    # Power
    # ========================================================

    @staticmethod
    def _build_power_delta(
        delta: float,
    ) -> str:
        if abs(delta) < 0.005:
            return """
<span class="power-delta neutral">
    Sin ajuste
</span>
"""

        css_class = (
            "positive"
            if delta > 0.0
            else "negative"
        )

        return f"""
<span class="power-delta {css_class}">
    {delta:+.2f}
</span>
"""

    # ========================================================
    # Highlight detail
    # ========================================================

    @staticmethod
    def _player_highlight_detail(
        player: PlayerReportData,
    ) -> str:
        parts = [
            player.team_name,
        ]

        if player.elo is not None:
            parts.append(
                f"ELO {player.elo}"
            )

        if player.seed is not None:
            parts.append(
                f"Seed {player.seed}"
            )

        return " · ".join(
            parts
        )

    # ========================================================
    # Formato
    # ========================================================

    @staticmethod
    def _format_optional(
        value: Any,
        decimals: int = 2,
    ) -> str:
        if (
            value is None
            or isinstance(
                value,
                bool,
            )
        ):
            return "N/A"

        try:
            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return "N/A"

        if decimals == 0:
            return str(
                int(
                    round(
                        numeric_value
                    )
                )
            )

        return (
            f"{numeric_value:.{decimals}f}"
        )

    @staticmethod
    def _format_percentage(
        value: float | None,
    ) -> str:
        if value is None:
            return "N/A"

        try:
            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return "N/A"

        return (
            f"{numeric_value:.1f}%"
        )

    # ========================================================
    # Empty
    # ========================================================

    @staticmethod
    def _build_empty_state(
        context: ReportContext,
    ) -> str:
        return """
<div class="section ranking-section">

    <div class="section-title">
        <div>
            <p class="eyebrow">
                POWER RANKING
            </p>

            <h2>
                Ranking individual
            </h2>
        </div>
    </div>

    <div class="empty-panel">
        No existen jugadores disponibles para generar
        el ranking.
    </div>

</div>
"""

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
