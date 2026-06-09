import { publicApiBaseUrl } from '$lib/api/config';

export type Repo = {
	id: number;
	name: string;
	url: string;
	cursor_position: string;
	clone_error: string;
};

type CreateRepoResponse = {
	queued: boolean;
	repo: Repo;
};

export async function listRepos(): Promise<Repo[]> {
	const res = await fetch(`${publicApiBaseUrl()}/repos`);
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as Repo[];
}

export async function createRepo(name: string, url: string): Promise<CreateRepoResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name, url })
	});
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as CreateRepoResponse;
}

export async function getRepo(repoId: string | number): Promise<Repo> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}`);
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as Repo;
}
