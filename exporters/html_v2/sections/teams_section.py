from __future__ import annotations

from html import escape
from typing import Any

from exporters.html_v2.report_context import (
    PlayerReportData,
    ReportContext,
    TeamReportData,
)
from exporters.html_v2.sections.section import (
    HtmlSection,
)


class TeamsSection(HtmlSection):
    """
    Muestra la composición y las estadísticas de todos los equipos.

    La sección trabaja exclusivamente con ReportContext y por tanto
    funciona con cualquier BaseReportResult.

    En modo optimizado:

        - Muestra los equipos finales.
        - Indica que la distribución procede del optimizador.
        - Permite comparar el Power final de cada equipo.

    En modo preasignado:

        - Muestra exactamente los equipos definidos mediante Team.
        - Señala explícitamente la asignación del CSV.
        - Permite evaluar estadísticamente la composición sin
          modificarla.

    Cada equipo incluye:

        - Power medio base.
        - Power medio ajustado por actividad.
        - ELO medio.
        - KD medio.
        - ADR medio.
        - Actividad media.
        - Cabezas de serie.
        - Jugadores y sus estadísticas.
    """

    @property
    def name(
        self,
    ) -> str:
        return "teams"

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

        teams_html = "\n".join(
            self._build_team(
                team=team,
                context=context,
            )
            for team in context.teams
        )

        return f"""
<div class="teams-section">
    {self._build_heading(context)}

    {self._build_global_comparison(context)}

    <div class="teams-report-grid">
        {teams_html}
    </div>
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
            eyebrow = "COMPOSICIÓN PREDETERMINADA"
            title = "Equipos evaluados"

            description = (
                "Los jugadores aparecen en los equipos definidos "
                "mediante la columna Team del CSV. La composición "
                "mostrada no ha sido modificada."
            )

        else:
            eyebrow = "DISTRIBUCIÓN FINAL"
            title = "Equipos optimizados"

            description = (
                "Esta es la composición final producida por el motor "
                "después de aplicar el proceso de optimización."
            )

        return f"""
<header class="section-heading">
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

    <div class="teams-heading-summary">
        <span>
            {context.team_count} equipos
        </span>

        <strong>
            {context.player_count} jugadores
        </strong>
    </div>
</header>
"""

    # ========================================================
    # Comparación general
    # ========================================================

    def _build_global_comparison(
        self,
        context: ReportContext,
    ) -> str:
        return f"""
<section class="teams-global-comparison">
    {self._global_metric(
        label="Power medio global",
        value=f"{context.average_final_power:.2f}",
        detail="Power ajustado por actividad",
    )}

    {self._global_metric(
        label="Diferencia máxima de Power",
        value=f"{context.power_spread:.2f}",
        detail="Entre el equipo más fuerte y el más débil",
    )}

    {self._global_metric(
        label="Diferencia ELO medio",
        value=self._format_optional(
            context.elo_spread,
            decimals=1,
        ),
        detail="Dispersión entre equipos",
    )}

    {self._global_metric(
        label="Diferencia KD medio",
        value=self._format_optional(
            context.kd_spread,
            decimals=3,
        ),
        detail="Dispersión entre equipos",
    )}
</section>
"""

    @staticmethod
    def _global_metric(
        label: str,
        value: str,
        detail: str,
    ) -> str:
        return f"""
