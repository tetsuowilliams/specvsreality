import { publicApiBaseUrl } from '$lib/api/config';

export type HelloWorldResponse = {
	queued: boolean;
};

export async function postHelloWorld(name: string): Promise<HelloWorldResponse> {
	const res = await fetch(`${publicApiBaseUrl()}/hello-world`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ name })
	});
	if (!res.ok) {
		const text = await res.text();
		throw new Error(text || `HTTP ${res.status}`);
	}
	return (await res.json()) as HelloWorldResponse;
}
