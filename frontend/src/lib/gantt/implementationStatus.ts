/** Display status aligned with gantt segment colors (mapGanttApiToSvelteGantt). */

export type ImplementationDisplayStatus =
	| 'implemented'
	| 'not_implemented'
	| 'unevaluated'
	| 'no_version';

export type ImplementationStatusTheme = {
	label: string;
	/** KPI / accent (gantt green) */
	accent: string;
	accentMuted: string;
	pillBg: string;
	pillFg: string;
	rowBg: string;
	rowBorder: string;
};

export const IMPLEMENTATION_STATUS_THEMES: Record<ImplementationDisplayStatus, ImplementationStatusTheme> =
	{
		implemented: {
			label: 'Implemented',
			accent: '#16a34a',
			accentMuted: '#dcfce7',
			pillBg: '#bbf7d0',
			pillFg: '#14532d',
			rowBg: '#f0fdf4',
			rowBorder: '#86efac'
		},
		not_implemented: {
			label: 'Not implemented',
			accent: '#d97706',
			accentMuted: '#fef3c7',
			pillBg: '#fde68a',
			pillFg: '#78350f',
			rowBg: '#fffbeb',
			rowBorder: '#fcd34d'
		},
		unevaluated: {
			label: 'Not evaluated',
			accent: '#64748b',
			accentMuted: '#f1f5f9',
			pillBg: '#e2e8f0',
			pillFg: '#334155',
			rowBg: '#f8fafc',
			rowBorder: '#cbd5e1'
		},
		no_version: {
			label: 'No version yet',
			accent: '#94a3b8',
			accentMuted: '#f8fafc',
			pillBg: '#f1f5f9',
			pillFg: '#64748b',
			rowBg: '#ffffff',
			rowBorder: '#e2e8f0'
		}
	};

export function resolveImplementationStatus(
	implemented: boolean | null | undefined,
	hasVersion: boolean
): ImplementationDisplayStatus {
	if (!hasVersion) return 'no_version';
	if (implemented === true) return 'implemented';
	if (implemented === false) return 'not_implemented';
	return 'unevaluated';
}

export function implementationStatusLabel(status: ImplementationDisplayStatus): string {
	return IMPLEMENTATION_STATUS_THEMES[status].label;
}

export function countByStatus(
	requirements: { implemented: boolean | null; has_version: boolean }[]
): Record<ImplementationDisplayStatus, number> {
	const counts: Record<ImplementationDisplayStatus, number> = {
		implemented: 0,
		not_implemented: 0,
		unevaluated: 0,
		no_version: 0
	};
	for (const req of requirements) {
		counts[resolveImplementationStatus(req.implemented, req.has_version)] += 1;
	}
	return counts;
}
