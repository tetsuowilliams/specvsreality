/** Host URL for the API (`PUBLIC_API_BASE_URL` at build time, see `.env.example`). */
export function publicApiBaseUrl(): string {
	const raw = import.meta.env.PUBLIC_API_BASE_URL;
	const base =
		typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : 'http://localhost:8000';
	return base.replace(/\/$/, '');
}
