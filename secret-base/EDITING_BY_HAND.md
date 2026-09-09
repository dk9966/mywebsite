# Editing the islands by hand, click by click

For the script-side reference see [BUILD_DECK.md](BUILD_DECK.md). This one is
about doing it in Blender's interface.

Written against **Blender 5.1.1**, the **Layout** workspace, `base.blend`.

---

## Read this first: your edits are temporary

`build_deck.py` **deletes and rebuilds** everything in the `deck_huge` and
`deck_workshop` collections every time it runs. If you move a panel by hand and
then re-run the script, your move is gone.

That is not a reason to avoid editing by hand — it is the fastest way to find
the number you want. The workflow is:

> **nudge it in the viewport → read the number off → type that number into the
> script → re-run.**

Part 6 below is the "read the number off" step. Part 7 covers making things that
survive a rebuild.

---

## Part 1 — Where you are when you open the file

Open `secret-base/base.blend`. The **Layout** tab is active at the very top of
the window. You are looking at four areas:

| Area | Where | What it is |
| --- | --- | --- |
| **3D Viewport** | the big middle | the scene |
| **Outliner** | top right, a tree of names | every object in the file |
| **Properties** | bottom right, a column of tab icons | settings for whatever is selected |
| **Timeline** | thin strip along the bottom | animation; ignore it |

In the Outliner you will see three top-level collections:

- **Collection** — the four rock pillars, the original Camera and Light
- **deck_huge** — the library island (65 objects)
- **deck_workshop** — the workstation island (77 objects)

Click the small **▶ triangle** to the left of `deck_workshop` to expand it.

---

## Part 2 — Looking at the thing you want to edit

The two islands are 8 metres apart: the **library is at x = 12**, the
**workstation at x = 20**.

1. Move your mouse **into the 3D viewport** (Blender acts on whichever area the
   cursor is over — this trips up everyone at first).
2. In the Outliner, **click the name** `deck_display_01_b`. It highlights, and
   an orange outline appears round it in the viewport.
3. Hover the viewport and press **Numpad .** (period) — "Frame Selected". The
   view flies to that object.
   *No numpad?* Use the **View** menu in the viewport header → **Frame
   Selected**. Or turn on Edit → Preferences → Input → **Emulate Numpad**.
4. Press **Numpad /** (slash) for **Local View** — everything else vanishes and
   you see only that object. Press **/** again to come back. With 77 objects
   packed onto one deck this is the single most useful key you have.

To see the emissive materials the way they actually look, click the **third of
the four sphere icons** at the top right of the viewport header (Material
Preview), or the **fourth** (Rendered). The default (Solid) shows flat grey.

**Orbiting**: middle-mouse drag. **Panning**: Shift + middle-mouse. **Zoom**:
scroll wheel.

---

## Part 3 — Moving something, precisely

With the object still selected:

1. Hover the viewport, press **N**. A sidebar opens on the right of the
   viewport. Make sure the **Item** tab (vertical text on its edge) is active.
2. You now see **Transform → Location X / Y / Z**.

For every deck object this reads `X 20.0, Y 0.0, Z 0.0` — the *pillar's*
centre, not the visible geometry. That is deliberate: the script builds each
mesh in place and parks the origin at the middle of the deck. The numbers in
this panel are still true world coordinates, so:

- **Click** a Location field, type a number, press **Enter** → the object jumps.
- **Drag** left/right across the field → it slides.
- Or in the viewport: **G** then move the mouse, **click** to confirm,
  **right-click** or **Esc** to cancel.
- **G** then **X** constrains to the X axis. **G, X, 0.25, Enter** moves it
  exactly 25 cm along +X.

Because the origin sits at the deck centre, X/Y/Z are world axes — there is no
"move it outward from the middle" button. For radial moves it is genuinely
easier to change the angle/radius numbers in the script.

**Z is always true vertical**, for every object in this scene. `G, Z, 0.1,
Enter` raises anything by exactly 10 cm.

---

## Part 4 — Resizing, and the trap

**Do not press S in Object Mode.** Scale happens around the object's origin,
and the origin is at the middle of the deck — so scaling a display panel will
also shove it toward or away from the centre by a couple of metres.

Do this instead:

1. Select the object.
2. Hover the viewport, press **Tab** → you are now in **Edit Mode**. The header
   top-left changes from "Object Mode" to "Edit Mode" and the mesh turns into
   dots and lines.
3. Press **A** to select all of it.
4. Press **S**, type `1.2`, press **Enter**. It scales around its own middle,
   in place.
5. Press **Tab** to go back to Object Mode.

Useful variants while in Edit Mode with everything selected:

| Keys | Effect |
| --- | --- |
| `S 1.2 Enter` | 20% bigger in every direction |
| `S Z 1.4 Enter` | 40% taller, same footprint |
| `S Shift+Z 1.3 Enter` | 30% wider and deeper, same height |
| `S 0.8 Enter` | 20% smaller |

`Shift+Z` means "the two axes that aren't Z". Every box in this scene is
rotated only around Z, so height is always clean to isolate; width and depth
are not, because the panel is turned to face the deck centre.

**The Dimensions field lies to you.** For `deck_display_01_b` it reads
`1.0845 × 0.7369 × 0.82` even though the panel is 1.30 m wide. That is the
world-axis-aligned bounding box of a rotated rectangle. Only the Z figure
(0.82) is the real measurement.

---

## Part 5 — Changing the shape itself

