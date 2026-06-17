import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/app/',
  build: {
    outDir: '../../finance_api/static/app',
    emptyOutDir: true,
  },
});
