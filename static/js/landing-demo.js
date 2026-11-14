// Self-playing example question on the home page. Pauses when off-screen,
// on hover/focus, on request, and never runs under prefers-reduced-motion.
(function () {
  const demo = document.querySelector("[data-landing-demo]");
  if (!demo) return;
  if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;

  const stage = demo.querySelector("[data-demo-stage]");
  const options = Array.from(demo.querySelectorAll("[data-demo-opt]"));
  const feedback = demo.querySelector("[data-demo-feedback]");
  const secsEl = demo.querySelector("[data-demo-secs]");
  const ring = demo.querySelector("[data-demo-ring]");
  const ringBar = demo.querySelector("[data-demo-ringbar]");
  const segs = Array.from(demo.querySelectorAll("[data-demo-segs] i"));
  const qn = demo.querySelector("[data-demo-qn]");
  const toggle = demo.querySelector("[data-demo-toggle]");
  const CIRC = 2 * Math.PI * 18;
  const TOTAL = 15;
  const items = [
    { statement: "Leo is lighter than Henry.", question: "Who is heavier?", answers: ["Leo", "Henry"], right: 1, time: "4.2s" },
    { statement: "Mia is not as tall as Ava.", question: "Who is shorter?", answers: ["Mia", "Ava"], right: 0, time: "3.8s" },
    { statement: "Sam runs faster than Noor.", question: "Who is slower?", answers: ["Sam", "Noor"], right: 1, time: "5.1s" },
  ];

  let timers = [];
  let tick = null;
  let index = 0;
  let question = 6;
  let paused = false;
  let hovering = false;
  let visible = true;

  ringBar.style.strokeDasharray = String(CIRC);
  toggle.hidden = false;

  const later = (fn, ms) => timers.push(window.setTimeout(fn, ms));
  const stop = () => {
    timers.forEach(window.clearTimeout);
    timers = [];
    window.clearInterval(tick);
  };
  const setRing = (seconds) => {
    secsEl.textContent = String(seconds).padStart(2, "0");
    ringBar.style.strokeDashoffset = String(CIRC * (1 - seconds / TOTAL));
    ring.classList.toggle("is-low", seconds <= 5);
  };
  const setProgress = (n) => {
    segs.forEach((seg, i) => {
      seg.className = i < n ? "is-done" : i === n ? "is-now" : "";
    });
    qn.textContent = String(n + 1).padStart(2, "0");
  };
  // Types the text into the stage one character at a time, like someone
  // reading the question on screen.
  const swapStage = (text) => {
    stage.classList.add("is-out");
    later(() => {
      stage.textContent = "";
      stage.classList.remove("is-out");
      stage.classList.add("is-typing");
      [...text].forEach((char, i) => {
        later(() => {
          stage.textContent += char;
          if (i === text.length - 1) stage.classList.remove("is-typing");
        }, 28 * i);
      });
    }, 180);
  };

  const run = () => {
    const item = items[index % items.length];
    let left = TOTAL;
    options.forEach((option, i) => {
      option.className = "landing-demo-option";
      option.textContent = item.answers[i];
      option.style.visibility = "hidden";
    });
    feedback.classList.remove("is-on");
    setProgress(question % 10);
    setRing(left);
    swapStage(item.statement);
    tick = window.setInterval(() => {
      if (left > 0) setRing(--left);
    }, 1000);
    later(() => {
      swapStage(item.question);
      options.forEach((option) => { option.style.visibility = "visible"; });
    }, 2600);
    const chosen = options[item.right];
    const other = options[1 - item.right];
    later(() => chosen.classList.add("is-pressed"), 4300);
    later(() => {
      chosen.classList.remove("is-pressed");
      chosen.classList.add("is-right");
      other.classList.add("is-dim");
      feedback.textContent = `✓ Correct · ${item.time}`;
      feedback.classList.add("is-on");
      window.clearInterval(tick);
    }, 4450);
    later(() => {
      index += 1;
      question += 1;
      run();
    }, 7000);
  };

  const start = () => {
    if (paused || hovering || !visible) return;
    stop();
    run();
  };

  toggle.addEventListener("click", () => {
    paused = !paused;
    toggle.textContent = paused ? "Play" : "Pause";
    if (paused) stop(); else start();
  });
  demo.addEventListener("mouseenter", () => { hovering = true; stop(); });
  demo.addEventListener("mouseleave", () => { hovering = false; start(); });

  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
      if (visible) start(); else stop();
    }).observe(demo);
  } else {
    start();
  }
})();