Still in Edit Mode, with the three buttons at the top left of the header
(next to the Edit Mode dropdown) switching between **vertex / edge / face**
select — or press **1**, **2**, **3**.

To make the desk deeper by dragging its front edge:

1. Select `deck_ws_graphite_b` in the Outliner, press **Numpad /** to isolate.
2. **Tab** into Edit Mode. **Alt+A** to deselect everything.
3. Press **3** for face select.
4. **Click** the face you want. **Shift+click** to add more.
5. **G**, move, **click** to place. Or **G, Z, -0.05, Enter** to drop it 5 cm.
6. **Tab** out, **Numpad /** to leave isolation.

`deck_ws_graphite_b` holds *all* the workstation's grey geometry in one mesh —
desk, gantry, machinery, bezels. That is why isolating first matters.

Other keys worth knowing in Edit Mode: **E** extrudes a face outward,
**Ctrl+R** adds a loop cut, **I** insets a face, **Ctrl+Z** undoes.

---

## Part 6 — Getting your change back into the script

This is the step that makes hand-editing worth doing. Blender tells you where
something ended up; you convert that to the angle/radius/height the script
speaks.

1. Select the object (or in Edit Mode, select the faces you moved).
2. Press **Shift+S** → a pie menu appears → choose **Cursor to Selected**. The
   3D cursor (the red-white striped ring) jumps to the middle of your selection.
3. Switch to the **Scripting** tab at the top of the window.
4. In the console at the bottom left, paste this and press Enter:

```python
import bpy, math
c = bpy.context.scene.cursor.location
CX, CY, F, R = 20.0, 0.0, 6.855178, 2.78     # workstation island
dx, dy = c.x - CX, c.y - CY
print("angle  D(%.1f)" % math.degrees(math.atan2(dy, dx)))
print("radius R - %.3f" % (R - math.hypot(dx, dy)))
print("height %.3f" % (c.z - F))
```

For the **library island** change the first numbers to `12.0, 0.0`.

It prints three lines, for example:

```
angle  D(56.0)
radius R - 0.420
height 1.180
```

Those drop straight into the script: `polar(D(56.0), R - 0.420, 1.180)`.

Go back to the **Layout** tab, and the change is now permanent — because it
lives in `build_deck.py`, not in the .blend.

---

## Part 7 — Adding something that survives a rebuild

The script only clears `deck_huge` and `deck_workshop`. Anything anywhere else
is left alone.

1. In the Outliner, **right-click** on the word `Scene Collection` at the very
   top → **New Collection**. A collection called `Collection.001` appears.
2. **Double-click** its name and rename it to something like `my_stuff`.
3. **Left-click** it once so it is the *active* collection — new objects go into
   whichever collection is highlighted.
4. Hover the viewport. **Add** menu in the header → **Mesh** → **Cube**.
5. Press **N**, set Location to roughly `X 20, Y 0, Z 7.5` to drop it onto the
   workstation deck.
6. Re-run the script. Your cube is still there.

This is the right home for one-off props you are sketching. Once you like one,
port it into the script as a builder function (there is a worked example at the
end of BUILD_DECK.md) and delete the hand-made one.

---

## Part 8 — Changing a colour or a glow

1. Select any object using the material, e.g. `deck_display_01_b`.
2. In **Properties** (bottom right), click the **material tab** — the small
   checkered-sphere icon, near the bottom of the vertical icon strip.
3. You see the material name, e.g. `displayPanel`, and below it **Surface** with
   the Principled BSDF settings.
4. Scroll to **Emission**. **Click the colour swatch** to change the hue;
   change **Strength** to change how hard it glows.
5. Switch the viewport to **Rendered** shading to judge it.

Materials are shared: every panel uses the same `displayPanel`, so changing it
changes all ten at once.

**This one is also wiped on rebuild** — the script rewrites every material in
its `MATS` table. Once you find a value you like, copy it into the table at the
top of `build_deck.py` (line 31 onward).

Remember the view transform is AgX: **very bright emitters wash out toward
white.** If a colour looks grey, lower the Strength rather than raising it.

---

## Part 9 — Running the script

1. Click the **Scripting** tab at the top of the window.
2. In the text editor in the middle, **Open** → navigate to
   `secret-base/build_deck.py` → **Open Text**.
3. Press the **▶ play button** in the text editor's header (or hover the text
   and press **Alt+P**).
4. Click back to **Layout** to see the result.

Errors appear in a red banner and in the system console. After the first open,
edits you make in an external editor need **Text → Reload** (or the little
refresh icon) before the ▶ button will run the new version.

To save the file: **Ctrl+S**. Blender keeps the previous version as
`base.blend1` automatically.

---

## Quick key reference

| Key | Does |
| --- | --- |
| `N` | transform sidebar |
| `T` | tool sidebar (left) |
| `Tab` | Object Mode ⇄ Edit Mode |
| `Numpad .` | frame the selection |
| `Numpad /` | isolate the selection |
| `Numpad 0` | look through the active camera |
| `Numpad 7 / 1 / 3` | top / front / side view |
| `G` `R` `S` | grab, rotate, scale |
| `X` `Y` `Z` | after G/R/S, lock to that axis |
| `Shift+Z` | after G/R/S, lock to the *other two* axes |
| `A` / `Alt+A` | select all / deselect all |
| `H` / `Alt+H` | hide / unhide |
| `Shift+S` | snap pie menu |
| `Ctrl+Z` | undo |
