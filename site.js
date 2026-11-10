// Every page: the navigation folds into a menu on narrow screens. Without JavaScript the
// links simply wrap onto a second row (site.css), so nothing here is required to navigate.
const nav = document.querySelector(".site-nav");
const toggle = nav?.querySelector(".site-nav__toggle");
if (nav && toggle) {
  const set = (open, { focus = false } = {}) => {
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Close" : "Menu";
    nav.toggleAttribute("data-open", open);
    if (focus) toggle.focus();
  };
  toggle.addEventListener("click", () => set(toggle.getAttribute("aria-expanded") !== "true"));
  nav.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.hasAttribute("data-open")) set(false, { focus: true });
  });
  nav.querySelector(".site-nav__menu").addEventListener("click", (event) => {
    if (event.target.closest("a")) set(false);
  });
  matchMedia("(min-width: 881px)").addEventListener("change", (event) => {
    if (event.matches) set(false);
  });
}
