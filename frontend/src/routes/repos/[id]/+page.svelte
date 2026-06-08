<script lang="ts">
	import RepoDashboard from '$lib/components/RepoDashboard.svelte';

	let { data }: { data: { id: string } } = $props();
</script>

<RepoDashboard repoId={data.id} />
