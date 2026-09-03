(() => {
  "use strict";

  const menuButton = document.querySelector("[data-menu-button]");
  const mobileMenu = document.querySelector("[data-mobile-menu]");

  const setMenuOpen = (open) => {
    if (!menuButton || !mobileMenu) return;
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    mobileMenu.classList.toggle("is-open", open);
    document.body.classList.toggle("menu-open", open);
  };

  menuButton?.addEventListener("click", () => {
    setMenuOpen(menuButton.getAttribute("aria-expanded") !== "true");
  });

  mobileMenu?.addEventListener("click", (event) => {
    if (event.target.closest("a")) setMenuOpen(false);
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuOpen(false);
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 960) setMenuOpen(false);
  });

  // This layer intentionally creates no cookies, user IDs, query-string capture,
  // or network requests. A site owner may attach a consent-aware collector to the
  // CustomEvent, subscribe API, or an existing dataLayer/Plausible installation.
  const subscribers = new Set();
  const propertyNames = [
    "category",
    "label",
    "placement",
    "product",
    "actor",
    "destination",
    "content",
    "format",
  ];
  const privacySignalEnabled =
    navigator.globalPrivacyControl === true ||
    navigator.doNotTrack === "1" ||
    window.doNotTrack === "1";

  const cleanValue = (value) => {
    if (typeof value !== "string") return undefined;
    const cleaned = value.trim().slice(0, 120);
    return cleaned || undefined;
  };

  const sanitizeProperties = (properties = {}) => {
    const result = {};
    for (const key of propertyNames) {
      const value = cleanValue(properties[key]);
      if (value) result[key] = value;
    }
    result.page = window.location.pathname;
    return result;
  };

  const track = (eventName, properties = {}) => {
    const event = cleanValue(eventName);
    if (!event || privacySignalEnabled) return false;

    const detail = Object.freeze({ event, ...sanitizeProperties(properties) });
    window.dispatchEvent(new CustomEvent("nomad-agent:analytics", { detail }));

    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push({ ...detail });
    }

    if (typeof window.plausible === "function") {
      const { event: _event, ...props } = detail;
      window.plausible(event, { props });
    }

    subscribers.forEach((subscriber) => {
      try {
        subscriber(detail);
      } catch {
        // A consumer must not break navigation or other page behavior.
      }
    });
    return true;
  };

  const subscribe = (subscriber) => {
    if (typeof subscriber !== "function") return () => {};
    subscribers.add(subscriber);
    return () => subscribers.delete(subscriber);
  };

  window.nomadAgentAnalytics = Object.freeze({
    track,
    subscribe,
    collectorConfigured: () =>
      Array.isArray(window.dataLayer) || typeof window.plausible === "function" || subscribers.size > 0,
  });

  document.addEventListener("click", (event) => {
    const origin = event.target instanceof Element ? event.target : event.target.parentElement;
    const element = origin?.closest("[data-event]");
    if (!element) return;

    const properties = {};
    for (const key of propertyNames) {
      if (element.dataset[key]) properties[key] = element.dataset[key];
    }
    track(element.dataset.event, properties);
  });

  const [pageGroup = "home"] = window.location.pathname.split("/").filter(Boolean);
  track("page_view", {
    category: "navigation",
    label: pageGroup,
    placement: "document",
  });

  const copyButton = document.querySelector("[data-copy-command]");
  const command = document.querySelector("[data-command]");
  const commandStatus = document.querySelector("[data-command-status]");
  const sourceOptions = document.querySelectorAll("[data-source-option]");
  let copyResetTimer;

  const resetCopyFeedback = () => {
    window.clearTimeout(copyResetTimer);
    copyButton?.classList.remove("is-copied");
    copyButton?.setAttribute("aria-label", "Copy install command");
    if (commandStatus) commandStatus.textContent = "";
  };

  const copyText = async (value) => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }

    const textArea = document.createElement("textarea");
    textArea.value = value;
    textArea.setAttribute("readonly", "");
    textArea.className = "clipboard-fallback";
    document.body.append(textArea);
    textArea.select();
    const copied = document.execCommand("copy");
    textArea.remove();
    if (!copied) throw new Error("Copy command failed");
  };

  sourceOptions.forEach((option) => {
    option.addEventListener("click", () => {
      sourceOptions.forEach((candidate) => {
        candidate.setAttribute("aria-pressed", String(candidate === option));
      });
      if (command) command.textContent = option.dataset.commandValue ?? "";
      resetCopyFeedback();
      track("skill_source_selected", {
        category: "agent_skill",
        product: option.dataset.sourceOption,
        placement: "skill-installer",
      });
    });
  });

  copyButton?.addEventListener("click", async () => {
    try {
      await copyText(command?.textContent?.trim() ?? "");
      copyButton.classList.add("is-copied");
      copyButton.setAttribute("aria-label", "Install command copied");
      if (commandStatus) commandStatus.textContent = "Install command copied to the clipboard.";
      const activeSource = document.querySelector('[data-source-option][aria-pressed="true"]');
      track("install_command_copied", {
        category: "agent_skill",
        product: activeSource?.dataset.sourceOption,
        placement: "skill-installer",
        format: "shell-command",
      });
      copyResetTimer = window.setTimeout(resetCopyFeedback, 3000);
    } catch {
      copyButton.setAttribute("aria-label", "Copy unavailable; select the command manually");
      if (commandStatus) commandStatus.textContent = "Copy unavailable. Select the command manually.";
    }
  });

  document.querySelectorAll("[data-year]").forEach((element) => {
    element.textContent = String(new Date().getFullYear());
  });
})();
