declare module "opentype.js" {
  export interface PathCommand {
    type: "M" | "L" | "Q" | "C" | "Z";
    x?: number;
    y?: number;
    x1?: number;
    y1?: number;
    x2?: number;
    y2?: number;
  }

  export interface BoundingBox {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  }

  export interface Path {
    commands: PathCommand[];
    getBoundingBox(): BoundingBox;
    toPathData(decimalPlaces?: number): string;
  }

  export interface Glyph {
    advanceWidth: number;
    path: Path;
    getPath(x: number, y: number, fontSize: number): Path;
    getBoundingBox(): BoundingBox;
  }

  export interface FontNames {
    fontFamily?: { en?: string } & Record<string, string>;
    fullName?: { en?: string } & Record<string, string>;
  }

  export interface Font {
    unitsPerEm: number;
    ascender: number;
    descender: number;
    names?: FontNames;
    charToGlyph(char: string): Glyph;
  }

  export function load(
    url: string,
    callback: (err: Error | null, font?: Font) => void,
  ): void;
}
