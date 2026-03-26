export interface TerminalLine {
  text: string;
  prompt?: boolean;
  speed?: number;
  delay?: number;
}

export const TERMINAL_LINES: TerminalLine[] = [
  { text: 'init', prompt: true, delay: 800, speed: 80 },
  { text: 'loading environment...', delay: 400, speed: 25 },
  { text: 'done.', delay: 600, speed: 30 },
  { text: '', delay: 300 },
  { text: 'whoami', prompt: true, delay: 500, speed: 80 },
  { text: 'daniel ku', delay: 200, speed: 30 },
  { text: 'software engineer', delay: 100, speed: 30 },
  { text: '', delay: 400 },
  { text: 'start', prompt: true, delay: 600, speed: 80 },
];
