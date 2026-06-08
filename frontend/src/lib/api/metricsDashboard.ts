import { publicApiBaseUrl } from '$lib/api/config';

async function readJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export type MetricsSummary = {
	total_cost_usd: string;
	total_tokens: number;
	total_runs: number;
	repo_count: number;
};

export type RepoMetricsRow = {
	repo_id: number;
	repo_name: string;
	total_cost_usd: string;
	total_tokens: number;
	run_count: number;
};

export type AgentMetricsRow = {
	agent: string;
	total_cost_usd: string;
	total_tokens: number;
	run_count: number;
};

export type AgentRunRow = {
	id: number;
	repo_id: number;
	repo_name: string;
	commit_sha: string;
	agent: string;
	model: string;
	input_tokens: number;
	output_tokens: number;
	total_tokens: number;
	cost_usd: string;
	ran_at: string;
};

export type MetricsDashboardResponse = {
	summary: MetricsSummary;
	by_repo: RepoMetricsRow[];
	by_agent: AgentMetricsRow[];
	recent_runs: AgentRunRow[];
};

export async function fetchMetricsDashboard(repoId?: number): Promise<MetricsDashboardResponse> {
	const params = new URLSearchParams();
	if (repoId != null) {
		params.set('repo_id', String(repoId));
	}
	const query = params.toString();
	const url = `${publicApiBaseUrl()}/metrics${query ? `?${query}` : ''}`;
	return readJson<MetricsDashboardResponse>(await fetch(url));
}
