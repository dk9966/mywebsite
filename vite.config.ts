import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { circuitsTuningSavePlugin } from './scripts/vite-circuits-tuning-save'
import { jsonFileSavePlugin } from './scripts/vite-json-file-save'
import { blenderLivePlugin } from './scripts/vite-blender-live'

const siteOnly = process.env.SITE_ONLY === '1'

// Vite dev serves secret-base/index.html at /secret-base/ but returns an
// empty response for /secret-base (no trailing slash) — redirect it.
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
      ],
    },
  },
  optimizeDeps: {
    include: [
      'three/addons/lines/Line2.js',
      'three/addons/lines/LineGeometry.js',
      'three/addons/lines/LineMaterial.js',
    ],
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
