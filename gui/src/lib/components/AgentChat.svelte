<script lang="ts">
import { chatMessages, executionState } from '$lib/stores.js';
import type { ChatMessage } from '$lib/types.js';

	let chatContainer: HTMLDivElement;

	// Auto-scroll to bottom only when agent is running
	$: if (chatContainer && $chatMessages.length > 0 && $executionState.isRunning) {
		setTimeout(() => {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}, 0);
	}

	function getMessageIcon(type: ChatMessage['type']): string {
		switch (type) {
			case 'user': return '👤';
			case 'agent-step': return '🔄';
			case 'agent-action': return '⚡';
			case 'system': return '🔧';
			case 'error': return '❌';
			case 'thinking': return '💭';
			case 'action': return '⚡';
			case 'result': return '✅';
			default: return '🤖';
		}
	}

	function isUserMessage(type: ChatMessage['type']): boolean {
		return type === 'user';
	}
</script>

<div class="agent-chat">
	<div class="panel-header">
		🤖 Agent Execution Stream
		<span class="status-badge" class:running={$executionState.isRunning}>
			{$executionState.isRunning ? 'RUNNING' : 'IDLE'}
		</span>
	</div>
	
	<div class="chat-container" bind:this={chatContainer}>
		{#if $chatMessages.length === 0}
			<div class="empty-state">
				<div class="empty-icon">🤖</div>
				<p>Ready to analyze your image and query.</p>
				<p class="empty-hint">Upload an image and enter your query to begin.</p>
			</div>
		{:else}
			{#each $chatMessages as message (message.id)}
				<div class="message-wrapper" class:user={isUserMessage(message.type)}>
					<div class="message-content">
						<span class="message-icon">{getMessageIcon(message.type)}</span>
						<span class="message-text">{message.content}</span>
					</div>
				</div>
			{/each}
		{/if}
		
		{#if $executionState.isRunning}
			<div class="typing-indicator">
				<div class="typing-dots">
					<span></span>
					<span></span>
					<span></span>
				</div>
				<span>Agent is thinking...</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.agent-chat {
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		background: var(--bg-tertiary);
		border-bottom: 1px solid var(--border-color);
		font-weight: 600;
		font-size: 0.875rem;
		color: var(--text-primary);
	}

	.status-badge {
		font-size: 0.75rem;
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
		background: var(--bg-tertiary);
		color: var(--text-secondary);
		font-weight: 500;
	}

	.status-badge.running {
		background: var(--accent-green);
		color: white;
	}

	.chat-container {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		text-align: center;
		color: var(--text-secondary);
	}

	.empty-icon {
		font-size: 3rem;
		margin-bottom: 1rem;
	}

	.empty-hint {
		font-size: 0.875rem;
		opacity: 0.8;
	}

	.message-wrapper {
		display: flex;
		width: 100%;
		margin-bottom: 0.25rem;
	}

	.message-wrapper.user {
		justify-content: flex-end;
	}

	.message-content {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		max-width: 80%;
		line-height: 1.4;
		color: var(--text-primary);
	}

	.message-wrapper.user .message-content {
		flex-direction: row-reverse;
		background: var(--accent-blue);
		color: white;
		padding: 0.5rem 0.75rem;
		border-radius: 18px 18px 4px 18px;
	}

	.message-icon {
		font-size: 1rem;
		flex-shrink: 0;
		margin-top: 0.1rem;
	}

	.message-wrapper.user .message-icon {
		margin-top: 0;
	}

	.message-text {
		flex: 1;
		word-wrap: break-word;
	}

	.typing-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0;
		color: var(--text-secondary);
		font-style: italic;
	}

	.typing-dots {
		display: flex;
		gap: 0.25rem;
	}

	.typing-dots span {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--accent-blue);
		animation: typing 1.4s infinite ease-in-out;
	}

	.typing-dots span:nth-child(2) {
		animation-delay: 0.2s;
	}

	.typing-dots span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes typing {
		0%, 80%, 100% {
			opacity: 0.3;
			transform: scale(0.8);
		}
		40% {
			opacity: 1;
			transform: scale(1);
		}
	}

	/* Scrollbar styling */
	.chat-container::-webkit-scrollbar {
		width: 6px;
	}

	.chat-container::-webkit-scrollbar-thumb {
		background: var(--border-color);
		border-radius: 3px;
	}

	.chat-container::-webkit-scrollbar-thumb:hover {
		background: var(--text-secondary);
	}
</style> 