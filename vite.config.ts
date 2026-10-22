import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { circuitsTuningSavePlugin } from './scripts/vite-circuits-tuning-save'
import { jsonFileSavePlugin } from './scripts/vite-json-file-save'
import { blenderLivePlugin } from './scripts/vite-blender-live'

const siteOnly = process.env.SITE_ONLY === '1'

// Vite dev serves secret-base/index.html at /secret-base/ but returns an
// empty response for /secret-base (no trailing slash) — redirect it. Also
// routes the cave page (cave/index.html) at /cave and the type lab
// (text/index.html) at /text.
const secretBaseRedirect = () => ({
  name: 'secret-base-redirect',
  configureServer(server: import('vite').ViteDevServer) {
    server.middlewares.use((req, res, next) => {
      if (req.url === '/secret-base' || req.url === '/secret-base?') {
        res.statusCode = 302
        res.setHeader('Location', '/secret-base/')
        res.end()
        return
      }
      const url = new URL(req.url ?? '/', 'http://localhost')
      // The cave lives at /cave; the old /secret-base/?cave links forward there
      // with their debug flags (?cave&locked → /cave?locked).
      if (url.pathname === '/secret-base/' && url.searchParams.has('cave')) {
        const flags = url.search.slice(1).split('&').filter((p) => p && p.split('=')[0] !== 'cave')
        res.statusCode = 302
        res.setHeader('Location', flags.length ? `/cave?${flags.join('&')}` : '/cave')
        res.end()
        return
      }
      // Serve cave/index.html at /cave itself, with no trailing-slash redirect.
      if (url.pathname === '/cave') req.url = `/cave/${url.search}`
      if (url.pathname === '/text') req.url = `/text/${url.search}`
      next()
    })
  },
})

const allBuildInputs = {
  main: path.resolve(__dirname, 'index.html'),
  terminalView: path.resolve(__dirname, 'terminal-view.html'),
  terminalText: path.resolve(__dirname, 'terminal-text.html'),
  backgroundMusic: path.resolve(__dirname, 'background-music.html'),
  centerlineDebug: path.resolve(__dirname, 'plans/centerline-debug.html'),
  drainstrokeExample: path.resolve(
    __dirname,
    'plans/drainstroke-example.html',
  ),
  tronLines: path.resolve(__dirname, 'tron-lines.html'),
  tronTable: path.resolve(__dirname, 'tron-table.html'),
  tronCircuitsOutline: path.resolve(__dirname, 'tron-circuits-outline.html'),
  tronCircuitsEditor: path.resolve(__dirname, 'tron-circuits-editor.html'),
  componentReferenceOutline: path.resolve(__dirname, 'component-reference-outline.html'),
  secretBase: path.resolve(__dirname, 'secret-base/index.html'),
  cave: path.resolve(__dirname, 'cave/index.html'),
  text: path.resolve(__dirname, 'text/index.html'),
  circuitPainter: path.resolve(__dirname, 'circuit-painter/index.html'),
  circuitGenerator: path.resolve(__dirname, 'circuit-generator/index.html'),
  circuitFlow: path.resolve(__dirname, 'circuit-flow/index.html'),
  circuitBoard: path.resolve(__dirname, 'circuit-board/index.html'),
  circuitRoad: path.resolve(__dirname, 'circuit-road/index.html'),
  circuitPainter2: path.resolve(__dirname, 'circuit-painter-2/index.html'),
}

export default defineConfig({
  server: {
    port: 5174,
    strictPort: true,
    // Dev save writes circuits-tuning.json in-process; the store already holds
    // the committed payload — reloading would reset the editor camera.
    watch: {
      ignored: [
        '**/*.blend',
        '**/*.blend1',
        '**/secret-base/models/*.glb',
        '**/src/data/circuits-tuning.json',
        '**/src/data/circuit-versions/**',
        '**/src/data/desk-layout-defaults.json',
        '**/secret-base/components/cave/labelLayout.json',
        '**/secret-base/components/cave/panelLayout.json',
        '**/secret-base/components/cave/zoomLayout.json',
      ],
    },
  },
  optimizeDeps: {
    include: [
      'three/addons/lines/Line2.js',
      'three/addons/lines/LineGeometry.js',
      'three/addons/lines/LineMaterial.js',
      // Voxelize itself must stay unbundled (below), but its CommonJS
      // dependencies still need pre-bundling to load as ES modules.
      ...['@voxelize/aabb', '@voxelize/debug', '@voxelize/physics-engine', '@voxelize/protocol',
        '@voxelize/raycast', 'deepmerge', 'domurl', 'events', 'gl-vec3', 'ndarray', 'omggif', 'uuid', 'zod']
        .map((dep) => `@voxelize/core > ${dep}`),
    ],
    // Voxelize loads its mesh/light workers via `new URL(..., import.meta.url)`
    // next to its own dist; pre-bundling moves the module and breaks those URLs.
    exclude: ['@voxelize/core'],
  },
  plugins: [
    react(),
    blenderLivePlugin(),
    secretBaseRedirect(),
    circuitsTuningSavePlugin(),
    jsonFileSavePlugin({
      name: 'desk-layout-save',
      route: '/__save-desk-layout',
      relPath: 'src/data/desk-layout-defaults.json',
    }),
    jsonFileSavePlugin({
      name: 'cave-labels-save',
      route: '/__save-cave-labels',
      relPath: 'secret-base/components/cave/labelLayout.json',
    }),
    jsonFileSavePlugin({
      name: 'cave-panels-save',
      route: '/__save-cave-panels',
      relPath: 'secret-base/components/cave/panelLayout.json',
    }),
    jsonFileSavePlugin({
      name: 'cave-zoom-save',
      route: '/__save-cave-zoom',
      relPath: 'secret-base/components/cave/zoomLayout.json',
    }),
  ],
  resolve: {
    alias: {
      react: path.resolve('./node_modules/react'),
      'react-dom': path.resolve('./node_modules/react-dom'),
    },
    dedupe: ['react', 'react-dom', 'three'],
  },
  build: {
    rollupOptions: {
      input: siteOnly
        ? { main: allBuildInputs.main }
        : allBuildInputs,
    },
  },
})
