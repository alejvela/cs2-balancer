from __future__ import annotations

from collections.abc import Iterable
from html import escape
from pathlib import Path

from application.results.base_report_result import (
    BaseReportResult,
)
from exporters.html_v2.report_context import (
    ReportContext,
)
from exporters.html_v2.sections.activity_section import (
    ActivitySection,
)
from exporters.html_v2.sections.ranking_section import (
    RankingSection,
)
from exporters.html_v2.sections.section import (
    HtmlSection,
)
from exporters.html_v2.sections.summary_section import (
    SummarySection,
)
from exporters.html_v2.sections.teams_section import (
    TeamsSection,
)
from exporters.html_v2.styles import ReportStyles
from scoring.scoring_model import ScoringModel


class HtmlExporterV2:
    """
    Exportador modular del informe HTML.

    Acepta cualquier BaseReportResult y genera un informe con
    navegación por pestañas.

    Secciones predeterminadas:

        - Resumen.
        - Ranking.
        - Actividad.
        - Equipos.

    Las secciones consumen ReportContext, por lo que el exportador no
    necesita conocer OptimizationResult ni EvaluationResult.
    """

    def __init__(
        self,
        scoring_model: ScoringModel | None = None,
        title: str = "LAN CS2 — Análisis de equipos",
        sections: Iterable[HtmlSection] | None = None,
    ) -> None:
        if (
            scoring_model is not None
            and not isinstance(
                scoring_model,
                ScoringModel,
            )
        ):
            raise TypeError(
                "scoring_model must be a ScoringModel or None."
            )

        self._scoring_model = scoring_model

        self._title = self._validate_required_text(
            value=title,
            field_name="title",
        )

        self._sections = self._validate_sections(
            sections
            if sections is not None
            else self._default_sections()
        )

    def export(
        self,
        result: BaseReportResult,
        output: str | Path,
    ) -> Path:
        validated_result = self._validate_result(
            result
        )

        output_path = self._prepare_output_path(
            output
        )

        context = ReportContext(
            result=validated_result,
            scoring_model=self._scoring_model,
            title=self._title,
        )

        html = self._build_document(
            context
        )

        output_path.write_text(
            html,
            encoding="utf-8",
        )

        return output_path

    def _build_document(
        self,
        context: ReportContext,
    ) -> str:
        first_section = self._section_identifier(
            self._sections[0]
        )

        navigation = self._build_navigation()

        panels = "\n".join(
            self._build_section_panel(
                section=section,
                context=context,
                active=index == 0,
            )
            for index, section in enumerate(
                self._sections
            )
        )

        return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">

    <meta
        name="viewport"
        content="
            width=device-width,
            initial-scale=1,
            maximum-scale=5,
            viewport-fit=cover
        "
    >

    <meta
        name="description"
        content="Informe de análisis competitivo de equipos de CS2"
    >

    <meta
        name="theme-color"
        content="#080a0f"
    >

    <title>
        {escape(context.title)}
    </title>

    <style>
        {ReportStyles.render()}
    </style>

    <noscript>
        <style>
            .report-navigation {{
                display: none !important;
            }}

            .section-panel {{
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: auto !important;
                margin-bottom: 48px;
            }}
        </style>
    </noscript>
</head>

<body
    data-default-section="{escape(first_section)}"
    data-report-mode="{escape(context.mode_value)}"
>
    <main class="container">

        {self._build_header(context)}

        {navigation}

        <div class="section-panels">
            {panels}
        </div>

        {self._build_footer(context)}

    </main>

    <script>
        {self._scripts()}
    </script>
</body>
</html>
"""

    @staticmethod
    def _build_header(
        context: ReportContext,
    ) -> str:
        mode_class = escape(
            context.mode.css_class
        )

        validity_class = (
            "valid"
            if context.is_valid
            else "invalid"
        )

        validity_text = (
            "Composición válida"
            if context.is_valid
            else "Composición con penalizaciones"
        )

        score_label = (
            "Puntuación de equilibrio"
            if context.evaluation_only
            else "Puntuación final"
        )

        process_detail = (
            "La distribución se ha evaluado sin modificar "
            "la asignación de jugadores."
            if context.evaluation_only
            else (
                f"Mejora obtenida: "
                f"{context.improvement:+.2f} puntos."
            )
        )

        return f"""
<header class="report-mode-banner {mode_class}">

    <div class="report-mode-copy">

        <div class="report-mode-badges">

            <span class="report-mode-badge">
                {escape(context.mode_short_label)}
            </span>

            <span class="status {validity_class}">
                {escape(validity_text)}
            </span>

        </div>

        <span class="eyebrow">
            CS2 LAN TEAM BALANCER
        </span>

        <h1>
            {escape(context.title)}
        </h1>

        <p>
            {escape(context.result_description)}
        </p>

        <p class="report-mode-detail">
            {escape(process_detail)}
        </p>

    </div>

    <div class="report-mode-score">

        <span>
            {escape(score_label)}
        </span>

        <strong>
            {context.final_score:.2f}
        </strong>

        <small
            class="
                balance-level
                {escape(context.balance_level)}
            "
        >
            {escape(context.balance_label)}
        </small>

    </div>

