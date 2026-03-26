import { create } from 'zustand';

export type Phase = 'terminal' | 'dissolve' | 'lines' | 'room' | 'cockpit';

interface PhaseState {
  phase: Phase;
  setPhase: (phase: Phase) => void;
}

export const usePhaseStore = create<PhaseState>((set) => ({
  phase: 'terminal',
  setPhase: (phase) => set({ phase }),
}));
