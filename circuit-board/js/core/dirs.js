// The 8-direction wheel shared by routing and pin geometry. Order matters:
// adjacent indices are 45 degrees apart, so heading deltas measure turn size.

export const DIRS = [
    [-1, -1], [0, -1], [1, -1], [1, 0],
    [1, 1], [0, 1], [-1, 1], [-1, 0],
];

export const UP = 1;
export const RIGHT = 3;
export const DOWN = 5;
export const LEFT = 7;

export function opposite(dir) {
    return (dir + 4) % 8;
}

export function directionBetween(a, b) {
    const dx = Math.sign(b.x - a.x);
    const dy = Math.sign(b.y - a.y);
    for (let d = 0; d < 8; d++) {
        if (DIRS[d][0] === dx && DIRS[d][1] === dy) return d;
    }
    return RIGHT;
}

export function dirAngle(dir) {
    const [dx, dy] = DIRS[dir];
    return Math.atan2(dy, dx);
}
