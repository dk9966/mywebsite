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
  summary: string;
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
    { value: "3", label: "Projects" },
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
    name: "Rotarygolf.info",
    context: "Personal",
    stack: ["React", "TypeScript", "PostgreSQL"],
    period: "Sep 2025 – Present",
    summary:
      "Full-stack golf tournament platform for a 50-member club (scaling to ~100 in Taipei): OCR score capture, role-based auth, real-time leaderboards, and automated award calculations.",
  },
  {
    name: "IoT Bicycle Hazard Detection",
    context: "CS 437",
    stack: ["C++", "Python", "Raspberry Pi"],
    period: "Jan – May 2024",
    summary:
      "Low-latency hazard detection on Raspberry Pi + Coral TPU with a BLE smart taillight on ESP32-S3 driving a real-time 8×8 LED alert array via multiprocessing queues.",
  },
  {
    name: "Numerical Methods for Shallow-Water PDEs",
    context: "CS 555",
    stack: ["Python"],
    period: "Jan – May 2025",
    summary:
      "Finite-volume solvers for shallow-water PDEs; optimized timestep selection and memory layout for numerically stable simulations, with visualizations comparing triangular vs. uniform grids.",
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
