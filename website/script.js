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

mobileMenu?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => setMenuOpen(false));
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setMenuOpen(false);
});

window.addEventListener("resize", () => {
  if (window.innerWidth > 960) setMenuOpen(false);
});

const track = (eventName, properties = {}) => {
  const detail = Object.freeze({ event: eventName, ...properties });
  window.dispatchEvent(new CustomEvent("nomad-agent:analytics", { detail }));

  if (typeof window.plausible === "function") {
    window.plausible(eventName, { props: properties });
  }
};

window.nomadAgentAnalytics = Object.freeze({ track });

document.querySelectorAll("[data-event]").forEach((element) => {
  element.addEventListener("click", () => {
    track(element.dataset.event, {
      actor: element.dataset.actor,
      placement: element.dataset.placement,
    });
  });
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
  textArea.style.position = "fixed";
  textArea.style.opacity = "0";
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
    track("skill_source_selected", { actor: option.dataset.sourceOption });
  });
});

copyButton?.addEventListener("click", async () => {
  try {
    await copyText(command?.textContent?.trim() ?? "");
    copyButton.classList.add("is-copied");
    copyButton.setAttribute("aria-label", "Install command copied");
    if (commandStatus) commandStatus.textContent = "Install command copied to the clipboard.";
    const activeSource = document.querySelector('[data-source-option][aria-pressed="true"]');
    track("install_command_copied", { actor: activeSource?.dataset.sourceOption });
    copyResetTimer = window.setTimeout(resetCopyFeedback, 3000);
  } catch {
    copyButton.setAttribute("aria-label", "Copy unavailable; select the command manually");
    if (commandStatus) commandStatus.textContent = "Copy unavailable. Select the command manually.";
  }
});

document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});
