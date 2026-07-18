import react from '@vitejs/plugin-react'
import { loadEnv } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, '.', 'BUTTERFLYLENS_')
  const base = environment.BUTTERFLYLENS_BASE_PATH || '/'
  if (!/^\/(?:[A-Za-z0-9._-]+\/)*$/.test(base)) {
    throw new Error('BUTTERFLYLENS_BASE_PATH must be an absolute directory path')
  }
  return {
    base,
    plugins: [react()],
    test: {
      environment: 'jsdom',
      exclude: [...configDefaults.exclude, 'e2e/**'],
      setupFiles: ['./src/test/setup.ts'],
    },
  }
})
