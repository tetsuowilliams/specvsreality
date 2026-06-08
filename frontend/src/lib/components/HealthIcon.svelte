<script lang="ts">
	let { status }: { status: 'good' | 'at_risk' | 'unknown' | string } = $props();
</script>

<span class="health-icon {status}" aria-hidden="true">
	{#if status === 'good'}
		<svg viewBox="0 0 16 16" fill="none">
			<circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.25" />
			<path
				d="M4.5 8.2 6.8 10.5 11.5 5.8"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
				stroke-linejoin="round"
			/>
		</svg>
	{:else if status === 'at_risk'}
		<svg viewBox="0 0 16 16" fill="none">
			<circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.25" />
			<path
				d="M5.5 5.5 10.5 10.5M10.5 5.5 5.5 10.5"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linecap="round"
			/>
		</svg>
	{:else}
		<svg viewBox="0 0 16 16" fill="none">
			<circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.25" />
			<path d="M5 8h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
		</svg>
	{/if}
</span>

<style>
	.health-icon {
		display: inline-flex;
		width: 1rem;
		height: 1rem;
		flex-shrink: 0;
	}

	svg {
		width: 100%;
		height: 100%;
	}

	.good {
		color: #16a34a;
	}

	.at_risk {
		color: #dc2626;
	}

	.unknown {
		color: #94a3b8;
	}
</style>
