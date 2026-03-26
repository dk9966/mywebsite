import { useTypewriter } from '../../hooks/useTypewriter';
import { TERMINAL_LINES } from '../../data/terminal';
import './Terminal.css';

export function Terminal() {
  const { display, typing, done } = useTypewriter(TERMINAL_LINES);

  return (
    <div className="terminal">
      <div className="terminal__screen">
        {display.length === 0 && (
          <div className="terminal__line">
            <span className="terminal__prompt">&gt;&nbsp;</span>
            <span className="terminal__cursor terminal__cursor--blink" />
          </div>
        )}

        {display.map((line, i) => (
          <div key={i} className="terminal__line">
            {line.prompt && (
              <span className="terminal__prompt">&gt;&nbsp;</span>
            )}
            <span className="terminal__text">{line.text}</span>
            {i === display.length - 1 && !done && (
              <span
                className={`terminal__cursor${typing ? '' : ' terminal__cursor--blink'}`}
              />
            )}
          </div>
        ))}

        {done && (
          <div className="terminal__line">
            <span className="terminal__prompt">&gt;&nbsp;</span>
            <span className="terminal__cursor terminal__cursor--blink" />
          </div>
        )}
      </div>
    </div>
  );
}
