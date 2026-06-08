<script lang="ts">
	import type { MetricHelp } from '$lib/dashboard/metrics';

	let {
		metric,
		value,
		warn = false,
		mono = false
	}: {
		metric: MetricHelp;
		value: string | number;
		warn?: boolean;
		mono?: boolean;
	} = $props();
</script>

<article class="card" title={metric.detail}>
	<span class="label">{metric.label}</span>
	<span class="short">{metric.short}</span>
	<strong class="value" class:warn class:mono>{value}</strong>
</article>

<style>
	.card {
		background: #fff;
		border: 1px solid #e2e8f0;
		border-radius: 0.65rem;
		padding: 0.75rem 0.85rem;
		display: grid;
		gap: 0.2rem;
	}

	.label {
		font-size: 0.72rem;
		font-weight: 600;
		color: #64748b;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.short {
		font-size: 0.72rem;
		font-weight: 400;
		color: #94a3b8;
		line-height: 1.35;
	}

	.value {
		font-size: 1.2rem;
		font-weight: 700;
		color: #0f172a;
	}

	.value.warn {
		color: #b45309;
	}

	.value.mono {
		font-family: ui-monospace, monospace;
		font-size: 1rem;
	}
</style>
