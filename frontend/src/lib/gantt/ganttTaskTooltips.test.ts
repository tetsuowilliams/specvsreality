import { describe, expect, it } from 'vitest';
import {
	artifactEvidenceByCommit,
	artifactSegmentTooltip,
	artifactTooltipText,
	requirementSegmentTooltips,
	requirementVersionsChronological
} from './ganttTaskTooltips';
import { mapGanttApiToRowsAndTasks } from './mapGanttApiToSvelteGantt';
import type { GanttChartResponse, RequirementVersionTreeResponse } from '$lib/api/repoCatalog';

const t0 = '2024-01-01T00:00:00.000Z';
const t1 = '2024-01-02T00:00:00.000Z';

describe('ganttTaskTooltips', () => {
	it('orders requirement versions chronologically for segment alignment', () => {
		const tree: RequirementVersionTreeResponse = {
			paper_id: 'R1',
			versions: [
				{
					id: 2,
					commit_sha: 'bbb',
					commit_datetime: t1,
					requirement_text: 'new',
					filepath_globs: [],
					status: 'active',
					implemented: false,
					summary: 'newer eval',
					gaps: null,
					artifact_versions: []
				},
				{
					id: 1,
					commit_sha: 'aaa',
					commit_datetime: t0,
					requirement_text: 'old',
					filepath_globs: [],
					status: 'active',
					implemented: true,
					summary: 'older eval',
					gaps: null,
					artifact_versions: []
				}
			]
		};
		expect(requirementVersionsChronological(tree).map((v) => v.summary)).toEqual([
			'older eval',
			'newer eval'
		]);
	});

	it('maps requirement segment tooltips by chronological index', () => {
		const chart: GanttChartResponse = {
			meta: { requirement_implemented: false },
			requirement: {
				paper_id: 'R1',
				history: [
					{ start: t0, end: t1, status: 'implemented', commit: null },
					{ start: t1, end: t1, status: 'not_implemented', commit: null }
				]
			},
			artifacts: []
		};
		const tree: RequirementVersionTreeResponse = {
			paper_id: 'R1',
			versions: [
				{
					id: 2,
					commit_sha: 'bbb',
					commit_datetime: t1,
					requirement_text: 'n',
					filepath_globs: [],
					status: 'active',
					implemented: false,
					summary: 'second summary',
					gaps: null,
					artifact_versions: []
				},
				{
					id: 1,
					commit_sha: 'aaa',
					commit_datetime: t0,
					requirement_text: 'o',
					filepath_globs: [],
					status: 'active',
					implemented: true,
					summary: 'first summary',
					gaps: null,
					artifact_versions: []
				}
			]
		};
		expect(requirementSegmentTooltips(chart, tree)).toEqual(['first summary', 'second summary']);
	});

	it('builds artifact tooltips from snippet and relevance', () => {
		const text = artifactTooltipText({
			evidence_file: 'f.ts',
			evidence_line_number: 1,
			evidence_snippet: 'const x = 1;',
			evidence_relevance: 'Defines constant.'
		});
		expect(text).toBe('const x = 1;\n\nDefines constant.');
	});

	it('resolves artifact segment tooltip by filepath and commit', () => {
		const chart: GanttChartResponse = {
			meta: { requirement_implemented: true },
			requirement: { paper_id: 'R', history: [] },
			artifacts: [
				{
					filepath: 'src/a.ts',
					history: [{ start: t0, end: t1, status: 'implemented', commit: 'sha1' }]
				}
			]
		};
		const tree: RequirementVersionTreeResponse = {
			paper_id: 'R',
			versions: [
				{
					id: 1,
					commit_sha: 'rv1',
					commit_datetime: t0,
					requirement_text: 't',
					filepath_globs: [],
					status: 'active',
					implemented: true,
					summary: null,
					gaps: null,
					artifact_versions: [
						{
							artifact_version_id: 10,
							filepath: 'src/a.ts',
							commit_sha: 'sha1',
							commit_datetime: t0,
							status: 'active',
							file_content: '',
							evidence: {
								evidence_file: null,
								evidence_line_number: null,
								evidence_snippet: 'snippet here',
								evidence_relevance: null
							}
						}
					]
				}
			]
		};
		const { tasks } = mapGanttApiToRowsAndTasks(chart, tree);
		expect(tasks[0]?.tooltip).toBe('snippet here');
		expect(
			artifactSegmentTooltip('src/a.ts', { start: t0, commit: 'sha1' }, tree)
		).toBe('snippet here');
	});
});
