"""CSS used by the local web interface."""

CSS = """
:root { color-scheme: dark; --bg: #0b0d12; --panel: #141823; --panel-2: #1d2330; --text: #edf2ff; --muted: #a8b3c7; --accent: #8fd14f; --danger: #ff6b6b; --line: #2a3242; }
* { box-sizing: border-box; }
body { margin: 0; background: radial-gradient(circle at top left, #25314a 0, #0b0d12 34rem); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
a { color: inherit; text-decoration: none; }
main { width: min(1180px, calc(100% - 32px)); margin: 0 auto 64px; }
.topbar { position: sticky; top: 0; z-index: 5; display: flex; gap: 18px; align-items: center; justify-content: space-between; padding: 16px max(16px, calc((100vw - 1180px) / 2)); background: rgba(11, 13, 18, .82); border-bottom: 1px solid var(--line); backdrop-filter: blur(16px); }
.main-nav { display: flex; gap: 16px; align-items: center; flex-shrink: 0; }
.brand { font-weight: 900; letter-spacing: -.03em; font-size: 1.35rem; }
.nav-link { padding: 9px 11px; border: 1px solid var(--line); border-radius: 12px; background: rgba(20, 24, 35, .72); color: var(--text); font-weight: 800; }
.nav-link:hover { border-color: rgba(143, 209, 79, .55); }
.search { display: flex; gap: 8px; flex: 1; max-width: 680px; }
input, select, button, .button { border: 1px solid var(--line); border-radius: 12px; padding: 11px 13px; background: var(--panel); color: var(--text); font: inherit; }
input[type="search"] { flex: 1; min-width: 0; }
button, .button { cursor: pointer; background: var(--accent); color: #081008; font-weight: 800; border-color: transparent; }
button.secondary, .button.secondary { background: var(--panel-2); color: var(--text); border-color: var(--line); }
button.danger { color: #fff; background: color-mix(in srgb, var(--danger) 78%, #171b24); }
.icon-toggle-form { display: inline-flex; }
.icon-toggle { display: inline-grid; place-items: center; width: 46px; height: 46px; padding: 0; border-radius: 999px; color: #fff; background: rgba(20, 24, 35, .38); border: 1px solid rgba(255,255,255,.54); }
.icon-toggle:hover { background: rgba(255,255,255,.12); border-color: rgba(255,255,255,.82); }
.icon-toggle.active { background: rgba(255,255,255,.13); border-color: rgba(255,255,255,.72); }
.icon-toggle svg { width: 24px; height: 24px; display: block; }
.hero { margin: 24px 0; padding: 24px 28px; border: 1px solid var(--line); border-radius: 24px; background: linear-gradient(135deg, rgba(143, 209, 79, .18), rgba(29, 35, 48, .85)); }
.hero h1 { max-width: 760px; margin: 0 0 8px; font-size: clamp(1.65rem, 4.5vw, 3.25rem); line-height: 1; letter-spacing: -.06em; }
.hero p { color: var(--muted); max-width: 680px; }
.eyebrow, .badge { color: var(--accent); text-transform: uppercase; font-size: .72rem; font-weight: 900; letter-spacing: .14em; }
.new-episode { display: inline-flex; align-items: center; gap: 6px; margin-left: 8px; color: #ffd166; }
.new-episode::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; box-shadow: 0 0 14px currentColor; }
section { margin-top: 34px; }
.section-title { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 14px; }
.section-title h2 { margin: 0; font-size: 1.45rem; letter-spacing: -.03em; }
.section-title span, .muted { color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 16px; }
.card { overflow: hidden; min-width: 0; border: 1px solid var(--line); border-radius: 20px; background: rgba(20, 24, 35, .88); box-shadow: 0 18px 50px rgba(0,0,0,.22); transition: transform .16s ease, border-color .16s ease; }
.card:hover { transform: translateY(-3px); border-color: rgba(143, 209, 79, .6); }
.cover { display: block; width: 100%; aspect-ratio: 2 / 3; object-fit: cover; background: var(--panel-2); }
.placeholder { display: grid; place-items: center; color: var(--accent); font-size: 2rem; font-weight: 900; }
.card-body { padding: 13px; }
.card h3 { margin: 7px 0 6px; font-size: 1rem; line-height: 1.15; }
.card p { margin: 0; color: var(--muted); font-size: .92rem; }
.seasonal-card .cover { aspect-ratio: 5 / 7; }
.saved-card { display: flex; grid-column: span 2; align-items: stretch; }
.saved-card > a { display: block; flex-shrink: 0; }
.saved-card .cover { width: 120px; min-width: 120px; height: 100%; aspect-ratio: unset; }
.row-actions { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 14px; }
.row-actions.compact { margin-top: 0; justify-content: flex-end; }
.season-toolbar { display: flex; justify-content: space-between; gap: 14px; align-items: center; margin: 28px 0 18px; }
.season-picker { display: flex; gap: 10px; align-items: center; }
.season-heading h1 { margin: 0 0 5px; font-size: clamp(2rem, 5vw, 3.35rem); line-height: 1; letter-spacing: -.04em; }
.season-heading p { margin: 0; }
.season-arrow { width: 46px; height: 46px; display: inline-grid; place-items: center; padding: 0; font-size: 1.45rem; }
.season-controls { display: flex; gap: 10px; align-items: center; margin-bottom: 18px; }
.detail { display: grid; grid-template-columns: minmax(180px, 290px) 1fr; gap: 28px; align-items: start; }
.poster-wrap { border-radius: 24px; overflow: hidden; border: 1px solid var(--line); background: var(--panel); }
.detail h1 { margin: 4px 0 10px; font-size: clamp(2rem, 5vw, 4rem); line-height: 1; letter-spacing: -.06em; }
.plot { color: #d7def0; line-height: 1.65; max-width: 850px; }
.info-list { display: grid; grid-template-columns: max-content 1fr; gap: 8px 18px; color: var(--muted); }
.info-list dt { color: var(--text); font-weight: 800; }
.episodes { display: grid; gap: 9px; }
.episode { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--line); border-radius: 16px; background: rgba(20, 24, 35, .88); }
.episode.active { border-color: rgba(143, 209, 79, .75); background: rgba(143, 209, 79, .1); }
.watch-page { max-width: 1120px; margin-inline: auto; }
.nav-group { display: flex; gap: 10px; margin-left: auto; align-items: center; }
.video-shell { position: relative; }
.video-player { width: 100%; max-height: 72vh; background: #000; border: 1px solid var(--line); border-radius: 24px; box-shadow: 0 24px 80px rgba(0,0,0,.45); }
.mode-pill { display: inline-flex; align-items: center; gap: 8px; padding: 8px 11px; border: 1px solid currentColor; border-radius: 999px; background: rgba(8, 10, 14, .78); font-size: .82rem; font-weight: 900; backdrop-filter: blur(12px); box-shadow: 0 10px 30px rgba(0,0,0,.32); white-space: nowrap; }
.mode-pill span { width: 9px; height: 9px; border-radius: 50%; background: currentColor; box-shadow: 0 0 18px currentColor; }
.mode-direct { color: #8fd14f; }
.mode-buffering { color: #7cc7ff; }
.mode-proxy { color: #ffd166; }
.mode-error { color: #ff6b6b; }
.error { color: #ffd0d0; background: rgba(255, 107, 107, .12); border: 1px solid rgba(255, 107, 107, .4); padding: 14px; border-radius: 14px; }
@media (max-width: 720px) { .topbar { align-items: stretch; flex-direction: column; } .main-nav { justify-content: space-between; } .search { max-width: none; } .search select { display: none; } .detail { grid-template-columns: 1fr; } .poster-wrap { max-width: 240px; } .saved-card { grid-column: auto; display: block; } .saved-card .cover { width: 100%; height: auto; } .episode { align-items: stretch; flex-direction: column; } .row-actions.compact { justify-content: flex-start; } .season-toolbar { align-items: stretch; flex-direction: column; } .season-picker, .season-controls { justify-content: space-between; } .season-controls select, .season-controls input { min-width: 0; width: 100%; } }
"""
