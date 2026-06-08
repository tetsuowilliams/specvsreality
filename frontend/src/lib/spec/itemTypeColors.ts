/** Pastel highlight colors per spec item type. */
export const ITEM_TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
	functional_behavior: { bg: '#dbeafe', border: '#93c5fd', text: '#1e3a8a' },
	input_rule: { bg: '#e0e7ff', border: '#a5b4fc', text: '#312e81' },
	output_rule: { bg: '#ede9fe', border: '#c4b5fd', text: '#4c1d95' },
	error_handling: { bg: '#fee2e2', border: '#fca5a5', text: '#991b1b' },
	edge_case: { bg: '#ffedd5', border: '#fdba74', text: '#9a3412' },
	exclusion: { bg: '#f3f4f6', border: '#d1d5db', text: '#374151' },
	non_functional_constraint: { bg: '#fce7f3', border: '#f9a8d4', text: '#9d174d' },
	acceptance_scenario: { bg: '#d1fae5', border: '#6ee7b7', text: '#065f46' },
	context: { bg: '#f1f5f9', border: '#cbd5e1', text: '#334155' },
	task: { bg: '#fef3c7', border: '#fcd34d', text: '#92400e' },
	design_note: { bg: '#e0f2fe', border: '#7dd3fc', text: '#0c4a6e' }
};

export function itemTypeColor(itemType: string) {
	return (
		ITEM_TYPE_COLORS[itemType] ?? {
			bg: '#f1f5f9',
			border: '#cbd5e1',
			text: '#334155'
		}
	);
}
