// Motion for the home page. Without JavaScript, or with reduced motion, every element
// shows its final state, so nothing here carries content.
const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// Run fn once, the first time el is on screen.
const whenSeen = (el, fn, threshold = 0.35) => {
  const seen = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      seen.disconnect();
      fn();
    }
  }, { threshold });
  seen.observe(el);
};

// The hero: merged pull requests take turns at the front of a deck. Each one opens, the
// retired value is struck, the replacement is typed, and it is merged. The deck waits
// while it is off screen or under the pointer, and the buttons under it pick a card.
const deck = document.querySelector("[data-deck]");
if (deck) {
  const cards = [...deck.querySelectorAll("[data-pr]")];
  const picker = deck.querySelector(".pr-picks");
  const picks = [...picker.querySelectorAll("button")];
  const texts = cards.map((card) => card.querySelector("[data-type]").textContent);
  const HOLD = 9000;
  let current = 0;
  let run = 0;
  let timer = 0;
  let left = HOLD;
  let since = 0;
  let running = false;
  let started = false;
  let visible = false;
  let hovering = false;

  // The card as merged, which is also what a visitor without JavaScript sees.
  const finish = (i) => {
    const card = cards[i];
    card.classList.remove("play");
    card.classList.add("s1", "s2", "s3", "s4");
    const state = card.querySelector("[data-state]");
    state.textContent = "Merged";
    state.classList.remove("open");
    card.querySelector("[data-type]").textContent = texts[i];
  };

  const rewind = (i) => {
    const card = cards[i];
    card.classList.remove("s1", "s2", "s3", "s4");
    card.classList.add("play");
    const state = card.querySelector("[data-state]");
    state.textContent = "Open";
    state.classList.add("open");
    card.querySelector("[data-type]").textContent = "";
  };

  const play = async (i) => {
    const mine = ++run;
    const card = cards[i];
    const state = card.querySelector("[data-state]");
    const typed = card.querySelector("[data-type]");
    const live = async (ms) => {
      await wait(ms);
      return mine === run;
    };
    rewind(i);
    if (!(await live(450))) return;
    card.classList.add("s1");
    if (!(await live(750))) return;
    card.classList.add("s2");
    for (const char of texts[i]) {
      typed.textContent += char;
      if (!(await live(42))) return;
    }
    if (!(await live(550))) return;
    state.textContent = "Merged";
    state.classList.remove("open");
    card.classList.add("s3");
    if (!(await live(450))) return;
    card.classList.add("s4");
  };

  // Count down on the front card only while someone can see the deck.
  const sync = () => {
    const go = started && visible && !hovering && !still;
    deck.classList.toggle("paused", !go);
    if (go && !running) {
      running = true;
      since = performance.now();
      timer = setTimeout(() => {
        running = false;
        show((current + 1) % cards.length);
      }, Math.max(0, left));
    } else if (!go && running) {
      running = false;
      clearTimeout(timer);
      left -= performance.now() - since;
    }
  };

  const show = (i) => {
    if (i !== current) finish(current);
    current = i;
    cards.forEach((card, n) => {
      card.classList.toggle("front", n === i);
      card.classList.toggle("back", n !== i);
      card.inert = n !== i;
    });
    for (const pick of picks) pick.setAttribute("aria-pressed", "false");
    void picker.offsetWidth; // restarts the progress bar under the button
    picks[i].setAttribute("aria-pressed", "true");
    if (still) finish(i);
    else play(i);
    clearTimeout(timer);
    running = false;
    left = HOLD;
    sync();
  };

  picker.hidden = false;
  deck.style.setProperty("--hold", `${HOLD}ms`);
  cards.forEach((card, n) => {
    if (n !== current) card.inert = true;
  });
  picks.forEach((pick, i) => pick.addEventListener("click", () => {
    started = true;
    show(i);
  }));
  deck.addEventListener("pointerenter", () => {
    hovering = true;
    sync();
  });
  deck.addEventListener("pointerleave", () => {
    hovering = false;
    sync();
  });
  if (!still) rewind(0);
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible && !started) {
      started = true;
      show(0);
    } else sync();
  }, { threshold: 0.2 }).observe(deck);
}

