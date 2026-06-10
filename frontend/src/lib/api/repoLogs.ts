import { publicApiBaseUrl } from '$lib/api/config';

async function readJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export type CommitLogSidebarEntry = {
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	log_count: number;
};

export type CommitLogEntry = {
	action: string;
	spec_folder: string;
	message: string;
	reasoning: string;
	created_at: string;
};

export type RepoLogsSidebarResponse = {
	commits: CommitLogSidebarEntry[];
};

export type RepoCommitLogsResponse = {
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	logs: CommitLogEntry[];
};

export async function fetchLogsSidebar(repoId: string | number): Promise<RepoLogsSidebarResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/logs/sidebar`);
	return readJson<RepoLogsSidebarResponse>(res);
}

export async function fetchCommitLogs(
	repoId: string | number,
	commitSha: string
): Promise<RepoCommitLogsResponse> {
	const url = new URL(`${publicApiBaseUrl()}/repos/${repoId}/logs`);
	url.searchParams.set('commit_sha', commitSha);
	const res = await fetch(url);
	return readJson<RepoCommitLogsResponse>(res);
}
