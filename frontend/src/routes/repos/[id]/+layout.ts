import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ params }) => {
	return { id: params.id };
};
