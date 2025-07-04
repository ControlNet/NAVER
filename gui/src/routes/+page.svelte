<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { 
		isConnected, 
		executionState, 
		currentImage, 
		currentQuery,
		storeActions
	} from '$lib/stores.js';
	import { websocketService } from '$lib/websocket.js';
	
	import InputPanel from '$lib/components/InputPanel.svelte';
	import AgentChat from '$lib/components/AgentChat.svelte';
	import FSAVisualization from '$lib/components/FSAVisualization.svelte';
	import MemoryOverlay from '$lib/components/MemoryOverlay.svelte';

	let connectionError: string | null = null;

	onMount(async () => {
		// Don't auto-connect on mount since we need a session ID from the server
		console.log('App mounted, ready to start analysis');
	});

	onDestroy(() => {
		websocketService.disconnect();
	});

	async function handleStartExecution(event: { detail: { imageFile: File; query: string } }): Promise<void> {
		const { imageFile, query } = event.detail;
		
		try {
			// Reset any previous state
			await storeActions.reset();
			connectionError = null;
			
			storeActions.updateExecutionState({ isRunning: true, currentState: 'STARTING' });
			storeActions.addChatMessage('user', `Query: "${query}"`);
			
			currentImage.set(imageFile);
			currentQuery.set(query);
			
			// Start analysis - this will create a session and establish WebSocket connection
			const result = await websocketService.startAnalysis(imageFile, query);
			
			console.log('Analysis started:', result);
			// The WebSocket will now receive and display the actual execution messages
			
		} catch (error) {
			console.error('Failed to start analysis:', error);
			const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
			connectionError = errorMessage;
			storeActions.updateExecutionState({ 
				isRunning: false, 
				currentState: 'ERROR', 
				error: errorMessage 
			});
			storeActions.addChatMessage('error', `Failed to start analysis: ${errorMessage}`);
		}
	}

	async function handleStopExecution(): Promise<void> {
		try {
			await websocketService.stopExecution();
			storeActions.updateExecutionState({ isRunning: false, currentState: 'STOPPED' });
			storeActions.addChatMessage('system', 'Execution stopped by user.');
		} catch (error) {
			console.error('Failed to stop execution:', error);
			const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
			storeActions.addChatMessage('error', `Failed to stop execution: ${errorMessage}`);
		}
	}

	async function handleClearAll(): Promise<void> {
		await storeActions.reset();
		currentImage.set(null);
		currentQuery.set('');
		connectionError = null;
		websocketService.disconnect();
	}
</script>

<div class="app-container">
	<!-- Header -->
	<header class="app-header">
		<h1>🤖 NAVER Agent Execution Viewer</h1>
		<div class="connection-status">
			{#if $isConnected}
				<span class="status-connected">🟢 Connected</span>
			{:else if connectionError}
				<span class="status-error">🔴 Connection Error: {connectionError}</span>
			{:else if $executionState.isRunning}
				<span class="status-connecting">🟡 Starting...</span>
			{:else}
				<span class="status-idle">⚪ Ready</span>
			{/if}
		</div>
	</header>

	<!-- Main Content -->
	<div class="main-content">
		<!-- Top Row: Input + Agent Chat -->
		<div class="top-row">
			<div class="input-section">
				<InputPanel 
					onstartExecution={handleStartExecution}
					onstopExecution={handleStopExecution}
					onclearAll={handleClearAll}
					disabled={$executionState.isRunning && $executionState.currentState === 'STARTING'}
				/>
			</div>
			<div class="chat-section">
				<AgentChat />
			</div>
		</div>

		<!-- Bottom Row: Visualizations -->
		<div class="bottom-row">
			<div class="fsa-container">
				<FSAVisualization />
			</div>
			<div class="memory-container">
				<MemoryOverlay />
			</div>
		</div>
	</div>
</div>

<style>
	.app-container {
		width: 100%;
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: var(--bg-primary);
	}

	.app-header {
		padding: 1rem 2rem;
		background: var(--bg-secondary);
		border-bottom: 1px solid var(--border-color);
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.app-header h1 {
		margin: 0;
		font-size: 1.5rem;
		color: var(--text-primary);
	}

	.connection-status {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.status-connected {
		color: var(--accent-green);
	}

	.status-error {
		color: var(--accent-red);
	}

	.status-connecting {
		color: var(--accent-orange);
	}

	.status-idle {
		color: var(--text-secondary);
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		padding: 1rem;
		overflow: hidden;
	}

	.top-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		height: 400px;
	}

	.input-section, .chat-section {
		background: var(--bg-secondary);
		border-radius: 8px;
		border: 1px solid var(--border-color);
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.bottom-row {
		display: grid;
		grid-template-columns: 1fr 2fr;
		gap: 1rem;
	}

	.fsa-container {
		background: var(--bg-secondary);
		border-radius: 8px;
		border: 1px solid var(--border-color);
		overflow: hidden;
	}

	.memory-container {
		background: var(--bg-secondary);
		border-radius: 8px;
		border: 1px solid var(--border-color);
		overflow: hidden;
	}

    :global(.memory-container img) {
        width: 100%;
        height: auto;
        display: block;
        object-fit: contain;
    }
</style>
