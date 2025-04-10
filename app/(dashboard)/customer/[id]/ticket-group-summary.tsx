'use client';

import React from 'react';
import { Loader2, RefreshCw } from 'lucide-react';

type TicketGroupSummaryProps = {
	customerId: string;
	dateRange?: {
		start: string;
		end: string;
	};
};

export default function TicketGroupSummary({
	customerId,
	dateRange
}: TicketGroupSummaryProps) {
	const [summary, setSummary] = React.useState<string>('');
	const [isLoading, setIsLoading] = React.useState(false);
	const [error, setError] = React.useState<string>('');
	const [metadata, setMetadata] = React.useState<any>(null);
	const [lastGenerated, setLastGenerated] = React.useState<string | null>(null);

	function formatDate(dateString: string) {
		return new Date(dateString).toLocaleString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function fetchGroupSummary(force = false) {
		setIsLoading(true);
		setError('');

		try {
			const url = new URL('http://localhost:8000/api/v1/summaries/group/all_tickets');
			if (dateRange?.start) {
				url.searchParams.append('start_date', dateRange.start);
			}
			if (dateRange?.end) {
				url.searchParams.append('end_date', dateRange.end);
			}
			if (force) {
				url.searchParams.append('force_regenerate', 'true');
			}
			if (customerId) {
				url.searchParams.append('customer_id', customerId);
			}

			const response = await fetch(url.toString(), {
				headers: {
					'Accept': 'application/json'
				}
			});

			if (!response.ok) {
				const errorText = await response.text();
				console.error('Group summary error:', errorText);
				throw new Error(`Error fetching group summary: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			console.log('Group summary response:', data);

			if (!data.summary) {
				throw new Error('No summary received from the server');
			}

			setSummary(data.summary);
			setMetadata(data.metadata);
			setLastGenerated(data.last_generated_at);
		} catch (error) {
			console.error('Error fetching group summary:', error);
			setError(error instanceof Error ? error.message : 'Failed to load group summary. Please try again.');
		} finally {
			setIsLoading(false);
		}
	}

	React.useEffect(() => {
		fetchGroupSummary();
	}, [dateRange?.start, dateRange?.end]); // Only depend on date range changes

	const formattedSummary = summary ? summary.split('\n').map((line, index) => (
		<div key={index} className="py-1">
			{line.startsWith('-') ? (
				<div className="flex gap-2">
					<span className="text-muted-foreground">•</span>
					{line.substring(1).trim()}
				</div>
			) : (
				line
			)}
		</div>
	)) : null;

	return (
		<div className="space-y-4">
			<div className="flex items-center justify-between">
				<h3 className="text-lg font-medium">All Tickets Summary</h3>
				<button
					onClick={() => fetchGroupSummary(true)}
					className="p-1 hover:bg-muted rounded-full"
					disabled={isLoading}
				>
					<RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
				</button>
			</div>

			{error && (
				<div className="text-sm text-red-500">
					{error}
				</div>
			)}

			{isLoading && (
				<div className="flex items-center gap-2 text-sm text-muted-foreground">
					<Loader2 className="h-4 w-4 animate-spin" />
					Generating summary...
				</div>
			)}

			{metadata && (
				<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
					<div className="p-4 border rounded-lg">
						<div className="text-sm font-medium text-muted-foreground">Total Tickets</div>
						<div className="text-2xl font-bold">{metadata.total_count}</div>
					</div>
					<div className="p-4 border rounded-lg">
						<div className="text-sm font-medium text-muted-foreground">Open Tickets</div>
						<div className="text-2xl font-bold">{metadata.open_tickets}</div>
					</div>
					<div className="p-4 border rounded-lg">
						<div className="text-sm font-medium text-muted-foreground">High Priority</div>
						<div className="text-2xl font-bold">{metadata.high_priority_tickets}</div>
					</div>
					<div className="p-4 border rounded-lg">
						<div className="text-sm font-medium text-muted-foreground">With Jira</div>
						<div className="text-2xl font-bold">{metadata.tickets_with_jira}</div>
					</div>
				</div>
			)}

			{formattedSummary && (
				<div className="space-y-2">
					<div className="text-sm text-muted-foreground space-y-1">
						{formattedSummary}
					</div>
					{lastGenerated && (
						<div className="text-xs text-muted-foreground border-t pt-2">
							Last generated: {formatDate(lastGenerated)}
						</div>
					)}
				</div>
			)}
		</div>
	);
} 