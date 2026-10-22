import type { CSSProperties, ReactNode } from "react";
import { contact, experience, profile, projects, skillGroups } from "../src/data/resume";
import { cssFontFamily } from "./fonts";
import { WORD_IDS, applyCase, useTextLab, type WordId } from "./store";

const list = (items: string[]) => `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;

// Paragraph specimens: each 3D title over real resume copy, so heading and
// body faces can be judged together at reading sizes.

const BODY: Record<WordId, ReactNode> = {
  project: projects.map((p) => (
    <div key={p.name} className="tl-copy__item">
      <p className="tl-copy__meta">
        {p.name} · {p.context} · {p.period}
      </p>
      <p>{p.summary}</p>
      <p className="tl-copy__meta">{p.stack.join(" / ")}</p>
    </div>
  )),
  about: (
    <>
      <p>
        I’m {profile.name}, a {profile.role.toLowerCase()} working toward an {profile.education[0].degree} at the{" "}
        {profile.education[0].school}, after a {profile.education[1].degree}. I like systems that hold up under
        real-time load — authoritative game servers, self-hosted inference, and ingestion pipelines that keep going
        when a sensor drops out.
      </p>
      <p>
        Day to day I work in {list(skillGroups[0].items)}, and ship on {list(skillGroups[1].items.slice(1))}.
      </p>
    </>
  ),
  experiences: experience.map((e) => (
    <div key={e.company} className="tl-copy__item">
      <p className="tl-copy__meta">
        {e.role} — {e.company} · {e.location} · {e.period}
      </p>
      <p>{e.highlight}</p>
    </div>
  )),
  contact: (
    <>
      <p>
        The fastest way to reach me is a message on any of these. I’m happy to talk about internships, real-time
        systems, or anything you saw on this site.
      </p>
      <p className="tl-copy__links">
        {contact.map((c) => (
          <a key={c.kind} href={c.href} target="_blank" rel="noreferrer">
            {c.label}
          </a>
        ))}
      </p>
    </>
  ),
};

export default function Paragraphs() {
  const p = useTextLab((s) => s.paragraph);
  const font = useTextLab((s) => s.font);
  const words = useTextLab((s) => s.words);

  const bodyStyle: CSSProperties = {
    fontFamily: cssFontFamily(p.bodyFont === "match" ? font : p.bodyFont),
    fontSize: p.size,
    lineHeight: p.lineHeight,
    letterSpacing: `${p.tracking}em`,
    color: p.color,
    maxWidth: `${p.measure}ch`,
    textAlign: p.align,
    marginInline: p.align === "center" ? "auto" : undefined,
  };

  return (
    <div className="tl-copy">
      {WORD_IDS.map((id) => {
        const word = words[id];
        const headingStyle: CSSProperties = {
          fontFamily: cssFontFamily(font),
          fontSize: p.headingSize,
          color: p.headingColor,
          textAlign: p.align === "center" ? "center" : "left",
        };
        return (
          <article key={id} className="tl-copy__block">
            <h2 className="tl-copy__heading" style={headingStyle}>
              {applyCase(word.text, p.headingCase)}
            </h2>
            <div className="tl-copy__body" style={bodyStyle}>
              {BODY[id]}
            </div>
          </article>
        );
      })}
    </div>
  );
}
