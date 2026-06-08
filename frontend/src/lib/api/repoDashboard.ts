import { publicApiBaseUrl } from '$lib/api/config';

async function readJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export type DashboardSummary = {
	specs_tracked: number;
	latest_commit_sha: string | null;
	latest_commit_message: string | null;
	latest_commit_at: string | null;
	coverage_percent: number | null;
	missing_items: number;
	low_confidence_items: number;
	candidate_artifacts: number;
};

export type DashboardSpecRow = {
	spec_id: number;
	paper_id: string;
	latest_version_id: number;
	latest_commit_sha: string;
	status: string;
	satisfied: number;
	missing: number;
	low_confidence: number;
	candidate_artifacts: number;
	last_evaluated_commit_sha: string | null;
	last_evaluated_at: string | null;
};

export type DashboardAttentionItem = {
	spec_id: number;
	paper_id: string;
	headline: string;
	detail: string;
	severity: string;
};

export type DashboardRecentChange = {
	spec_id: number;
	paper_id: string;
	local_key: string | null;
	message: string;
	commit_sha: string;
	committed_at: string;
};

export type DashboardArtifactActivity = {
	filepath: string;
	link_type: string;
	item_count: number;
	spec_paper_id: string | null;
	label: string;
};

export type RepoDashboardResponse = {
	repo_id: number;
	repo_name: string;
	summary: DashboardSummary;
	specs: DashboardSpecRow[];
	needs_attention: DashboardAttentionItem[];
	recent_changes: DashboardRecentChange[];
	artifact_activity: DashboardArtifactActivity[];
};

export type SidebarSpecVersion = {
	version_id: number;
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	title: string | null;
	status: string;
};

export type SidebarSpec = {
	id: number;
	paper_id: string;
	title: string;
	versions: SidebarSpecVersion[];
};

export type RepoSidebarResponse = {
	specs: SidebarSpec[];
};

export async function fetchRepoDashboard(repoId: string | number): Promise<RepoDashboardResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/dashboard`);
	return readJson(res);
}

export async function fetchRepoSidebar(repoId: string | number): Promise<RepoSidebarResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/sidebar`);
	return readJson(res);
}
