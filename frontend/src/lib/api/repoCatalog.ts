import { publicApiBaseUrl } from '$lib/api/config';

async function readJson<T>(res: Response): Promise<T> {
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as T;
}

export type CatalogRequirementItem = {
	id: number;
	paper_id: string;
};

export type CatalogSpecItem = {
	id: number;
	paper_id: string;
	requirements: CatalogRequirementItem[];
};

export type RepoCatalogResponse = {
	specs: CatalogSpecItem[];
};

export async function fetchRepoCatalog(repoId: string | number): Promise<RepoCatalogResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/catalog`);
	return readJson(res);
}

export type SpecDetailVersionItem = {
	id: number;
	spec_md: string;
	tasks_md: string | null;
	plan_md: string | null;
};

export type SpecRequirementStatusItem = {
	id: number;
	paper_id: string;
	has_version: boolean;
	implemented: boolean | null;
};

export type SpecDetailResponse = {
	id: number;
	paper_id: string;
	versions: SpecDetailVersionItem[];
	requirements: SpecRequirementStatusItem[];
};

export async function fetchSpecDetail(
	repoId: string | number,
	specId: string | number
): Promise<SpecDetailResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}`);
	return readJson(res);
}

export type GanttHistorySegment = {
	start: string;
	end: string;
	status: string;
	commit: string | null;
};

export type GanttRequirementBlock = {
	paper_id: string;
	history: GanttHistorySegment[];
};

export type GanttArtifactBlock = {
	filepath: string;
	history: GanttHistorySegment[];
};

export type GanttChartMeta = {
	requirement_implemented: boolean;
};

export type GanttChartResponse = {
	meta: GanttChartMeta;
	requirement: GanttRequirementBlock;
	artifacts: GanttArtifactBlock[];
};

export async function fetchGanttChart(
	repoId: string | number,
	specId: string | number,
	options?: { requirementId?: string | number | null }
): Promise<GanttChartResponse> {
	const rid = options?.requirementId;
	const q =
		rid !== undefined && rid !== null && String(rid).length > 0
			? `?requirement_id=${encodeURIComponent(String(rid))}`
			: '';
	const res = await fetch(`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}/gantt${q}`);
	return readJson(res);
}

export type RequirementLatestVersionResponse = {
	paper_id: string;
	requirement_text: string;
	commit_sha: string;
	commit_datetime: string;
};

export type ImplementsEvidenceItem = {
	evidence_file: string | null;
	evidence_line_number: number | null;
	evidence_snippet: string | null;
	evidence_relevance: string | null;
};

export type RequirementTreeArtifactVersion = {
	artifact_version_id: number;
	filepath: string;
	commit_sha: string;
	commit_datetime: string;
	status: string;
	file_content: string;
	evidence: ImplementsEvidenceItem;
};

export type RequirementTreeVersion = {
	id: number;
	commit_sha: string;
	commit_datetime: string;
	requirement_text: string;
	filepath_globs: string[];
	status: string;
	implemented: boolean | null;
	summary: string | null;
	gaps: string[] | null;
	artifact_versions: RequirementTreeArtifactVersion[];
};

export type RequirementVersionTreeResponse = {
	paper_id: string;
	versions: RequirementTreeVersion[];
};

export async function fetchRequirementVersionTree(
	repoId: string | number,
	specId: string | number,
	options?: { requirementId?: string | number | null }
): Promise<RequirementVersionTreeResponse> {
	const rid = options?.requirementId;
	const q =
		rid !== undefined && rid !== null && String(rid).length > 0
			? `?requirement_id=${encodeURIComponent(String(rid))}`
			: '';
	const res = await fetch(
		`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}/requirements/version-tree${q}`
	);
	return readJson(res);
}

export async function fetchRequirementLatestVersion(
	repoId: string | number,
	specId: string | number,
	options?: { requirementId?: string | number | null }
): Promise<RequirementLatestVersionResponse> {
	const rid = options?.requirementId;
	const q =
		rid !== undefined && rid !== null && String(rid).length > 0
			? `?requirement_id=${encodeURIComponent(String(rid))}`
			: '';
	const res = await fetch(
		`${publicApiBaseUrl()}/repos/${repoId}/specs/${specId}/requirements/latest-version${q}`
	);
	return readJson(res);
}
