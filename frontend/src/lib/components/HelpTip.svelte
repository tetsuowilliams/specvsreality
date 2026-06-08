<script lang="ts">
	let {
		label,
		short,
		detail,
		inline = false
	}: {
		label: string;
		short: string;
		detail?: string;
		inline?: boolean;
	} = $props();
</script>

<span class="help-tip" class:inline>
	<span class="help-label">{label}</span>
	<button
		type="button"
		class="help-trigger"
		aria-label="Help: {label}"
		title={[short, detail].filter(Boolean).join('\n\n')}
	>
		?
	</button>
	{#if !inline}
		<span class="help-short">{short}</span>
	{/if}
</span>

<style>
	.help-tip {
		display: inline-flex;
		align-items: flex-start;
		gap: 0.3rem;
	}

	.help-tip.inline {
		align-items: center;
	}

	.help-label {
		font-size: inherit;
		font-weight: inherit;
		color: inherit;
		text-transform: inherit;
		letter-spacing: inherit;
	}

	.help-trigger {
		flex-shrink: 0;
		width: 1rem;
		height: 1rem;
		border: 1px solid #cbd5e1;
		border-radius: 999px;
		background: #f8fafc;
		color: #64748b;
		font-size: 0.62rem;
		font-weight: 700;
		line-height: 1;
		cursor: help;
		padding: 0;
	}

	.help-trigger:hover {
		background: #eff6ff;
		border-color: #93c5fd;
		color: #1d4ed8;
	}

	.help-short {
		display: block;
		width: 100%;
		margin-top: 0.15rem;
		font-size: 0.72rem;
		font-weight: 400;
		color: #64748b;
		line-height: 1.35;
		text-transform: none;
		letter-spacing: normal;
	}
</style>
