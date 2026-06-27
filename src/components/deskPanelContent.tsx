import type { ReactNode } from "react";
import {
  contact,
  experience,
  profile,
  projects,
  skillGroups,
  type ContactKind,
} from "../data/resume";
import "./deskPanelContent.css";

// Real resume content for the five curved HUD panels, sourced from
// src/data/resume.ts. Each panel keeps the cyan glass aesthetic: line-art
// icons stroked in currentColor, thin rules, and a small type hierarchy.

// Profile (01) ---------------------------------------------------------------

export function ProfilePanel() {
  return (
    <div className="hud-profile">
      <div className="hud-profile__avatar">{profile.initials}</div>
      <div className="hud-profile__name">{profile.name}</div>
      <div className="hud-profile__role">{profile.role}</div>

      <ul className="hud-profile__edu">
        {profile.education.map((e) => (
          <li className="hud-profile__edu-item" key={e.degree}>
            <span className="hud-profile__edu-degree">{e.degree}</span>
            <span className="hud-profile__edu-meta">
              {e.school} · {e.period}
            </span>
          </li>
        ))}
      </ul>

      <div className="hud-profile__stats">
        {profile.stats.map((s) => (
          <div className="hud-profile__stat" key={s.label}>
            <span className="hud-profile__stat-value">{s.value}</span>
            <span className="hud-profile__stat-label">{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Skills (02) ----------------------------------------------------------------

export function SkillsPanel() {
  return (
    <div className="hud-skills">
      {skillGroups.map((group) => (
        <div className="hud-skills__group" key={group.label}>
          <span className="hud-skills__label">{group.label}</span>
          <ul className="hud-skills__chips">
            {group.items.map((item) => (
              <li className="hud-skills__chip" key={item}>
                {item}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// Featured Projects (03) -----------------------------------------------------

export function FeaturedPanel() {
  return (
    <ul className="hud-projects">
      {projects.map((p) => (
        <li className="hud-projects__item" key={p.name}>
          <div className="hud-projects__head">
            <span className="hud-projects__name">{p.name}</span>
            <span className="hud-projects__period">{p.period}</span>
          </div>
          <ul className="hud-projects__stack">
            <li className="hud-projects__tag hud-projects__tag--context">
              {p.context}
            </li>
            {p.stack.map((tech) => (
              <li className="hud-projects__tag" key={tech}>
                {tech}
              </li>
            ))}
          </ul>
          <p className="hud-projects__summary">{p.summary}</p>
        </li>
      ))}
    </ul>
  );
}

// Experience (04) ------------------------------------------------------------

const BRIEFCASE = (
  <>
    <rect x="3" y="6.5" width="14" height="10" rx="1.5" />
    <path d="M7 6.5V5a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 13 5v1.5M3 10.5h14" />
  </>
);

export function ExperiencePanel() {
  return (
    <ol className="hud-exp">
      {experience.map((e) => (
        <li className="hud-exp__row" key={e.company}>
          <span className="hud-exp__marker">
            <HudIcon>{BRIEFCASE}</HudIcon>
          </span>
          <div className="hud-exp__entry">
            <div className="hud-exp__head">
              <span className="hud-exp__role">{e.role}</span>
              <span className="hud-exp__date">{e.period}</span>
            </div>
            <span className="hud-exp__org">
              {e.company} · {e.location}
            </span>
            <p className="hud-exp__highlight">{e.highlight}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

// Contact (05) ---------------------------------------------------------------

const CONTACT_ICONS: Record<ContactKind, ReactNode> = {
  email: (
    <>
      <rect x="2.5" y="4.5" width="15" height="11" rx="1.5" />
      <path d="M3 5.5l7 5 7-5" />
    </>
  ),
  phone: (
    <path d="M5 3.5h2.5l1.2 3-1.6 1.2a9 9 0 0 0 4 4l1.2-1.6 3 1.2V15a1.5 1.5 0 0 1-1.6 1.5C9 16.2 3.8 11 3.5 5.1A1.5 1.5 0 0 1 5 3.5z" />
  ),
  linkedin: (
    <>
      <rect x="3" y="3" width="14" height="14" rx="2" />
      <path d="M6.5 8.5V14M6.5 5.6v.01M9.5 14V8.5M9.5 11c0-1.4.9-2.5 2.3-2.5S14 9.4 14 11v3" />
    </>
  ),
  github: (
    <path d="M10 2.5a7.5 7.5 0 0 0-2.4 14.6c.4.1.5-.2.5-.4v-1.3c-2 .4-2.5-.5-2.7-1-.1-.3-.6-1-1-1.2-.3-.2-.8-.6 0-.6.7 0 1.2.7 1.4 1 .8 1.3 2 1 2.5.7.1-.6.3-1 .6-1.2-1.8-.2-3.6-.9-3.6-3.9 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.4 7.4 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.5 1.1.2 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3-1.8 3.7-3.6 3.9.3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A7.5 7.5 0 0 0 10 2.5z" />
  ),
};

export function ContactPanel() {
  return (
    <ul className="hud-contact">
      {contact.map((c) => (
        <li className="hud-contact__row" key={c.kind}>
          <span className="hud-contact__icon">
            <HudIcon>{CONTACT_ICONS[c.kind]}</HudIcon>
          </span>
          <span className="hud-contact__value">{c.value}</span>
        </li>
      ))}
    </ul>
  );
}

// Shared line-icon wrapper — stroked in the inherited cyan via currentColor,
// matching the HUD's thin-stroke look under the CSS3D bend.
function HudIcon({ children }: { children: ReactNode }) {
  return (
    <svg
      className="hud-icon"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      shapeRendering="geometricPrecision"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}
