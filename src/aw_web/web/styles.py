"""CSS used by the local web interface."""

CSS = """
:root {
  color-scheme: dark;
  --bg: #050505;
  --surface: #101010;
  --surface-2: #191919;
  --surface-3: #242424;
  --text: #f5f5f5;
  --muted: #a8a8a8;
  --subtle: #737373;
  --accent: #8fd14f;
  --accent-strong: #a6ed5e;
  --danger: #ff5f56;
  --line: #303030;
  --shadow: 0 18px 36px rgba(0, 0, 0, .48);
}
* { box-sizing: border-box; }
html { min-height: 100%; background: var(--bg); scroll-behavior: smooth; }
body {
  min-height: 100vh;
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
a { color: inherit; text-decoration: none; }
svg { display: block; width: 1.05em; height: 1.05em; flex: 0 0 auto; }
main { width: min(1240px, calc(100% - 40px)); margin: 0 auto 64px; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  gap: 24px;
  align-items: center;
  justify-content: space-between;
  min-height: 58px;
  padding: 0 max(20px, calc((100vw - 1240px) / 2));
  background: rgba(24, 24, 24, .98);
  border-bottom: 1px solid #2a2a2a;
}
.main-nav { display: flex; gap: 4px; align-items: center; min-width: 0; }
.brand {
  display: inline-flex;
  gap: 7px;
  align-items: center;
  min-height: 58px;
  margin-right: 18px;
  color: var(--accent);
  font-size: 1.22rem;
  font-weight: 900;
  letter-spacing: 0;
}
.brand-mark {
  display: inline-grid;
  place-items: center;
  width: 28px;
  height: 28px;
  color: #061006;
  background: var(--accent);
  border-radius: 50%;
  font-size: .82rem;
  line-height: 1;
}
.nav-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 58px;
  padding: 0 14px;
  color: #d8d8d8;
  font-size: .95rem;
  font-weight: 700;
}
.nav-link::after {
  content: "";
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 3px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: center;
  transition: transform .2s ease;
}
.nav-link:hover, .nav-link:focus-visible { color: #fff; outline: 0; }
.nav-link:hover::after, .nav-link:focus-visible::after { transform: scaleX(1); }
.search { display: flex; gap: 0; flex: 1; max-width: 460px; }
input, select, button, .button {
  min-height: 40px;
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 10px 13px;
  background: var(--surface-2);
  color: var(--text);
  font: inherit;
}
input[type="search"] {
  flex: 1;
  min-width: 0;
  border-right: 0;
  border-radius: 4px 0 0 4px;
  background: #0c0c0c;
}
button, .button {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-color: transparent;
  background: var(--accent);
  color: #071107;
  font-weight: 900;
  line-height: 1;
}
.search button { border-radius: 0 4px 4px 0; }
button:hover, .button:hover, button:focus-visible, .button:focus-visible {
  background: var(--accent-strong);
  outline: 2px solid rgba(143, 209, 79, .28);
  outline-offset: 2px;
}
button.secondary, .button.secondary {
  background: transparent;
  color: var(--text);
  border-color: #555;
}
button.secondary:hover, .button.secondary:hover, button.secondary:focus-visible, .button.secondary:focus-visible {
  background: var(--surface-3);
  border-color: #777;
}
button.danger, .button.danger { color: #fff; border-color: rgba(255, 95, 86, .38); }
button.danger:hover, .button.danger:hover { background: rgba(255, 95, 86, .16); border-color: var(--danger); }
.button-text { display: inline; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
button.is-loading, button.is-loading:hover, button.is-loading:focus-visible {
  min-width: var(--loading-button-width, 78px);
  cursor: progress;
  background: transparent;
  border-color: transparent;
  color: var(--accent);
  outline: 0;
}
.play-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(143, 209, 79, .24);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: playSpinner .72s linear infinite;
}
.hero {
  position: relative;
  display: grid;
  align-items: end;
  min-height: clamp(360px, 54vw, 560px);
  margin: 0 calc(50% - 50vw) 38px;
  padding: 76px max(20px, calc((100vw - 1240px) / 2)) 56px;
  overflow: hidden;
  background: linear-gradient(135deg, #151515, #252525);
}
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(90deg, #050505 0%, rgba(5, 5, 5, .92) 25%, rgba(5, 5, 5, .34) 62%, rgba(5, 5, 5, .86) 100%),
    linear-gradient(0deg, #050505 0%, rgba(5, 5, 5, .18) 42%, rgba(5, 5, 5, .08) 100%);
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  z-index: 1;
  height: 120px;
  background: linear-gradient(0deg, var(--bg), rgba(5, 5, 5, 0));
  pointer-events: none;
}
.hero-slideshow {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}
.hero-slide {
  position: absolute;
  inset: 0;
  opacity: 0;
  background-image: var(--slide-image);
  background-position: center;
  background-size: cover;
  animation: heroSlideshow var(--slideshow-duration) ease-in-out var(--slide-delay) infinite both;
  transform: scale(1.02);
}
.hero-slideshow.is-static .hero-slide {
  opacity: 1;
  animation: none;
}
@keyframes playSpinner {
  to { transform: rotate(360deg); }
}
.hero-copy { position: relative; z-index: 2; max-width: 600px; }
.hero h1 {
  margin: 8px 0 12px;
  max-width: 620px;
  font-size: clamp(2.2rem, 5vw, 4.7rem);
  line-height: .98;
  letter-spacing: 0;
}
.hero p { margin: 0; max-width: 560px; color: #dedede; line-height: 1.55; }
.eyebrow, .badge {
  color: var(--accent);
  text-transform: uppercase;
  font-size: .72rem;
  font-weight: 900;
  letter-spacing: 0;
}
.badge-row { display: flex; min-height: 18px; gap: 7px; flex-wrap: wrap; align-items: center; }
.new-episode {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  color: #ffd166;
}
.new-episode::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 12px currentColor;
}
section { margin-top: 42px; }
.catalog-section { position: relative; }
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 12px;
  margin-bottom: 16px;
}
.section-title h2 {
  margin: 0;
  font-size: clamp(1.45rem, 2vw, 2rem);
  line-height: 1.1;
  letter-spacing: 0;
}
.section-title span, .muted { color: var(--muted); }
.rail {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(220px, 254px);
  gap: 22px;
  margin: 0 -20px;
  padding: 0 20px 18px;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x proximity;
  scrollbar-color: #555 transparent;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 28px 22px;
}
.catalog-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  background: var(--bg);
  border-radius: 6px;
  scroll-snap-align: start;
  transition: transform .16s ease, box-shadow .16s ease;
}
.catalog-card:hover, .catalog-card:focus-within {
  transform: translateY(-4px);
  box-shadow: var(--shadow);
  z-index: 5;
}
.card-detail-link {
  position: absolute;
  inset: 0;
  z-index: 2;
  border-radius: inherit;
}
.card-detail-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}
.card-backdrop {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  transition: opacity .16s ease;
}
.card-backdrop .cover {
  width: 100%;
  height: 100%;
  aspect-ratio: auto;
  filter: brightness(.34);
  transform: scale(1.08);
  transition: filter .16s ease, transform .24s ease;
}
.catalog-card:hover .card-backdrop, .catalog-card:focus-within .card-backdrop {
  opacity: 1;
}
.catalog-card:hover .card-backdrop .cover, .catalog-card:focus-within .card-backdrop .cover {
  filter: brightness(.3);
  transform: scale(1.15);
}
.poster-frame {
  position: relative;
  z-index: 1;
  display: block;
  background: var(--bg);
  transition: opacity .16s ease;
}
.cover {
  display: block;
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  background: var(--surface-2);
  transition: filter .16s ease, transform .2s ease;
}
.catalog-card:hover .cover, .catalog-card:focus-within .cover {
  filter: brightness(.45);
  transform: scale(1.03);
}
.catalog-card:hover .poster-frame, .catalog-card:focus-within .poster-frame {
  opacity: 0;
}
.placeholder {
  display: grid;
  place-items: center;
  color: var(--accent);
  font-size: 2rem;
  font-weight: 900;
}
.card-info {
  position: relative;
  z-index: 1;
  min-height: 84px;
  padding: 13px 0 0;
  background: var(--bg);
  transition: opacity .16s ease;
}
.catalog-card:hover .card-info, .catalog-card:focus-within .card-info {
  opacity: 0;
}
.card-info h3, .card-hover h3 {
  margin: 6px 0 5px;
  font-size: 1.02rem;
  line-height: 1.25;
  letter-spacing: 0;
}
.card-info p, .hover-meta, .hover-description {
  margin: 0;
  color: var(--muted);
  font-size: .86rem;
  line-height: 1.42;
}
.card-hover {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 12px;
  padding: 14px;
  background:
    linear-gradient(0deg, rgba(5, 5, 5, .98) 0%, rgba(5, 5, 5, .9) 48%, rgba(5, 5, 5, .54) 100%);
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity .16s ease, visibility .16s ease;
}
.catalog-card:hover .card-hover, .catalog-card:focus-within .card-hover {
  opacity: 1;
  visibility: visible;
}
.hover-description {
  display: -webkit-box;
  margin-top: 8px;
  overflow: hidden;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
}
.hover-actions {
  position: relative;
  z-index: 4;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  pointer-events: auto;
}
.hover-actions form { display: inline-flex; margin: 0; }
.card-action { min-height: 38px; padding: 9px 12px; font-size: .88rem; }
.hover-actions .card-action {
  background: transparent;
  border-color: var(--accent);
  color: var(--accent);
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.hover-actions .card-action:hover, .hover-actions .card-action:focus-visible {
  background: var(--accent);
  border-color: var(--accent);
  color: #071107;
}
.play-action { color: var(--accent); background: transparent; }
.card-icon-action {
  width: 36px;
  min-height: 36px;
  padding: 0;
}
.hover-actions .card-icon-action {
  background: transparent;
  border-color: var(--danger);
  color: var(--danger);
  transition: background .15s ease, border-color .15s ease, color .15s ease;
}
.hover-actions .card-icon-action:hover, .hover-actions .card-icon-action:focus-visible {
  background: var(--danger);
  border-color: var(--danger);
  color: #fff;
}
.seasonal-card .cover { aspect-ratio: 5 / 7; }
.icon-toggle-form { display: inline-flex; margin: 0; }
.icon-toggle {
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 44px;
  padding: 0;
  color: #fff;
  background: rgba(0, 0, 0, .55);
  border: 1px solid rgba(255, 255, 255, .48);
  border-radius: 50%;
}
.icon-toggle:hover, .icon-toggle:focus-visible { background: rgba(143, 209, 79, .18); border-color: var(--accent); }
.icon-toggle.active { color: var(--accent); border-color: var(--accent); }
.icon-toggle svg { width: 23px; height: 23px; }
.row-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 16px;
}
.row-actions.compact { margin-top: 0; justify-content: flex-end; }
.season-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: end;
  margin: 34px 0 16px;
}
.season-picker, .season-controls { display: flex; gap: 10px; align-items: center; }
.season-heading h1 {
  margin: 4px 0 6px;
  font-size: clamp(2.1rem, 4vw, 3.8rem);
  line-height: 1;
  letter-spacing: 0;
}
.season-heading p { margin: 0; }
.season-arrow {
  width: 44px;
  min-height: 44px;
  display: inline-grid;
  place-items: center;
  padding: 0;
  font-size: 1.3rem;
}
.season-controls { margin-bottom: 22px; }
.detail {
  display: grid;
  grid-template-columns: minmax(180px, 280px) 1fr;
  gap: 30px;
  align-items: start;
  margin-top: 34px;
}
.poster-wrap {
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
}
.detail h1 {
  margin: 5px 0 12px;
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1;
  letter-spacing: 0;
}
.plot { max-width: 850px; color: #dedede; line-height: 1.65; }
.info-list {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 18px;
  color: var(--muted);
}
.info-list dt { color: var(--text); font-weight: 800; }
.episodes { display: grid; gap: 9px; }
.episode {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--surface);
}
.episode.active { border-color: rgba(143, 209, 79, .75); background: rgba(143, 209, 79, .1); }
.error {
  color: #ffd0d0;
  background: rgba(255, 95, 86, .12);
  border: 1px solid rgba(255, 95, 86, .42);
  padding: 14px;
  border-radius: 6px;
}
@media (max-width: 760px) {
  main { width: calc(100% - 28px); }
  .topbar {
    position: sticky;
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
    padding: 0 14px 12px;
  }
  .main-nav { overflow-x: auto; }
  .brand, .nav-link { min-height: 50px; }
  .search { max-width: none; }
  .button-text { display: none; }
  .hero {
    min-height: 430px;
    margin-bottom: 30px;
    padding: 78px 20px 44px;
  }
  .hero::before {
    background:
      linear-gradient(0deg, #050505 0%, rgba(5, 5, 5, .3) 70%),
      linear-gradient(90deg, rgba(5, 5, 5, .94), rgba(5, 5, 5, .42));
  }
  .rail {
    grid-auto-columns: minmax(178px, 70vw);
    gap: 14px;
    margin: 0 -14px;
    padding: 0 14px 16px;
  }
  .grid { grid-template-columns: repeat(auto-fill, minmax(164px, 1fr)); gap: 20px 14px; }
  .card-backdrop { display: none; }
  .card-hover {
    position: static;
    opacity: 1;
    visibility: visible;
    padding: 11px 0 0;
    background: var(--bg);
  }
  .catalog-card:hover, .catalog-card:focus-within { transform: none; box-shadow: none; }
  .catalog-card:hover .cover, .catalog-card:focus-within .cover { filter: none; transform: none; }
  .catalog-card:hover .poster-frame, .catalog-card:focus-within .poster-frame,
  .catalog-card:hover .card-info, .catalog-card:focus-within .card-info { opacity: 1; }
  .hover-copy .badge-row, .hover-copy h3, .hover-meta, .hover-description { display: none; }
  .detail { grid-template-columns: 1fr; }
  .poster-wrap { max-width: 240px; }
  .episode { align-items: stretch; flex-direction: column; }
  .row-actions.compact { justify-content: flex-start; }
  .season-toolbar { align-items: stretch; flex-direction: column; }
  .season-picker, .season-controls { justify-content: space-between; }
  .season-controls select, .season-controls input { min-width: 0; width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .hero-slide {
    animation: none;
    opacity: 0;
  }
  .hero-slide:first-child { opacity: 1; }
}
"""
