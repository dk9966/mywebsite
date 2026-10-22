import { useEffect, useRef, useState } from "react";
import Paragraphs from "./Paragraphs";
import TextPanel from "./TextPanel";
import TextScene from "./TextScene";
import "./text-lab.css";

// /text — a type lab for the four section titles: rotatable 3D words with a
// control panel, the same titles over paragraph copy, then the live root
// scene (desk panels + table) underneath for context.

/** `once` latches true after the first intersection. */
function useInView<T extends Element>({ margin = "0px", initial = true, once = false } = {}) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(initial);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => setInView((prev) => (once && prev) || entry.isIntersecting),
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [margin, once]);
  return [ref, inView] as const;
}

const NAV = [
  ["titles", "3D titles"],
  ["paragraphs", "Paragraph text"],
  ["root", "Root scene"],
] as const;

function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function TextLab() {
  const [heroRef, heroInView] = useInView<HTMLElement>();
  // Mount the root scene only as it approaches, so its boot doesn't compete
  // with the font lab's first load.
  const [rootRef, showRoot] = useInView<HTMLElement>({ margin: "600px", initial: false, once: true });

  return (
    <div className="tl-page">
      {/* Wheel zooms the 3D view, so it can't also scroll the page while the
          pointer is over it — this nav (and the scrollbar) covers that. */}
      <nav className="tl-nav" aria-label="Sections">
        {NAV.map(([id, label]) => (
          <button key={id} type="button" className="tl-nav__btn" onClick={() => jump(id)}>
            {label}
          </button>
        ))}
      </nav>
      <section id="titles" ref={heroRef} className="tl-hero" aria-label="3D titles">
        <TextScene active={heroInView} />
        <div className="tl-hero__caption">
          <span>Drag: rotate · Right-drag / Shift-drag: pan · Wheel: zoom</span>
          <button type="button" className="tl-hero__more" onClick={() => jump("paragraphs")}>
            Paragraph text ↓
          </button>
        </div>
      </section>

      <section id="paragraphs" className="tl-section-block" aria-label="Paragraph text">
        <header className="tl-section-block__head">
          <span className="tl-kicker">02</span>
          <h1>Paragraph text</h1>
        </header>
        <Paragraphs />
      </section>

      <section id="root" ref={rootRef} className="tl-section-block tl-root" aria-label="Root scene">
        <header className="tl-section-block__head">
          <span className="tl-kicker">03</span>
          <h1>Root scene — panels &amp; table</h1>
          <a className="tl-root__open" href="/" target="_blank" rel="noreferrer">
            Open / ↗
          </a>
        </header>
        <div className="tl-root__frame">
          {showRoot ? <iframe src="/" title="Root desk scene" /> : <div className="tl-root__placeholder">Loading…</div>}
        </div>
      </section>

      <TextPanel />
    </div>
  );
}
