<script lang="ts">
	import { createRepo, listRepos, type Repo } from '$lib/api/repos';

	type Status = 'idle' | 'loading' | 'ok' | 'error';

	let name = $state('');
	let url = $state('');
	let repos = $state<Repo[]>([]);
	let loadingRepos = $state(true);
	let status = $state<Status>('idle');
	let message = $state<string | null>(null);

	async function refreshRepos() {
		loadingRepos = true;
		try {
			repos = await listRepos();
		} finally {
			loadingRepos = false;
		}
	}

	async function submit() {
		status = 'loading';
		message = null;
		try {
			await createRepo(name.trim(), url.trim());
			name = '';
			url = '';
			status = 'ok';
			message = 'Repo queued for scanning.';
			await refreshRepos();
		} catch (e) {
			status = 'error';
			message = e instanceof Error ? e.message : 'Request failed';
		}
	}

	function onSubmit(event: SubmitEvent) {
		event.preventDefault();
		void submit();
	}

	$effect(() => {
		void refreshRepos();
	});
</script>

<section class="panel">
	<h1>Tracked Repositories</h1>
	<p class="subtitle">Connect repositories and monitor scan progress in one place.</p>
	<form class="form" onsubmit={onSubmit}>
		<label>
			Name
			<input bind:value={name} required minlength="1" maxlength="255" />
		</label>
		<label>
			Git URL
			<input bind:value={url} required minlength="1" maxlength="2048" />
		</label>
		<button type="submit" class="primary" disabled={status === 'loading'}>
			{status === 'loading' ? 'Adding…' : 'Add repo'}
		</button>
	</form>
	{#if message}
		<p class="status" data-variant={status}>{message}</p>
	{/if}
	{#if loadingRepos}
		<p>Loading repos…</p>
	{:else if repos.length === 0}
		<p>No repos yet.</p>
	{:else}
		<ul class="repo-list">
			{#each repos as repo}
				<li>
					<strong><a href={`/repos/${repo.id}`}>{repo.name}</a></strong>
					<div>{repo.url}</div>
					<div>location: {repo.location || '(pending scan)'}</div>
					<div>cursor: {repo.cursor_position || '(pending scan)'}</div>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.panel {
		max-width: 56rem;
		margin: 2.25rem auto;
		padding: 0 1.25rem;
		font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
	}
	h1 {
		margin: 0;
		font-size: 1.6rem;
		letter-spacing: -0.02em;
	}
	.subtitle {
		margin: 0.4rem 0 1rem 0;
		color: #4b5563;
		font-size: 0.94rem;
	}
	.form {
		display: grid;
		gap: 0.75rem;
		margin-bottom: 1rem;
		padding: 1rem;
		border: 1px solid #e5e7eb;
		border-radius: 0.75rem;
		background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
		box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
	}
	label {
		display: grid;
		gap: 0.35rem;
		font-size: 0.9rem;
		color: #334155;
	}
	input {
		padding: 0.6rem 0.7rem;
		border: 1px solid #cbd5e1;
		border-radius: 0.5rem;
		background: #fff;
	}
	input:focus-visible {
		outline: 2px solid #bfdbfe;
		outline-offset: 1px;
		border-color: #60a5fa;
	}
	.primary {
		cursor: pointer;
		border: none;
		border-radius: 0.6rem;
		padding: 0.6rem 1rem;
		font-size: 0.94rem;
		font-weight: 500;
		color: #fff;
		background: linear-gradient(90deg, #1d4ed8 0%, #4338ca 100%);
		width: fit-content;
	}
	.primary:disabled {
		opacity: 0.7;
	}
	.repo-list {
		list-style: none;
		padding: 0;
		display: grid;
		gap: 0.75rem;
	}
	.repo-list li {
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.85rem;
		background: #fff;
		box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
		font-size: 0.9rem;
		color: #334155;
	}
	.repo-list li strong a {
		color: #0f172a;
		text-decoration: none;
	}
	.repo-list li strong a:hover {
		text-decoration: underline;
	}
	.status[data-variant='ok'] {
		color: #0d5c2e;
		font-size: 0.9rem;
	}
	.status[data-variant='error'] {
		color: #9a1c1c;
		font-size: 0.9rem;
	}
</style>