// The seismograph: one deprecation recorded twice. Without Tiltmeter the line stays calm
// until the shutdown date and then breaks; with it, the notice, the pull requests and the
// merges come first and the shutdown passes without a tremor. The traces are drawn at the
// plot's own size, and a playhead reveals them while the stages on the rail light up.
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

  const path = (points) => points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");
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
    whenSeen(plot, () => {
      const DURATION = 6400;
      const t0 = performance.now();
      const frame = (now) => {
        show(Math.max(0, Math.min(1, (now - t0) / DURATION)));
        if (progress < 1) requestAnimationFrame(frame);
        else seis.classList.add("done");
      };
      requestAnimationFrame(frame);
    }, 0.45);
  }
}

// Step 2: the terminal prints line by line.
const term = document.querySelector("[data-typed]");
if (term && !still) {
  term.innerHTML = term.innerHTML.split("\n").map((row) => `<span class="tl">${row}</span>`).join("\n");
  term.classList.add("play");
  whenSeen(term, async () => {
    for (const row of term.querySelectorAll(".tl")) {
      row.classList.add("on");
      await wait(330);
    }
  });
}

// Step 3: the tracker starts with every pull request open, then the merges land.
const tracker = document.querySelector("[data-tracker]");
if (tracker && !still) {
  const flips = [...tracker.querySelectorAll("[data-flip]")];
  for (const badge of flips) {
    badge.className = "badge open";
    badge.textContent = "Open";
  }
  whenSeen(tracker, async () => {
    await wait(500);
    for (const badge of flips) {
      const final = badge.dataset.flip;
      badge.className = `badge ${final} flipped`;
      badge.textContent = final[0].toUpperCase() + final.slice(1);
      await wait(480);
    }
  });
}

// Numbers count up the first time they are seen.
if (!still) {
  for (const el of document.querySelectorAll("[data-count]")) {
    const end = Number(el.dataset.count);
    el.textContent = "0";
    whenSeen(el, () => {
      const t0 = performance.now();
      const frame = (now) => {
        const f = Math.max(0, Math.min(1, (now - t0) / 1100));
        el.textContent = String(Math.round(end * (1 - (1 - f) ** 3)));
        if (f < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    }, 0.6);
  }
}

// Sections rise into place as they scroll in.
if (!still) {
  const reveals = document.querySelectorAll("[data-reveal]");
  const shown = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        entry.target.classList.add("in");
        shown.unobserve(entry.target);
      }
    }
  }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  for (const el of reveals) {
    el.classList.add("rv");
    shown.observe(el);
  }
}

// -- Isometric scenes ---------------------------------------------------------------
// Each [data-scene] tells one story in a loop while it is on screen. The SVG comes from
// scripts/iso_scene.py and shows the final state on its own; .play rewinds it.

