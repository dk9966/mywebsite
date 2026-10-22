//! Voxelize server for the box recessed into the cave hole behind the
//! central platform (`/secret-base/?cave`).
//!
//! The world is one bounded 2×2-chunk region. Voxel X runs across the hole,
//! voxel Z runs into the rock (Z = 0 is the open face the camera sees through)
//! and Y is up. The client places and scales the whole grid to the hole, so the
//! server only deals in whole blocks.

use voxelize::{
    Block, BlockFaces, Chunk, ChunkStage, Registry, Resources, Server, Space, Vec3, VoxelAccess,
    Voxelize, World, WorldConfig,
};

/// Interior dimensions in blocks (the shell sits one block outside these).
pub const WIDTH: i32 = 28;
pub const DEPTH: i32 = 18;
pub const HEIGHT: i32 = 22;
/// Grid origin of the interior, leaving room for the shell at x = 0 / y = 0.
const X0: i32 = 1;
const Y0: i32 = 1;
const Z0: i32 = 0;

fn registry() -> Registry {
    let mut registry = Registry::new();
    let plant = BlockFaces::diagonal_faces()
        .scale_horizontal(0.7)
        .scale_vertical(0.7)
        .build();
    registry.register_blocks(&[
        Block::new("Stone").id(1).build(),
        Block::new("Deepslate").id(2).build(),
        Block::new("Dirt").id(3).build(),
        Block::new("Grass Block").id(4).build(),
        Block::new("Moss Block").id(5).build(),
        Block::new("Cobblestone").id(6).build(),
        Block::new("Oak Log").id(7).build(),
        Block::new("Oak Leaves")
            .id(8)
            .is_transparent(true)
            .is_see_through(true)
            .light_reduce(true)
            .build(),
        Block::new("Coal Ore").id(9).build(),
        Block::new("Iron Ore").id(10).build(),
        Block::new("Diamond Ore").id(11).build(),
        Block::new("Oak Planks").id(12).build(),
        // Cool cave light, matching the scene's blue-white spot colour.
        Block::new("Sea Lantern")
            .id(13)
            .red_light_level(12)
            .green_light_level(14)
            .blue_light_level(15)
            .build(),
        // Warm accents, matching the amber practicals on the platforms.
        Block::new("Glowstone")
            .id(14)
            .red_light_level(15)
            .green_light_level(13)
            .blue_light_level(9)
            .build(),
        Block::new("Short Grass")
            .id(15)
            .faces(&plant)
            .is_passable(true)
            .is_see_through(true)
            .is_transparent(true)
            .is_plant(true)
            .build(),
        Block::new("Blue Orchid")
            .id(16)
            .faces(&plant)
            .is_passable(true)
            .is_see_through(true)
            .is_transparent(true)
            .is_plant(true)
            .build(),
    ]);
    registry
}

/// Deterministic per-voxel hash in [0, 1).
fn hash(x: i32, y: i32, z: i32) -> f32 {
    let mut h = (x as u32).wrapping_mul(374_761_393)
        ^ (y as u32).wrapping_mul(668_265_263)
        ^ (z as u32).wrapping_mul(2_246_822_519);
    h = (h ^ (h >> 13)).wrapping_mul(1_274_126_177);
    (h ^ (h >> 16)) as f32 / u32::MAX as f32
}

/// Terraced floor: low at the open face, climbing in steps toward the back
/// and the left wall so the whole interior reads through the hole.
fn floor_height(x: i32, z: i32) -> i32 {
    let back = (z as f32 / DEPTH as f32 * 7.0) as i32;
    let side = ((x as f32 - WIDTH as f32 * 0.6).max(0.0) / 4.0) as i32;
    let bump = ((x as f32 * 0.55).sin() + (z as f32 * 0.42).cos()) * 0.7;
    (1 + back + side + bump.round() as i32).clamp(1, 11)
}

/// Stalactites hanging from the ceiling, as a depth in blocks.
fn hang(x: i32, z: i32) -> i32 {
    let r = hash(x * 7, 91, z * 13);
    if r < 0.1 { 1 + (r * 40.0) as i32 % 3 } else { 0 }
}

struct BoxStage;

impl ChunkStage for BoxStage {
    fn name(&self) -> String {
        "Recessed box".to_owned()
    }

