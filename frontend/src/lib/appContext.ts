import { getContext, setContext } from 'svelte';
import type { Repo } from '$lib/api/repos';

export type AppContext = {
	getRepos: () => Repo[];
	refreshRepos: () => Promise<void>;
	openAddRepo: () => void;
};

const APP_CONTEXT_KEY = 'app-context';

export function setAppContext(ctx: AppContext) {
	setContext(APP_CONTEXT_KEY, ctx);
}

export function getAppContext(): AppContext {
	return getContext<AppContext>(APP_CONTEXT_KEY);
}
