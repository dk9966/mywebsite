import type { BootPanelId } from "../lib/bootParts";
import { useBootTuning } from "../stores/bootTuning";
import BootClockDriver from "./BootClockDriver";
import RezTitle from "./RezTitle";
import TitleFlickerControls from "./TitleFlickerControls";
import "./HudScreen.css";
import "./TitlePreview.css";

const TITLES: { id: BootPanelId; title: string; seed: number }[] = [
  { id: "profile", title: "Profile", seed: 1 },
  { id: "skills", title: "Skills", seed: 2 },
  { id: "featured", title: "Projects", seed: 3 },
  { id: "education", title: "Education", seed: 4 },
  { id: "experience", title: "Experiences", seed: 5 },
  { id: "contact", title: "Contact", seed: 6 },
];

/** A plain stage for inspecting title motion without the desk scene. */
export default function TitlePreview() {
  const panelStartMs = useBootTuning((s) => s.panelStartMs);

  return (
    <main className="title-preview">
      <TitleFlickerControls />
      <section className="title-preview__titles" aria-label="Animated titles">
        {TITLES.map(({ id, title, seed }) => (
          <h2 className="title-preview__item" key={id}>
            <RezTitle
              title={title}
              boot={{ startMs: panelStartMs[id], pulseDelayMs: 0, seed }}
              headerFontPx={38}
              padX={0}
              padY={0}
              center={false}
            />
          </h2>
        ))}
      </section>
      <BootClockDriver />
    </main>
  );
}