    fn process(&self, mut chunk: Chunk, resources: Resources, _: Option<Space>) -> Chunk {
        let id = |name: &str| resources.registry.get_block_by_name(name).id;
        let (stone, deepslate, dirt, grass, moss, cobble) = (
            id("Stone"),
            id("Deepslate"),
            id("Dirt"),
            id("Grass Block"),
            id("Moss Block"),
            id("Cobblestone"),
        );
        let (coal, iron, diamond) = (id("Coal Ore"), id("Iron Ore"), id("Diamond Ore"));
        let (sea, glow, short_grass, orchid) = (
            id("Sea Lantern"),
            id("Glowstone"),
            id("Short Grass"),
            id("Blue Orchid"),
        );
        let (log, leaves, planks) = (id("Oak Log"), id("Oak Leaves"), id("Oak Planks"));

        let Vec3(min_x, _, min_z) = chunk.min;
        let Vec3(max_x, _, max_z) = chunk.max;
        let (x1, y1, z1) = (X0 + WIDTH, Y0 + HEIGHT, Z0 + DEPTH);

        for vx in min_x..max_x {
            for vz in min_z..max_z {
                if vx < X0 - 1 || vx > x1 || vz < Z0 || vz > z1 {
                    continue;
                }
                let shell_x = vx == X0 - 1 || vx == x1;
                let shell_z = vz == z1;
                let lx = vx - X0;
                let lz = vz - Z0;
                let ground = if shell_x || shell_z { 0 } else { floor_height(lx, lz) };
                for vy in 0..=y1 {
                    let shell = shell_x || shell_z || vy == 0 || vy == y1;
                    let r = hash(vx, vy, vz);
                    let ceiling_drop = if !shell_x && !shell_z { hang(lx, lz) } else { 0 };
                    let voxel = if !shell && vy >= y1 - ceiling_drop {
                        if r < 0.5 { deepslate } else { stone }
                    } else if shell {
                        // Ores speckle the walls; the ceiling carries the lamps.
                        let wall_lamp = (vy == Y0 + 6 || vy == Y0 + 12)
                            && ((shell_x && lz % 5 == 2 && lz < DEPTH) || (shell_z && lx % 5 == 2 && lx >= 0 && lx < WIDTH));
                        if wall_lamp {
                            sea
                        } else if vy == y1 && !shell_x && !shell_z && lx % 5 == 2 && lz % 5 == 2 {
                            if (lx + lz) % 4 == 1 { glow } else { sea }
                        } else if r < 0.035 {
                            coal
                        } else if r < 0.055 {
                            iron
                        } else if r < 0.062 {
                            diamond
                        } else if vy < 4 || r > 0.7 {
                            deepslate
                        } else if r > 0.62 {
                            cobble
                        } else {
                            stone
                        }
                    } else if vy < Y0 + ground - 2 {
                        stone
                    } else if vy < Y0 + ground - 1 {
                        dirt
                    } else if vy == Y0 + ground - 1 {
                        if r < 0.18 { moss } else { grass }
                    } else if vy == Y0 + ground && r < 0.22 {
                        if r < 0.03 { orchid } else { short_grass }
                    } else {
                        continue;
                    };
                    chunk.set_voxel(vx, vy, vz, voxel);
                }
            }
        }

        // Small oak on the rear terrace, and a plank ledge with a lantern.
        let (tx, tz) = (X0 + 9, Z0 + 12);
        if chunk.contains(tx, 0, tz) || chunk.contains(tx + 2, 0, tz + 2) || chunk.contains(tx - 2, 0, tz - 2) {
            let base = Y0 + floor_height(tx - X0, tz - Z0);
            for dy in 0..5 {
                set_if_inside(&mut chunk, tx, base + dy, tz, log);
            }
            for dx in -2i32..=2 {
                for dz in -2i32..=2 {
                    for dy in 3..7 {
                        let edge = dx.abs() + dz.abs() + (dy - 3).max(0) / 2;
                        if (dx != 0 || dz != 0 || dy > 4) && edge <= 3 {
                            set_if_inside(&mut chunk, tx + dx, base + dy, tz + dz, leaves);
                        }
                    }
                }
            }
        }
        // A plank walkway across the first terrace, lit by a glowstone post.
        for dx in 0..7 {
            let (px, pz) = (X0 + 16 + dx, Z0 + 6);
            let base = Y0 + floor_height(px - X0, pz - Z0);
            set_if_inside(&mut chunk, px, base, pz, planks);
            set_if_inside(&mut chunk, px, base, pz + 1, planks);
        }
        let post = (X0 + 22, Z0 + 8);
        let post_base = Y0 + floor_height(post.0 - X0, post.1 - Z0);
        for dy in 0..2 {
            set_if_inside(&mut chunk, post.0, post_base + dy, post.1, log);
        }
        set_if_inside(&mut chunk, post.0, post_base + 2, post.1, glow);
        // Glowstone lantern posts on the terraces.
        for (px, pz) in [(X0 + 5, Z0 + 4), (X0 + 13, Z0 + 3), (X0 + 18, Z0 + 13), (X0 + 25, Z0 + 15), (X0 + 2, Z0 + 10)] {
            let base = Y0 + floor_height(px - X0, pz - Z0);
            set_if_inside(&mut chunk, px, base, pz, log);
            set_if_inside(&mut chunk, px, base + 1, pz, glow);
        }
        // A stone column with an ore seam near the back right.
        let column = (X0 + 4, Z0 + 14);
        for vy in Y0..Y0 + HEIGHT {
            let id = if hash(column.0, vy, column.1) < 0.2 { diamond } else { cobble };
            set_if_inside(&mut chunk, column.0, vy, column.1, id);
            set_if_inside(&mut chunk, column.0 + 1, vy, column.1, cobble);
        }

        chunk
    }
}

fn set_if_inside(chunk: &mut Chunk, x: i32, y: i32, z: i32, id: u32) {
    if chunk.contains(x, y, z) {
        chunk.set_voxel(x, y, z, id);
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let registry = registry();
    let port = std::env::var("VOXEL_PORT")
        .ok()
        .and_then(|value| value.parse().ok())
        .unwrap_or(4100);

    let mut server = Server::new()
        .port(port)
        .secret("secret-base")
        .registry(&registry)
        .build();

    let config = WorldConfig::new()
        .chunk_size(16)
        .sub_chunks(2)
        .max_height(32)
        .min_chunk([0, 0])
        .max_chunk([1, 1])
        .preload(true)
        .preload_radius(2)
        .does_tick_time(false)
        .default_time(0.0)
        .saving(true)
        .save_dir("data/worlds/cave-box")
        .build();

    let mut world = World::new("cave-box", &config);
    world.pipeline_mut().add_stage(BoxStage);
    server.add_world(world).expect("Could not create the cave box world.");

    println!("[voxel] cave-box world on ws://localhost:{port}");
    Voxelize::run(server).await
}
