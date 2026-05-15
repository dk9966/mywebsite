# Tron Base Mesh Plan

## Goal

Build a base mesh that feels like `PCB logic translated into sci-fi architecture`, so the Tron lines have a clean structure to trace instead of just decorating random geometry.

The mesh should work even with the glow turned off. If the plain mesh already looks like a designed system, the traced lines will look good.

## Feedback Update

The first pass proved the placement and general idea, but it was still too compact and too blocky.

The revised direction is:

- make the board much longer so the camera has a real travel path toward the table
- stretch the main boxes so they feel more like chips and routed housings than stubby blocks
- add many more traces so the surface reads like a real circuit field
- favor long straight runs with occasional slanted connectors instead of soft or random paths
- borrow more from the reference images: dense parallel lanes, pin-like fanouts, and a cleaner PCB rhythm

## Phase Status

Done so far:

- placed the base system in front of the curved table
- proved the overall scale and table-facing direction
- established a first pass for masses, pads, and route logic
- documented scene **front = +Y** (bulging arc of the desk) and left/right columns (−X / +X) in `.cursor/rules/blender-table-front.mdc`; added `blender/table/vehicle_bays.py` for a three-lane plaza (center clearing + side columns): Luke speeder + Tron bike (−X), Batmobile + Impala (+X); FBX paths live under `models/*/source/` after unzipping the shipped archives.

Next in the current pass:

- rebuild the board into a longer runway
- replace chunkier masses with more elongated modules
- increase the trace count and distribute it across more of the surface
- push the path language closer to PCB geometry

## Core Idea

Do not model a literal motherboard.

Instead, build a `floorplan-style structure` with:

- a dark base plane
- a few large rectangular masses
- a few smaller support modules
- narrow routing corridors or inset channels
- only selected seams and edges intended for tracing

The best visual direction is:

`chip floorplan` + `motherboard routing logic` + `sci-fi architectural massing`

## What Makes It Look Good

The important part is restraint.

- Use `3 to 5` major blocks, not dozens.
- Repeat a small number of widths and pad sizes.
- Use only `3 height levels` plus maybe one hero height.
- Leave negative space so the layout can breathe.
- Give the lines long straight runs before they turn.
- Let only some edges trace, not every edge in the scene.

If everything is detailed, nothing feels important.

## Recommended Mesh Structure

Think in three layers:

1. `Primary masses`
   Big rectangular modules that act like the main architectural blocks.

2. `Secondary connectors`
   Smaller pads, bridges, and step blocks that connect the main masses.

3. `Trace rails`
   Inset seams, selected top edges, or narrow path strips where the light runs.

## First-Pass Build Recipe

Start with:

1. One large base plate.
2. `4 or 5` main rectangular modules.
3. `6 to 10` smaller connectors or pads.
4. `3` major route corridors.
5. A few terminal nodes where the line can branch, pause, or climb.
6. Light bevels so the form catches highlights.

This is enough for a strong first pass.

## Good Taste Rules

- Favor clean orthogonal blocks over tiny greebles.
- Use repeated dimensions so the layout feels designed.
- Keep most turns at `90 degrees`.
- Make the routing feel intentional, not noisy.
- Let some paths stay flat and let a few climb vertically onto hero masses.
- Build for the camera angle, not just top view.

## Material and Lighting Direction

The base mesh should stay simple:

- dark graphite or black body
- subtle specular response
- minimal texture noise
- emissive lines added later with care

Too much bloom will erase the structure. The mesh needs to stay readable underneath the glow.

## Placement Direction For This Scene

For the curved table scene, the first pass should sit `in front of the table` on the open camera-facing side.

The blockout should feel like a routed system leading toward the table, not like a random prop dropped in front of it.

## First Blender Pass

The first blockout should include:

- one base floorplate in front of the table
- a dominant central route
- a few stepped rectangular modules
- a small number of pads and side branches
- enough depth variation to support line climbs later

The goal of this pass is not final detail. It is to establish:

- hierarchy
- spacing
- route logic
- silhouette
- camera readability
