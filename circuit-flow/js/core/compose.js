// Chip placement, following the reference composition: evenly spaced
// x-stations hugging a horizontal spine. A station holds either a single
// chip nudged above/below the spine, or a stacked pair straddling it with a
// clear gap for the spine traces to flow through.

function sampleChipSize(rng, config) {
    const { chips } = config;
    if (rng.chance(chips.pinkShare)) {
        return {
            color: 'pink',
            w: rng.range(...chips.pinkRect.w),
            h: rng.range(...chips.pinkRect.h),
        };
    }
    const s = rng.range(...chips.greenSquare.size);
    return { color: 'green', w: s, h: s * rng.range(0.85, 1.1) };
}

function pinRow(y, h, config) {
    const { pinInset } = config.chips;
    const pitch = config.lanes.pitch;
    const count = Math.max(2, Math.floor((h - 2 * pinInset) / pitch) + 1);
    const start = y + h / 2 - ((count - 1) * pitch) / 2;
    return Array.from({ length: count }, (_, i) => start + i * pitch);
}

// Snap to the global pin grid: with every pin on a multiple of the pitch,
// any pin-to-pin dy is joggable (0 or >= pitch) -- arbitrary sub-jog
// misalignments would make chip-to-chip routes impossible.
function snapToPinGrid(y, h, config) {
    const pitch = config.lanes.pitch;
    const firstPin = pinRow(y, h, config)[0];
    return y + Math.round(firstPin / pitch) * pitch - firstPin;
}

function makeChip(rng, state, size, cx, y) {
    const { config } = state;
    const snapped = snapToPinGrid(y, size.h, config);
    return {
        x: cx - size.w / 2,
        y: snapped,
        w: size.w,
        h: size.h,
        color: size.color,
        station: state.station,
        pins: {
            left: pinRow(snapped, size.h, config),
            right: pinRow(snapped, size.h, config),
        },
    };
}

export function composeChips(rng, config) {
    const { board, chips: cc } = config;
    const spineY = board.height / 2;
    const stationCount = rng.int(...cc.stations);

    const outerPad = rng.range(...cc.outerPad);
    const span = (board.width - 2 * outerPad) / (stationCount - 1);

    const out = [];
    let lastSide = rng.sign(); // singles alternate sides of the spine
    for (let s = 0; s < stationCount; s++) {
        // Mild jitter only: the best boards keep their stations evenly
        // spread, so spine links stay short and fans get equal room.
        const cx = outerPad + s * span + rng.range(-0.04, 0.04) * span;
        const state = { config, station: s };

        // Stacked pairs at the ends would wall off the edge fans, so only
        // interior stations straddle the spine.
        const interior = s > 0 && s < stationCount - 1;
        if (interior && rng.chance(cc.stackChance)) {
            const gap = rng.range(...cc.stackGap);
            const top = sampleChipSize(rng, config);
            const bottom = sampleChipSize(rng, config);
            out.push(makeChip(rng, state, top, cx, spineY - gap / 2 - top.h));
            out.push(makeChip(rng, state, bottom, cx, spineY + gap / 2));
        } else {
            const size = sampleChipSize(rng, config);
            lastSide = -lastSide;
            const off = lastSide * rng.range(...cc.singleOffset);
            out.push(makeChip(rng, state, size, cx, spineY + off - size.h / 2));
        }
    }

    // The reference always shows at least one pink rect; force one if the
    // sampler never rolled it.
    if (!out.some((c) => c.color === 'pink')) {
        const c = out[rng.int(1, out.length - 2)];
        c.color = 'pink';
    }
    return out;
}