</header>
"""

    def _build_navigation(
        self,
    ) -> str:
        links = "\n".join(
            self._build_navigation_link(
                section=section,
                active=index == 0,
            )
            for index, section in enumerate(
                self._sections
            )
        )

        return f"""
<nav
    class="report-navigation"
    aria-label="Secciones del informe"
>
    <div
        class="navigation-scroll"
        role="tablist"
        aria-label="Contenido del informe"
    >
        {links}
    </div>
</nav>
"""

    @classmethod
    def _build_navigation_link(
        cls,
        section: HtmlSection,
        active: bool,
    ) -> str:
        identifier = cls._section_identifier(
            section
        )

        active_class = (
            " is-active"
            if active
            else ""
        )

        selected = (
            "true"
            if active
            else "false"
        )

        tab_index = (
            "0"
            if active
            else "-1"
        )

        return f"""
<a
    href="#{escape(identifier)}"
    id="tab-{escape(identifier)}"
    class="navigation-button{active_class}"
    data-target="{escape(identifier)}"
    role="tab"
    aria-controls="panel-{escape(identifier)}"
    aria-selected="{selected}"
    tabindex="{tab_index}"
>
    {escape(cls._section_label(section))}
</a>
"""

    @classmethod
    def _build_section_panel(
        cls,
        section: HtmlSection,
        context: ReportContext,
        active: bool,
    ) -> str:
        identifier = cls._section_identifier(
            section
        )

        active_class = (
            " is-active"
            if active
            else ""
        )

        aria_hidden = (
            "false"
            if active
            else "true"
        )

        return f"""
<section
    id="panel-{escape(identifier)}"
    class="section-panel{active_class}"
    data-section="{escape(identifier)}"
    role="tabpanel"
    aria-labelledby="tab-{escape(identifier)}"
    aria-hidden="{aria_hidden}"
>
    {section.render(context)}
</section>
"""

    @staticmethod
    def _section_identifier(
        section: HtmlSection,
    ) -> str:
        return (
            section.name
            .strip()
            .casefold()
            .replace("_", "-")
            .replace(" ", "-")
        )

    @staticmethod
    def _section_label(
        section: HtmlSection,
    ) -> str:
        labels = {
            "summary": "Resumen",
            "ranking": "Ranking",
            "activity": "Actividad",
            "teams": "Equipos",
            "restrictions": "Restricciones",
            "history": "Historial",
        }

        normalized = (
            section.name
            .strip()
            .casefold()
        )

        return labels.get(
            normalized,
            section.name.replace(
                "_",
                " ",
            ).title(),
        )

    @staticmethod
    def _build_footer(
        context: ReportContext,
    ) -> str:
        return f"""
<footer class="report-footer">
    <span>
        Informe generado por LAN CS2 Team Balancer.
    </span>

    <span>
        Modo: {escape(context.mode_label)}
    </span>
</footer>
"""

    @staticmethod
    def _scripts() -> str:
        return r"""