const sceneKit = (root) => {
  const added = [];
  const movers = [...root.querySelectorAll(".mv")];
  for (const mv of movers) mv.dataset.home = mv.getAttribute("transform");
  const kit = {
    q: (sel) => root.querySelector(sel),
    qa: (sel) => [...root.querySelectorAll(sel)],
    on(el, ...names) {
      for (const name of names) {
        el.classList.add(name);
        added.push([el, name]);
      }
    },
    off(el, ...names) {
      for (const name of names) el.classList.remove(name);
    },
    reset() {
      for (const [el, name] of added) el.classList.remove(name);
      added.length = 0;
      for (const mv of movers) {
        mv.setAttribute("transform", mv.dataset.home);
        mv.style.opacity = "";
      }
      for (const beam of root.querySelectorAll(".beam")) {
        beam.setAttribute("transform", "");
        beam.style.opacity = "";
      }
    },
    place(el, x, y) {
      el.setAttribute("transform", `translate(${x.toFixed(1)},${y.toFixed(1)})`);
    },
    // Move a .mv group along its data-path (a polyline) or its data-arc (a quadratic curve).
    move(els, ms, { hide = true } = {}) {
      const list = Array.isArray(els) ? els : [els];
      const routes = list.map((el) => {
        const points = (el.dataset.arc || el.dataset.path).trim().split(/\s+/).map((pair) => pair.split(",").map(Number));
        if (el.dataset.arc) {
          const [a, c, b] = points;
          return (t) => [0, 1].map((i) => (1 - t) ** 2 * a[i] + 2 * (1 - t) * t * c[i] + t ** 2 * b[i]);
        }
        const lengths = points.slice(1).map(([x, y], i) => Math.hypot(x - points[i][0], y - points[i][1]));
        const total = lengths.reduce((sum, n) => sum + n, 0);
        return (t) => {
          let left = t * total;
          for (let i = 0; i < lengths.length; i++) {
            if (left <= lengths[i] || i === lengths.length - 1) {
              const f = lengths[i] ? Math.min(1, left / lengths[i]) : 1;
              return [0, 1].map((k) => points[i][k] + (points[i + 1][k] - points[i][k]) * f);
            }
            left -= lengths[i];
          }
          return points.at(-1);
        };
      });
      return new Promise((done) => {
        for (const el of list) el.style.opacity = "1";
        const t0 = performance.now();
        const frame = (now) => {
          const f = Math.max(0, Math.min(1, (now - t0) / ms));
          const eased = f < 0.5 ? 2 * f * f : 1 - (-2 * f + 2) ** 2 / 2;
          list.forEach((el, i) => {
            const at = routes[i](eased);
            if (at) kit.place(el, ...at);
          });
          if (f < 1) requestAnimationFrame(frame);
          else {
            if (hide) for (const el of list) el.style.opacity = "0";
            done();
          }
        };
        requestAnimationFrame(frame);
      });
    },
    // Sweep a .beam across its data-dx/data-dy; onStep(f) runs every frame with 0 → 1.
    sweep(beam, ms, onStep) {
      const dx = Number(beam.dataset.dx);
      const dy = Number(beam.dataset.dy);
      beam.style.opacity = "1";
      return new Promise((done) => {
        const t0 = performance.now();
        const frame = (now) => {
          const f = Math.max(0, Math.min(1, (now - t0) / ms));
          beam.setAttribute("transform", `translate(${(dx * f).toFixed(1)},${(dy * f).toFixed(1)})`);
          onStep(f);
          if (f < 1) requestAnimationFrame(frame);
          else {
            beam.style.opacity = "0";
            done();
          }
        };
        requestAnimationFrame(frame);
      });
    },
  };
  return kit;
};

