from __future__ import annotations

from html import escape
from statistics import mean

from exporters.html_v2.report_context import (
    PlayerReportData,
    ReportContext,
)
from exporters.html_v2.sections.section import (
    HtmlSection,
)


class ActivitySection(HtmlSection):
    """
    Sección de análisis de actividad competitiva.

    Esta sección explica de forma transparente las dos fases del
    ajuste por actividad:

        1. Actividad observada.

            Se calcula exclusivamente a partir de las partidas jugadas
            en las ventanas:

                - 0–7 días.
                - 8–30 días.
                - 31–90 días.

        2. Impacto sobre el Power.

            La actividad observada produce primero un factor base.

            Después, el nivel FACEIT modifica únicamente la intensidad
            de la penalización:

                actividad
                    ↓
                factor base
                    ↓
                ajuste por nivel FACEIT
                    ↓
                factor efectivo
                    ↓
                Power final

    La sección NO recalcula ningún valor.

    Todos los datos proceden de:

        ScoringModel
            ↓
        ActivityFactorModel
            ↓
        ReportContext

    Por tanto, los valores mostrados coinciden exactamente con los que
    utiliza el balanceador.
    """

    @property
    def name(
        self,
    ) -> str:
        return "activity"

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

        if not context.players:
            return self._build_empty_state()

        players = self._sorted_players(
            context
        )

        return f"""
<div class="section activity-section">

    {self._build_heading(context)}

    {self._build_summary(players)}

    {self._build_model_explanation()}

    {self._build_table(players)}

</div>
"""

    # ========================================================
    # Encabezado
    # ========================================================

    @staticmethod
    def _build_heading(
        context: ReportContext,
    ) -> str:
        return f"""
<div class="section-title">

    <div>

        <p class="eyebrow">
            ESTADO DE FORMA
        </p>

        <h2>
            Actividad competitiva
        </h2>

        <p class="section-description">
            La actividad reciente modifica el Power del jugador.
            El nivel FACEIT no cambia la actividad observada:
            únicamente suaviza o endurece cuánto Power se pierde
            por falta de continuidad competitiva.
        </p>

    </div>

    <span class="section-counter">
        {context.player_count} jugadores
    </span>

</div>
"""

    # ========================================================
    # Resumen
    # ========================================================

    def _build_summary(
        self,
        players: tuple[PlayerReportData, ...],
    ) -> str:
        raw_activity = [
            player.activity_score
            for player in players
        ]

        base_factors = [
            player.base_activity_factor
            for player in players
        ]

        final_factors = [
            player.activity_factor
            for player in players
        ]

        level_adjustments = [
            player.level_adjustment
            for player in players
        ]

        penalties = [
            player.power_penalty
            for player in players
        ]

        average_raw_activity = (
            mean(raw_activity)
            if raw_activity
            else 1.0
        )

        average_base_factor = (
            mean(base_factors)
            if base_factors
            else 1.0
        )

        average_final_factor = (
            mean(final_factors)
            if final_factors
            else 1.0
        )

        average_level_adjustment = (
            mean(level_adjustments)
            if level_adjustments
            else 0.0
        )

        average_penalty = (
            mean(penalties)
            if penalties
            else 0.0
        )

        penalized_players = sum(
            1
            for player in players
            if player.is_activity_penalized
        )

        softened_players = sum(
            1
            for player in players
            if player.level_adjustment > 1e-9
        )

        hardened_players = sum(
            1
            for player in players
            if player.level_adjustment < -1e-9
        )

        return f"""
<div class="activity-summary-grid">

    {self._summary_card(
        label="Actividad observada",
        value=(
            f"{average_raw_activity * 100.0:.1f}%"
        ),
        detail="Actividad media real del grupo",
        tone=self._activity_tone(
            average_raw_activity
        ),
    )}

    {self._summary_card(
        label="Factor base",
        value=(
            f"{average_base_factor * 100.0:.1f}%"
        ),
        detail="Antes del ajuste por nivel FACEIT",
        tone=self._factor_tone(
            average_base_factor
        ),
    )}

    {self._summary_card(
        label="Factor efectivo",
        value=(
            f"{average_final_factor * 100.0:.1f}%"
        ),
        detail="Factor realmente aplicado al Power",
        tone=self._factor_tone(
            average_final_factor
        ),
    )}

    {self._summary_card(
        label="Ajuste medio por nivel",
        value=self._format_signed_percentage(
            average_level_adjustment
        ),
        detail=self._level_adjustment_summary(
            average_level_adjustment
        ),
        tone=self._adjustment_tone(
            average_level_adjustment
        ),
    )}

    {self._summary_card(
        label="Penalización media",
        value=f"-{average_penalty:.2f}",
        detail="Puntos de Power por jugador",
        tone=(
            "positive"
            if average_penalty <= 0.01
            else "warning"
        ),
    )}

    {self._summary_card(
        label="Jugadores penalizados",
        value=str(
            penalized_players
        ),
        detail=(
            f"{softened_players} suavizados · "
            f"{hardened_players} endurecidos"
        ),
        tone=(
            "warning"
            if penalized_players > 0
            else "positive"
        ),
    )}

</div>
"""

    @staticmethod
    def _summary_card(
        label: str,
        value: str,
        detail: str,
        tone: str,
    ) -> str:
        return f"""
<article
    class="
        activity-summary-card
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

    # ========================================================
    # Explicación del modelo
    # ========================================================

    @staticmethod
    def _build_model_explanation() -> str:
        return """
