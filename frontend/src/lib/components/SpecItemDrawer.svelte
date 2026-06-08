<script lang="ts">
	import type { SpecViewItem } from '$lib/api/repoCatalog';
	import { itemTypeColor } from '$lib/spec/itemTypeColors';

	let {
		item,
		open,
		onClose
	}: {
		item: SpecViewItem | null;
		open: boolean;
		onClose: () => void;
	} = $props();

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function formatConfidence(confidence: number | null): string {
		if (confidence === null || confidence === undefined) return '—';
		return `${Math.round(confidence * 100)}%`;
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) onClose();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && open) onClose();
	}

	let active = $state(false);

	$effect(() => {
		if (open && item) {
			requestAnimationFrame(() => {
				active = true;
			});
		} else {
			active = false;
		}
	});
</script>

<svelte:window onkeydown={handleKeydown} />

{#if item}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="backdrop" class:visible={active} onclick={handleBackdropClick}>
		<aside
			class="drawer"
			class:open={active}
			aria-label="Spec item details"
			aria-hidden={!active}
		>
			<header class="drawer-header">
				<div class="title-row">
					<span class="key">{item.local_key}</span>
					<span
						class="badge type"
						style:background={itemTypeColor(item.item_type).bg}
						style:color={itemTypeColor(item.item_type).text}
						style:border-color={itemTypeColor(item.item_type).border}
					>
						{item.item_type.replaceAll('_', ' ')}
					</span>
					<span class="badge importance importance-{item.importance}">{item.importance}</span>
				</div>
				<button type="button" class="close-btn" onclick={onClose} aria-label="Close">×</button>
			</header>

			<div class="drawer-body">
				<section>
					<h3>Requirement</h3>
					<p>{item.text}</p>
				</section>

				{#if item.source_quote}
					<section>
						<h3>Source quote</h3>
						<blockquote>{item.source_quote}</blockquote>
					</section>
				{/if}

				{#if item.success_criteria.length > 0}
					<section>
						<h3>Success criteria</h3>
						<ul>
							{#each item.success_criteria as criterion}<li>{criterion}</li>{/each}
						</ul>
					</section>
				{/if}

				{#if item.failure_criteria.length > 0}
					<section>
						<h3>Failure criteria</h3>
						<ul class="failure">
							{#each item.failure_criteria as criterion}<li>{criterion}</li>{/each}
						</ul>
					</section>
				{/if}

				<section>
					<h3>Implementation</h3>
					{#if item.implementations.length === 0}
						<p class="muted">Not yet evaluated.</p>
					{:else}
						{#each item.implementations as impl (impl.id)}
							<div class="impl" class:implemented={impl.implemented}>
								<div class="impl-head">
									<span class="status">
										{impl.implemented ? 'Implemented' : 'Not implemented'}
									</span>
									<span class="confidence">conf {formatConfidence(impl.confidence)}</span>
									<span class="commit">{shortSha(impl.commit_sha)}</span>
								</div>
								{#if impl.summary}
									<p class="impl-summary">{impl.summary}</p>
								{/if}
								{#if impl.gaps.length > 0}
									<ul class="gaps">
										{#each impl.gaps as gap}<li>{gap}</li>{/each}
									</ul>
								{/if}
								{#if impl.artifacts.length > 0}
									<ul class="artifacts">
										{#each impl.artifacts as artifact (artifact.artifact_version_id)}
											<li class="artifact">
												<code class="filepath">{artifact.filepath}</code>
												{#if artifact.evidence_line_number !== null}
													<span class="line">:{artifact.evidence_line_number}</span>
												{/if}
												{#if artifact.evidence_snippet}
													<pre class="snippet">{artifact.evidence_snippet}</pre>
												{/if}
												{#if artifact.evidence_relevance}
													<p class="relevance">{artifact.evidence_relevance}</p>
												{/if}
											</li>
										{/each}
									</ul>
								{/if}
							</div>
						{/each}
					{/if}
				</section>
			</div>
		</aside>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 50;
		background: rgba(15, 23, 42, 0.3);
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.3s ease;
	}

	.backdrop.visible {
		opacity: 1;
		pointer-events: auto;
	}

	.drawer {
		position: fixed;
		top: 0;
		right: 0;
		height: 100%;
		width: min(44rem, 58vw);
		max-width: 100%;
		background: #fff;
		box-shadow: -16px 0 48px rgba(15, 23, 42, 0.16);
		transform: translateX(100%);
		transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
		display: flex;
		flex-direction: column;
		will-change: transform;
	}

	.drawer.open {
		transform: translateX(0);
	}

	@media (max-width: 768px) {
		.drawer {
			width: 100%;
		}
	}

	.drawer-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 1rem 1.1rem;
		border-bottom: 1px solid #e2e8f0;
		background: #f8fafc;
	}

	.title-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem;
	}

	.key {
		font-family: ui-monospace, monospace;
		font-weight: 700;
		font-size: 0.9rem;
		color: #0f172a;
	}

	.badge {
		font-size: 0.68rem;
		padding: 0.1rem 0.45rem;
		border-radius: 0.35rem;
		border: 1px solid transparent;
		text-transform: lowercase;
	}

	.importance-must {
		background: #fee2e2;
		color: #991b1b;
	}
	.importance-should {
		background: #fef3c7;
		color: #92400e;
	}

	.close-btn {
		border: none;
		background: transparent;
		font-size: 1.5rem;
		line-height: 1;
		color: #64748b;
		cursor: pointer;
		padding: 0.1rem 0.35rem;
		border-radius: 0.35rem;
	}

	.close-btn:hover {
		background: #e2e8f0;
		color: #0f172a;
	}

	.drawer-body {
		overflow: auto;
		padding: 1.15rem 1.5rem 1.75rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.drawer-body h3 {
		margin: 0 0 0.35rem 0;
		font-size: 0.78rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #64748b;
	}

	.drawer-body p {
		margin: 0;
		font-size: 0.9rem;
		color: #1e293b;
		line-height: 1.5;
	}

	blockquote {
		margin: 0;
		padding: 0.5rem 0.75rem;
		border-left: 3px solid #cbd5e1;
		background: #f8fafc;
		color: #475569;
		font-size: 0.85rem;
	}

	ul {
		margin: 0;
		padding-left: 1.1rem;
		font-size: 0.85rem;
		color: #334155;
	}

	.failure {
		color: #b91c1c;
	}

	.impl {
		border-left: 3px solid #cbd5e1;
		padding: 0.45rem 0.6rem;
		background: #f8fafc;
		border-radius: 0.35rem;
		margin-top: 0.4rem;
	}

	.impl.implemented {
		border-left-color: #16a34a;
	}

	.impl-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.78rem;
	}

	.status {
		font-weight: 600;
		color: #334155;
	}

	.impl.implemented .status {
		color: #15803d;
	}

	.confidence,
	.commit {
		color: #64748b;
		font-family: ui-monospace, monospace;
	}

	.impl-summary {
		margin-top: 0.3rem;
	}

	.gaps {
		color: #b45309;
	}

	.artifacts {
		list-style: none;
		padding: 0;
		margin-top: 0.35rem;
	}

	.filepath {
		font-family: ui-monospace, monospace;
		font-size: 0.78rem;
	}

	.line {
		color: #64748b;
		font-family: ui-monospace, monospace;
	}

	.snippet {
		margin: 0.25rem 0;
		padding: 0.4rem 0.55rem;
		background: #0f172a;
		color: #e2e8f0;
		border-radius: 0.35rem;
		font-size: 0.72rem;
		overflow: auto;
		white-space: pre-wrap;
	}

	.relevance {
		font-size: 0.78rem;
		color: #475569;
	}

	.muted {
		color: #64748b;
		font-size: 0.85rem;
	}
</style>
