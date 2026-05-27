# Component catalog

Every component variation in `components/component_builders.py`. The
reference sheet GLB (`build_reference_sheet.py`) renders all of these as an
8×20 grid for visual inspection.

Each cell of the reference sheet has a `geom_name` of the form
`r{row}_{family}_c{col}_p{part}` so you can pick out a specific variation
in Blender/Three.js by name.

## Row 0 — QFP / chip ICs (footprint ~2.0 × 2.0)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | QFP, 10 pins/side, dot marker      | baseline 10-pin |
| 1  | QFP, 12 pins/side, line marker     | longer pin-1 line |
| 2  | QFP, 14 pins/side, square pad      | center pad marker |
| 3  | QFP, 11 pins/side, triple stripe   | three parallel lines |
| 4  | QFP, 13 pins/side, cross marker    | + shape on top |
| 5  | QFP, 12 pins/side, square + pin1 dot, gold pins | premium look |
| 6  | QFP, 14 pins/side, lighter body    | desaturated body |
| 7  | QFP, 15 pins/side, square pin1, corner chamfer | with chamfer notch |
| 8  | BGA (no pins), 12×12 ball grid     | flat top, solder balls below |
| 9  | Ceramic QFP, 13 pins/side, gold pins | tan ceramic body |
| 10 | QFP, 13 pins/side, exposed silver die | silver pad on top |
| 11 | QFP, 14 pins/side, dual marker (dot + line) | both markers |
| 12 | QFP, 15 pins/side, square + label band | side band marking |
| 13 | Ceramic QFP, 12 pins/side, chamfer, gold pins | ceramic + chamfer + gold |
| 14 | QFP with center dimple             | round indent in middle |
| 15 | QFP with diagonal text-like ridges | hint of part marking |
| 16 | QFP with two visible dies side-by-side | dual-die package |
| 17 | Ceramic cavity QFP with bond wires | premium "lid-off" look |
| 18 | QFP with stacked logo bars         | logo-like marking |
| 19 | QFP with crystal can on top        | combo package |

## Row 1 — DIP ICs (footprint ~1.5–1.8 × 0.5)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | DIP, 7 pins/side, dot notch        | baseline |
| 1  | DIP, 8 pins/side, half-circle notch | curved end indent |
| 2  | DIP, 9 pins/side, slot notch       | side slot |
| 3  | DIP, 8 pins/side, end bar          | bar across one end |
| 4  | DIP, 10 pins/side, gold pins       | premium variant |
| 5  | DIP, 9 pins/side, half-circle      | another notch style |
| 6  | DIP, 10 pins/side, slot notch      | larger DIP |
| 7  | DIP, 9 pins/side, no notch         | bare style |
| 8  | DIP in socket                      | sitting in raised socket |
| 9  | Ceramic DIP, gold pins             | premium ceramic |
| 10 | DIP with center groove             | line down the middle |
| 11 | Wide ceramic DIP                   | bigger footprint |
| 12 | Light body DIP, gold pins          | contrasty look |
| 13 | Ceramic, groove, gold pins         | maxed out premium |
| 14 | DIP with quartz window             | EPROM look |
| 15 | DIP in ZIF socket with lever       | extraction lever |
| 16 | DIP with notches on both ends      | industrial style |
| 17 | DIP with secondary SMD on top      | piggyback |
| 18 | DIP with date-code dots            | speckled markings |
| 19 | Extra-long ceramic DIP             | 12 pins/side |

