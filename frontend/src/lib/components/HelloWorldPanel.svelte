<script lang="ts">
	import { postHelloWorld } from '$lib/api/helloWorld';

	type Status = 'idle' | 'loading' | 'ok' | 'error';

	let status = $state<Status>('idle');
	let message = $state<string | null>(null);

	async function sendHello() {
		status = 'loading';
		message = null;
		try {
			const r = await postHelloWorld('World');
			status = 'ok';
			message = r.queued ? 'Message queued for the worker.' : 'Sent.';
		} catch (e) {
			status = 'error';
			message = e instanceof Error ? e.message : 'Request failed';
		}
	}
</script>

<section class="panel">
	<h1>Spec vs Reality</h1>
	<p class="lede">Smoke-test the API → RabbitMQ → worker pipeline.</p>
	<button type="button" class="primary" onclick={sendHello} disabled={status === 'loading'}>
		{status === 'loading' ? 'Sending…' : 'Send hello world'}
	</button>
	{#if message}
		<p class="status" data-testid="status" data-variant={status}>{message}</p>
	{/if}
</section>

<style>
	.panel {
		max-width: 36rem;
		margin: 3rem auto;
		padding: 0 1.25rem;
		font-family:
			system-ui,
			-apple-system,
			'Segoe UI',
			sans-serif;
	}
	h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin: 0 0 0.5rem;
		letter-spacing: -0.02em;
	}
	.lede {
		color: #444;
		margin: 0 0 1.5rem;
		line-height: 1.5;
	}
	.primary {
		cursor: pointer;
		border: none;
		border-radius: 0.5rem;
		padding: 0.65rem 1.25rem;
		font-size: 1rem;
		font-weight: 500;
		color: #fff;
		background: #1a1a2e;
	}
	.primary:hover:not(:disabled) {
		background: #2d2d44;
	}
	.primary:disabled {
		opacity: 0.65;
		cursor: not-allowed;
	}
	.status {
		margin-top: 1rem;
		line-height: 1.4;
	}
	.status[data-variant='ok'] {
		color: #0d5c2e;
	}
	.status[data-variant='error'] {
		color: #9a1c1c;
	}
</style>