<div class="activity-explanation">

    <div class="activity-explanation-copy">

        <span class="eyebrow">
            MODELO DE ACTIVIDAD
        </span>

        <strong>
            Actividad y nivel FACEIT son dos conceptos independientes.
        </strong>

        <p>
            Dos jugadores con la misma actividad tienen el mismo
            activity score y el mismo factor base. El nivel FACEIT
            modifica únicamente cuánto de la penalización base termina
            afectando al Power.
        </p>

    </div>

    <div class="activity-window-grid">

        <div class="activity-window">

            <span>
                0–7 días
            </span>

            <strong>
                50%
            </strong>

            <small>
                Objetivo: 10 partidas
            </small>

        </div>

        <div class="activity-window">

            <span>
                8–30 días
            </span>

            <strong>
                30%
            </strong>

            <small>
                Objetivo: 20 partidas
            </small>

        </div>

        <div class="activity-window">

            <span>
                31–90 días
            </span>

            <strong>
                20%
            </strong>

            <small>
                Objetivo: 30 partidas
            </small>

        </div>

    </div>

</div>

<div class="activity-calculation-flow">

    <div class="activity-calculation-step">

        <span>
            1
        </span>

        <small>
            Actividad
        </small>

        <strong>
            Partidas recientes
        </strong>

    </div>

    <div class="activity-calculation-arrow">
        →
    </div>

    <div class="activity-calculation-step">

        <span>
            2
        </span>

        <small>
            Factor base
        </small>

        <strong>
            Actividad → Power
        </strong>

    </div>

    <div class="activity-calculation-arrow">
        →
    </div>

    <div class="activity-calculation-step">

        <span>
            3
        </span>

        <small>
            Nivel FACEIT
        </small>

        <strong>
            Intensidad
        </strong>

    </div>

    <div class="activity-calculation-arrow">
        →
    </div>

    <div class="activity-calculation-step">

        <span>
            4
        </span>

        <small>
            Factor efectivo
        </small>

        <strong>
            Power final
        </strong>

    </div>

</div>
"""

    # ========================================================
    # Tabla
    # ========================================================

    def _build_table(
        self,
        players: tuple[PlayerReportData, ...],
    ) -> str:
        rows = "\n".join(
            self._build_player_row(
                position=position,
                player=player,
            )
            for position, player in enumerate(
                players,
                start=1,
            )
        )

        return f"""
