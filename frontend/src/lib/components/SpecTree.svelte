<script lang="ts">
	import type { SpecTreeResponse } from '$lib/api/repoCatalog';

	let { tree }: { tree: SpecTreeResponse } = $props();

	function shortSha(sha: string): string {
		return sha.slice(0, 7);
	}

	function formatConfidence(confidence: number | null): string {
		if (confidence === null || confidence === undefined) return '—';
		return `${Math.round(confidence * 100)}%`;
	}
</script>

<div class="spec-tree">
	{#if tree.versions.length === 0}
		<p class="muted">No spec versions extracted yet.</p>
	{/if}

	{#each tree.versions as version, vi (version.id)}
		<details class="version" open={vi === tree.versions.length - 1}>
			<summary>
				<span class="version-title">{version.title ?? `Version #${version.id}`}</span>
				<span class="commit">{shortSha(version.commit_sha)}</span>
			</summary>

			{#if version.summary}
				<p class="summary">{version.summary}</p>
			{/if}
			<p class="commit-msg">{version.commit_message}</p>

			{#if version.items.length === 0}
				<p class="muted">No spec items in this version.</p>
			{:else}
				<ul class="items">
					{#each version.items as item (item.id)}
						<li class="item">
							<div class="item-head">
								<span class="key">{item.local_key}</span>
								<span class="badge type">{item.item_type}</span>
								<span class="badge importance importance-{item.importance}">{item.importance}</span>
							</div>
							<p class="item-text">{item.text}</p>

							{#if item.success_criteria.length > 0}
								<div class="criteria">
									<span class="criteria-label success">Success</span>
									<ul>
										{#each item.success_criteria as c}<li>{c}</li>{/each}
									</ul>
								</div>
							{/if}
							{#if item.failure_criteria.length > 0}
								<div class="criteria">
									<span class="criteria-label failure">Failure</span>
									<ul>
										{#each item.failure_criteria as c}<li>{c}</li>{/each}
									</ul>
								</div>
							{/if}

							{#if item.implementations.length === 0}
								<p class="muted small">Not yet evaluated.</p>
							{:else}
								<div class="impls">
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
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</details>
	{/each}
</div>

<style>
	.spec-tree {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
	}
	.version {
		border: 1px solid #e2e8f0;
		border-radius: 0.6rem;
		padding: 0.5rem 0.7rem;
		background: #fafafa;
	}
	.version summary {
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-weight: 600;
		color: #0f172a;
	}
	.version-title {
		flex: 1;
	}
	.commit {
		font-family: ui-monospace, monospace;
		font-size: 0.72rem;
		color: #64748b;
		background: #e2e8f0;
		padding: 0.05rem 0.35rem;
		border-radius: 0.3rem;
	}
	.summary {
		margin: 0.5rem 0 0.2rem 0;
		font-size: 0.85rem;
		color: #334155;
	}
	.commit-msg {
		margin: 0 0 0.5rem 0;
		font-size: 0.78rem;
		color: #64748b;
	}
	.items {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.item {
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		padding: 0.5rem 0.6rem;
		background: #fff;
	}
	.item-head {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
	}
	.key {
		font-family: ui-monospace, monospace;
		font-weight: 700;
		font-size: 0.8rem;
		color: #0f172a;
	}
	.badge {
		font-size: 0.68rem;
		padding: 0.05rem 0.4rem;
		border-radius: 0.3rem;
		text-transform: lowercase;
	}
	.badge.type {
		background: #e0e7ff;
		color: #3730a3;
	}
	.importance {
		background: #f1f5f9;
		color: #475569;
	}
	.importance-must {
		background: #fee2e2;
		color: #991b1b;
	}
	.importance-should {
		background: #fef3c7;
		color: #92400e;
	}
	.item-text {
		margin: 0.35rem 0;
		font-size: 0.85rem;
		color: #1e293b;
	}
	.criteria {
		display: flex;
		gap: 0.4rem;
		margin: 0.2rem 0;
		font-size: 0.78rem;
	}
	.criteria-label {
		font-weight: 600;
		flex-shrink: 0;
	}
	.criteria-label.success {
		color: #15803d;
	}
	.criteria-label.failure {
		color: #b91c1c;
	}
	.criteria ul {
		margin: 0;
		padding-left: 1rem;
		color: #475569;
	}
	.impls {
		margin-top: 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.impl {
		border-left: 3px solid #cbd5e1;
		padding: 0.3rem 0.5rem;
		background: #f8fafc;
		border-radius: 0.3rem;
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
	.confidence {
		color: #64748b;
	}
	.impl-summary {
		margin: 0.25rem 0;
		font-size: 0.8rem;
		color: #334155;
	}
	.gaps {
		margin: 0.2rem 0;
		padding-left: 1rem;
		font-size: 0.78rem;
		color: #b45309;
	}
	.artifacts {
		list-style: none;
		padding: 0;
		margin: 0.3rem 0 0 0;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.artifact {
		font-size: 0.78rem;
	}
	.filepath {
		font-family: ui-monospace, monospace;
		color: #0f172a;
	}
	.line {
		color: #64748b;
		font-family: ui-monospace, monospace;
	}
	.snippet {
		margin: 0.2rem 0;
		padding: 0.35rem 0.5rem;
		background: #0f172a;
		color: #e2e8f0;
		border-radius: 0.3rem;
		font-size: 0.72rem;
		overflow: auto;
		white-space: pre-wrap;
		word-break: break-word;
	}
	.relevance {
		margin: 0.15rem 0;
		color: #475569;
	}
	.muted {
		color: #64748b;
		font-size: 0.85rem;
	}
	.muted.small {
		font-size: 0.78rem;
		margin: 0.3rem 0 0 0;
	}
</style>
