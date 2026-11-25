import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { apiTarget, dashboardPort, swaggerPath } from './src/config.ts';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: dashboardPort,
    strictPort: true,
    proxy: {
      '/api': apiTarget,
      '/health': apiTarget,
      [swaggerPath]: apiTarget,
      '/openapi.json': apiTarget,
    },
  },
});
