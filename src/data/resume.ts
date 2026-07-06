// Single source of truth for the desk HUD panels. Extracted verbatim from
// resume/03-17-2026-Daniel-Ku-Resume.pdf so the 3D panels and the document
// never drift. Presentation lives in deskPanelContent.tsx; only data here.

export interface ProfileStat {
  value: string;
  label: string;
}

export interface EducationEntry {
  degree: string;
  school: string;
  period: string;
}

export interface SkillGroup {
  label: string;
  items: string[];
}

export interface Project {
  name: string;
  context: string;
  stack: string[];
  period: string;
  /** One-line pitch shown under the title. */
  tagline: string;
  /** Longer paragraph with the technical detail. */
  summary: string;
  /** Repository link for the "View on GitHub" action. */
  href: string;
}

export interface ExperienceEntry {
  company: string;
  role: string;
  location: string;
  period: string;
  highlight: string;
}

export type ContactKind = "github" | "linkedin" | "x";

export interface ContactLink {
  kind: ContactKind;
  label: string;
  href: string;
}

export const profile = {
  initials: "DK",
  name: "Daniel Ku",
  role: "Full-stack Developer",
  education: [
    {
      degree: "MCS Computer Science",
      school: "University of Illinois Urbana-Champaign",
      period: "Jan 2025 – Present",
    },
    {
      degree: "B.S. Computer Science, Honors",
      school: "University of Illinois Urbana-Champaign",
      period: "Aug 2021 – Dec 2024",
    },
  ] satisfies EducationEntry[],
  stats: [
    { value: "3.81", label: "GPA / 4.0" },
    { value: "3", label: "Internships" },
    { value: "2", label: "Projects" },
  ] satisfies ProfileStat[],
};

export const skillGroups: SkillGroup[] = [
  {
    label: "Languages",
    items: ["Python", "TypeScript", "Java", "C++", "Rust"],
  },
  {
    label: "DevOps & Cloud",
    items: ["Cursor MCP", "Docker", "AWS", "Railway"],
  },
  { label: "Frameworks", items: ["TensorFlow.js", "WebSockets"] },
  { label: "Databases", items: ["PostgreSQL", "MongoDB"] },
];

export const projects: Project[] = [
  {
    name: "Multiplayer Mahjong",
    context: "Personal",
    stack: ["Node.js", "TypeScript", "WebSockets"],
    period: "2025 – Present",
    tagline:
      "Real-time multiplayer Mahjong with authoritative server, matchmaking, and tick-based state sync.",
    summary:
      "Four-player Taiwanese mahjong over WebSockets: authoritative server, lobby matchmaking, and tick-based state sync, with explicit handling of concurrent turns, reconnects, and client/server race conditions.",
    href: "https://github.com/dk9966",
  },
  {
    name: "Self-Hosted LLM Chatbot",
    context: "Personal",
    stack: ["C++", "CUDA", "TypeScript", "Llama"],
    period: "2025 – Present",
    tagline:
      "Self-hosted LLM inference in C++/CUDA, serving this site's chatbot without a third-party API.",
    summary:
      "Open-source inference for this site's chatbot via tiny-vllm—a C++/CUDA engine with PagedAttention, continuous batching, and KV cache—serving Llama 3.2 1B locally instead of a third-party API.",
    href: "https://github.com/dk9966",
  },
];

export const experience: ExperienceEntry[] = [
  {
    company: "Aeyesafe",
    role: "Full-Stack Intern",
    location: "Remote, USA",
    period: "Oct 2025 – Jan 2026",
    highlight:
      "Built a fault-tolerant ingestion pipeline for HC2 health sensors with webhook processing and real-time alerting.",
  },
  {
    company: "Luca Park Share",
    role: "Software Developer",
    location: "Taipei, Taiwan",
    period: "May – Oct 2025",
    highlight:
      "Designed the reservation and payment schema with atomic transactions for conflict-free booking, plus an admin dashboard.",
  },
  {
    company: "Steel Perlot",
    role: "Research Intern",
    location: "NYC, New York",
    period: "May – Aug 2022",
    highlight:
      "Ran a $1.5M Web3 startup incubation program and led technical due diligence on potential investments.",
  },
];

export const contact: ContactLink[] = [
  {
    kind: "github",
    label: "GitHub",
    href: "https://github.com/dk9966",
  },
  {
    kind: "linkedin",
    label: "LinkedIn",
    href: "https://linkedin.com/in/danielku96",
  },
  {
    kind: "x",
    label: "X",
    href: "https://x.com/DanielKu123",
  },
];
