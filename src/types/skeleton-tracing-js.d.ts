declare module "skeleton-tracing-js" {
  interface TraceResult {
    polylines: number[][][];
    rects: number[][];
    width: number;
    height: number;
  }

  interface TraceSkeleton {
    fromImageData(im: ImageData): TraceResult;
    fromCanvas(canvas: HTMLCanvasElement | OffscreenCanvas): TraceResult;
    fromBoolArray(im: ArrayLike<unknown>, w: number, h: number): TraceResult;
    fromCharString(im: string, w: number, h: number): TraceResult;
  }

  const TraceSkeleton: TraceSkeleton;
  export default TraceSkeleton;
}
