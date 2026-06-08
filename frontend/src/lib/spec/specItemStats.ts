import type { SpecTreeImplementation, SpecViewItem } from '$lib/api/repoCatalog';

const LOW_CONFIDENCE_THRESHOLD = 0.7;
const TRACKED_IMPORTANCE = new Set(['must', 'should']);

export function latestImplementation(item: SpecViewItem): SpecTreeImplementation | null {
	if (!item.implementations.length) return null;
	return [...item.implementations].sort(
		(a, b) => new Date(b.committed_at).getTime() - new Date(a.committed_at).getTime()
	)[0];
}

export function isTrackedItem(item: SpecViewItem): boolean {
	return TRACKED_IMPORTANCE.has(item.importance);
}

export function isLowConfidence(confidence: number | null): boolean {
	return confidence !== null && confidence < LOW_CONFIDENCE_THRESHOLD;
}

export type SpecItemAttention = {
	item: SpecViewItem;
	latest: SpecTreeImplementation | null;
	kind: 'mandatory_gap' | 'low_confidence' | 'unevaluated';
};

export function attentionItems(items: SpecViewItem[]): SpecItemAttention[] {
	const result: SpecItemAttention[] = [];

	for (const item of items) {
		if (!isTrackedItem(item)) continue;
		const latest = latestImplementation(item);
		if (!latest) {
			result.push({ item, latest: null, kind: 'unevaluated' });
			continue;
		}
		if (!latest.implemented && item.importance === 'must') {
			result.push({ item, latest, kind: 'mandatory_gap' });
			continue;
		}
		if (isLowConfidence(latest.confidence)) {
			result.push({ item, latest, kind: 'low_confidence' });
		}
	}

	const order = { mandatory_gap: 0, low_confidence: 1, unevaluated: 2 };
	return result.sort((a, b) => order[a.kind] - order[b.kind]);
}
