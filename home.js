// The home page. Without JavaScript, or with reduced motion, every element shows its final
// state and every case is readable, so nothing here carries content.
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// -- The cases: two merged pull requests as an ARIA tablist (arrow keys, Home, End). ---------
// Without JavaScript both records show, one after the other.
const cases = document.querySelector("[data-cases]");
if (cases) {
  const list = cases.querySelector('[role="tablist"]');
  const tabs = [...list.querySelectorAll('[role="tab"]')];
  const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));
  const select = (i, { focus = false } = {}) => {
    tabs.forEach((tab, n) => {
      tab.setAttribute("aria-selected", String(n === i));
      tab.tabIndex = n === i ? 0 : -1;
      panels[n].hidden = n !== i;
    });
    if (focus) tabs[i].focus();
  };
  panels.forEach((panel, n) => {
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", tabs[n].id);
  });
  list.hidden = false;
  select(0);
  tabs.forEach((tab, i) => tab.addEventListener("click", () => select(i)));
  list.addEventListener("keydown", (event) => {
    const at = tabs.indexOf(document.activeElement);
    const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[event.key];
    if (to === undefined || at < 0) return;
    event.preventDefault();
    select((to + tabs.length) % tabs.length, { focus: true });
  });
}

// -- Fig. 1: the drawing follows the step at the reading line. ------------------------------
// Each step has an end state (apply). Moving forward by one step plays the motion that leads
// there (animate); any other move, or a scroll that interrupts, jumps straight to the state.
const sequence = document.querySelector("[data-sequence]");
if (sequence && !still) {
  const svgs = [...sequence.querySelectorAll(".iso-svg")];
  const steps = [...sequence.querySelectorAll(".step[data-step]")];
  const narrow = matchMedia("(max-width: 760px)");
  const homes = new Map();
  for (const svg of svgs) for (const mv of svg.querySelectorAll(".mv")) homes.set(mv, mv.getAttribute("transform"));

  const place = (el, x, y) => el.setAttribute("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`);
  const points = (attr) => attr.trim().split(/\s+/).map((pair) => pair.split(",").map(Number));
  const ease = (f) => (f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2);

  // Run onFrame(0 → 1) over ms, unless the run it belongs to is overtaken.
  const tween = (ms, onFrame, alive) => new Promise((done) => {
    const t0 = performance.now();
    const frame = (now) => {
      if (!alive()) return done(false);
      const f = Math.min(1, (now - t0) / ms);
      onFrame(f);
      if (f < 1) requestAnimationFrame(frame);
      else done(true);
    };
    requestAnimationFrame(frame);
  });
  const along = (el) => {
    if (el.dataset.arc) {
      const [a, c, b] = points(el.dataset.arc);
      return (t) => [0, 1].map((k) => (1 - t) ** 2 * a[k] + 2 * (1 - t) * t * c[k] + t ** 2 * b[k]);
    }
    const pts = points(el.dataset.path);
    const lengths = pts.slice(1).map(([x, y], i) => Math.hypot(x - pts[i][0], y - pts[i][1]));
    const total = lengths.reduce((sum, n) => sum + n, 0);
    return (t) => {
      let left = t * total;
      for (let i = 0; i < lengths.length; i++) {
        if (left <= lengths[i] || i === lengths.length - 1) {
          const f = lengths[i] ? Math.min(1, left / lengths[i]) : 1;
          return [0, 1].map((k) => pts[i][k] + (pts[i + 1][k] - pts[i][k]) * f);
        }
        left -= lengths[i];
      }
      return pts.at(-1);
    };
  };

  const apply = (svg, n) => {
    const q = (sel) => svg.querySelector(sel);
    const qa = (sel) => [...svg.querySelectorAll(sel)];
    svg.classList.remove("flying", "ping");
    svg.classList.toggle("sent", n >= 2);
    svg.classList.toggle("quaking", n === 2);
    q(".needle").classList.toggle("tilt", n === 2 || n === 3);
    for (const mv of qa(".mv")) {
      mv.setAttribute("transform", homes.get(mv));
      mv.style.opacity = "";
    }
    const beam = q(".beam");
    beam.setAttribute("transform", "");
    beam.style.opacity = "";
    for (const tile of qa(".tile.hit")) {
      tile.classList.toggle("found", n >= 2 && n < 4);
      tile.classList.toggle("fixed", n >= 4);
    }
    for (const card of qa(".bb.prb")) {
      card.classList.toggle("show", n >= 3);
      card.classList.toggle("done", n >= 4);
    }
  };

  const animate = async (svg, to, alive) => {
    const q = (sel) => svg.querySelector(sel);
    const qa = (sel) => [...svg.querySelectorAll(sel)];
    if (to === 2) {
      const notice = q(".mv.notice");
      const route = along(notice);
      svg.classList.add("flying");
      if (!(await tween(1100, (f) => place(notice, ...route(ease(f))), alive))) return false;
      svg.classList.remove("flying");
      svg.classList.add("sent", "ping", "quaking");
      q(".needle").classList.add("tilt");
      await wait(250);
      if (!alive()) return false;
      const beam = q(".beam");
      const dx = Number(beam.dataset.dx);
      const dy = Number(beam.dataset.dy);
      const tiles = qa(".tile.hit");
      beam.style.opacity = "1";
      const swept = await tween(1300, (f) => {
        beam.setAttribute("transform", `translate(${(dx * f).toFixed(1)},${(dy * f).toFixed(1)})`);
        for (const tile of tiles) if (f >= Number(tile.dataset.at)) tile.classList.add("found");
      }, alive);
      beam.style.opacity = "";
      return swept;
    }
    if (to === 3) {
      const fixers = qa(".mv.fixer");
      const routes = fixers.map(along);
      fixers.forEach((el) => (el.style.opacity = "1"));
      const flown = await tween(1100, (f) => fixers.forEach((el, i) => {
        const g = Math.max(0, Math.min(1, (f * 1.3 - i * 0.15)));
        place(el, ...routes[i](ease(g)));
      }), alive);
      fixers.forEach((el) => (el.style.opacity = ""));
      if (!flown) return false;
      for (const card of qa(".bb.prb")) {
        card.classList.add("show");
        await wait(120);
        if (!alive()) return false;
      }
      return true;
    }
    if (to === 4) {
      for (const name of ["a", "b", "c"]) {
        q(`.tile.h-${name}`).classList.add("fixed");
        q(`.tile.h-${name}`).classList.remove("found");
        q(`.bb.prb-${name}`).classList.add("done");
        await wait(260);
        if (!alive()) return false;
      }
      q(".needle").classList.remove("tilt");
      return true;
    }
    return true;
  };

  let shown = 1;
  let run = 0;
  const shownSvg = () => svgs.find((svg) => svg.getClientRects().length > 0);
  const go = async (n) => {
    const mine = ++run;
    const alive = () => mine === run;
    const svg = shownSvg();
    for (const other of svgs) if (other !== svg) apply(other, n);
    if (svg && n === shown + 1) {
      apply(svg, shown);
      const finished = await animate(svg, n, alive);
      if (!finished) return;
    }
    if (svg) apply(svg, n);
    shown = n;
  };

  // The reading line: halfway down a desktop screen, and below the pinned figure on a phone.
  let active = 0;
  let queued = 0;
  const read = () => {
    queued = 0;
    const line = innerHeight * (narrow.matches ? 0.66 : 0.55);
    let n = 1;
    for (const step of steps) if (step.getBoundingClientRect().top <= line) n = Number(step.dataset.step);
    if (n === active) return;
    active = n;
    steps.forEach((step) => step.classList.toggle("is-active", Number(step.dataset.step) === n));
    go(n);
  };
  const schedule = () => {
    if (!queued) queued = requestAnimationFrame(read);
  };

  sequence.setAttribute("data-live", "");
  for (const svg of svgs) apply(svg, 1);
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);
  narrow.addEventListener("change", () => {
    for (const svg of svgs) apply(svg, shown);
    schedule();
  });
  read();
}

