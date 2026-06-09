import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	// Leave 5173 for Opik’s local API/UI; see worker `.env.example` / OPIK_URL_OVERRIDE.
	server: { port: 5180, strictPort: false },
	test: {
		environment: 'jsdom',
		include: ['src/**/*.{test,spec}.ts']
	}
});
