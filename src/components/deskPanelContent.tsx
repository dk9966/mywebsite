import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  contact,
  experience,
  profile,
  projects,
  skillGroups,
  type ContactKind,
} from "../data/resume";
import { useDeskLayout } from "../stores/deskLayout";
import "./deskPanelContent.css";

// Real resume content for the curved HUD panels, sourced from
// src/data/resume.ts. Each panel keeps the cyan glass aesthetic: line-art
// icons stroked in currentColor, thin rules, and a small type hierarchy.

// Profile (01) ---------------------------------------------------------------

export function ProfilePanel() {
  return (
    <div className="hud-profile">
      <div className="hud-profile__avatar-wrap">
        <div className="hud-profile__avatar">{profile.initials}</div>
      </div>
      <div className="hud-profile__text">
        <div className="hud-profile__name">{profile.name}</div>
        <div className="hud-profile__role">{profile.role}</div>
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

const CHEVRON_LEFT = <path d="M12.5 5 7.5 10l5 5" />;
const CHEVRON_RIGHT = <path d="M7.5 5 12.5 10l-5 5" />;
const ARROW_RIGHT = <path d="M3.5 10h13M11 4.5l5.5 5.5-5.5 5.5" />;
const GITHUB = (
  <path d="M10 2.5a7.5 7.5 0 0 0-2.4 14.6c.4.1.5-.2.5-.4v-1.3c-2 .4-2.5-.5-2.7-1-.1-.3-.6-1-1-1.2-.3-.2-.8-.6 0-.6.7 0 1.2.7 1.4 1 .8 1.3 2 1 2.5.7.1-.6.3-1 .6-1.2-1.8-.2-3.6-.9-3.6-3.9 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.4 7.4 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.5 1.1.2 1.9.1 2.1.5.5.8 1.2.8 2.1 0 3-1.8 3.7-3.6 3.9.3.3.6.8.6 1.6v2.3c0 .2.1.5.5.4A7.5 7.5 0 0 0 10 2.5z" />
);

// Bent panels mount one FeaturedPanel per vertical slice; keep carousel index
// in sync so every strip shows the same project after prev/next.
let sharedProjectIndex = 0;
const projectIndexListeners = new Set<(index: number) => void>();

function setSharedProjectIndex(next: number) {
  sharedProjectIndex = next;
  projectIndexListeners.forEach((fn) => fn(next));
}

function useSyncedProjectIndex(count: number) {
  const [index, setIndex] = useState(sharedProjectIndex);

  useEffect(() => {
    projectIndexListeners.add(setIndex);
    return () => {
      projectIndexListeners.delete(setIndex);
    };
  }, []);

  const goPrev = () =>
    setSharedProjectIndex((sharedProjectIndex - 1 + count) % count);
  const goNext = () => setSharedProjectIndex((sharedProjectIndex + 1) % count);
  const goTo = (next: number) =>
    setSharedProjectIndex(((next % count) + count) % count);

  return { index, goPrev, goNext, goTo };
}

// Carousel controls live in the panel header (upper right). Prev/next chevrons
// flank a dot per project; the shared index keeps them in step with the card.
export function ProjectsNav() {
  const count = projects.length;
  const { index, goPrev, goNext, goTo } = useSyncedProjectIndex(count);

  if (count <= 1) return null;

  const stopNavPointer = (e: ReactPointerEvent<HTMLButtonElement>) => {
    e.stopPropagation();
  };

  return (
    <div className="hud-projects-nav">
      <button
        type="button"
        className="hud-projects-nav__arrow"
        onClick={goPrev}
        onPointerDown={stopNavPointer}
        aria-label="Previous project"
      >
        <HudIcon>{CHEVRON_LEFT}</HudIcon>
      </button>
      <ul className="hud-projects-nav__dots">
        {projects.map((project, i) => (
          <li key={project.name}>
            <button
              type="button"
              className={
                i === index
                  ? "hud-projects-nav__dot hud-projects-nav__dot--active"
                  : "hud-projects-nav__dot"
              }
              onClick={() => goTo(i)}
              onPointerDown={stopNavPointer}
              aria-label={`Show ${project.name}`}
              aria-current={i === index}
            />
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="hud-projects-nav__arrow"
        onClick={goNext}
        onPointerDown={stopNavPointer}
        aria-label="Next project"
      >
        <HudIcon>{CHEVRON_RIGHT}</HudIcon>
      </button>
    </div>
  );
}

export function FeaturedPanel() {
  const count = projects.length;
  const { index } = useSyncedProjectIndex(count);
  const project = projects[index];

  if (!project) return null;

  const openRepo = (e: ReactPointerEvent<HTMLButtonElement> | MouseEvent) => {
    e.stopPropagation();
    if (project.href) {
      window.open(project.href, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="hud-projects">
      <article className="hud-projects__card" key={project.name}>
        <div className="hud-projects__media" aria-hidden="true">
          <div className="hud-projects__media-placeholder">
            <span className="hud-projects__media-label">Preview</span>
          </div>
        </div>

        <span className="hud-projects__name">{project.name}</span>

        <p className="hud-projects__tagline">{project.tagline}</p>

        <div className="hud-projects__stack">
          <span className="hud-projects__stack-label">Tech Stack</span>
          <ul className="hud-projects__tags">
            {project.stack.map((tech) => (
              <li className="hud-projects__tag" key={tech}>
                {tech}
              </li>
            ))}
          </ul>
        </div>

        <p className="hud-projects__summary">{project.summary}</p>

        {project.href ? (
          <button
            type="button"
            className="hud-projects__link"
            onClick={openRepo}
            onPointerDown={(e) => e.stopPropagation()}
          >
            <span className="hud-projects__link-label">
              <HudIcon>{GITHUB}</HudIcon>
              View on GitHub
            </span>
            <HudIcon>{ARROW_RIGHT}</HudIcon>
          </button>
        ) : null}
      </article>
    </div>
  );
}

// Education (04) -------------------------------------------------------------

const GRAD_CAP = (
  <>
    <path d="M3.5 8.5 10 5l6.5 3.5" />
    <path d="M6 10v3.5c0 .8 1.8 1.5 4 1.5s4-.7 4-1.5V10" />
    <path d="M16.5 8.5V12" />
  </>
);

export function EducationPanel() {
  const scrollRef = useSyncedPanelScroll("education");
  const eduBaseFontPx = useDeskLayout((s) => s.eduBaseFontPx);
  const eduDegreeEm = useDeskLayout((s) => s.eduDegreeEm);
  const eduDateEm = useDeskLayout((s) => s.eduDateEm);
  const eduSchoolEm = useDeskLayout((s) => s.eduSchoolEm);

  const typeStyle = {
    "--edu-base-font": `${eduBaseFontPx}px`,
    "--edu-degree-em": eduDegreeEm,
    "--edu-date-em": eduDateEm,
    "--edu-school-em": eduSchoolEm,
  } as CSSProperties;

  return (
    <div
      ref={scrollRef}
      className="hud-edu-wrap"
      data-hud-scroll-group="education"
      style={typeStyle}
    >
      <div className="hud-edu">
        <div className="hud-edu__timeline">
          <div className="hud-edu__rail" aria-hidden="true">
            <span className="hud-edu__marker">
              <HudIcon>{GRAD_CAP}</HudIcon>
            </span>
            <span className="hud-edu__rail-line" />
          </div>
          <div className="hud-edu__body">
            {profile.education[0] ? (
              <p className="hud-edu__school">{profile.education[0].school}</p>
            ) : null}
            <div className="hud-edu__degrees">
              {profile.education.map((entry) => (
                <div className="hud-edu__item" key={entry.degree}>
                  <span className="hud-edu__degree">{entry.degree}</span>
                  <span className="hud-edu__date">{entry.period}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Experience (05) ------------------------------------------------------------

const BRIEFCASE = (
  <>
    <rect x="3" y="6.5" width="14" height="10" rx="1.5" />
    <path d="M7 6.5V5a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 13 5v1.5M3 10.5h14" />
  </>
);

export function ExperiencePanel() {
  const scrollRef = useSyncedPanelScroll("experience");
  const expBaseFontPx = useDeskLayout((s) => s.expBaseFontPx);
  const expRoleEm = useDeskLayout((s) => s.expRoleEm);
  const expDateEm = useDeskLayout((s) => s.expDateEm);
  const expOrgEm = useDeskLayout((s) => s.expOrgEm);

  const typeStyle = {
    "--exp-base-font": `${expBaseFontPx}px`,
    "--exp-role-em": expRoleEm,
    "--exp-date-em": expDateEm,
    "--exp-org-em": expOrgEm,
  } as CSSProperties;

  return (
    <div
      ref={scrollRef}
      className="hud-exp-wrap"
      data-hud-scroll-group="experience"
      style={typeStyle}
    >
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
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

// Contact (06) ---------------------------------------------------------------

const CONTACT_ICONS: Record<ContactKind, ReactNode> = {
  linkedin: (
    <>
      <rect x="3" y="3" width="14" height="14" rx="2" />
      <path d="M6.5 8.5V14M6.5 5.6v.01M9.5 14V8.5M9.5 11c0-1.4.9-2.5 2.3-2.5S14 9.4 14 11v3" />
    </>
  ),
  github: GITHUB,
  x: (
    <path d="M5.8 4h2.1l2.9 4.1L14.2 4h2l-3.9 5.3L16.8 16h-2.1l-3.2-4.5L7.5 16H5.4l4.1-5.5L5.8 4z" />
  ),
};

export function ContactHeaderIcons() {
  const headerFontPx = useDeskLayout((s) => s.headerFontPx);
  const contactIconSizePx = useDeskLayout((s) => s.contactIconSizePx);

  const iconPx = Math.min(contactIconSizePx, Math.round(headerFontPx * 1.15));

  const iconStyle = {
    "--contact-icon-size": `${iconPx}px`,
  } as CSSProperties;

  return (
    <ul className="hud-contact" style={iconStyle} aria-hidden="true">
      {contact.map((c) => (
        <li className="hud-contact__item" key={c.kind}>
          <span className="hud-contact__icon" title={c.label}>
            <HudIcon>{CONTACT_ICONS[c.kind]}</HudIcon>
          </span>
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

// Bent panels duplicate DOM per vertical slice; keep scrollTop in sync so the
// full panel moves together instead of one strip scrolling on its own.
function useSyncedPanelScroll(group: string) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const syncing = useRef(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const onScroll = () => {
      if (syncing.current) return;
      syncing.current = true;
      const top = el.scrollTop;
      document
        .querySelectorAll<HTMLElement>(`[data-hud-scroll-group="${group}"]`)
        .forEach((node) => {
          if (node !== el && node.scrollTop !== top) node.scrollTop = top;
        });
      syncing.current = false;
    };

    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [group]);

  return wrapRef;
}
