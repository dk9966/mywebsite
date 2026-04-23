/**
 * Character sections used by centerline-debug and the home page charset showcase.
 */
export const SECTIONS: { label: string; chars: string[] }[] = [
  {
    label: "Uppercase",
    chars: "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split(""),
  },
  {
    label: "Lowercase",
    chars: "abcdefghijklmnopqrstuvwxyz".split(""),
  },
  {
    label: "Digits",
    chars: "0123456789".split(""),
  },
  {
    label: "Symbols",
    chars: [
      ".",
      ",",
      "!",
      "?",
      ":",
      ";",
      "-",
      "+",
      "=",
      "(",
      ")",
      "/",
      "@",
      "#",
      "$",
      "&",
      "*",
      "'",
      '"',
    ],
  },
];

/** Sample monospace-style lines shown below the charset rows on `/`. */
export const TERMINAL_SAMPLE_LINES = [
  "$ ls -la",
  "git status",
  "npm run build",
  "pnpm dev",
];
