import adapter from '@sveltejs/adapter-static';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		// Default relative `./_app/...` URLs break on deep links when nginx falls back to
		// `index.html` (browser resolves assets under `/repos/.../gantt/_app/` → HTML → MIME error).
		paths: { relative: false },
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: undefined,
			precompress: false,
			strict: true
		}),
		prerender: {
			handleMissingId: 'warn',
			handleHttpError: 'warn',
			handleUnseenRoutes: 'warn',
			entries: ['*']
		}
	}
};

export default config;
