import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.stubEnv('PUBLIC_API_BASE_URL', '');

const { createRepo, getRepo, listRepos } = await import('./repos');

describe('repos api', () => {
	beforeEach(() => {
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('GETs repos from API base URL', async () => {
		const fetchMock = vi.mocked(globalThis.fetch);
		fetchMock.mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve([
					{
						id: 1,
						name: 'repo-a',
						url: 'https://example.test/repo-a.git',
						cursor_position: '',
						clone_error: ''
					}
				]),
			text: () => Promise.resolve('')
		} as Response);

		const repos = await listRepos();
		expect(repos).toHaveLength(1);
		expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/repos');
	});

	it('POSTs repo creation payload', async () => {
		const fetchMock = vi.mocked(globalThis.fetch);
		fetchMock.mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					queued: true,
					repo: {
						id: 1,
						name: 'repo-a',
						url: 'https://example.test/repo-a.git',
						cursor_position: '',
						clone_error: ''
					}
				}),
			text: () => Promise.resolve('')
		} as Response);

		const result = await createRepo('repo-a', 'https://example.test/repo-a.git');
		expect(result.queued).toBe(true);
		expect(fetchMock).toHaveBeenCalledWith(
			'http://localhost:8000/repos',
			expect.objectContaining({
				method: 'POST',
				headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
				body: JSON.stringify({ name: 'repo-a', url: 'https://example.test/repo-a.git' })
			})
		);
	});

	it('GETs a single repo by id', async () => {
		const fetchMock = vi.mocked(globalThis.fetch);
		fetchMock.mockResolvedValue({
			ok: true,
			json: () =>
				Promise.resolve({
					id: 1,
					name: 'repo-a',
					url: 'https://example.test/repo-a.git',
					cursor_position: 'abc',
					clone_error: ''
				}),
			text: () => Promise.resolve('')
		} as Response);

		const repo = await getRepo('1');
		expect(repo.id).toBe(1);
		expect(repo.cursor_position).toBe('abc');
		expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/repos/1');
	});
});
