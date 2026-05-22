import type {
	GanttChartResponse,
	ImplementsEvidenceItem,
	RequirementTreeVersion,
	RequirementVersionTreeResponse
} from '$lib/api/repoCatalog';

export function rvTooltipText(summary: string | null | undefined): string | null {
	const text = summary?.trim();
	return text ? text : null;
}

export function artifactTooltipText(evidence: ImplementsEvidenceItem): string | null {
	const parts: string[] = [];
	const snippet = evidence.evidence_snippet?.trim();
	const relevance = evidence.evidence_relevance?.trim();
	if (snippet) parts.push(snippet);
	if (relevance) parts.push(relevance);
	return parts.length > 0 ? parts.join('\n\n') : null;
}

/** Gantt requirement segments follow commit_datetime ascending (oldest first). */
export function requirementVersionsChronological(
	tree: RequirementVersionTreeResponse
): RequirementTreeVersion[] {
	return [...tree.versions].sort(
		(a, b) => Date.parse(a.commit_datetime) - Date.parse(b.commit_datetime)
	);
}

function artifactEvidenceKey(filepath: string, commitSha: string): string {
	return `${filepath}\0${commitSha}`;
}

/** Latest evidence per filepath+commit from the version tree (implements links). */
export function artifactEvidenceByCommit(
	tree: RequirementVersionTreeResponse
): Map<string, ImplementsEvidenceItem> {
	const map = new Map<string, ImplementsEvidenceItem>();
	for (const rv of tree.versions) {
		for (const av of rv.artifact_versions) {
			map.set(artifactEvidenceKey(av.filepath, av.commit_sha), av.evidence);
		}
	}
	return map;
}

function segmentStartMs(iso: string): number | null {
	const t = Date.parse(iso);
	return Number.isFinite(t) ? t : null;
}

function requirementVersionForSegmentStart(
	chron: RequirementTreeVersion[],
	segStart: string
): RequirementTreeVersion | undefined {
	const t = segmentStartMs(segStart);
	if (t == null) return undefined;
	return chron.find((rv) => segmentStartMs(rv.commit_datetime) === t);
}

export function requirementSegmentTooltips(
	chart: GanttChartResponse,
	tree: RequirementVersionTreeResponse
): (string | null)[] {
	const chron = requirementVersionsChronological(tree);
	return chart.requirement.history.map((seg) =>
		rvTooltipText(requirementVersionForSegmentStart(chron, seg.start)?.summary)
	);
}

export function artifactSegmentTooltip(
	filepath: string,
	seg: { start: string; commit: string | null },
	tree: RequirementVersionTreeResponse
): string | null {
	const t = segmentStartMs(seg.start);
	if (t != null) {
		for (const rv of tree.versions) {
			for (const av of rv.artifact_versions) {
				if (av.filepath === filepath && segmentStartMs(av.commit_datetime) === t) {
					return artifactTooltipText(av.evidence);
				}
			}
		}
	}
	if (!seg.commit) return null;
	const byCommit = artifactEvidenceByCommit(tree);
	let evidence = byCommit.get(artifactEvidenceKey(filepath, seg.commit));
	if (!evidence) {
		for (const [key, ev] of byCommit) {
			const [fp, sha] = key.split('\0');
			if (fp !== filepath || !sha) continue;
			if (sha.startsWith(seg.commit) || seg.commit.startsWith(sha)) {
				evidence = ev;
				break;
			}
		}
	}
	return evidence ? artifactTooltipText(evidence) : null;
}