// -- The seismograph (problem section, until that section is rebuilt) ----------------------
const plot = document.querySelector("[data-seis]");
if (plot) {
  const seis = plot.closest(".seis");
  const svg = plot.querySelector("svg");
  const clip = plot.querySelector(".seis-clip");
  const marks = [...seis.querySelectorAll("[data-at]")];
  const [penA, penB] = plot.querySelectorAll(".seis-pen");
  const CUT = 0.75;
  const STEP = 3;
  let traces = null;
  let progress = 1;

  const path = (pts) => pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");
  const draw = () => {
    const w = svg.clientWidth;
    const h = svg.clientHeight;
    if (!w || !h) return;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    let seed = 11;
    const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    const half = h / 2;
    const baseA = half * 0.6 + 4;
    const baseB = half * 1.58;
    const calm = (x, base) => base + Math.sin(x / 31) * 1.4 + (random() - 0.5) * 4.5;
    const cut = CUT * w;
    const a = [];
    const b = [];
    for (let x = 0; x <= w; x += STEP) {
      b.push([x, calm(x, baseB)]);
      if (x <= cut) a.push([x, calm(x, baseA)]);
    }
    const amp = half * 0.32;
    const quake = [];
    for (let x = cut; x <= w; x += 1.5) {
      const t = x - cut;
      const envelope = amp * (0.28 + 0.72 * Math.exp(-t / 120)) * (0.85 + 0.15 * Math.sin(t / 23));
      quake.push([x, baseA + envelope * Math.sin(t / 4.6) * (0.7 + random() * 0.3)]);
    }
    plot.querySelector(".seis-a").setAttribute("d", path(a));
    plot.querySelector(".seis-quake").setAttribute("d", path(quake));
    plot.querySelector(".seis-b").setAttribute("d", path(b));
    traces = { w, cut, a, b, quake };
  };

  const show = (f) => {
    progress = f;
    if (!traces) return;
    const { w, cut, a, b, quake } = traces;
    const x = f * w;
    clip.setAttribute("width", `${x.toFixed(1)}`);
    plot.style.setProperty("--p", f.toFixed(4));
    const yA = x <= cut ? a[Math.min(a.length - 1, Math.round(x / STEP))][1] : quake[Math.min(quake.length - 1, Math.round((x - cut) / 1.5))][1];
    const yB = b[Math.min(b.length - 1, Math.round(x / STEP))][1];
    for (const [pen, y] of [[penA, yA], [penB, yB]]) {
      pen.style.left = `${x}px`;
      pen.style.top = `${y}px`;
    }
    for (const mark of marks) mark.classList.toggle("on", f >= Number(mark.dataset.at));
    seis.classList.toggle("quaked", f >= CUT);
  };

  draw();
  show(1);
  let resizing = 0;
  addEventListener("resize", () => {
    cancelAnimationFrame(resizing);
    resizing = requestAnimationFrame(() => {
      draw();
      show(progress);
    });
  });

  if (!still) {
    seis.classList.add("play");
    show(0);
    const seen = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      seen.disconnect();
      const t0 = performance.now();
      const frame = (now) => {
        show(Math.max(0, Math.min(1, (now - t0) / 6400)));
        if (progress < 1) requestAnimationFrame(frame);
        else seis.classList.add("done");
      };
      requestAnimationFrame(frame);
    }, { threshold: 0.45 });
    seen.observe(plot);
  }
}

