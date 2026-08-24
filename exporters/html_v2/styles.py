from __future__ import annotations


class ReportStyles:
    """
    Estilos autocontenidos del informe HTML v2.
    """

    @classmethod
    def render(
        cls,
    ) -> str:
        return """
:root {
    color-scheme: dark;

    --background: #080a0f;
    --background-soft: #0c0f16;
    --panel: rgba(17, 21, 30, 0.94);
    --panel-secondary: #121722;
    --panel-hover: #171d2a;

    --border: #252c3b;
    --border-strong: #343e52;

    --text: #f6f8fc;
    --text-soft: #a7b0c0;
    --text-muted: #737e91;

    --primary: #ff5c35;
    --primary-soft: rgba(255, 92, 53, 0.14);

    --secondary: #8496ff;
    --secondary-soft: rgba(132, 150, 255, 0.14);

    --success: #65dda2;
    --success-soft: rgba(101, 221, 162, 0.13);

    --warning: #f3c866;
    --warning-soft: rgba(243, 200, 102, 0.13);

    --danger: #ff7e83;
    --danger-soft: rgba(255, 126, 131, 0.13);

    --gold: #f4cf68;
    --silver: #c3cad6;
    --bronze: #d69469;

    --radius-large: 24px;
    --radius-medium: 16px;
    --radius-small: 10px;

    --shadow:
        0 28px 80px
        rgba(0, 0, 0, 0.34);
}

* {
    box-sizing: border-box;
}

html {
    scroll-behavior: smooth;
}

body {
    margin: 0;

    background:
        radial-gradient(
            circle at 92% 4%,
            rgba(255, 92, 53, 0.12),
            transparent 30rem
        ),
        radial-gradient(
            circle at 5% 20%,
            rgba(132, 150, 255, 0.10),
            transparent 34rem
        ),
        var(--background);

    color: var(--text);

    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

button,
input,
select {
    font: inherit;
}

a {
    color: inherit;
}

.container {
    width: min(
        1580px,
        calc(100% - 32px)
    );

    margin: 0 auto;
    padding: 42px 0 90px;
}

.panel {
    border: 1px solid var(--border);
    border-radius: var(--radius-large);
    background: var(--panel);
    box-shadow: var(--shadow);
}

.report-navigation {
    position: sticky;
    top: 12px;
    z-index: 100;

    margin-bottom: 24px;
    padding: 8px;

    border: 1px solid var(--border);
    border-radius: 16px;

    background:
        rgba(12, 15, 22, 0.92);

    box-shadow:
        0 14px 40px
        rgba(0, 0, 0, 0.28);

    backdrop-filter: blur(16px);
}

.navigation-scroll {
    display: flex;
    gap: 7px;
    overflow-x: auto;
    scrollbar-width: thin;
}

.navigation-button {
    flex: 0 0 auto;
    padding: 10px 15px;

    border: 1px solid transparent;
    border-radius: 11px;

    color: var(--text-soft);
    background: transparent;

    font-size: 0.78rem;
    font-weight: 800;

    cursor: pointer;

    transition:
        color 150ms ease,
        background 150ms ease,
        border-color 150ms ease,
        transform 150ms ease;
}

.navigation-button:hover {
    color: var(--text);
    background: rgba(255, 255, 255, 0.055);
}

.navigation-button:focus-visible {
    outline: 2px solid var(--secondary);
    outline-offset: 2px;
}

.navigation-button.active,
.navigation-button.is-active {
    color: #ffffff;

    border-color:
        rgba(255, 92, 53, 0.35);

    background:
        linear-gradient(
            135deg,
            rgba(255, 92, 53, 0.24),
            rgba(255, 92, 53, 0.11)
        );
}

.section-panel {
    display: none;
    animation:
        section-enter
        180ms ease-out;
}

.section-panel.active,
.section-panel.is-active {
    display: block;
}

.section-panel[hidden] {
    display: none !important;
}

.section-panel > :first-child {
    margin-top: 0;
}

.section-description {
    max-width: 760px;
    margin: 10px 0 0;

    color: var(--text-soft);
    line-height: 1.6;
}

.summary-heading-status {
    display: flex;
    align-items: flex-start;
}

.summary-mode-notice {
    display: flex;
    align-items: flex-start;
    gap: 14px;

    margin-top: 22px;
    padding: 18px;

    border: 1px solid var(--border);
    border-radius: 15px;

    background: var(--panel-secondary);
}

.summary-mode-notice.preassigned {
    border-color:
        rgba(243, 200, 102, 0.28);

    background:
        rgba(243, 200, 102, 0.06);
}

.summary-mode-notice.optimized {
    border-color:
        rgba(132, 150, 255, 0.28);

    background:
        rgba(132, 150, 255, 0.06);
}

.summary-mode-icon {
    display: flex;
    align-items: center;
    justify-content: center;

    flex: 0 0 32px;

    width: 32px;
    height: 32px;

    border-radius: 50%;

    color: var(--success);
    background: var(--success-soft);

    font-weight: 900;
}

.summary-mode-notice strong {
    display: block;
    margin-bottom: 5px;
}

.summary-mode-notice p {
    margin: 0;

    color: var(--text-soft);
    line-height: 1.5;
}

.summary-block {
    margin-top: 28px;
}

.summary-block-heading {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 20px;

    margin-bottom: 15px;
}

.summary-block-heading h3 {
    margin: 0;
}

.summary-metric-grid {
    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px, 1fr)
        );
}

.summary-metric-card small {
    display: block;
    margin-top: 8px;

    color: var(--text-soft);
    line-height: 1.35;
}

.summary-metric-card.positive {
    border-color:
        rgba(82, 210, 148, 0.24);
}

.summary-metric-card.warning {
    border-color:
        rgba(243, 200, 102, 0.28);
}

.summary-metric-card.negative {
    border-color:
        rgba(242, 89, 94, 0.30);
}

.summary-overview-grid,
.comparison-grid,
.restriction-summary-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(230px, 1fr)
        );

    gap: 14px;
}

.summary-status-card,
.summary-information-card,
.comparison-card,
.restriction-summary-card {
    padding: 18px;

    border: 1px solid var(--border);
    border-radius: 15px;

    background: var(--panel-secondary);
}

.summary-status-card.valid {
    border-color:
        rgba(82, 210, 148, 0.25);
}

.summary-status-card.invalid {
    border-color:
        rgba(242, 89, 94, 0.30);
}

.summary-card-label {
    display: block;
    margin-bottom: 9px;

    color: var(--text-soft);
    font-size: 0.72rem;
}

.summary-status-card strong,
.summary-information-card strong {
    display: block;
    margin-bottom: 8px;
}

.summary-status-card p,
.summary-information-card p,
.restriction-summary-card p {
    margin: 0;

    color: var(--text-soft);
    font-size: 0.8rem;
    line-height: 1.5;
}

.comparison-card {
    position: relative;
    overflow: hidden;
}

.comparison-card.positive,
.restriction-summary-card.positive {
    border-color:
        rgba(82, 210, 148, 0.25);
}

.comparison-card.warning,
.restriction-summary-card.warning {
    border-color:
        rgba(243, 200, 102, 0.28);
}

.comparison-card.negative,
.restriction-summary-card.negative {
    border-color:
        rgba(242, 89, 94, 0.30);
}

.comparison-card.strongest {
    border-color:
        rgba(132, 150, 255, 0.30);
}

.comparison-card.weakest {
    border-color:
        rgba(255, 255, 255, 0.10);
}

.comparison-team-name {
    display: block;
    margin-bottom: 12px;
}

.comparison-value {
    display: block;

    margin-bottom: 7px;

    font-size: 1.8rem;
    font-weight: 850;
    letter-spacing: -0.04em;
}

.comparison-card small {
    color: var(--text-soft);
}

.restriction-summary-card strong {
    display: block;

    margin-bottom: 8px;

    font-size: 1.7rem;
    letter-spacing: -0.04em;
}

@media (max-width: 760px) {
    .summary-heading-status {
        width: 100%;
    }

    .summary-block-heading {
        align-items: flex-start;
        flex-direction: column;
    }

    .summary-overview-grid,
    .comparison-grid,
    .restriction-summary-grid {
        grid-template-columns: 1fr;
    }
}

@keyframes section-enter {
    from {
        opacity: 0;
        transform: translateY(7px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero {
    display: grid;

    grid-template-columns:
        minmax(0, 1fr)
        minmax(220px, 300px);

    align-items: center;
    gap: 34px;
    padding: 34px;
}

.hero-copy h1 {
    max-width: 900px;
    margin: 8px 0 14px;

    font-size:
        clamp(
            2.2rem,
            6vw,
            5.4rem
        );

    line-height: 0.96;
    letter-spacing: -0.065em;
}

.hero-description {
    max-width: 720px;
    margin: 0;

    color: var(--text-soft);
    line-height: 1.65;
}

.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin-top: 24px;
}

.eyebrow {
    color: var(--primary);

    font-size: 0.76rem;
    font-weight: 850;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.badge,
.micro-badge,
.team-pill,
.seed-badge {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    border-radius: 999px;
    font-weight: 800;
}

.badge {
    padding: 7px 11px;
    font-size: 0.75rem;
}

.micro-badge {
    padding: 3px 6px;
    font-size: 0.59rem;
}

.team-pill,
.seed-badge {
    padding: 5px 8px;
    font-size: 0.68rem;
}

.badge.success,
.micro-badge.success {
    color: var(--success);
    background: var(--success-soft);
}

.badge.danger {
    color: var(--danger);
    background: var(--danger-soft);
}

.badge.warning,
.micro-badge.warning,
.seed-badge {
    color: var(--warning);
    background: var(--warning-soft);
}

.badge.neutral,
.micro-badge.neutral {
    color: var(--text-soft);
    background: rgba(255, 255, 255, 0.055);
}

.team-pill {
    color: var(--secondary);
    background: var(--secondary-soft);
}

.final-score {
    padding: 25px;

    border: 1px solid var(--border-strong);
    border-radius: 20px;

    background:
        linear-gradient(
            145deg,
            rgba(255, 92, 53, 0.12),
            rgba(132, 150, 255, 0.07)
        ),
        var(--panel-secondary);
}

.final-score-label {
    display: block;
    color: var(--text-soft);
    font-size: 0.82rem;
}

.final-score strong {
    display: block;
    margin: 8px 0 18px;

    font-size: 4rem;
    line-height: 1;
    letter-spacing: -0.07em;
}

.score-progress,
.mini-progress {
    overflow: hidden;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.07);
}

.score-progress {
    height: 8px;
}

.mini-progress {
    height: 5px;
    margin-top: 7px;
}

.score-progress span,
.mini-progress span {
    display: block;
    height: 100%;
    border-radius: inherit;
}

.score-progress span {
    background:
        linear-gradient(
            90deg,
            var(--primary),
            #ff9b4a
        );
}

.activity-high {
    color: var(--success);
}

.activity-medium {
    color: var(--warning);
}

.activity-low {
    color: var(--danger);
}

.mini-progress .activity-high {
    background: var(--success);
}

.mini-progress .activity-medium {
    background: var(--warning);
}

.mini-progress .activity-low {
    background: var(--danger);
}

.section {
    margin-top: 54px;
}

.section-title {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 22px;
    margin-bottom: 20px;
}

.section-title h2 {
    margin: 6px 0 0;
    font-size: 2rem;
    letter-spacing: -0.04em;
}

.section-description {
    max-width: 760px;
    margin: 9px 0 0;
    color: var(--text-soft);
    line-height: 1.55;
}

.section-counter {
    padding: 8px 12px;

    border: 1px solid var(--border);
    border-radius: 999px;

    background: var(--panel);
    color: var(--text-soft);

    font-size: 0.78rem;
    font-weight: 750;
}

.metric-grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(180px, 1fr)
        );

    gap: 13px;
}

.metric-card {
    min-height: 138px;
    padding: 20px;

    border: 1px solid var(--border);
    border-radius: var(--radius-medium);

    background: var(--panel);
}

.metric-label,
.highlight-label {
    display: block;
    color: var(--text-soft);
    font-size: 0.76rem;
}

.metric-value {
    display: block;
    margin: 8px 0 7px;

    font-size: 1.85rem;
    letter-spacing: -0.04em;
}

.metric-value.positive {
    color: var(--success);
}

.metric-value.negative {
    color: var(--danger);
}

.metric-card small,
.ranking-highlight-card small,
.team-highlight-card small {
    color: var(--text-muted);
    line-height: 1.4;
}

.ranking-highlight-grid,
.team-highlight-grid {
    display: grid;

    grid-template-columns:
        repeat(
            3,
            minmax(0, 1fr)
        );

    gap: 14px;
    margin-bottom: 18px;
}

.ranking-highlight-card,
.team-highlight-card {
    padding: 19px;

    border: 1px solid var(--border);
    border-radius: var(--radius-medium);

    background:
        linear-gradient(
            145deg,
            rgba(132, 150, 255, 0.045),
            transparent
        ),
        var(--panel);
}

.highlight-card-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.highlight-badge {
    padding: 5px 8px;
    border-radius: 999px;

    color: var(--secondary);
    background: var(--secondary-soft);

    font-size: 0.68rem;
    font-weight: 800;
}

.highlight-player,
.highlight-value,
.team-highlight-name {
    display: block;
}

.highlight-player,
.team-highlight-name {
    margin-top: 15px;
    font-size: 1.1rem;
}

.highlight-value {
    margin: 6px 0 5px;

    color: var(--success);
    font-size: 1.9rem;
    font-weight: 850;
    letter-spacing: -0.045em;
}

.highlight-value.danger {
    color: var(--danger);
}

.table-panel {
    overflow: hidden;

    border: 1px solid var(--border);
    border-radius: var(--radius-medium);

    background: var(--panel);
}

.table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;

    padding: 17px 19px;
    border-bottom: 1px solid var(--border);
}

.table-toolbar strong,
.table-toolbar span {
    display: block;
}

.table-toolbar strong {
    font-size: 0.92rem;
}

.table-toolbar > div > span {
    margin-top: 3px;
    color: var(--text-muted);
    font-size: 0.72rem;
}

.table-scroll,
.team-player-table-wrapper {
    overflow-x: auto;
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.79rem;
}

.data-table th,
.data-table td {
    padding: 12px 13px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: middle;
    white-space: nowrap;
}

.data-table th {
    color: var(--text-soft);
    background: #111620;

    font-size: 0.67rem;
    font-weight: 800;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

.data-table tbody tr:last-child td {
    border-bottom: 0;
}

.data-table tbody tr {
    transition:
        background 140ms ease;
}

.data-table tbody tr:hover {
    background: var(--panel-hover);
}

.numeric-cell {
    text-align: right !important;
    font-variant-numeric: tabular-nums;
}

.comparison-table th,
.comparison-table td {
    text-align: center;
}

.comparison-table th:first-child {
    text-align: left;
}

.comparison-value {
    font-weight: 800;
}

.comparison-value.heat-high {
    color: var(--success);
    background: rgba(101, 221, 162, 0.075);
}

.comparison-value.heat-medium {
    color: var(--warning);
    background: rgba(243, 200, 102, 0.055);
}

.comparison-value.heat-low {
    color: var(--danger);
    background: rgba(255, 126, 131, 0.055);
}

/* ============================================================
   COMMON SECTION HEADINGS
   ============================================================ */

.section-heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 20px;
}

.section-heading > div:first-child {
    min-width: 0;
}

.section-heading h2 {
    margin: 6px 0 0;
    font-size: clamp(1.7rem, 3vw, 2.25rem);
    line-height: 1.08;
    letter-spacing: -0.045em;
}

.section-heading .eyebrow {
    margin: 0;
}

.summary-section,
.ranking-section,
.teams-section {
    width: 100%;
}

/* ============================================================
   RANKING SECTION
   ============================================================ */

.ranking-heading-summary {
    display: flex;
    flex: 0 0 auto;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    min-width: 110px;
    color: var(--text-soft);
    font-size: 0.70rem;
}

.ranking-heading-summary strong {
    color: var(--text);
    font-size: 1.35rem;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}

.ranking-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin: 22px 0;
}

.ranking-summary-card {
    min-width: 0;
    padding: 16px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--panel-secondary);
    transition:
        border-color 150ms ease,
        background 150ms ease,
        transform 150ms ease;
}

.ranking-summary-card:hover {
    transform: translateY(-1px);
    background: var(--panel-hover);
}

.ranking-summary-card > span {
    display: block;
    margin-bottom: 7px;
    color: var(--text-soft);
    font-size: 0.67rem;
}

.ranking-summary-card > strong {
    display: block;
    overflow: hidden;
    margin-bottom: 5px;
    color: var(--text);
    font-size: 1.25rem;
    line-height: 1.15;
    letter-spacing: -0.025em;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.ranking-summary-card > small {
    display: block;
    color: var(--text-soft);
    line-height: 1.35;
}

.ranking-summary-card.strongest {
    border-color: rgba(132, 150, 255, 0.36);
    background:
        linear-gradient(
            145deg,
            rgba(132, 150, 255, 0.08),
            transparent 70%
        ),
        var(--panel-secondary);
}

.ranking-summary-card.weakest,
.ranking-summary-card.neutral {
    border-color: var(--border);
}

.ranking-summary-card.positive {
    border-color: rgba(101, 221, 162, 0.30);
}

.ranking-summary-card.negative {
    border-color: rgba(255, 126, 131, 0.32);
}

.ranking-table-wrapper {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    border: 1px solid var(--border);
    border-radius: var(--radius-medium);
    background: var(--panel);
    box-shadow: 0 18px 48px rgba(0, 0, 0, 0.16);
    -webkit-overflow-scrolling: touch;
}

.ranking-table {
    width: 100%;
    min-width: 1160px;
    border-collapse: collapse;
    border-spacing: 0;
    font-size: 0.78rem;
}

.ranking-table th,
.ranking-table td {
    padding: 13px 14px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: middle;
    white-space: nowrap;
}

.ranking-table th {
    position: sticky;
    top: 0;
    z-index: 2;
    color: var(--text-soft);
    background: #111620;
    font-size: 0.64rem;
    font-weight: 800;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

.ranking-table tbody tr {
    transition: background 140ms ease;
}

.ranking-table tbody tr:hover td {
    background: rgba(255, 255, 255, 0.025);
}

.ranking-table tbody tr:last-child td {
    border-bottom: 0;
}

.ranking-table th:first-child,
.ranking-table td:first-child {
    width: 54px;
    text-align: center;
}

.ranking-position {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 30px;
    height: 30px;
    padding: 0 7px;
    border: 1px solid transparent;
    border-radius: 9px;
    color: var(--text-soft);
    background: rgba(255, 255, 255, 0.05);
    font-weight: 850;
    font-variant-numeric: tabular-nums;
}

.ranking-position.first {
    color: var(--gold);
    border-color: rgba(244, 207, 104, 0.24);
    background: rgba(244, 207, 104, 0.12);
}

.ranking-position.second {
    color: var(--silver);
    border-color: rgba(195, 202, 214, 0.20);
    background: rgba(195, 202, 214, 0.10);
}

.ranking-position.third {
    color: var(--bronze);
    border-color: rgba(214, 148, 105, 0.22);
    background: rgba(214, 148, 105, 0.11);
}

.ranking-position.normal {
    color: var(--text-muted);
}

.ranking-player {
    display: flex;
    flex-direction: column;
    gap: 5px;
    min-width: 140px;
}

.ranking-player > strong {
    color: var(--text);
    font-size: 0.82rem;
}

.ranking-player-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 7px;
}

.ranking-role {
    color: var(--text-muted);
    font-size: 0.62rem;
}

.ranking-profile-link {
    width: fit-content;
    color: var(--secondary);
    font-size: 0.62rem;
    font-weight: 750;
    text-decoration: none;
}

.ranking-profile-link:hover {
    color: var(--primary);
    text-decoration: underline;
}

.ranking-team-name {
    display: inline-flex;
    align-items: center;
    min-height: 27px;
    padding: 4px 8px;
    border-radius: 8px;
    color: var(--secondary);
    background: var(--secondary-soft);
    font-size: 0.68rem;
    font-weight: 750;
}

.ranking-team-csv {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 30px;
    height: 30px;
    padding: 0 8px;
    border-radius: 9px;
    color: var(--warning);
    background: var(--warning-soft);
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

.ranking-power {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
    min-width: 72px;
}

.ranking-power > strong {
    color: var(--success);
    font-size: 0.91rem;
    font-variant-numeric: tabular-nums;
}

.ranking-power-delta {
    display: block;
    font-size: 0.61rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
}

.ranking-power-delta.positive {
    color: var(--success);
}

.ranking-power-delta.negative {
    color: var(--danger);
}

.ranking-power-delta.neutral {
    color: var(--text-muted);
}

.ranking-activity {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
    min-width: 118px;
}

.ranking-activity small {
    color: var(--text-muted);
    font-size: 0.60rem;
}

.ranking-seed-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 28px;
    height: 28px;
    padding: 0 8px;
    border-radius: 999px;
    color: var(--warning);
    background: var(--warning-soft);
    font-size: 0.66rem;
    font-weight: 900;
    font-variant-numeric: tabular-nums;
}

.ranking-table td:nth-child(n + 4) {
    font-variant-numeric: tabular-nums;
}

@media (max-width: 820px) {
    .section-heading {
        align-items: flex-start;
        flex-direction: column;
        gap: 14px;
    }

    .ranking-heading-summary {
        align-items: flex-start;
    }

    .ranking-summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .ranking-table {
        min-width: 1100px;
    }
}

@media (max-width: 520px) {
    .ranking-summary-grid {
        grid-template-columns: 1fr;
    }

    .ranking-summary-card {
        padding: 15px;
    }
}

.teams-heading-summary {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;

    color: var(--text-soft);
    font-size: 0.76rem;
}

.teams-heading-summary strong {
    color: var(--text);
    font-size: 1rem;
}

.teams-global-comparison {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );

    gap: 12px;

    margin-top: 22px;
    margin-bottom: 24px;
}

.teams-global-metric {
    padding: 16px;

    border: 1px solid var(--border);
    border-radius: 14px;

    background: var(--panel-secondary);
}

.teams-global-metric span {
    display: block;

    margin-bottom: 7px;

    color: var(--text-soft);
    font-size: 0.7rem;
}

.teams-global-metric strong {
    display: block;

    margin-bottom: 5px;

    font-size: 1.55rem;
    letter-spacing: -0.04em;
}

.teams-global-metric small {
    color: var(--text-soft);
    line-height: 1.35;
}

.teams-report-grid {
    display: grid;
    gap: 22px;
}

.team-report-card {
    overflow: hidden;

    border: 1px solid var(--border);
    border-radius: var(--radius-large);

    background: var(--panel);

    box-shadow: var(--shadow);
}

.team-report-card.strongest-team {
    border-color:
        rgba(132, 150, 255, 0.35);
}

.team-report-card.weakest-team {
    border-color:
        rgba(255, 255, 255, 0.10);
}

.team-report-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;

    padding: 22px 24px;

    border-bottom: 1px solid var(--border);
}

.team-report-index {
    display: block;

    margin-bottom: 6px;

    color: var(--text-soft);

    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.team-report-header h3 {
    margin: 0;
}

.team-report-power {
    min-width: 120px;

    text-align: right;
}

.team-report-power span {
    display: block;

    margin-bottom: 5px;

    color: var(--text-soft);
    font-size: 0.68rem;
}

.team-report-power strong {
    font-size: 2rem;
    letter-spacing: -0.05em;
}

.team-badge-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;

    margin-top: 10px;
}

.team-badge {
    display: inline-flex;

    padding: 5px 8px;

    border-radius: 999px;

    font-size: 0.65rem;
    font-weight: 800;
}

.team-badge.preassigned {
    color: var(--warning);
    background: var(--warning-soft);
}

.team-badge.strongest {
    color: var(--secondary);
    background: var(--secondary-soft);
}

.team-badge.weakest {
    color: var(--text-soft);
    background: rgba(255, 255, 255, 0.06);
}

.team-report-statistics {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(105px, 1fr)
        );

    gap: 1px;

    border-bottom: 1px solid var(--border);

    background: var(--border);
}

.team-report-stat {
    padding: 14px;

    background: var(--panel-secondary);
}

.team-report-stat span {
    display: block;

    margin-bottom: 5px;

    color: var(--text-soft);
    font-size: 0.65rem;
}

.team-report-stat strong {
    font-size: 1rem;
}

.team-seed-information {
    display: flex;
    align-items: center;
    gap: 12px;

    padding: 11px 24px;

    border-bottom: 1px solid var(--border);

    background:
        rgba(243, 200, 102, 0.055);
}

.team-seed-information span {
    color: var(--warning);

    font-size: 0.68rem;
    font-weight: 800;
    text-transform: uppercase;
}

.team-seed-information strong {
    font-size: 0.78rem;
}

.team-player-table-wrapper {
    width: 100%;

    overflow-x: auto;

    -webkit-overflow-scrolling: touch;
}

.team-player-table {
    width: 100%;
    min-width: 850px;

    border-collapse: collapse;
}

.team-player-table th,
.team-player-table td {
    padding: 13px 14px;

    border-bottom: 1px solid var(--border);

    text-align: left;
    white-space: nowrap;
}

.team-player-table th {
    color: var(--text-soft);

    background: rgba(255, 255, 255, 0.025);

    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.team-player-table td {
    font-size: 0.78rem;
}

.team-player-table tbody tr:last-child td {
    border-bottom: 0;
}

.team-player-table tbody tr:hover td {
    background:
        rgba(255, 255, 255, 0.025);
}

.team-player-identity {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.team-player-identity > strong {
    color: var(--text);
}

.team-player-meta {
    display: flex;
    align-items: center;
    gap: 7px;
}

.player-role-label {
    color: var(--text-soft);
    font-size: 0.65rem;
}

.player-profile-link {
    color: var(--secondary);

    font-size: 0.65rem;
    font-weight: 750;

    text-decoration: none;
}

.player-profile-link:hover {
    text-decoration: underline;
}

.player-power-cell {
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.player-power-cell > strong {
    color: var(--success);
}

.power-delta {
    font-size: 0.62rem;
}

.power-delta.positive {
    color: var(--success);
}

.power-delta.negative {
    color: var(--danger);
}

.power-delta.neutral {
    color: var(--text-soft);
}

.player-activity-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.player-activity-cell small {
    color: var(--text-soft);
    font-size: 0.62rem;
}

.activity-indicator {
    display: inline-flex;

    width: fit-content;

    padding: 4px 7px;

    border-radius: 999px;

    font-size: 0.66rem;
    font-weight: 800;
}

.activity-indicator.high {
    color: var(--success);
    background: var(--success-soft);
}

.activity-indicator.medium {
    color: var(--warning);
    background: var(--warning-soft);
}

.activity-indicator.low {
    color: var(--danger);
    background: var(--danger-soft);
}

.player-seed-badge {
    display: inline-flex;

    padding: 4px 7px;

    border-radius: 999px;

    color: var(--warning);
    background: var(--warning-soft);

    font-size: 0.64rem;
    font-weight: 800;
}

.assigned-team-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;

    min-width: 28px;
    min-height: 28px;

    border-radius: 8px;

    color: var(--secondary);
    background: var(--secondary-soft);

    font-weight: 900;
}

@media (max-width: 760px) {
    .teams-heading-summary {
        align-items: flex-start;
    }

    .team-report-header {
        flex-direction: column;
    }

    .team-report-power {
        text-align: left;
    }

    .teams-global-comparison {
        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );
    }

    .team-report-statistics {
        grid-template-columns:
            repeat(
                2,
                minmax(0, 1fr)
            );
    }

    .team-seed-information {
        align-items: flex-start;
        flex-direction: column;
        gap: 5px;
    }
}

@media (max-width: 480px) {
    .teams-global-comparison {
        grid-template-columns: 1fr;
    }
}

.teams-card-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 22px;
    margin-top: 22px;
}

.team-report-card {
    overflow: hidden;

    border: 1px solid var(--border);
    border-radius: var(--radius-large);

    background: var(--panel);
    box-shadow:
        0 18px 50px
        rgba(0, 0, 0, 0.18);
}

.team-report-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;

    padding: 25px;
    border-bottom: 1px solid var(--border);

    background:
        linear-gradient(
            135deg,
            rgba(132, 150, 255, 0.07),
            transparent
        );
}

.team-number {
    color: var(--primary);
    font-size: 0.7rem;
    font-weight: 850;
    letter-spacing: 0.13em;
}

.team-report-header h3 {
    margin: 6px 0 10px;
    font-size: 1.65rem;
    letter-spacing: -0.035em;
}

.team-seeds {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.team-power-summary {
    min-width: 145px;
    padding: 15px;

    border: 1px solid var(--border-strong);
    border-radius: 14px;

    background: var(--panel-secondary);
    text-align: right;
}

.team-power-summary span {
    display: block;
    color: var(--text-soft);
    font-size: 0.7rem;
}

.team-power-summary strong {
    display: block;
    margin-top: 5px;

    color: var(--success);
    font-size: 2rem;
    letter-spacing: -0.05em;
}

.team-main-metrics {
    display: grid;

    grid-template-columns:
        repeat(
            6,
            minmax(120px, 1fr)
        );

    gap: 10px;
    padding: 18px 22px;
}

.team-metric {
    min-height: 112px;
    padding: 14px;

    border: 1px solid var(--border);
    border-radius: 13px;

    background: var(--panel-secondary);
}

.team-metric > span {
    display: block;
    color: var(--text-soft);
    font-size: 0.68rem;
}

.team-metric > strong {
    display: block;
    margin: 6px 0 5px;

    font-size: 1.3rem;
    letter-spacing: -0.035em;
}

.team-metric small {
    color: var(--text-muted);
    font-size: 0.66rem;
}

.team-progress {
    margin-top: 11px;
}

.team-player-table-wrapper {
    border-top: 1px solid var(--border);
}

.team-player-name,
.ranking-player {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.player-profile-link {
    width: fit-content;
    text-decoration: none;
}

.player-profile-link:hover {
    color: var(--primary);
}

.player-meta-line {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
}

.activity-cell {
    min-width: 125px;
}

.activity-cell.compact {
    min-width: 95px;
}

.activity-value-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.activity-value-line strong {
    font-variant-numeric: tabular-nums;
}

.factor-value {
    font-weight: 800;
}

.final-power-value {
    display: block;
    color: var(--success);
    font-size: 0.93rem;
}

.power-delta {
    display: block;
    margin-top: 3px;
    font-size: 0.63rem;
}

.power-delta.positive {
    color: var(--success);
}

.power-delta.negative {
    color: var(--danger);
}

.power-delta.neutral,
.muted-value {
    color: var(--text-muted);
}

.empty-panel {
    padding: 42px;

    border: 1px dashed var(--border-strong);
    border-radius: var(--radius-medium);

    color: var(--text-muted);
    text-align: center;
}

.report-footer {
    margin-top: 60px;

    color: var(--text-muted);
    font-size: 0.76rem;
    text-align: center;
}

@media (max-width: 1200px) {
    .team-main-metrics {
        grid-template-columns:
            repeat(
                3,
                minmax(130px, 1fr)
            );
    }
}

@media (max-width: 1050px) {
    .ranking-highlight-grid,
    .team-highlight-grid {
        grid-template-columns: 1fr;
    }

    .table-toolbar {
        align-items: flex-start;
        flex-direction: column;
    }
}

@media (max-width: 820px) {
    .container {
        width: min(
            100% - 20px,
            1580px
        );

        padding-top: 20px;
    }

    .report-navigation {
        top: 6px;
        margin-bottom: 18px;
    }

    .navigation-button {
        padding: 9px 12px;
    }

    .hero {
        grid-template-columns: 1fr;
        padding: 24px;
    }

    .final-score {
        width: 100%;
    }

    .section-title,
    .team-report-header {
        align-items: flex-start;
        flex-direction: column;
    }

    .team-power-summary {
        width: 100%;
        text-align: left;
    }

    .team-main-metrics {
        grid-template-columns:
            repeat(
                2,
                minmax(120px, 1fr)
            );
    }
}

@media (max-width: 520px) {
    .team-main-metrics {
        grid-template-columns: 1fr;
    }
}




/* ============================================================
   REPORT HEADER / MODE BANNER
   ============================================================ */

.report-mode-banner {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(210px, 280px);
    align-items: center;
    gap: 30px;
    margin-bottom: 22px;
    padding: 30px;
    border: 1px solid var(--border);
    border-radius: var(--radius-large);
    background:
        linear-gradient(
            135deg,
            rgba(132, 150, 255, 0.08),
            rgba(255, 92, 53, 0.045)
        ),
        var(--panel);
    box-shadow: var(--shadow);
}

.report-mode-banner.preassigned {
    border-color: rgba(243, 200, 102, 0.20);
    background:
        linear-gradient(
            135deg,
            rgba(243, 200, 102, 0.075),
            rgba(132, 150, 255, 0.035)
        ),
        var(--panel);
}

.report-mode-banner.optimized {
    border-color: rgba(132, 150, 255, 0.22);
    background:
        linear-gradient(
            135deg,
            rgba(132, 150, 255, 0.09),
            rgba(255, 92, 53, 0.045)
        ),
        var(--panel);
}

.report-mode-copy {
    min-width: 0;
}

.report-mode-badges {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-bottom: 18px;
}

.report-mode-badge {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 6px 10px;
    border-radius: 999px;
    color: var(--secondary);
    background: var(--secondary-soft);
    font-size: 0.68rem;
    font-weight: 850;
    line-height: 1;
    letter-spacing: 0.075em;
    text-transform: uppercase;
}

.report-mode-banner.preassigned .report-mode-badge {
    color: var(--warning);
    background: var(--warning-soft);
}

.report-mode-copy > .eyebrow {
    display: block;
    margin: 0 0 8px;
    color: var(--primary);
    font-size: 0.72rem;
    font-weight: 850;
    line-height: 1.2;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.report-mode-copy h1 {
    max-width: 920px;
    margin: 0 0 14px;
    color: var(--text);
    font-size: clamp(2.15rem, 5.2vw, 4.7rem);
    font-weight: 850;
    line-height: 0.98;
    letter-spacing: -0.055em;
}

.report-mode-copy > p:not(.report-mode-detail) {
    max-width: 760px;
    margin: 0;
    color: var(--text-soft);
    font-size: 1rem;
    font-weight: 450;
    line-height: 1.65;
}

.report-mode-copy .report-mode-detail {
    max-width: 760px;
    margin: 10px 0 0;
    color: var(--text-muted);
    font-size: 0.78rem;
    font-weight: 500;
    line-height: 1.5;
}

.report-mode-score {
    align-self: stretch;
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    padding: 22px;
    border: 1px solid var(--border-strong);
    border-radius: 18px;
    background:
        linear-gradient(
            145deg,
            rgba(255, 92, 53, 0.09),
            rgba(132, 150, 255, 0.055)
        ),
        var(--panel-secondary);
}

.report-mode-score > span {
    display: block;
    color: var(--text-soft);
    font-size: 0.72rem;
    font-weight: 650;
}

.report-mode-score > strong {
    display: block;
    margin: 8px 0 13px;
    color: var(--text);
    font-size: clamp(2.5rem, 4.5vw, 3.8rem);
    font-weight: 900;
    line-height: 0.95;
    letter-spacing: -0.065em;
    font-variant-numeric: tabular-nums;
}

.status {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 6px 9px;
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 800;
}

.status.valid {
    color: var(--success);
    background: var(--success-soft);
}

.status.invalid {
    color: var(--danger);
    background: var(--danger-soft);
}

.balance-level {
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 6px 9px;
    border-radius: 999px;
    font-size: 0.67rem;
    font-weight: 850;
}

.balance-level.excellent,
.balance-level.good {
    color: var(--success);
    background: var(--success-soft);
}

.balance-level.acceptable {
    color: var(--warning);
    background: var(--warning-soft);
}

.balance-level.poor,
.balance-level.critical,
.balance-level.invalid {
    color: var(--danger);
    background: var(--danger-soft);
}

@media (max-width: 820px) {
    .report-mode-banner {
        grid-template-columns: 1fr;
        gap: 20px;
        padding: 23px;
    }

    .report-mode-copy h1 {
        font-size: clamp(2rem, 10vw, 3.5rem);
    }

    .report-mode-copy > p:not(.report-mode-detail) {
        font-size: 0.92rem;
    }

    .report-mode-score {
        width: 100%;
    }
}

@media (max-width: 480px) {
    .report-mode-banner {
        padding: 19px;
        border-radius: 18px;
    }

    .report-mode-badges {
        margin-bottom: 15px;
    }

    .report-mode-copy > .eyebrow {
        font-size: 0.65rem;
    }

    .report-mode-copy h1 {
        margin-bottom: 12px;
        font-size: 2.15rem;
        line-height: 1.02;
    }

    .report-mode-copy > p:not(.report-mode-detail) {
        font-size: 0.88rem;
        line-height: 1.55;
    }

    .report-mode-copy .report-mode-detail {
        margin-top: 8px;
        font-size: 0.72rem;
    }

    .report-mode-score {
        padding: 18px;
    }
}

/* ============================================================
   ACTIVITY SECTION
   ============================================================ */

.activity-summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 13px;
    margin-bottom: 22px;
}

.activity-summary-card {
    min-height: 128px;
    padding: 18px;
    border: 1px solid var(--border);
    border-radius: var(--radius-medium);
    background:
        linear-gradient(
            145deg,
            rgba(132, 150, 255, 0.035),
            transparent
        ),
        var(--panel);
}

.activity-summary-card span {
    display: block;
    color: var(--text-soft);
    font-size: 0.72rem;
    font-weight: 700;
}

.activity-summary-card strong {
    display: block;
    margin: 9px 0 7px;
    font-size: 1.7rem;
    letter-spacing: -0.04em;
}

.activity-summary-card small {
    color: var(--text-muted);
    line-height: 1.4;
}

.activity-summary-card.positive {
    border-color: rgba(82, 210, 148, 0.25);
}

.activity-summary-card.warning {
    border-color: rgba(243, 200, 102, 0.30);
}

.activity-summary-card.negative {
    border-color: rgba(242, 89, 94, 0.32);
}

.activity-summary-card.positive strong {
    color: var(--success);
}

.activity-summary-card.warning strong {
    color: var(--warning);
}

.activity-summary-card.negative strong {
    color: var(--danger);
}

.activity-explanation {
    display: grid;
    grid-template-columns:
        minmax(220px, 0.8fr)
        minmax(0, 1.2fr);
    gap: 20px;
    margin-bottom: 22px;
    padding: 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius-medium);
    background:
        linear-gradient(
            135deg,
            rgba(132, 150, 255, 0.055),
            rgba(243, 200, 102, 0.025)
        ),
        var(--panel-secondary);
}

.activity-explanation-copy {
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.activity-explanation-copy > strong {
    display: block;
    margin: 7px 0 8px;
    font-size: 1rem;
}

.activity-explanation-copy p {
    margin: 0;
    color: var(--text-soft);
    font-size: 0.8rem;
    line-height: 1.55;
}

.activity-window-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
}

.activity-window {
    padding: 14px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.025);
}

.activity-window span {
    display: block;
    color: var(--text-soft);
    font-size: 0.68rem;
    font-weight: 750;
}

.activity-window strong {
    display: block;
    margin: 7px 0 5px;
    color: var(--secondary);
    font-size: 1.55rem;
    letter-spacing: -0.04em;
}

.activity-window small {
    color: var(--text-muted);
    font-size: 0.68rem;
}

.activity-table-panel {
    margin-top: 0;
}

.activity-data-table {
    min-width: 1180px;
}

.activity-player {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.activity-player > strong {
    color: var(--text);
}

.activity-factor-cell {
    min-width: 110px;
}

.activity-factor-cell .activity-value-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.activity-factor-cell .mini-progress {
    width: 100%;
    min-width: 90px;
}

.activity-penalty {
    font-weight: 850;
}

.activity-penalty.none {
    color: var(--success);
}

.activity-penalty.applied {
    color: var(--danger);
}

.final-power-value {
    color: var(--success);
}

.micro-badge.success {
    color: var(--success);
    background: var(--success-soft);
}

.micro-badge.danger {
    color: var(--danger);
    background: var(--danger-soft);
}

@media (max-width: 900px) {
    .activity-explanation {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 620px) {
    .activity-summary-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .activity-window-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 430px) {
    .activity-summary-grid {
        grid-template-columns: 1fr;
    }
}



/* ============================================================
   ACTIVITY LEVEL ADJUSTMENT
   ============================================================ */

.activity-calculation-flow {
    display: grid;
    grid-template-columns:
        minmax(0, 1fr)
        auto
        minmax(0, 1fr)
        auto
        minmax(0, 1fr)
        auto
        minmax(0, 1fr);
    align-items: stretch;
    gap: 10px;
    margin: -6px 0 22px;
}

.activity-calculation-step {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 96px;
    padding: 15px;
    border: 1px solid var(--border);
    border-radius: 13px;
    background:
        linear-gradient(
            145deg,
            rgba(132, 150, 255, 0.035),
            transparent
        ),
        var(--panel);
}

.activity-calculation-step > span {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    margin-bottom: 8px;
    border-radius: 999px;
    color: var(--secondary);
    background: var(--secondary-soft);
    font-size: 0.68rem;
    font-weight: 900;
}

.activity-calculation-step small {
    display: block;
    margin-bottom: 4px;
    color: var(--text-muted);
    font-size: 0.67rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.activity-calculation-step strong {
    color: var(--text);
    font-size: 0.82rem;
    line-height: 1.25;
}

.activity-calculation-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    font-size: 1.15rem;
    font-weight: 900;
}

.activity-level-adjustment {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    min-width: 88px;
    gap: 3px;
}

.activity-level-adjustment strong {
    font-size: 0.79rem;
    font-weight: 900;
    white-space: nowrap;
}

.activity-level-adjustment strong.positive {
    color: var(--success);
}

.activity-level-adjustment strong.negative {
    color: var(--danger);
}

.activity-level-adjustment strong.neutral {
    color: var(--text-soft);
}

.activity-level-adjustment small {
    color: var(--text-muted);
    font-size: 0.66rem;
    font-variant-numeric: tabular-nums;
}

.activity-penalty-detail {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 3px;
    white-space: nowrap;
}

.activity-penalty-detail small {
    color: var(--text-muted);
    font-size: 0.65rem;
    font-variant-numeric: tabular-nums;
}

.activity-data-table {
    min-width: 1660px;
}

.activity-data-table th,
.activity-data-table td {
    vertical-align: middle;
}

.activity-data-table th:nth-child(2),
.activity-data-table td:nth-child(2) {
    min-width: 145px;
}

.activity-data-table th:nth-child(3),
.activity-data-table td:nth-child(3) {
    min-width: 105px;
}

.activity-data-table th:nth-child(6),
.activity-data-table td:nth-child(6),
.activity-data-table th:nth-child(7),
.activity-data-table td:nth-child(7),
.activity-data-table th:nth-child(9),
.activity-data-table td:nth-child(9) {
    min-width: 120px;
}

.activity-data-table th:nth-child(8),
.activity-data-table td:nth-child(8) {
    min-width: 95px;
}

.activity-data-table .numeric-cell {
    font-variant-numeric: tabular-nums;
}

@media (max-width: 980px) {
    .activity-calculation-flow {
        grid-template-columns:
            minmax(0, 1fr)
            minmax(0, 1fr);
    }

    .activity-calculation-arrow {
        display: none;
    }
}

@media (max-width: 620px) {
    .activity-calculation-flow {
        grid-template-columns: 1fr;
        gap: 8px;
    }

    .activity-calculation-step {
        min-height: 82px;
    }

    .activity-data-table {
        min-width: 1560px;
    }
}



/* ============================================================
   GLOBAL OPTIMIZATION
   ============================================================ */

.global-optimization-block {
    display: grid;
    gap: 18px;
}

.global-optimization-hero {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 20px;

    padding: 24px;

    border: 1px solid var(--border-strong);
    border-radius: var(--radius-medium);

    background:
        linear-gradient(
            135deg,
            rgba(132, 150, 255, 0.10),
            rgba(255, 92, 53, 0.06)
        ),
        var(--panel-secondary);
}

.global-optimization-hero.proven {
    border-color: rgba(101, 221, 162, 0.38);
    background:
        linear-gradient(
            135deg,
            rgba(101, 221, 162, 0.12),
            rgba(132, 150, 255, 0.07)
        ),
        var(--panel-secondary);
}

.global-optimization-hero.unproven {
    border-color: rgba(243, 200, 102, 0.34);
    background:
        linear-gradient(
            135deg,
            rgba(243, 200, 102, 0.10),
            rgba(132, 150, 255, 0.06)
        ),
        var(--panel-secondary);
}

.global-optimization-status-icon {
    display: grid;
    place-items: center;

    width: 52px;
    height: 52px;

    border: 1px solid var(--border-strong);
    border-radius: 50%;

    background: var(--background-soft);

    font-size: 1.35rem;
    font-weight: 900;
}

.global-optimization-hero.proven
.global-optimization-status-icon {
    border-color: rgba(101, 221, 162, 0.42);
    background: var(--success-soft);
    color: var(--success);
}

.global-optimization-hero.unproven
.global-optimization-status-icon {
    border-color: rgba(243, 200, 102, 0.42);
    background: var(--warning-soft);
    color: var(--warning);
}

.global-optimization-copy h3 {
    margin: 4px 0 8px;

    font-size: clamp(1.25rem, 2vw, 1.65rem);
    letter-spacing: -0.025em;
}

.global-optimization-copy p:last-child {
    max-width: 880px;
    margin: 0;

    color: var(--text-soft);
    line-height: 1.6;
}

.global-optimization-score {
    min-width: 138px;
    text-align: right;
}

.global-optimization-score span,
.global-optimization-score small {
    display: block;
    color: var(--text-muted);
}

.global-optimization-score span {
    margin-bottom: 4px;

    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.10em;
    text-transform: uppercase;
}

.global-optimization-score strong {
    display: block;

    font-size: clamp(2rem, 4vw, 3.25rem);
    line-height: 1;
    letter-spacing: -0.055em;
}

.global-optimization-score small {
    margin-top: 5px;
    font-size: 0.76rem;
}

.global-optimization-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
}

.global-optimization-metric {
    min-width: 0;
    padding: 16px;

    border: 1px solid var(--border);
    border-radius: var(--radius-small);

    background: var(--panel-secondary);
}

.global-optimization-metric.positive {
    border-color: rgba(101, 221, 162, 0.28);
}

.global-optimization-metric.warning {
    border-color: rgba(243, 200, 102, 0.28);
}

.global-optimization-metric span,
.global-optimization-metric small {
    display: block;
}

.global-optimization-metric span {
    margin-bottom: 9px;

    color: var(--text-muted);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.global-optimization-metric strong {
    display: block;
    margin-bottom: 7px;

    font-size: 1.45rem;
    line-height: 1.05;
    letter-spacing: -0.04em;
}

.global-optimization-metric.positive strong {
    color: var(--success);
}

.global-optimization-metric small {
    color: var(--text-soft);
    font-size: 0.74rem;
    line-height: 1.45;
}

@media (max-width: 1180px) {
    .global-optimization-metrics {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 760px) {
    .global-optimization-hero {
        grid-template-columns: auto minmax(0, 1fr);
        align-items: start;
    }

    .global-optimization-score {
        grid-column: 1 / -1;
        padding-top: 16px;
        border-top: 1px solid var(--border);
        text-align: left;
    }

    .global-optimization-metrics {
        grid-template-columns: 1fr;
    }
}
"""