<article class="teams-global-metric">
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

    # ========================================================
    # Equipo
    # ========================================================

    def _build_team(
        self,
        team: TeamReportData,
        context: ReportContext,
    ) -> str:
        strongest = (
            context.strongest_team is not None
            and team.index
            == context.strongest_team.index
        )

        weakest = (
            context.weakest_team is not None
            and team.index
            == context.weakest_team.index
        )

        card_classes = [
            "team-report-card",
        ]

        if strongest:
            card_classes.append(
                "strongest-team"
            )

        if weakest:
            card_classes.append(
                "weakest-team"
            )

        class_attribute = " ".join(
            card_classes
        )

        players_html = "\n".join(
            self._build_player_row(
                player=player,
                context=context,
            )
            for player in team.players
        )

        badge = self._build_team_badge(
            team=team,
            context=context,
            strongest=strongest,
            weakest=weakest,
        )

        return f"""
<article
    class="{escape(class_attribute)}"
    data-team-index="{team.index}"
>
    <header class="team-report-header">
        <div>
            <span class="team-report-index">
                Equipo {team.index}
            </span>

            <h3>
                {escape(team.name)}
            </h3>

            {badge}
        </div>

        <div class="team-report-power">
            <span>
                Power medio
            </span>

            <strong>
                {team.average_final_power:.2f}
            </strong>
        </div>
    </header>

    {self._build_team_statistics(team)}

    {self._build_seed_information(team)}

    <div class="team-player-table-wrapper">
        <table class="team-player-table">
            <thead>
                <tr>
                    <th>
                        Jugador
                    </th>

                    <th>
                        Power
                    </th>

                    <th>
                        Base
                    </th>

                    <th>
                        Actividad
                    </th>

                    <th>
                        ELO
                    </th>

                    <th>
                        LVL
                    </th>

                    <th>
                        KD
                    </th>

                    <th>
                        ADR
                    </th>

                    <th>
                        Seed
                    </th>

                    {
                        "<th>Team CSV</th>"
                        if context.evaluation_only
                        else ""
                    }
                </tr>
            </thead>

            <tbody>
                {players_html}
            </tbody>
        </table>
    </div>
</article>
"""

    # ========================================================
    # Badge del equipo
    # ========================================================

    @staticmethod
    def _build_team_badge(
        team: TeamReportData,
        context: ReportContext,
        strongest: bool,
        weakest: bool,
    ) -> str:
        badges: list[str] = []

        if context.evaluation_only:
            badges.append(
                f"""
<span class="team-badge preassigned">
    Asignación CSV · Team {team.index}
</span>
"""
            )

        if strongest:
            badges.append(
                """
<span class="team-badge strongest">
    Mayor Power medio
</span>
"""
            )

        if weakest:
            badges.append(
                """
<span class="team-badge weakest">
    Menor Power medio
</span>
"""
            )

        if not badges:
            return ""

        return (
            '<div class="team-badge-list">'
            + "".join(badges)
            + "</div>"
        )

    # ========================================================
    # Estadísticas de equipo
    # ========================================================

    def _build_team_statistics(
        self,
        team: TeamReportData,
    ) -> str:
        return f"""
<div class="team-report-statistics">
    {self._team_stat(
        label="Power base",
        value=f"{team.average_base_power:.2f}",
    )}

    {self._team_stat(
        label="Power final",
        value=f"{team.average_final_power:.2f}",
    )}

    {self._team_stat(
        label="ELO medio",
        value=self._format_optional(
            team.average_elo,
            decimals=0,
        ),
    )}

    {self._team_stat(
        label="KD medio",
        value=self._format_optional(
            team.average_kd,
            decimals=3,
        ),
    )}

    {self._team_stat(
        label="ADR medio",
        value=self._format_optional(
            team.average_adr,
            decimals=1,
        ),
    )}

    {self._team_stat(
        label="Rating medio",
        value=self._format_optional(
            team.average_rating,
            decimals=3,
        ),
    )}

    {self._team_stat(
        label="Winrate medio",
        value=self._format_percentage(
            team.average_winrate
        ),
    )}

    {self._team_stat(
        label="Actividad",
        value=f"{team.activity_percentage:.1f}%",
    )}

    {self._team_stat(
        label="Seeds",
        value=str(
            team.seed_count
        ),
    )}

    {self._team_stat(
        label="Jugadores",
        value=str(
            team.player_count
        ),
    )}
</div>
"""

    @staticmethod
    def _team_stat(
        label: str,
        value: str,
    ) -> str:
        return f"""
<div class="team-report-stat">
    <span>
        {escape(label)}
    </span>

    <strong>
        {escape(value)}
    </strong>
</div>
"""

    # ========================================================
    # Seeds
    # ========================================================

    @staticmethod
    def _build_seed_information(
        team: TeamReportData,
    ) -> str:
        if not team.seeded_players:
            return ""

        seeded_players = ", ".join(
            (
                f"{player.nickname} "
                f"(Seed {player.seed})"
            )
            for player in team.seeded_players
        )

        return f"""
<div class="team-seed-information">
    <span>
        Cabezas de serie
    </span>

    <strong>
        {escape(seeded_players)}
    </strong>
</div>
"""

    # ========================================================
    # Jugadores
    # ========================================================

    def _build_player_row(
        self,
        player: PlayerReportData,
        context: ReportContext,
    ) -> str:
        power_delta = (
            player.final_power
            - player.base_power
        )

        activity_class = self._activity_class(
            player.activity_factor
        )

        seed_html = (
            f"""
<span class="player-seed-badge">
    Seed {player.seed}
</span>
"""
            if player.seed is not None
            else "—"
        )

        assigned_team_html = ""

        if context.evaluation_only:
            team_number = (
                str(
                    player.assigned_team_number
                )
                if (
                    player.assigned_team_number
                    is not None
                )
                else "—"
            )

            assigned_team_html = f"""
<td>
    <span class="assigned-team-badge">
        {escape(team_number)}
    </span>
</td>
"""

        return f"""
<tr>
    <td>
        {self._build_player_identity(player)}
    </td>

    <td>
        <div class="player-power-cell">
            <strong>
                {player.final_power:.2f}
            </strong>

            {self._build_power_delta(
                power_delta
            )}
        </div>
    </td>

    <td>
        {player.base_power:.2f}
    </td>

    <td>
        <div class="player-activity-cell">
            <span
                class="
                    activity-indicator
                    {escape(activity_class)}
                "
            >
                {player.activity_percentage:.0f}%
            </span>

            <small>
                {self._activity_matches_text(
                    player
                )}
            </small>
        </div>
    </td>

    <td>
        {self._format_optional(
            player.elo,
            decimals=0,
        )}
    </td>

    <td>
        {self._format_optional(
            player.level,
            decimals=0,
        )}
    </td>

    <td>
        {self._format_optional(
            player.kd,
            decimals=2,
        )}
    </td>

    <td>
        {self._format_optional(
            player.adr,
            decimals=1,
        )}
    </td>

    <td>
        {seed_html}
    </td>

    {assigned_team_html}
</tr>
"""

    # ========================================================
    # Identidad del jugador
    # ========================================================

    @staticmethod
    def _build_player_identity(
        player: PlayerReportData,
    ) -> str:
        role_html = ""

        if player.role:
            role_html = f"""
<span class="player-role-label">
    {escape(player.role)}
</span>
"""

        profile_html = ""

        if player.profile_url:
            profile_html = f"""
<a
    href="{escape(player.profile_url, quote=True)}"
    target="_blank"
    rel="noopener noreferrer"
    class="player-profile-link"
>
    Perfil
</a>
"""

        return f"""
<div class="team-player-identity">
    <strong>
        {escape(player.nickname)}
    </strong>

    <div class="team-player-meta">
        {role_html}
        {profile_html}
    </div>
</div>
"""

    # ========================================================
    # Actividad
    # ========================================================

    @staticmethod
    def _activity_class(
        activity_factor: float,
    ) -> str:
        if activity_factor >= 0.90:
            return "high"

        if activity_factor >= 0.75:
            return "medium"

        return "low"

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
            return "Actividad disponible"

        if matches == 1:
            return "1 partida / 90d"

        return (
            f"{matches} partidas / 90d"
        )

    # ========================================================
    # Variación de Power
    # ========================================================

    @staticmethod
    def _build_power_delta(
        delta: float,
    ) -> str:
        if abs(delta) < 0.005:
            return """
<small class="power-delta neutral">
    =
</small>
"""

        css_class = (
            "positive"
            if delta > 0.0
            else "negative"
        )

        return f"""
<small class="power-delta {css_class}">
    {delta:+.2f}
</small>
"""

    # ========================================================
    # Formato
    # ========================================================

    @staticmethod
    def _format_optional(
        value: Any,
        decimals: int = 2,
    ) -> str:
        if value is None:
            return "N/A"

        if isinstance(
            value,
            bool,
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

        return f"{float(value):.1f}%"

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r})"
        )
