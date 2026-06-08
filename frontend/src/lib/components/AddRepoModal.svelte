<script lang="ts">
	import { createRepo } from '$lib/api/repos';

	let {
		open,
		onClose,
		onCreated
	}: {
		open: boolean;
		onClose: () => void;
		onCreated: () => void;
	} = $props();

	let name = $state('');
	let url = $state('');
	let loading = $state(false);
	let error = $state<string | null>(null);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		loading = true;
		error = null;
		try {
			await createRepo(name.trim(), url.trim());
			name = '';
			url = '';
			onCreated();
			onClose();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to add repository';
		} finally {
			loading = false;
		}
	}

	function handleBackdrop(event: MouseEvent) {
		if (event.target === event.currentTarget) onClose();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onClose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="backdrop" onclick={handleBackdrop}>
		<div class="modal" role="dialog" aria-modal="true" aria-labelledby="add-repo-title">
			<header class="modal-header">
				<h2 id="add-repo-title">Add repository</h2>
				<button type="button" class="close" onclick={onClose} aria-label="Close">×</button>
			</header>
			<form class="modal-body" onsubmit={submit}>
				<p class="hint">Connect a Git repository to start tracking specs and implementation health.</p>
				<label>
					<span>Name</span>
					<input bind:value={name} required minlength="1" maxlength="255" placeholder="my-service" />
				</label>
				<label>
					<span>Git URL</span>
					<input
						bind:value={url}
						required
						minlength="1"
						maxlength="2048"
						placeholder="https://github.com/org/repo.git"
					/>
				</label>
				{#if error}
					<p class="error">{error}</p>
				{/if}
				<div class="actions">
					<button type="button" class="secondary" onclick={onClose}>Cancel</button>
					<button type="submit" class="primary" disabled={loading}>
						{loading ? 'Adding…' : 'Add repository'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 60;
		background: rgba(15, 23, 42, 0.4);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
	}

	.modal {
		width: min(28rem, 100%);
		background: #fff;
		border-radius: 0.85rem;
		box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
		border: 1px solid #e2e8f0;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.1rem 0.5rem;
	}

	.modal-header h2 {
		margin: 0;
		font-size: 1.05rem;
		font-weight: 600;
		color: #0f172a;
	}

	.close {
		border: none;
		background: transparent;
		font-size: 1.4rem;
		line-height: 1;
		color: #64748b;
		cursor: pointer;
	}

	.modal-body {
		padding: 0.5rem 1.1rem 1.1rem;
		display: grid;
		gap: 0.85rem;
	}

	.hint {
		margin: 0;
		font-size: 0.85rem;
		color: #64748b;
		line-height: 1.45;
	}

	label {
		display: grid;
		gap: 0.35rem;
		font-size: 0.82rem;
		font-weight: 500;
		color: #334155;
	}

	input {
		padding: 0.55rem 0.65rem;
		border: 1px solid #cbd5e1;
		border-radius: 0.5rem;
		font-size: 0.9rem;
	}

	input:focus-visible {
		outline: 2px solid #bfdbfe;
		border-color: #60a5fa;
	}

	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		padding-top: 0.25rem;
	}

	.primary,
	.secondary {
		border-radius: 0.5rem;
		padding: 0.5rem 0.85rem;
		font-size: 0.86rem;
		font-weight: 500;
		cursor: pointer;
	}

	.primary {
		border: none;
		background: #2563eb;
		color: #fff;
	}

	.primary:disabled {
		opacity: 0.7;
	}

	.secondary {
		border: 1px solid #cbd5e1;
		background: #fff;
		color: #334155;
	}

	.error {
		margin: 0;
		color: #b91c1c;
		font-size: 0.84rem;
	}
</style>
