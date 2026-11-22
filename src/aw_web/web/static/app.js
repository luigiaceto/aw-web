// Pulsanti "Guarda": apre MPV in background e mostra lo spinner finché il video non parte.
(() => {
  function setPlayLoading(form, submitter) {
    const button = submitter || form.querySelector('button[type="submit"], button:not([type])');
    if (!button || button.dataset.playLoading === "1") return null;
    const state = {
      button,
      disabled: button.disabled,
      html: button.innerHTML,
    };
    button.dataset.playLoading = "1";
    button.style.setProperty("--loading-button-width", `${button.offsetWidth}px`);
    button.disabled = true;
    button.classList.add("is-loading");
    button.setAttribute("aria-busy", "true");
    button.innerHTML = '<span class="play-spinner" aria-hidden="true"></span><span class="sr-only">Apertura MPV...</span>';
    return state;
  }

  function restorePlayLoading(state) {
    if (!state) return;
    state.button.disabled = state.disabled;
    state.button.classList.remove("is-loading");
    state.button.removeAttribute("aria-busy");
    state.button.removeAttribute("data-play-loading");
    state.button.style.removeProperty("--loading-button-width");
    state.button.innerHTML = state.html;
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function showPlaybackError(message) {
    window.alert(message || "Impossibile aprire MPV.");
  }

  async function waitForPlayback(payload) {
    if (!payload.status_url) return payload.redirect;
    const startedAt = Date.now();
    while (Date.now() - startedAt < 60000) {
      await delay(400);
      const response = await fetch(payload.status_url, {
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
      });
      if (!response.ok) throw new Error("Impossibile controllare lo stato di MPV.");
      const status = await response.json();
      if (status.status === "ready") return payload.redirect;
      if (status.status === "error") throw new Error(status.error || "Impossibile aprire MPV.");
    }
    throw new Error("Timeout durante l'apertura di MPV.");
  }

  async function submitPlayForm(form, submitter) {
    // prima di setPlayLoading: un bottone disabilitato non entra nel FormData
    const body = new URLSearchParams(new FormData(form, submitter));
    const state = setPlayLoading(form, submitter);
    try {
      const response = await fetch("/play/start", {
        method: "POST",
        body,
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
        },
      });
      if (!response.ok) {
        const html = await response.text();
        document.open();
        document.write(html);
        document.close();
        return;
      }
      const payload = await response.json();
      const redirect = await waitForPlayback(payload);
      if (redirect) {
        window.location.assign(redirect);
        return;
      }
    } catch (error) {
      console.error("Errore apertura MPV", error);
      showPlaybackError(error instanceof Error ? error.message : "");
    }
    restorePlayLoading(state);
  }

  document.addEventListener("submit", (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.getAttribute("action") !== "/play") return;
    event.preventDefault();
    submitPlayForm(form, event.submitter);
  }, true);
})();

// Home: ricarica le card della watchlist quando il refresh in background è finito.
(() => {
  const rail = document.querySelector("#watchlist .rail");
  if (!rail) return;
  let polls = 0;
  const poll = async () => {
    let data;
    try {
      const response = await fetch("/watchlist/cards", {
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
      });
      if (!response.ok) return;
      data = await response.json();
    } catch (error) {
      return;
    }
    rail.innerHTML = data.html;
    if (!data.refreshing || polls++ > 20) return;
    window.setTimeout(poll, 1500);
  };
  window.setTimeout(poll, 1500);
})();