<div class="table-panel activity-table-panel">

    <div class="table-toolbar">

        <div>

            <strong>
                Desglose de actividad por jugador
            </strong>

            <span>
                Ordenado por mayor pérdida porcentual de Power
            </span>

        </div>

        <div>

            <strong>
                {len(players)}
            </strong>

            <span>
                jugadores
            </span>

        </div>

    </div>

    <div class="table-scroll">

        <table class="data-table activity-data-table">

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

                    <th class="numeric-cell">
                        LVL
                    </th>

                    <th class="numeric-cell">
                        Power base
                    </th>

                    <th>
                        Actividad real
                    </th>

                    <th>
                        Factor base
                    </th>

                    <th>
                        Ajuste LVL
                    </th>

                    <th>
                        Factor final
                    </th>

                    <th class="numeric-cell">
                        Penalización
                    </th>

                    <th class="numeric-cell">
                        Power final
                    </th>

                    <th class="numeric-cell">
                        0–7d
                    </th>

                    <th class="numeric-cell">
                        8–30d
                    </th>

                    <th class="numeric-cell">
                        31–90d
                    </th>

                    <th class="numeric-cell">
                        Total 90d
                    </th>

                    <th class="numeric-cell">
                        Última
                    </th>

                    <th>
                        Historial
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
    # Fila de jugador
    # ========================================================

    def _build_player_row(
        self,
        position: int,
        player: PlayerReportData,
    ) -> str:
        raw_activity_class = (
            self._activity_class(
                player.activity_score
            )
        )

        base_factor_class = (
            self._factor_class(
                player.base_activity_factor
            )
        )

        final_factor_class = (
            self._factor_class(
                player.activity_factor
            )
        )

        return f"""
<tr>

    <td>
        <span class="muted-value">
            #{position}
        </span>
    </td>

    <td>
        {self._build_player_identity(
            player
        )}
    </td>

    <td>
        <span class="team-pill">
            {escape(player.team_name)}
        </span>
    </td>

    <td class="numeric-cell">
        {self._format_level(
            player.faceit_level
        )}
    </td>

    <td class="numeric-cell">
        {player.base_power:.2f}
    </td>

    <td>
        {self._build_percentage_bar(
            value=player.activity_score,
            css_class=raw_activity_class,
            label=(
                f"{player.raw_activity_percentage:.1f}%"
            ),
        )}
    </td>

    <td>
        {self._build_percentage_bar(
            value=player.base_activity_factor,
            css_class=base_factor_class,
            label=(
                f"{player.base_activity_percentage:.1f}%"
            ),
        )}
    </td>

    <td>
        {self._build_level_adjustment(
            player
        )}
    </td>

    <td>
        {self._build_percentage_bar(
            value=player.activity_factor,
            css_class=final_factor_class,
            label=(
                f"{player.effective_activity_percentage:.1f}%"
            ),
        )}
    </td>

    <td class="numeric-cell">
        {self._build_penalty(
            player
        )}
    </td>

    <td class="numeric-cell">
        <strong class="final-power-value">
            {player.final_power:.2f}
        </strong>
    </td>

    <td class="numeric-cell">
        {self._format_matches(
            player.matches_0_7_days
        )}
    </td>

    <td class="numeric-cell">
        {self._format_matches(
            player.matches_8_30_days
        )}
    </td>

    <td class="numeric-cell">
        {self._format_matches(
            player.matches_31_90_days
        )}
    </td>

    <td class="numeric-cell">
        {self._format_matches(
            player.total_matches_90_days
        )}
    </td>

    <td class="numeric-cell">
        {self._format_last_match(
            player.days_since_last_match
        )}
    </td>

    <td>
        {self._build_history_status(
            player
        )}
    </td>

</tr>
"""

    # ========================================================
    # Jugador
    # ========================================================

    @staticmethod
    def _build_player_identity(
        player: PlayerReportData,
    ) -> str:
        profile_html = ""

        if player.profile_url:
            profile_html = f"""
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

        return f"""
<div class="activity-player">

    <strong>
        {escape(player.nickname)}
    </strong>

    {profile_html}

</div>
"""

    # ========================================================
    # Barras
    # ========================================================

    @staticmethod
    def _build_percentage_bar(
        value: float,
        css_class: str,
        label: str,
    ) -> str:
        progress = max(
            0.0,
            min(
                100.0,
                value * 100.0,
            ),
        )

        return f"""
<div class="activity-factor-cell">

    <div class="activity-value-line">

        <strong class="{escape(css_class)}">
            {escape(label)}
        </strong>

    </div>

    <div class="mini-progress">

        <span
            class="{escape(css_class)}"
            style="width: {progress:.2f}%;"
        ></span>

    </div>

</div>
"""

    # ========================================================
    # Ajuste por nivel
    # ========================================================

    @staticmethod
    def _build_level_adjustment(
        player: PlayerReportData,
    ) -> str:
        adjustment = (
            player.level_adjustment_percentage
        )

        strength = (
            player.level_penalty_strength
        )

        if abs(adjustment) <= 1e-9:
            css_class = "neutral"
            symbol = "±"
        elif adjustment > 0.0:
            css_class = "positive"
            symbol = "+"
        else:
            css_class = "negative"
            symbol = ""

        return f"""
<div class="activity-level-adjustment">

    <strong class="{escape(css_class)}">
        {symbol}{adjustment:.1f} pp
    </strong>

    <small>
        {strength:.2f}×
    </small>

</div>
"""

    # ========================================================
    # Penalización
    # ========================================================

    @staticmethod
    def _build_penalty(
        player: PlayerReportData,
    ) -> str:
        penalty = (
            player.power_penalty
        )

        percentage = (
            player.power_penalty_percentage
        )

        if penalty <= 0.005:
            return """
