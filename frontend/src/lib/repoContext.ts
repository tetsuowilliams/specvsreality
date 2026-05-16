import { getContext, setContext } from 'svelte';
import type { Repo } from '$lib/api/repos';

type RepoContext = {
	getRepo: () => Repo | null;
	getRepoId: () => string;
};

const repoContextKey = 'repo-context';

export function setRepoContext(value: RepoContext): void {
	setContext(repoContextKey, value);
}

export function getRepoContext(): RepoContext {
	const context = getContext<RepoContext>(repoContextKey);
	if (!context) {
		throw new Error('Repo context is not available in this route.');
	}
	return context;
}
