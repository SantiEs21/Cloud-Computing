import { defineConfig } from 'vite'

// es2022 for top-level await in src/main.ts
export default defineConfig({ build: { target: 'es2022' } })
