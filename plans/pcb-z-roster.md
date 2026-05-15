# PCB Parts With Z Height — Roster

**View with images (recommended):** open [`plans/pcb-z-roster.html`](pcb-z-roster.html) in a browser. Many Markdown previews block remote image URLs; the HTML uses normal `<img>` tags.

Plain English: anything soldered or mounted on a board has *some* thickness. This list orders typical **maximum height above the PCB plane** (package body + standing pins + tallest variants people actually use). Real boards vary by vendor; use the ranges as layout guides, not CAD tolerances.

**Circuit scream** is subjective: **10** = instant “that’s a board / computer,” **1** = could be almost anything.

**Images** are reference photos (mostly Wikimedia Commons via Wikipedia summaries). Click through to the file page if a link ever breaks.

---

| Typical max **Z** (mm) | Part / feature | Circuit scream (1–10) | Notes | Reference |
|---:|---|---:|---|---|
| **0.2–0.6** | **0201 / 0402 / 0603** passives (R, C, L) | 7 | Density read — “rice grain city.” Almost no silhouette alone; power is *massed repetition*. | ![](https://upload.wikimedia.org/wikipedia/commons/6/6b/Smt_closeup.jpg) |
| **0.6–1.2** | **SMD LEDs / diodes / small SOT** | 5 | Low slabs; silhouette needs clusters or paired polarity marks to read. | ![](https://upload.wikimedia.org/wikipedia/commons/c/cb/RBG-LED.jpg) |
| **0.9–1.4** | **QFN / MLF** (pads under body; optional exposed pad) | 8 | Square “dark tile” from above; edge pads sometimes visible as a halo. | ![](https://upload.wikimedia.org/wikipedia/commons/2/23/28_pin_MLP_integrated_circuit.jpg) |
| **1.0–1.4** | **TSSOP / SSOP** (two fine-pitch rows) | 9 | Strong “train-track IC” read from an angle; great paired rails for line tracing. | ![](https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/TSOP_32_%28T1%29_BW.svg/960px-TSOP_32_%28T1%29_BW.svg.png) |
| **1.5–1.9** | **SOIC** (wider two-row SO packages) | 8 | The everyday logic IC silhouette — readable without microscope. | ![](https://upload.wikimedia.org/wikipedia/commons/9/98/Laptop_Acrobat_Model_NBD_486C%2C_Type_DXh2_-_California_Micro_Devices_CMD_9324_on_motherboard-9749.jpg) |
| **1.8–2.6** | **QFP / LQFP / TQFP** (gull leads on four sides) | 10 | The “chip city” poster child — perimeter legs read instantly (your QFP obsession is justified). | ![](https://upload.wikimedia.org/wikipedia/commons/4/40/Z84C0010FEC_LQFP.png) |
| **2.0–3.0** | **BGA** (under-body balls; molded lid) | 9 | Top reads as a **flat square cap**; identity is “dense silicon,” not legs. X-ray art loves BGAs. | ![](https://upload.wikimedia.org/wikipedia/commons/8/8a/Solder_ball_grid.jpg) |
| **2–4** | **SMD tantalum** (“blob” / molded chip tantalum) | 7 | Directionality marked; reads as *serious decoupling* next to big ICs. | ![](https://upload.wikimedia.org/wikipedia/commons/3/34/Tantal-P1100196c.jpg) |
| **2–8** | **Stamped EMI shield / RF can** | 9 | Boxy volumes with seams — great **Z jumps** at corners without fragile pins. | ![](https://upload.wikimedia.org/wikipedia/commons/5/55/Electromagnetic_shielding_inside_mobile_phone.jpg) |
| **~2.4–4.5** | **M.2 2280 module** (single-sided vs double-sided stacks higher) | 9 | Low long slab — **storage highway** silhouette; pairs with PCIe lanes by association. | ![](https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Intel_512G_M2_Solid_State_Drive.jpg/3840px-Intel_512G_M2_Solid_State_Drive.jpg) |
| **3–5** | **HC-49 through-hole crystal** | 8 | Metal can “timing tower”; pairs well with MCU/QFP clusters. | ![](https://upload.wikimedia.org/wikipedia/commons/c/c7/16MHZ_Crystal.jpg) |
| **3.5–5** | **DIP IC** (through-hole plastic dual-inline) | 9 | Retro breadboard soul — parallel pin forest on two sides. | ![](https://upload.wikimedia.org/wikipedia/commons/8/80/Three_IC_circuit_chips.JPG) |
| **4–12** | **Cylindrical / V‑chip SMD aluminum electrolytics** | 9 | Classic **motherboard skyline** caps (until everything went solid-state). | ![](https://upload.wikimedia.org/wikipedia/commons/3/3f/Kondensator-Al-Elko-Wiki-07-02-11.jpg) |
| **4–15** | **Power inductors** (shielded + open bobbin) | 8 | Fat prisms / drums — instant **switching supply** read near VRM. | ![](https://upload.wikimedia.org/wikipedia/commons/a/a1/Electronic_component_inductors.jpg) |
| **4–20** | **TO‑220 / TO‑247** (vertical regulator / FET + tab) | 8 | Tab as vertical plane — **power device** silhouette everyone recognizes. | ![](https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/TO-220_Front_Coloured.svg/960px-TO-220_Front_Coloured.svg.png) |
| **4–8** | **CR2032 / coin-cell holder** | 8 | CMOS / RTC vibes — low pancake tower with visible retention clips. | ![](https://upload.wikimedia.org/wikipedia/commons/c/c7/Coin-cells.jpg) |
| **6–40+** | **Radial aluminum electrolytics** (through-hole, tall cans) | 10 | Often the **tallest discrete** on consumer boards until coolers dominate. | ![](https://upload.wikimedia.org/wikipedia/commons/f/f6/Electrolytic_capacitors-P1090328.JPG) |
| **8–17** | **1.27 mm / 2.54 mm pin headers** (vertical stacks) | 10 | Prototype DNA — rows of square pins; tallest when stacked or long tails. | ![](https://upload.wikimedia.org/wikipedia/commons/b/bf/6_Pin_Header.jpg) |
| **8–15** | **CPU socket + retention frame / ILM** | 10 | Mechanical ring around the die land — reads as **central plaza** before cooler mounts. | ![](https://upload.wikimedia.org/wikipedia/commons/0/0c/AM5_Socket_Open.jpg) |
| **11–14** | **RJ45 jack + magnetics block** | 10 | Chunky cubic connector — **network hardware** identity. | ![](https://upload.wikimedia.org/wikipedia/commons/7/7f/Rjxx.jpg) |
| **~11 (+card)** | **PCIe / PCI / edge connectors** (slot + retention clip region) | 10 | **Gold fingers + slot mouth** — interface machinery identity (photo shows add-in card context). | ![](https://upload.wikimedia.org/wikipedia/commons/e/ee/LSI_9207-4i4e_PCI-E_SAS_HBA.jpg) |
| **13–17** | **Through-hole USB-A socket** (and many stacked USB stacks) | 9 | Tall cage — swap in your own PCB-mount USB macro if you want less “catalog,” more Tron. | ![](https://upload.wikimedia.org/wikipedia/commons/2/24/PCB_mounting_female_USB_A_and_B_connectors.jpg) |
| **20–55** | **Chipset / VRM / northbridge style heatsinks** | 10 | Stepped extrusions — **hero mesas** without inventing fantasy buildings. | ![](https://upload.wikimedia.org/wikipedia/commons/a/a6/Abit-kt7-large.jpg) |
| **~30** | **DDR DIMM module** (vertical UDIMM in socket) | 10 | Paired **RAM slabs** — your tall-flank “skyscraper” language maps here 1:1. | ![](https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/168_pin_and_184_pin_DIMM.jpg/3840px-168_pin_and_184_pin_DIMM.jpg) |
| **40–165** | **CPU cooler** (stock heatpipe tower / downdraft / AIO pump block on bracket) | 10 | Usually **wins tallest object** on the board; dominates silhouette shots. | ![](https://upload.wikimedia.org/wikipedia/commons/2/25/AMD_heatsink_and_fan.jpg) |

---

## How to use this for your Tron mesh

- Pick **one spine** (PCIe trace corridor or long DIMM channel) and hang **4 height tiers** off it: **passives + low packages → QFP/DIMM slabs → socket/heatsink mesas → cooler peak**.
- **Repeat dimensions** within a tier (that’s how real boards stay legible).
- If Z feels flat, add **one EMI can**, **one radial or SMD electrolytic cluster**, and **one vertical connector wall** (RJ45/USB stack) before touching fantasy geometry.

## Licensing note

Images are from Wikimedia Commons / Wikipedia and carry their own licenses (typically CC BY-SA / GFDL / public domain for simple diagrams). Attribute on your site only if you ship these photos in production; for internal layout reference you’re fine.