(function () {
    "use strict";

    var links = Array.prototype.slice.call(
        document.querySelectorAll(
            ".navigation-button[data-target]"
        )
    );

    var panels = Array.prototype.slice.call(
        document.querySelectorAll(
            ".section-panel[data-section]"
        )
    );

    if (!links.length || !panels.length) {
        return;
    }

    var defaultSection = (
        document.body.getAttribute(
            "data-default-section"
        )
        || links[0].getAttribute(
            "data-target"
        )
    );

    function normalize(value) {
        return String(value || "")
            .replace(/^#/, "")
            .trim()
            .toLowerCase();
    }

    function exists(sectionName) {
        return panels.some(
            function (panel) {
                return (
                    panel.getAttribute(
                        "data-section"
                    )
                    === sectionName
                );
            }
        );
    }

    function activate(
        requestedSection,
        updateHash,
        focusTab
    ) {
        var sectionName = normalize(
            requestedSection
        );

        if (!exists(sectionName)) {
            sectionName = defaultSection;
        }

        links.forEach(
            function (link) {
                var active = (
                    link.getAttribute(
                        "data-target"
                    )
                    === sectionName
                );

                link.classList.toggle(
                    "is-active",
                    active
                );

                link.setAttribute(
                    "aria-selected",
                    active
                        ? "true"
                        : "false"
                );

                link.setAttribute(
                    "tabindex",
                    active
                        ? "0"
                        : "-1"
                );

                if (
                    active
                    && focusTab
                ) {
                    try {
                        link.focus({
                            preventScroll: true
                        });
                    } catch (error) {
                        link.focus();
                    }
                }
            }
        );

        panels.forEach(
            function (panel) {
                var active = (
                    panel.getAttribute(
                        "data-section"
                    )
                    === sectionName
                );

                panel.classList.toggle(
                    "is-active",
                    active
                );

                panel.setAttribute(
                    "aria-hidden",
                    active
                        ? "false"
                        : "true"
                );
            }
        );

        if (updateHash) {
            var hash = (
                "#" + sectionName
            );

            if (
                window.location.hash
                !== hash
            ) {
                if (
                    window.history
                    && window.history.replaceState
                ) {
                    window.history.replaceState(
                        null,
                        "",
                        hash
                    );
                } else {
                    window.location.hash = (
                        sectionName
                    );
                }
            }
        }
    }

    links.forEach(
        function (link) {
            link.addEventListener(
                "click",
                function (event) {
                    event.preventDefault();

                    activate(
                        link.getAttribute(
                            "data-target"
                        ),
                        true,
                        false
                    );
                },
                false
            );

            link.addEventListener(
                "touchend",
                function (event) {
                    event.preventDefault();

                    activate(
                        link.getAttribute(
                            "data-target"
                        ),
                        true,
                        false
                    );
                },
                {
                    passive: false
                }
            );
        }
    );

    document.addEventListener(
        "keydown",
        function (event) {
            if (
                event.key !== "ArrowLeft"
                && event.key !== "ArrowRight"
                && event.key !== "Home"
                && event.key !== "End"
            ) {
                return;
            }

            var currentIndex = links.findIndex(
                function (link) {
                    return link.classList.contains(
                        "is-active"
                    );
                }
            );

            if (currentIndex < 0) {
                currentIndex = 0;
            }

            event.preventDefault();

            var nextIndex = currentIndex;

            if (event.key === "ArrowRight") {
                nextIndex = (
                    currentIndex + 1
                ) % links.length;
            }

            if (event.key === "ArrowLeft") {
                nextIndex = (
                    currentIndex
                    - 1
                    + links.length
                ) % links.length;
            }

            if (event.key === "Home") {
                nextIndex = 0;
            }

            if (event.key === "End") {
                nextIndex = (
                    links.length - 1
                );
            }

            var nextLink = links[
                nextIndex
            ];

            activate(
                nextLink.getAttribute(
                    "data-target"
                ),
                true,
                true
            );
        },
        false
    );

    window.addEventListener(
        "hashchange",
        function () {
            activate(
                window.location.hash,
                false,
                false
            );
        },
        false
    );

    function initialize() {
        activate(
            window.location.hash
            || defaultSection,
            false,
            false
        );

        document.documentElement.classList.add(
            "tabs-ready"
        );
    }

    if (
        document.readyState
        === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initialize,
            false
        );
    } else {
        initialize();
    }
})();
"""

    @staticmethod
    def _default_sections() -> tuple[HtmlSection, ...]:
        return (
            SummarySection(),
            RankingSection(),
            ActivitySection(),
            TeamsSection(),
        )

    @staticmethod
    def _validate_sections(
        sections: Iterable[HtmlSection],
    ) -> tuple[HtmlSection, ...]:
        if sections is None:
            raise ValueError(
                "sections cannot be None."
            )

        try:
            section_list = tuple(
                sections
            )

        except TypeError as error:
            raise TypeError(
                "sections must be iterable."
            ) from error

        if not section_list:
            raise ValueError(
                "At least one HTML section is required."
            )

        names: set[str] = set()

        for index, section in enumerate(
            section_list,
            start=1,
        ):
            if not isinstance(
                section,
                HtmlSection,
            ):
                raise TypeError(
                    f"Section {index} must be an HtmlSection."
                )

            normalized_name = (
                section.name
                .strip()
                .casefold()
            )

            if not normalized_name:
                raise ValueError(
                    f"Section {index} has an empty name."
                )

            if normalized_name in names:
                raise ValueError(
                    f"Duplicated section name "
                    f"'{section.name}'."
                )

            names.add(
                normalized_name
            )

        return section_list

    @staticmethod
    def _validate_result(
        result: BaseReportResult,
    ) -> BaseReportResult:
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            BaseReportResult,
        ):
            raise TypeError(
                "result must be a BaseReportResult instance."
            )

        return result

    @staticmethod
    def _validate_required_text(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _prepare_output_path(
        output: str | Path,
    ) -> Path:
        if output is None:
            raise ValueError(
                "output cannot be None."
            )

        if not isinstance(
            output,
            (
                str,
                Path,
            ),
        ):
            raise TypeError(
                "output must be a string or Path."
            )

        output_path = Path(
            output
        )

        if output_path.suffix.casefold() != ".html":
            output_path = output_path.with_suffix(
                ".html"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return output_path

    @property
    def scoring_model(
        self,
    ) -> ScoringModel | None:
        return self._scoring_model

    @property
    def title(
        self,
    ) -> str:
        return self._title

    @property
    def sections(
        self,
    ) -> tuple[HtmlSection, ...]:
        return self._sections

    def __repr__(
        self,
    ) -> str:
        section_names = ", ".join(
            section.name
            for section in self._sections
        )

        return (
            f"{self.__class__.__name__}("
            f"title={self._title!r}, "
            f"sections=[{section_names}])"
        )
