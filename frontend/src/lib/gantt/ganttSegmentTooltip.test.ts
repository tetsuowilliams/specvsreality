import { describe, expect, it } from 'vitest';
import { buildRequirementSegmentTooltip, statusLabel } from './ganttSegmentTooltip';

describe('ganttSegmentTooltip', () => {
	it('maps status to readable labels', () => {
		expect(statusLabel('not_implemented')).toBe('Not implemented');
		expect(statusLabel('active')).toBe('Present in repo');
	});

	it('builds requirement tooltip with text and formatted dates', () => {
		const tip = buildRequirementSegmentTooltip(
			{ paper_id: 'REQ-1', history: [] },
			{
				start: '2024-01-01T12:00:00.000Z',
				end: '2024-02-01T12:00:00.000Z',
				status: 'implemented',
				commit: 'a'.repeat(40),
				requirement_text: 'Do the thing',
				blob_sha: null
			}
		);
		expect(tip.kind).toBe('requirement');
		expect(tip.title).toBe('REQ-1');
		expect(tip.requirementText).toBe('Do the thing');
		expect(tip.start).toContain('2024');
	});
});