// -- The sandbox drawing (security section, until that section is rebuilt) -----------------
const fixScene = document.querySelector('[data-scene="fix"]');
if (fixScene && !still) {
  const q = (sel) => fixScene.querySelector(sel);
  const qa = (sel) => [...fixScene.querySelectorAll(sel)];
  const added = [];
  const on = (el, ...names) => names.forEach((name) => { el.classList.add(name); added.push([el, name]); });
  const movers = qa(".mv");
  for (const mv of movers) mv.dataset.home = mv.getAttribute("transform");
  const fly = (el, ms) => new Promise((done) => {
    const [a, c, b] = el.dataset.arc.trim().split(/\s+/).map((pair) => pair.split(",").map(Number));
    el.style.opacity = "1";
    const t0 = performance.now();
    const frame = (now) => {
      const f = Math.min(1, (now - t0) / ms);
      const t = f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2;
      const at = [0, 1].map((k) => (1 - t) ** 2 * a[k] + 2 * (1 - t) * t * c[k] + t ** 2 * b[k]);
      el.setAttribute("transform", `translate(${at[0].toFixed(1)},${at[1].toFixed(1)})`);
      if (f < 1) requestAnimationFrame(frame);
      else done();
    };
    requestAnimationFrame(frame);
  });
  const story = async () => {
    for (const [el, name] of added) el.classList.remove(name);
    added.length = 0;
    for (const mv of movers) mv.setAttribute("transform", mv.dataset.home);
    const card = q(".mv.pr-card");
    const [takeoff] = card.dataset.arc.split(/\s+/).map((pair) => pair.split(",").map(Number));
    card.setAttribute("transform", `translate(${takeoff[0]},${takeoff[1]})`);
    card.style.opacity = "0";
    await wait(600);
    await fly(q(".mv.agent-cube"), 1000);
    on(q(".file.broken"), "fixed");
    on(q(".bb.edit-bb"), "show");
    await wait(700);
    on(q(".bb.dead-bb"), "show");
    await wait(900);
    q(".mv.agent-cube").style.opacity = "0";
    for (const test of qa(".test")) {
      on(test, "pass");
      await wait(230);
    }
    await wait(300);
    on(q(".bb.card"), "show");
    await fly(card, 1400);
    await wait(500);
    on(q(".bb.card"), "done");
  };
  fixScene.classList.add("play");
  const seen = new IntersectionObserver((entries) => {
    if (!entries.some((entry) => entry.isIntersecting)) return;
    seen.disconnect();
    story();
  }, { threshold: 0.35 });
  seen.observe(fixScene);
}