## Row 2 — Capacitors (footprint ~0.6 × 0.6, cylindrical body)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | Electrolytic, flat top             | baseline cap |
| 1  | Electrolytic, ring top             | sunken-center top |
| 2  | Electrolytic, dome top             | bulged top |
| 3  | Electrolytic, plus-vent top        | cross-cut vent |
| 4  | Electrolytic with polarity stripe + ring top | |
| 5  | Red-top electrolytic with stripe   | different chemistry |
| 6  | Dome top with stripe               | polarized dome |
| 7  | Red-top, higher facet count        | smoother cylinder |
| 8  | Plus vent + horizontal label band  | |
| 9  | Blue-sleeved cap with red top      | colored sleeve |
| 10 | Tantalum SMD (rectangular)         | box-shaped, polarity bar |
| 11 | Film cap (rectangular tall)        | yellow film |
| 12 | Two stacked electrolytics          | paired caps |
| 13 | Green-sleeved cap with label band  | |
| 14 | Electrolytic with double polarity stripes | |
| 15 | Squat SMD aluminum cap             | low and wide |
| 16 | Cap with band AND dome top         | combined details |
| 17 | Translucent orange-top cap         | |
| 18 | Cap with screw-style top           | unusual style |
| 19 | Cap with top-side text bars        | parallel markings |

## Row 3 — Heatsinks (footprint ~1.9 × 1.4)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | 7 X-axis fins, flat base           | baseline |
| 1  | 9 X-axis fins, raised plinth base  | |
| 2  | 8 Z-axis fins (perpendicular)      | other orientation |
| 3  | 8 X-axis fins with mounting holes  | corner holes |
| 4  | 10 X-axis fins, beveled tops       | sharper fin tips |
| 5  | 7 X-axis pinned fins, raised       | tiny caps on each fin |
| 6  | 11 Z-axis fins with mounting holes | dense Z fins |
| 7  | 9 X-axis beveled, raised, dark     | premium look |
| 8  | Pin-fin grid (8×6 vertical pegs)   | not plate fins |
| 9  | Heatsink with copper thermal pad   | exposed slug underneath |
| 10 | Black anodized pin-fin (10×7)      | matte black |
| 11 | Black anodized with mount holes + pinned tops | |
| 12 | Dense Z-axis fins, raised base     | 12 fins |
| 13 | Chunky black anodized pin-fin (6×4) | bigger pegs |
| 14 | Crosshatch fins (X + Z combined)   | grid-of-pockets |
| 15 | Radial sun-burst (12 blades)       | round footprint |
| 16 | Heatsink with fan/spinner on top   | 4-blade fan |
| 17 | Low-profile (14 thin fins)         | flat |
| 18 | Diagonal fins (45° rotated)        | unusual orientation |
| 19 | Fins with through-holes            | industrial look |

## Row 4 — Octagonal / drum (footprint ~1.1 × 1.1)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | 6-sided hex prism                  | hexagonal |
| 1  | 8-sided octagonal                  | classic octagon |
| 2  | Octagonal with ring on top         | indicator ring |
| 3  | Octagonal with screw + slot top    | screw head detail |
| 4  | 10-sided with center pin           | pin sticking up |
| 5  | 12-sided with double ring top      | concentric rings |
| 6  | 12-sided with screw top            | more facets |
| 7  | 16-sided, lighter body, double ring | almost-circular |
| 8  | Octagonal with copper torus on top | donut top |
| 9  | Shielded can with metal strap + bolts | |
| 10 | Vented with vertical slot cutouts  | sides have slots |
| 11 | Copper-bodied octagonal with ring  | full copper |
| 12 | Larger shielded variant            | 12-sided shield |
| 13 | Ceramic body with center pin       | premium |
| 14 | Octagonal with hex-bolt metal cap  | hexagonal cap |
| 15 | Octagonal with horizontal label band | |
| 16 | Octagonal with 4 side-mount pins (relay style) | |
| 17 | Octagonal with strongly glowing top | indicator |
| 18 | Taller octagonal can               | extra height |
| 19 | Octagonal with diagonal strap      | offset bolt strap |

