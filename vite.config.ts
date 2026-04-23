import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      react: path.resolve('./node_modules/react'),
      'react-dom': path.resolve('./node_modules/react-dom'),
    },
    dedupe: ['react', 'react-dom', 'three'],
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        terminalText: path.resolve(__dirname, 'terminal-text.html'),
        backgroundMusic: path.resolve(__dirname, 'background-music.html'),
        centerlineDebug: path.resolve(__dirname, 'plans/centerline-debug.html'),
        drainstrokeExample: path.resolve(
          __dirname,
          'plans/drainstroke-example.html',
        ),
        tronLines: path.resolve(__dirname, 'tron-lines.html'),
      },
    },
  },
})
