import { publicApiBaseUrl } from '$lib/api/config';

async function readJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export type CatalogSpecItem = {
	id: number;
	paper_id: string;
};

export type RepoCatalogResponse = {
	specs: CatalogSpecItem[];
};

export async function fetchRepoCatalog(repoId: string | number): Promise<RepoCatalogResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/catalog`);
	return readJson(res);
}

export type SpecTreeImplementsArtifact = {
	artifact_version_id: number;
	filepath: string;
	evidence_file: string | null;
	evidence_line_number: number | null;
	evidence_snippet: string | null;
	evidence_relevance: string | null;
};

export type SpecTreeImplementation = {
	id: number;
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	implemented: boolean;
	summary: string | null;
	gaps: string[];
	confidence: number | null;
	artifacts: SpecTreeImplementsArtifact[];
};

export type SpecTreeItem = {
	id: number;
	local_key: string;
	item_type: string;
	importance: string;
	text: string;
	source_quote: string;
	success_criteria: string[];
	failure_criteria: string[];
	implementations: SpecTreeImplementation[];
};

export type SpecTreeVersion = {
	id: number;
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	title: string | null;
	summary: string | null;
	spec_md: string;
	tasks_md: string | null;
	plan_md: string | null;
	items: SpecTreeItem[];
};

export type SpecTreeResponse = {
	id: number;
	paper_id: string;
	versions: SpecTreeVersion[];
};

export async function fetchSpecTree(
	repoId: string | number,
	specId: string | number
): Promise<SpecTreeResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}/tree`);
	return readJson(res);
}

export type SpecViewItemSpan = {
	start: number;
	end: number;
};

export type SpecDocument = 'spec' | 'tasks' | 'plan';

export type SpecViewItemSpans = {
	spec: SpecViewItemSpan | null;
	tasks: SpecViewItemSpan | null;
	plan: SpecViewItemSpan | null;
};

export type SpecViewItem = {
	id: number;
	local_key: string;
	item_type: string;
	importance: string;
	text: string;
	source_quote: string;
	spans: SpecViewItemSpans;
	success_criteria: string[];
	failure_criteria: string[];
	implementations: SpecTreeImplementation[];
};

export type SpecViewSummary = {
	total_items: number;
	tracked_items: number;
	evaluated: number;
	implemented: number;
	mandatory_gaps: number;
	low_confidence: number;
	unevaluated: number;
	coverage_percent: number | null;
	status: string;
};

export type SpecViewVersion = {
	id: number;
	commit_sha: string;
	commit_message: string;
	committed_at: string;
	title: string | null;
	summary: string | null;
	spec_md: string;
	tasks_md: string | null;
	plan_md: string | null;
};

export type SpecViewResponse = {
	id: number;
	paper_id: string;
	version: SpecViewVersion;
	summary: SpecViewSummary;
	items: SpecViewItem[];
};

export type SpecTab = 'overview' | SpecDocument;

export async function fetchSpecView(
	repoId: string | number,
	specId: string | number,
	commitSha?: string
): Promise<SpecViewResponse> {
	const url = new URL(`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}/view`);
	if (commitSha) url.searchParams.set('commit_sha', commitSha);
	const res = await fetch(url);
	return readJson(res);
}
