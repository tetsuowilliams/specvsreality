<script lang="ts">
	let { data }: { data: { id: string } } = $props();
</script>

<section class="placeholder">
	<h2>Repository workspace</h2>
	<p>Select a <strong>spec</strong> or <strong>requirement</strong> in the catalog to view details or the Gantt chart.</p>
	<p class="hint">Repo id: <code>{data.id}</code></p>
</section>

<style>
	.placeholder h2 {
		margin: 0 0 0.5rem 0;
		font-size: 1.15rem;
		color: #0f172a;
	}
	.placeholder p {
		margin: 0.35rem 0;
		color: #475569;
		font-size: 0.92rem;
		line-height: 1.45;
	}
	.hint {
		font-size: 0.85rem;
		color: #64748b;
	}
	code {
		background: #f1f5f9;
		padding: 0.1rem 0.35rem;
		border-radius: 0.25rem;
	}
</style>