<div class="activity-penalty-detail">

    <span class="activity-penalty none">
        0.00
    </span>

    <small>
        0.0%
    </small>

</div>
"""

        return f"""
<div class="activity-penalty-detail">

    <span class="activity-penalty applied">
        -{penalty:.2f}
    </span>

    <small>
        -{percentage:.1f}%
    </small>

</div>
"""

    # ========================================================
    # Historial
    # ========================================================

    @staticmethod
    def _build_history_status(
        player: PlayerReportData,
    ) -> str:
        if not player.has_activity_data:
            return """
<span class="micro-badge danger">
    Sin datos
</span>
"""

        complete = (
            player.activity_history_complete
        )

        if complete is True:
            return """
<span class="micro-badge success">
    Completo
</span>
"""

        if complete is False:
            return """
<span class="micro-badge warning">
    Incompleto
</span>
"""

        return """
<span class="micro-badge neutral">
    Desconocido
</span>
"""

    # ========================================================
    # Orden
    # ========================================================

    @staticmethod
    def _sorted_players(
        context: ReportContext,
    ) -> tuple[PlayerReportData, ...]:
        """
        Orden de análisis:

            1. Mayor penalización porcentual de Power.
            2. Mayor penalización absoluta.
            3. Menor factor final.
            4. Mayor Power base.
            5. Nick.

        Esto permite que arriba aparezcan los jugadores para los que la
        inactividad tiene un mayor impacto relativo.
        """
        return tuple(
            sorted(
                context.players,
                key=lambda player: (
                    -player.power_penalty_percentage,
                    -player.power_penalty,
                    player.activity_factor,
                    -player.base_power,
                    player.nickname.casefold(),
                ),
            )
        )

    # ========================================================
    # Clasificación visual
    # ========================================================

    @staticmethod
    def _activity_class(
        activity_score: float,
    ) -> str:
        if activity_score >= 0.80:
            return "activity-high"

        if activity_score >= 0.50:
            return "activity-medium"

        return "activity-low"

    @staticmethod
    def _factor_class(
        factor: float,
    ) -> str:
        if factor >= 0.95:
            return "activity-high"

        if factor >= 0.85:
            return "activity-medium"

        return "activity-low"

    @staticmethod
    def _activity_tone(
        activity_score: float,
    ) -> str:
        if activity_score >= 0.80:
            return "positive"

        if activity_score >= 0.50:
            return "warning"

        return "negative"

    @staticmethod
    def _factor_tone(
        factor: float,
    ) -> str:
        if factor >= 0.95:
            return "positive"

        if factor >= 0.85:
            return "warning"

        return "negative"

    @staticmethod
    def _adjustment_tone(
        adjustment: float,
    ) -> str:
        if adjustment > 1e-9:
            return "positive"

        if adjustment < -1e-9:
            return "negative"

        return "neutral"

    @staticmethod
    def _level_adjustment_summary(
        adjustment: float,
    ) -> str:
        if adjustment > 1e-9:
            return (
                "El nivel suaviza la penalización media"
            )

        if adjustment < -1e-9:
            return (
                "El nivel endurece la penalización media"
            )

        return (
            "El nivel no altera la penalización media"
        )

    # ========================================================
    # Formato
    # ========================================================

    @staticmethod
    def _format_signed_percentage(
        value: float,
    ) -> str:
        percentage = (
            value
            * 100.0
        )

        if abs(
            percentage
        ) <= 1e-9:
            return "±0.0 pp"

        return (
            f"{percentage:+.1f} pp"
        )

    @staticmethod
    def _format_level(
        level: int | None,
    ) -> str:
        if level is None:
            return "—"

        return str(
            level
        )

    @staticmethod
    def _format_matches(
        value: int | None,
    ) -> str:
        if value is None:
            return "—"

        return str(
            value
        )

    @staticmethod
    def _format_last_match(
        days: int | None,
    ) -> str:
        if days is None:
            return "—"

        if days == 0:
            return "Hoy"

        if days == 1:
            return "1 día"

        return (
            f"{days} días"
        )

    # ========================================================
    # Empty state
    # ========================================================

    @staticmethod
    def _build_empty_state() -> str:
        return """
<div class="section activity-section">

    <div class="section-title">

        <div>

            <p class="eyebrow">
                ESTADO DE FORMA
            </p>

            <h2>
                Actividad competitiva
            </h2>

        </div>

    </div>

    <div class="empty-panel">
        No existen jugadores disponibles para analizar actividad.
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
