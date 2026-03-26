import { useState, useEffect } from 'react';
import type { TerminalLine } from '../data/terminal';

interface DisplayLine {
  text: string;
  prompt: boolean;
  done: boolean;
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function useTypewriter(lines: TerminalLine[]) {
  const [sequence] = useState(() => lines);
  const [display, setDisplay] = useState<DisplayLine[]>([]);
  const [typing, setTyping] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let active = true;

    (async () => {
      const out: DisplayLine[] = [];

      for (const line of sequence) {
        if (!active) return;
        await sleep(line.delay ?? 200);
        if (!active) return;

        if (line.text.length === 0) {
          out.push({ text: '', prompt: !!line.prompt, done: true });
          setDisplay([...out]);
          continue;
        }

        out.push({ text: '', prompt: !!line.prompt, done: false });
        setTyping(true);
        setDisplay([...out]);

        for (let i = 1; i <= line.text.length; i++) {
          if (!active) return;
          out[out.length - 1] = {
            ...out[out.length - 1],
            text: line.text.slice(0, i),
          };
          setDisplay([...out]);
          await sleep(line.speed ?? 50);
        }

        out[out.length - 1] = { ...out[out.length - 1], done: true };
        setDisplay([...out]);
        setTyping(false);
      }

      if (active) setDone(true);
    })();

    return () => {
      active = false;
    };
  }, [sequence]);

  return { display, typing, done };
}
