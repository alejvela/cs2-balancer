"""Embedded, dependency-free styling for the standalone LAN report."""

TOURNAMENT_CSS = """
:root{color-scheme:dark;--bg:#0b1017;--panel:#141d28;--line:#2d3b4c;
--text:#edf3fa;--muted:#a9b9ca;--accent:#ffb454;--ok:#74dec8;--warn:#ffcc83}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);
color:var(--text);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}
a{color:var(--ok);text-underline-offset:4px}a:focus-visible,summary:focus-visible{
outline:3px solid var(--accent);outline-offset:5px}main{max-width:1440px;margin:auto;padding:32px}
.hero{border-top:5px solid var(--accent);padding:40px;background:linear-gradient(120deg,#243448,#141d28 70%)}
.eyebrow{text-transform:uppercase;letter-spacing:.18em;color:var(--accent);font-size:.78rem;font-weight:800}
h1{font-size:clamp(2rem,5vw,4rem);line-height:1.1;letter-spacing:-.04em;margin:12px 0 20px}
h2{font-size:1.8rem;letter-spacing:-.025em;margin:0 0 14px}h3{margin:0 0 8px;font-size:1.2rem}
h4{margin:20px 0 8px}p{margin:8px 0 16px}.muted,small{color:var(--muted)}
nav{display:flex;gap:20px;flex-wrap:wrap;padding:18px 0;border-bottom:1px solid var(--line)}
section{margin-top:40px;scroll-margin-top:20px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
.card{background:var(--panel);border:1px solid var(--line);padding:24px;border-radius:8px;min-width:0}
.stat strong{display:block;font-size:2.4rem;line-height:1.3}.stat span{color:var(--muted)}
.mvp{border-left:5px solid var(--accent);display:grid;grid-template-columns:1fr 2fr;gap:24px}
.mvp .score{font-size:4rem;font-weight:800;color:var(--accent);line-height:1.1}
.badge{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:.8rem;color:var(--ok)}
.warning{color:var(--warn)}.award{border-top:3px solid var(--accent)}.award .recipient{font-size:1.4rem;font-weight:700}
.award .value{font-size:1.6rem;color:var(--ok)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.87rem}
caption{text-align:left;padding:14px 16px;color:var(--muted);background:var(--panel)}
th,td{text-align:right;padding:12px 14px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;background:#192432}
th:nth-child(2),td:nth-child(2){text-align:left}tbody tr:hover{background:#1c2b39}tbody tr:first-child td:first-child{color:var(--accent);font-weight:800}
details{border:1px solid var(--line);border-radius:8px;padding:16px 20px;margin:12px 0;background:var(--panel)}
summary{cursor:pointer;font-weight:700}dl{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px 20px;margin:12px 0}
dt{color:var(--muted);overflow-wrap:anywhere}dd{margin:0;text-align:right;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.components{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
.component{padding:14px;background:#0e1721;border-radius:6px}meter{width:100%;height:12px;accent-color:var(--ok)}
.provenance,li{overflow-wrap:anywhere}.series{border-left:3px solid var(--ok)}
footer{margin-top:40px;padding-top:20px;border-top:1px solid var(--line);color:var(--muted)}
@media(max-width:700px){main{padding:16px}.hero{padding:24px}.mvp{grid-template-columns:1fr}.card{padding:18px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{html{color-scheme:light}body{background:white;color:#111}main{padding:0}
.hero,.card,details,.component,th,caption{background:white;color:#111}a,.muted,small,dt,th{color:#333}
.table-wrap{overflow:visible}table{white-space:normal;font-size:8pt}th,td{padding:5px}
nav{display:none}section{break-before:auto}.card{break-inside:avoid}}
"""