const scenes = {
  // A signed notice flies to Tiltmeter, the beam finds the code, the fixes go out, all merge.
  async provider(k, root) {
    const steps = k.qa(".iso-steps li");
    const step = (n) => steps.forEach((li, i) => {
      if (i < n - 1) k.on(li, "done");
      if (i === n - 1) k.on(li, "on");
    });
    const tiles = k.qa(".tile.hit");
    step(1);
    await wait(700);
    k.on(root, "fly");
    await k.move(k.q(".mv.notice"), 1500);
    k.off(root, "fly");
    k.on(root, "sent");
    k.on(root, "think", "quake");
    step(2);
    await wait(350);
    await k.sweep(k.q(".beam"), 2100, (f) => {
      for (const tile of tiles) if (f >= Number(tile.dataset.at)) k.on(tile, "found");
    });
    k.off(root, "quake");
    step(3);
    const fixers = k.qa(".mv.fixer");
    fixers.forEach((cube, i) => setTimeout(() => k.move(cube, 1300), i * 200));
    await wait(1300 + (fixers.length - 1) * 200);
    for (const card of k.qa(".bb.prb")) {
      k.on(card, "show");
      await wait(140);
    }
    await wait(900);
    const order = ["a", "b", "c"];
    for (const name of order) {
      k.on(k.q(`.tile.h-${name}`), "fixed");
      k.on(k.q(`.bb.prb-${name}`), "done");
      await wait(320);
    }
    step(4);
    steps.forEach((li) => k.on(li, "done"));
    k.off(root, "think");
    await wait(2800);
  },

  // No provider: responses flow in, one has a new shape, CI and the agent hear about it, the fix merges.
  async drift(k, root) {
    const normal = k.qa(".mv.resp:not(.odd)");
    normal.forEach((packet, i) => setTimeout(() => k.move(packet, 1500), i * 520));
    await wait(normal.length * 520 + 300);
    await k.move(k.q(".mv.resp.odd"), 1600);
    k.on(root, "think", "quake");
    k.on(k.q(".bb.diff-bb"), "show");
    await wait(700);
    k.on(root, "alarm");
    await k.move(k.qa(".mv.ping"), 900);
    k.on(k.q(".bb.ci-bb"), "show");
    k.on(k.q(".bb.agent-bb"), "show");
    await wait(1300);
    k.on(k.q(".bb.fix-bb"), "show");
    await wait(1200);
    k.on(k.q(".bb.fix-bb"), "done");
    k.on(k.q(".bb.ci-bb"), "done");
    k.off(root, "alarm", "quake", "think");
    k.on(root, "calm");
    k.off(k.q(".bb.agent-bb"), "show");
    await wait(2800);
  },

  // tiltmeter scan: the beam crosses the repository and tags what already broke.
  async scan(k, root) {
    const files = k.qa(".file");
    k.on(root, "think");
    await wait(600);
    await k.sweep(k.q(".beam"), 2800, (f) => {
      for (const file of files) {
        if (f < Number(file.dataset.at) || file.classList.contains("scanned")) continue;
        k.on(file, "scanned");
        if (file.classList.contains("hit")) {
          k.on(file, "found");
          const id = [...file.classList].find((name) => /^f\d\d$/.test(name)).slice(1);
          k.on(k.q(`.bb.t${id}`), "show");
        }
      }
    });
    k.off(root, "think");
    await wait(300);
    k.on(k.q(".bb.result"), "show");
    await wait(3200);
  },

  // The pull request: the agent fixes the file, skips dead code, the tests pass, the PR merges.
  async fix(k) {
    const card = k.q(".mv.pr-card");
    const [takeoff] = card.dataset.arc.split(/\s+/).map((pair) => pair.split(",").map(Number));
    k.place(card, ...takeoff);
    card.style.opacity = "0";
    await wait(600);
    await k.move(k.q(".mv.agent-cube"), 1000, { hide: false });
    k.on(k.q(".file.broken"), "fixed");
    k.on(k.q(".bb.edit-bb"), "show");
    await wait(700);
    k.on(k.q(".bb.dead-bb"), "show");
    await wait(900);
    k.q(".mv.agent-cube").style.opacity = "0";
    for (const test of k.qa(".test")) {
      k.on(test, "pass");
      await wait(230);
    }
    await wait(300);
    k.on(k.q(".bb.card"), "show");
    await k.move(card, 1400, { hide: false });
    await wait(500);
    k.on(k.q(".bb.card"), "done");
    await wait(2800);
  },
};

if (!still) {
  for (const root of document.querySelectorAll("[data-scene]")) {
    const play = scenes[root.dataset.scene];
    if (!play) continue;
    const kit = sceneKit(root);
    let visible = false;
    new IntersectionObserver((entries) => {
      visible = entries.some((entry) => entry.isIntersecting);
    }, { threshold: 0.35 }).observe(root);
    root.classList.add("play");
    (async () => {
      for (;;) {
        while (!visible) await wait(250);
        kit.reset();
        await play(kit, root);
      }
    })();
  }
}

// The scenes lean toward the pointer, a few degrees, on devices with a fine pointer.
if (!still && matchMedia("(hover: hover) and (pointer: fine)").matches) {
  for (const stage of document.querySelectorAll(".iso-stage")) {
    const box = stage.closest(".iso") || stage;
    box.addEventListener("pointermove", (event) => {
      const rect = box.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      stage.style.setProperty("--ry", `${(x * 6).toFixed(2)}deg`);
      stage.style.setProperty("--rx", `${(-y * 5).toFixed(2)}deg`);
    });
    box.addEventListener("pointerleave", () => {
      stage.style.setProperty("--ry", "0deg");
      stage.style.setProperty("--rx", "0deg");
    });
  }
}
