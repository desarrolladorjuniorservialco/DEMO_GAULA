/// <reference types="vitest" />
import { defineConfig } from 'vite';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  build: {
    lib: {
      entry: path.resolve(__dirname, 'src/osint-graph.js'),
      name: 'OsintGraph',
      formats: ['iife'],
      fileName: () => 'osint-graph.bundle.js',
    },
    outDir: path.resolve(__dirname, '../static/js'),
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: 'osint-graph.bundle.js',
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
