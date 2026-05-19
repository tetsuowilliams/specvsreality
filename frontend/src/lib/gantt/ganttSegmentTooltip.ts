import type { GanttArtifactBlock, GanttHistorySegment, GanttRequirementBlock } from '$lib/api/repoCatalog';

export type GanttSegmentTooltip = {
	kind: 'requirement' | 'artifact';
	title: string;
	status: string;
	statusLabel: string;
	start: string;
	end: string;
	commit: string | null;
	requirementText: string | null;
	blobSha: string | null;
};

const STATUS_LABELS: Record<string, string> = {
	implemented: 'Implemented',
	not_implemented: 'Not implemented',
	active: 'Present in repo',
	inactive: 'Inactive',
	deleted: 'Removed'
};

export function statusLabel(status: string): string {
	const key = status.toLowerCase();
	return STATUS_LABELS[key] ?? status.replaceAll('_', ' ');
}

function formatWhen(iso: string): string {
	const d = new Date(iso);
	return Number.isFinite(d.getTime())
		? d.toLocaleString(undefined, {
				dateStyle: 'medium',
				timeStyle: 'short'
			})
		: iso;
}

export function buildRequirementSegmentTooltip(
	block: GanttRequirementBlock,
	seg: GanttHistorySegment
): GanttSegmentTooltip {
	return {
		kind: 'requirement',
		title: block.paper_id,
		status: seg.status,
		statusLabel: statusLabel(seg.status),
		start: formatWhen(seg.start),
		end: formatWhen(seg.end),
		commit: seg.commit,
		requirementText: seg.requirement_text,
		blobSha: null
	};
}

export function buildArtifactSegmentTooltip(
	block: GanttArtifactBlock,
	seg: GanttHistorySegment
): GanttSegmentTooltip {
	return {
		kind: 'artifact',
		title: block.filepath,
		status: seg.status,
		statusLabel: statusLabel(seg.status),
		start: formatWhen(seg.start),
		end: formatWhen(seg.end),
		commit: seg.commit,
		requirementText: null,
		blobSha: seg.blob_sha
	};
}
