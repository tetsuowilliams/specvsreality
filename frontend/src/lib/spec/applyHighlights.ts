import type { SpecDocument, SpecViewItem } from '$lib/api/repoCatalog';

/** Insert highlight markup into raw markdown at API-provided character spans. */
export function applyHighlights(
	markdown: string,
	items: SpecViewItem[],
	document: SpecDocument
): string {
	const highlighted = items
		.filter((item) => item.spans[document] != null)
		.sort((a, b) => b.spans[document]!.start - a.spans[document]!.start);

	let result = markdown;
	for (const item of highlighted) {
		const span = item.spans[document]!;
		const { start, end } = span;
		if (start < 0 || end > result.length || start >= end) continue;
		const inner = result.slice(start, end);
		const mark = `<mark class="spec-highlight" data-item-id="${item.id}" data-item-type="${item.item_type}" title="${item.local_key}">${inner}</mark>`;
		result = result.slice(0, start) + mark + result.slice(end);
	}
	return result;
}
