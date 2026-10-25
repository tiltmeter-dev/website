const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;

// The seismogram: a quiet trace, one quake where the vendor changed the API, then quiet again.
const trace = document.querySelector("[data-trace]");
if (trace) {
  const WIDTH = 1200;
  const HEIGHT = 220;
  const MID = 120;
  const QUAKE_START = (25 / 39) * WIDTH;
  const QUAKE_END = QUAKE_START + 170;

  let seed = 7;
  const random = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  const calmY = (x) => MID + Math.sin(x / 37) * 1.6 + (random() - 0.5) * 5;
  const quakeY = (x) => {
    const t = x - QUAKE_START;
    const y = MID + 92 * Math.exp(-t / 55) * Math.sin(t / 6.5);
    return Math.min(HEIGHT - 8, Math.max(8, y));
  };
  const points = (from, to, step, y) => {
    const list = [];
    for (let x = from; x < to; x += step) list.push([x, y(x)]);
    list.push([to, y(to)]);
    return list;
  };
  const path = (list) => list.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join("");

  const before = points(0, QUAKE_START, 4, calmY);
  const quake = points(QUAKE_START, QUAKE_END, 1.5, quakeY);
  const after = points(QUAKE_END, WIDTH, 4, calmY);
  quake[0] = before.at(-1);
  after[0] = quake.at(-1);

  const segments = [
    [trace.querySelector(".before"), before],
    [trace.querySelector(".quake"), quake],
    [trace.querySelector(".after"), after],
  ].map(([el, list]) => {
    el.setAttribute("d", path(list));
    const length = el.getTotalLength();
    el.style.strokeDasharray = `${length}`;
    return { el, length, list };
  });

  const pen = document.createElement("span");
  pen.className = "pen";
  trace.append(pen);
  const place = ([x, y]) => {
    pen.style.left = `${(x / WIDTH) * 100}%`;
    pen.style.top = `calc(10px + ${y / HEIGHT} * (100% - 20px))`;
  };

  const total = segments.reduce((sum, s) => sum + s.length, 0);
  const quakeAt = segments[0].length;
  const draw = (progress) => {
    let start = 0;
    for (const s of segments) {
      const drawn = Math.min(Math.max(progress - start, 0), s.length);
      s.el.style.strokeDashoffset = `${s.length - drawn}`;
      if (drawn > 0 && drawn <= s.length) {
        const p = s.el.getPointAtLength(drawn);
        place([p.x, p.y]);
      }
      start += s.length;
    }
    trace.classList.toggle("shown", progress > quakeAt + segments[1].length * 0.25);
    trace.classList.toggle("settled", progress >= total);
  };

  if (calm) {
    draw(total);
  } else {
    draw(0);
    const run = () => {
      const began = performance.now();
      const speed = 0.75;
      const frame = (now) => {
        const progress = Math.min((now - began) * speed, total);
        draw(progress);
        if (progress < total) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    };
    const watch = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        watch.disconnect();
        setTimeout(run, 400);
      },
      { threshold: 0.15 },
    );
    watch.observe(trace);
  }
}

// tiltmeter fix, step by step: drift, worktree, edits, approval, pull request.
const theater = document.querySelector("[data-theater]");
if (theater) {
  // How long each step stays before the next one (ms); the last one holds.
  const DELAYS = [800, 1300, 1400, 1000, 1000, 1000, 1600, 2600, 1300];
  const LAST = DELAYS.length;
  const lines = [...theater.querySelectorAll(".stage [data-at]")];
  const rail = [...theater.querySelectorAll(".rail [data-at]")];
  const files = [...theater.querySelectorAll("[data-edit]")];
  const replay = theater.querySelector(".replay");
  let timer;

  const render = (step) => {
    for (const el of lines) {
      const until = el.dataset.until ? Number(el.dataset.until) : Infinity;
      el.hidden = step < Number(el.dataset.at) || step > until;
    }
    for (const el of rail) el.classList.toggle("on", step >= Number(el.dataset.at));
    for (const el of files) {
      const at = Number(el.dataset.edit);
      el.dataset.state = step < at ? "" : step === at ? "editing" : "done";
    }
    replay.hidden = step < LAST || calm;
  };

  const play = (step = 0) => {
    clearTimeout(timer);
    render(step);
    if (step < LAST) timer = setTimeout(() => play(step + 1), DELAYS[step]);
  };

  replay.addEventListener("click", () => play(0));

  if (calm) {
    render(LAST);
  } else {
    render(0);
    const watch = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        watch.disconnect();
        play(0);
      },
      { threshold: 0.35 },
    );
    watch.observe(theater);
  }
}

for (const el of document.querySelectorAll("[data-copy]")) {
  el.addEventListener("click", async () => {
    const hint = el.querySelector(".hint");
    try {
      await navigator.clipboard.writeText(el.dataset.copy);
      hint.textContent = "copied";
    } catch {
      hint.textContent = "⌘C";
    }
    setTimeout(() => (hint.textContent = "copy"), 1400);
  });
}

for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener("click", () => {
    for (const t of document.querySelectorAll(".tab")) t.classList.toggle("on", t === tab);
    for (const p of document.querySelectorAll(".panel")) p.classList.toggle("on", p.dataset.panel === tab.dataset.tab);
  });
}

for (const btn of document.querySelectorAll("[data-copy-from]")) {
  btn.addEventListener("click", async () => {
    const text = document.querySelector(`[data-panel="${btn.dataset.copyFrom}"] .snippet`).textContent;
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied";
    } catch {
      btn.textContent = "Select & copy";
    }
    setTimeout(() => (btn.textContent = "Copy"), 1400);
  });
}
