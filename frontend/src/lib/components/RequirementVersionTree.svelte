<script lang="ts">
	import type { RequirementVersionTreeResponse } from '$lib/api/repoCatalog';

	let { tree }: { tree: RequirementVersionTreeResponse } = $props();

	function shortSha(sha: string): string {
		return sha.length > 7 ? sha.slice(0, 7) : sha;
	}

	function formatDt(iso: string): string {
		return new Date(iso).toLocaleString();
	}

	function hasEvidence(
		evidence: RequirementVersionTreeResponse['versions'][0]['artifact_versions'][0]['evidence']
	): boolean {
		return (
			evidence.evidence_file != null ||
			evidence.evidence_snippet != null ||
			evidence.evidence_relevance != null
		);
	}
</script>

<section class="version-tree" aria-label="Requirement version tree">
	<h3 class="tree-title">Versions · {tree.paper_id}</h3>
	{#if tree.versions.length === 0}
		<p class="muted">No requirement versions yet.</p>
	{:else}
		<ul class="tree-root">
			{#each tree.versions as version, vi}
				<li class="tree-node version-node">
					<details class="node-details" open={vi === 0}>
						<summary class="node-summary">
							<span class="node-label">Requirement version</span>
							<code class="mono">{shortSha(version.commit_sha)}</code>
							<span class="node-date">{formatDt(version.commit_datetime)}</span>
							<span class="badge status">{version.status}</span>
							{#if version.implemented === true}
								<span class="badge ok">implemented</span>
							{:else if version.implemented === false}
								<span class="badge warn">not implemented</span>
							{/if}
						</summary>
						<div class="node-body">
							<div class="field">
								<span class="field-label">Requirement text</span>
								<pre class="pre-block">{version.requirement_text}</pre>
							</div>
							{#if version.filepath_globs.length > 0}
								<div class="field inline">
									<span class="field-label">Scope globs</span>
									<span class="field-value">{version.filepath_globs.join(', ')}</span>
								</div>
							{/if}
							{#if version.summary}
								<div class="field">
									<span class="field-label">Evaluation summary</span>
									<p class="field-value">{version.summary}</p>
								</div>
							{/if}
							{#if version.gaps && version.gaps.length > 0}
								<div class="field">
									<span class="field-label">Gaps</span>
									<ul class="gaps">
										{#each version.gaps as gap}
											<li>{gap}</li>
										{/each}
									</ul>
								</div>
							{/if}

							{#if version.artifact_versions.length === 0}
								<p class="muted nested">No linked artifact versions.</p>
							{:else}
								<ul class="tree-children">
									{#each version.artifact_versions as artifact}
										<li class="tree-node artifact-node">
											<details class="node-details">
												<summary class="node-summary sub">
													<span class="node-label">Artifact</span>
													<code class="filepath">{artifact.filepath}</code>
													<code class="mono">{shortSha(artifact.commit_sha)}</code>
													<span class="node-date">{formatDt(artifact.commit_datetime)}</span>
													<span class="badge status">{artifact.status}</span>
												</summary>
												<div class="node-body nested-body">
													{#if hasEvidence(artifact.evidence)}
														<div class="evidence">
															<span class="field-label">Evidence</span>
															{#if artifact.evidence.evidence_file}
																<p class="evidence-line">
																	<span class="dim">file</span>
																	<code>{artifact.evidence.evidence_file}</code>
																	{#if artifact.evidence.evidence_line_number != null}
																		<span class="dim">line {artifact.evidence.evidence_line_number}</span>
																	{/if}
																</p>
															{/if}
															{#if artifact.evidence.evidence_snippet}
																<pre class="pre-block snippet">{artifact.evidence.evidence_snippet}</pre>
															{/if}
															{#if artifact.evidence.evidence_relevance}
																<p class="evidence-relevance">{artifact.evidence.evidence_relevance}</p>
															{/if}
														</div>
													{/if}
													<div class="field">
														<span class="field-label">File content</span>
														<pre class="pre-block content">{artifact.file_content}</pre>
													</div>
												</div>
											</details>
										</li>
									{/each}
								</ul>
							{/if}
						</div>
					</details>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.version-tree {
		margin: 0 0 1.25rem 0;
		min-width: 0;
	}
	.tree-title {
		margin: 0 0 0.65rem 0;
		font-size: 0.82rem;
		font-weight: 600;
		color: #475569;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.tree-root,
	.tree-children {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.tree-root {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
	.tree-children {
		margin: 0.65rem 0 0 0;
		padding-left: 0.85rem;
		border-left: 2px solid #cbd5e1;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.node-details {
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		background: #fafbfc;
		min-width: 0;
	}
	.node-summary {
		cursor: pointer;
		padding: 0.5rem 0.65rem;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem 0.5rem;
		font-size: 0.82rem;
		list-style: none;
	}
	.node-summary::-webkit-details-marker {
		display: none;
	}
	.node-summary.sub {
		font-size: 0.8rem;
		background: #fff;
	}
	.node-label {
		font-weight: 600;
		color: #334155;
	}
	.node-date {
		color: #64748b;
		font-size: 0.78rem;
	}
	.filepath {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.78rem;
		background: #f1f5f9;
		padding: 0.1rem 0.3rem;
		border-radius: 0.2rem;
		word-break: break-all;
	}
	.mono {
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.78rem;
		background: #f1f5f9;
		padding: 0.1rem 0.3rem;
		border-radius: 0.2rem;
	}
	.badge {
		font-size: 0.68rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		padding: 0.12rem 0.35rem;
		border-radius: 0.25rem;
	}
	.badge.status {
		background: #e2e8f0;
		color: #475569;
	}
	.badge.ok {
		background: #dcfce7;
		color: #166534;
	}
	.badge.warn {
		background: #fee2e2;
		color: #991b1b;
	}
	.node-body {
		padding: 0 0.65rem 0.65rem 0.65rem;
		border-top: 1px solid #e2e8f0;
	}
	.nested-body {
		background: #fff;
	}
	.field {
		margin-top: 0.55rem;
	}
	.field.inline {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		align-items: baseline;
	}
	.field-label {
		display: block;
		font-size: 0.72rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		margin-bottom: 0.25rem;
	}
	.field.inline .field-label {
		display: inline;
		margin-bottom: 0;
	}
	.field-value {
		margin: 0;
		font-size: 0.82rem;
		color: #0f172a;
	}
	.pre-block {
		margin: 0;
		padding: 0.45rem 0.5rem;
		background: #fff;
		border: 1px solid #e5e7eb;
		border-radius: 0.35rem;
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 0.76rem;
		line-height: 1.4;
		white-space: pre-wrap;
		word-break: break-word;
		max-height: 12rem;
		overflow: auto;
	}
	.pre-block.content {
		max-height: 10rem;
	}
	.pre-block.snippet {
		max-height: 6rem;
		background: #f8fafc;
	}
	.evidence {
		margin-top: 0.5rem;
		padding: 0.45rem 0.5rem;
		background: #f0f9ff;
		border: 1px solid #bae6fd;
		border-radius: 0.35rem;
	}
	.evidence-line {
		margin: 0.2rem 0 0.35rem 0;
		font-size: 0.8rem;
	}
	.evidence-relevance {
		margin: 0.35rem 0 0 0;
		font-size: 0.8rem;
		color: #334155;
	}
	.dim {
		color: #64748b;
		font-size: 0.75rem;
		margin-right: 0.25rem;
	}
	.gaps {
		margin: 0.2rem 0 0 0;
		padding-left: 1.1rem;
		font-size: 0.82rem;
		color: #0f172a;
	}
	.muted {
		color: #64748b;
		font-size: 0.82rem;
		margin: 0.35rem 0 0 0;
	}
	.muted.nested {
		margin-top: 0.5rem;
	}
</style>
