<script lang="ts">
	import { marked } from 'marked';
	import type { SpecDocument, SpecViewItem } from '$lib/api/repoCatalog';
	import { applyHighlights } from '$lib/spec/applyHighlights';
	let {
		markdown,
		document,
		items,
		onItemClick
	}: {
		markdown: string;
		document: SpecDocument;
		items: SpecViewItem[];
		onItemClick: (itemId: number) => void;
	} = $props();

	const html = $derived.by(() => {
		const withHighlights = applyHighlights(markdown, items, document);
		return marked.parse(withHighlights, { async: false, gfm: true }) as string;
	});

	function handleClick(event: MouseEvent) {
		const target = (event.target as HTMLElement | null)?.closest?.(
			'mark.spec-highlight'
		) as HTMLElement | null;
		if (!target) return;
		const itemId = Number(target.dataset.itemId);
		if (!Number.isFinite(itemId)) return;
		onItemClick(itemId);
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="markdown-body" onclick={handleClick}>
	{@html html}
</div>

<style>
	.markdown-body {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
		font-size: 14px;
		line-height: 1.6;
		color: #24292f;
		word-wrap: break-word;
	}

	.markdown-body :global(h1),
	.markdown-body :global(h2),
	.markdown-body :global(h3),
	.markdown-body :global(h4) {
		margin-top: 1.25em;
		margin-bottom: 0.6em;
		font-weight: 600;
		line-height: 1.25;
		color: #1f2328;
	}

	.markdown-body :global(h1) {
		font-size: 2em;
		padding-bottom: 0.3em;
		border-bottom: 1px solid #d8dee4;
	}
	.markdown-body :global(h2) {
		font-size: 1.5em;
		padding-bottom: 0.25em;
		border-bottom: 1px solid #d8dee4;
	}
	.markdown-body :global(h3) {
		font-size: 1.25em;
	}
	.markdown-body :global(h4) {
		font-size: 1em;
	}

	.markdown-body :global(p),
	.markdown-body :global(ul),
	.markdown-body :global(ol),
	.markdown-body :global(blockquote),
	.markdown-body :global(pre) {
		margin-top: 0;
		margin-bottom: 1em;
	}

	.markdown-body :global(ul),
	.markdown-body :global(ol) {
		padding-left: 2em;
	}

	.markdown-body :global(li + li) {
		margin-top: 0.25em;
	}

	.markdown-body :global(blockquote) {
		padding: 0 1em;
		color: #57606a;
		border-left: 0.25em solid #d0d7de;
	}

	.markdown-body :global(code) {
		padding: 0.2em 0.4em;
		margin: 0;
		font-size: 85%;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		background-color: #f6f8fa;
		border-radius: 6px;
	}

	.markdown-body :global(pre) {
		padding: 16px;
		overflow: auto;
		font-size: 85%;
		line-height: 1.45;
		background-color: #f6f8fa;
		border-radius: 6px;
	}

	.markdown-body :global(pre code) {
		padding: 0;
		background: transparent;
	}

	.markdown-body :global(table) {
		border-spacing: 0;
		border-collapse: collapse;
		width: 100%;
		margin-bottom: 1em;
	}

	.markdown-body :global(th),
	.markdown-body :global(td) {
		padding: 6px 13px;
		border: 1px solid #d0d7de;
	}

	.markdown-body :global(tr:nth-child(2n)) {
		background-color: #f6f8fa;
	}

	.markdown-body :global(hr) {
		height: 0.25em;
		padding: 0;
		margin: 1.5em 0;
		background-color: #d8dee4;
		border: 0;
	}

	.markdown-body :global(mark.spec-highlight) {
		cursor: pointer;
		border-radius: 3px;
		padding: 0.05em 0;
		transition:
			box-shadow 0.15s ease,
			filter 0.15s ease;
	}

	.markdown-body :global(mark.spec-highlight:hover) {
		filter: brightness(0.97);
		box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
	}

	.markdown-body :global(mark.spec-highlight[data-item-type='functional_behavior']) {
		background-color: #dbeafe;
		box-shadow: inset 0 -2px 0 #93c5fd;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='input_rule']) {
		background-color: #e0e7ff;
		box-shadow: inset 0 -2px 0 #a5b4fc;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='output_rule']) {
		background-color: #ede9fe;
		box-shadow: inset 0 -2px 0 #c4b5fd;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='error_handling']) {
		background-color: #fee2e2;
		box-shadow: inset 0 -2px 0 #fca5a5;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='edge_case']) {
		background-color: #ffedd5;
		box-shadow: inset 0 -2px 0 #fdba74;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='exclusion']) {
		background-color: #f3f4f6;
		box-shadow: inset 0 -2px 0 #d1d5db;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='non_functional_constraint']) {
		background-color: #fce7f3;
		box-shadow: inset 0 -2px 0 #f9a8d4;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='acceptance_scenario']) {
		background-color: #d1fae5;
		box-shadow: inset 0 -2px 0 #6ee7b7;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='context']) {
		background-color: #f1f5f9;
		box-shadow: inset 0 -2px 0 #cbd5e1;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='task']) {
		background-color: #fef3c7;
		box-shadow: inset 0 -2px 0 #fcd34d;
	}
	.markdown-body :global(mark.spec-highlight[data-item-type='design_note']) {
		background-color: #e0f2fe;
		box-shadow: inset 0 -2px 0 #7dd3fc;
	}
</style>
