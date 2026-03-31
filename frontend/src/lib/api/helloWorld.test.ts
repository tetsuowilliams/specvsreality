import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.stubEnv('PUBLIC_API_BASE_URL', '');

const { postHelloWorld } = await import('./helloWorld');

describe('postHelloWorld', () => {
	beforeEach(() => {
		vi.stubGlobal(
			'fetch',
			vi.fn().mockResolvedValue({
				ok: true,
				json: () => Promise.resolve({ queued: true }),
				text: () => Promise.resolve('')
			})
		);
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('POSTs JSON to the public API base', async () => {
		const r = await postHelloWorld('Ada');
		expect(r).toEqual({ queued: true });
		const fetchMock = vi.mocked(globalThis.fetch);
		expect(fetchMock).toHaveBeenCalledWith(
			'http://localhost:8000/hello-world',
			expect.objectContaining({
				method: 'POST',
				headers: expect.objectContaining({
					'Content-Type': 'application/json'
				}),
				body: JSON.stringify({ name: 'Ada' })
			})
		);
	});
});