## Row 5 — Headers / terminals (footprint ~1.6 × 0.4-0.7)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | 10-pin single-row header           | basic |
| 1  | 12-pin double-row header           | 2 rows of pins |
| 2  | 10-pin shrouded with polarization key | box around pins |
| 3  | 10-pin right-angle header          | pins bend horizontally |
| 4  | 11-pin single-row                  | |
| 5  | 11-pin double-row shrouded         | |
| 6  | 10-pin double-row right-angle      | |
| 7  | 12-pin shrouded, tighter spacing   | |
| 8  | 4-position screw terminal (green)  | wire terminal |
| 9  | 8-pin IDC ribbon header            | shrouded with latch bumps |
| 10 | 4-pin JST-style with side latch    | white plastic |
| 11 | 5-position screw terminal          | wider |
| 12 | 10-pin IDC ribbon                  | |
| 13 | 6-pin JST                          | |
| 14 | Blue boxed pin header (10 pins)    | painted plastic |
| 15 | Blue 4-pos screw terminal          | |
| 16 | Black 5-pos screw terminal         | |
| 17 | Dual IDC port (8 pins each)        | two banks |
| 18 | Header with locking lever          | latch arm |
| 19 | Barrier strip terminal (5 screws)  | barrier walls between screws |

## Row 6 — Connectors / ports (footprint ~1.7 × 0.6-0.85)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | Plain connector, no slot           | baseline |
| 1  | Connector with single slot         | |
| 2  | Connector with double slots        | |
| 3  | Connector with 6 multi-slots       | |
| 4  | Connector with keyed slot          | polarization bump |
| 5  | Connector with latch tab           | |
| 6  | Multi-slot with latch              | |
| 7  | Keyed with latch, light body       | |
| 8  | USB-A-style port (metal shell)     | |
| 9  | 3.5mm audio jack (square + barrel) | side-emerging cylinder |
| 10 | RJ45 jack with green/amber LEDs    | Ethernet jack |
| 11 | Card-edge / PCI-style slot         | gold contacts |
| 12 | Smaller USB port                   | |
| 13 | Thinner card-edge slot             | |
| 14 | USB-C port                         | rounded mouth |
| 15 | HDMI-style port                    | trapezoidal mouth |
| 16 | DC barrel jack                     | cylindrical socket |
| 17 | SD card slot                       | wide low slot |
| 18 | Micro USB port                     | small mouth |
| 19 | RJ45 variant                       | slightly different proportions |

## Row 7 — SMD passives / LEDs (footprint ~0.8 × 0.4)

| Col | Variation | Notes |
|-----|-----------|-------|
| 0  | Plain SMD resistor                 | no marking |
| 1  | Plain SMD resistor                 | duplicate (use as filler) |
| 2  | SMD resistor with white stripe     | |
| 3  | SMD resistor with cyan stripe      | |
| 4  | SMD resistor with gold end caps    | |
| 5  | SMD resistor with gold + warm stripe | |
| 6  | Wider SMD resistor with white stripe | |
| 7  | Wider SMD resistor with green + gold | |
| 8  | Red SMD LED                        | colored top zone |
| 9  | Green SMD LED                      | |
| 10 | Blue SMD LED                       | |
| 11 | SMD inductor with winding stripes  | |
| 12 | 4-pad SMD array                    | square package, 4 contacts |
| 13 | Tall SMD electrolytic cap          | cylindrical body on square base |
| 14 | SMD diode (cathode stripe)         | |
| 15 | SMD crystal (4 corner pads)        | metal can |
| 16 | RGB SMD LED (three lens zones)     | |
| 17 | SOT-23 transistor                  | 3-lead small package |
| 18 | Shielded SMD inductor              | solid metal cube |
| 19 | SMD fuse                           | with copper element on top |

## How to use this in code

Pick a specific variation by indexing into the family's builder list:

```python
import sys; sys.path.insert(0, 'components')
from component_builders import ROWS

builders = dict(ROWS)['QFP / chip ICs']
my_bga = builders[8]()    # the BGA variation, index 8 in row 0
```

Or sample randomly via the layout planner:

```python
from mesh_builder import FAMILY_BUILDERS
import random
some_qfp = random.choice(FAMILY_BUILDERS['qfp'])()
```
