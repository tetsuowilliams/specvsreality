/** Plain-language definitions for dashboard metrics and statuses. */

export type MetricHelp = {
	label: string;
	short: string;
	detail: string;
};

export const DASHBOARD_METRICS: Record<string, MetricHelp> = {
	specs_tracked: {
		label: 'Specs tracked',
		short: 'Logical specs discovered in this repository.',
		detail:
			'Each spec is a spec.md bundle (and optional tasks/plan) extracted from the repo at a commit.'
	},
	latest_commit: {
		label: 'Latest commit',
		short: 'Most recent commit the scanner has analysed.',
		detail:
			'Usually matches the repo scan cursor. Evaluations and spec versions are tied to specific commits.'
	},
	coverage: {
		label: 'Coverage',
		short: 'Share of evaluated must/should items judged implemented.',
		detail:
			'Calculated as implemented ÷ evaluated for items marked must or should, using each item’s most recent evaluation. Optional and context items are excluded.'
	},
	missing: {
		label: 'Mandatory gaps',
		short: 'Must-have spec items judged not implemented.',
		detail:
			'Counts mandatory (must) items whose latest evaluation returned implemented = false. These are requirements the codebase is believed to lack—not unevaluated items.'
	},
	low_confidence: {
		label: 'Low confidence',
		short: 'Evaluations the model was unsure about.',
		detail:
			'Items whose latest evaluation confidence score is below 70%. Worth a human review even if marked implemented.'
	},
	candidates: {
		label: 'Candidate artifacts',
		short: 'Source files flagged as possible implementation locations.',
		detail:
			'Files the system considered during candidate discovery for the latest spec version. Candidates are not proof of implementation—only starting points for evaluation.'
	},
	satisfied: {
		label: 'Satisfied',
		short: 'Must/should items judged implemented.',
		detail:
			'Items marked must or should whose latest evaluation returned implemented = true.'
	},
	status: {
		label: 'Status',
		short: 'Overall health of this spec from its latest evaluations.',
		detail:
			'Derived from must/should item outcomes: good (all implemented), mostly implemented (majority implemented, no must gaps), at risk (must gap), unknown (never evaluated), stale (no evaluation at the latest analysed commit).'
	},
	status_good: {
		label: 'Good',
		short: 'All tracked must/should items are implemented.',
		detail: 'No mandatory gaps on the latest evaluations.'
	},
	status_mostly_implemented: {
		label: 'Mostly implemented',
		short: 'Majority implemented and no mandatory gaps.',
		detail: 'At least half of evaluated must/should items are implemented, but not all.'
	},
	status_at_risk: {
		label: 'At risk',
		short: 'One or more mandatory items are not implemented.',
		detail: 'At least one must item’s latest evaluation returned implemented = false.'
	},
	status_unknown: {
		label: 'Unknown',
		short: 'No evaluations yet for this spec.',
		detail: 'Spec items exist but ImplementationAtCommit rows have not been recorded.'
	},
	status_stale: {
		label: 'Stale',
		short: 'Not re-evaluated at the latest analysed commit.',
		detail:
			'The latest spec version is tied to the cursor commit, but evaluations at that commit are missing.'
	},
	needs_attention: {
		label: 'Needs attention',
		short: 'Specs or items that merit review before drilling in.',
		detail:
			'Prioritises mandatory gaps, missing candidates, low-confidence judgements, unevaluated specs, and specs with candidates but no implemented items.'
	},
	recent_changes: {
		label: 'Recent changes',
		short: 'Implementation judgements that changed across commits.',
		detail:
			'Compares the latest evaluation per item with the prior evaluation for the same spec and local key, when available.'
	},
	artifact_activity: {
		label: 'Artifact activity',
		short: 'Files linked as evidence or candidates.',
		detail:
			'Evidence = files cited in Implements rows for an evaluation. Candidate = files proposed during discovery but not necessarily used as evidence.'
	}
};

export function statusHelp(status: string): MetricHelp {
	const key = `status_${status}` as keyof typeof DASHBOARD_METRICS;
	return DASHBOARD_METRICS[key] ?? DASHBOARD_METRICS.status;
}

export const METRICS_DASHBOARD: Record<string, MetricHelp> = {
	total_spend: {
		label: 'Total spend',
		short: 'Estimated LLM cost across all recorded agent runs.',
		detail: 'USD computed at run time from configured per-model token rates.'
	},
	total_tokens: {
		label: 'Total tokens',
		short: 'Input plus output tokens consumed by agents.',
		detail: 'Summed across every persisted agent run in the workspace.'
	},
	agent_runs: {
		label: 'Agent runs',
		short: 'Individual Pydantic AI invocations recorded.',
		detail: 'One row per run_sync call, including batched implements evaluations.'
	},
	avg_cost_per_run: {
		label: 'Avg cost / run',
		short: 'Mean spend per recorded agent invocation.',
		detail: 'Total spend divided by the number of agent runs.'
	},
	cost_by_agent: {
		label: 'Cost by agent',
		short: 'Spend split across spec extraction, candidate discovery, and implements evaluation.',
		detail: 'Useful for spotting which pipeline stage drives LLM usage.'
	},
	per_repo: {
		label: 'Per repository',
		short: 'Token and cost totals grouped by repository.',
		detail: 'Click a row to filter the recent runs table to that repository.'
	},
	recent_runs: {
		label: 'Recent agent runs',
		short: 'Latest invocations with model, tokens, and cost.',
		detail: 'Ordered by run time descending. Filtered when a repository row is selected.'
	}
};

export const AGENT_LABELS: Record<string, string> = {
	spec_extraction: 'Spec extraction',
	artifact_candidate: 'Candidate discovery',
	implements: 'Implements evaluation'
};
