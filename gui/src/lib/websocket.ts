import { 
	wsConnection, 
	isConnected, 
	sessionId,
	storeActions,
	executionState,
	entities,
	relations,
	context,
	executionHistory,
	stateInfo
} from './stores';
import type { 
	WebSocketMessage, 
	StateUpdateData, 
	ExecutionCompleteData, 
	ExecutionErrorData,
	ExecutionMessage,
	StateInfo
} from './types';

interface AnalysisResponse {
	status: string;
	session_id: string;
}

interface StopResponse {
	status: string;
}

class WebSocketService {
	private ws: WebSocket | null = null;
	private reconnectAttempts: number = 0;
	private readonly maxReconnectAttempts: number = 5;
	private readonly reconnectDelay: number = 1000;
	private currentSessionId: string | null = null;
	private isAnalysisStarted: boolean = false;

	connect(newSessionId: string | null = null): Promise<void> {
		return new Promise((resolve, reject) => {
			// Prevent connecting if no session ID is provided
			if (!newSessionId && !this.currentSessionId) {
				reject(new Error('No session ID available for WebSocket connection'));
				return;
			}

			// Use the provided session ID or the current one
			const sessionIdToUse = newSessionId || this.currentSessionId;
			
			if (this.ws && this.ws.readyState === WebSocket.OPEN) {
				console.log('WebSocket already connected');
				resolve();
				return;
			}

			// Close existing connection if any
			if (this.ws) {
				this.ws.close();
			}

			this.currentSessionId = sessionIdToUse;
			
			const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
			const wsUrl = `${protocol}//${window.location.host}/ws/${this.currentSessionId}`;
			
			console.log(`Connecting to WebSocket: ${wsUrl}`);
			
			try {
				this.ws = new WebSocket(wsUrl);
				
				this.ws.onopen = () => {
					console.log('WebSocket connected successfully');
					isConnected.set(true);
					wsConnection.set(this.ws);
					sessionId.set(this.currentSessionId);
					this.reconnectAttempts = 0;
					
					// Send ping to confirm connection
					this.send({ type: 'ping' });
					resolve();
				};

				this.ws.onmessage = (event: MessageEvent) => {
					try {
						const message: WebSocketMessage = JSON.parse(event.data);
						console.log('WebSocket message received:', message);
						// Handle message asynchronously without blocking
						this.handleMessage(message).catch(error => {
							console.error('Error handling WebSocket message:', error);
						});
					} catch (error) {
						console.error('Error parsing WebSocket message:', error);
					}
				};

				this.ws.onclose = (event: CloseEvent) => {
					console.log('WebSocket disconnected:', event.code, event.reason);
					isConnected.set(false);
					wsConnection.set(null);
					
					// Attempt to reconnect if not a deliberate close and analysis is still running
					if (event.code !== 1000 && this.isAnalysisStarted && this.reconnectAttempts < this.maxReconnectAttempts) {
						this.attemptReconnect();
					}
				};

				this.ws.onerror = (error: Event) => {
					console.error('WebSocket error:', error);
					reject(new Error('WebSocket connection failed'));
				};

			} catch (error) {
				console.error('Failed to create WebSocket connection:', error);
				reject(error);
			}
		});
	}

	disconnect(): void {
		console.log('Disconnecting WebSocket');
		this.isAnalysisStarted = false;
		if (this.ws) {
			this.ws.close(1000, 'Deliberate disconnect');
			this.ws = null;
		}
		isConnected.set(false);
		wsConnection.set(null);
		this.currentSessionId = null;
	}

	send(message: WebSocketMessage): void {
		if (this.ws && this.ws.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(message));
		} else {
			console.warn('WebSocket not connected, cannot send message:', message);
		}
	}

	private async handleMessage(message: WebSocketMessage): Promise<void> {
		try {
			switch (message.type) {
				case 'pong':
					console.log('Received pong from server');
					break;

				case 'execution_message':
					await this.handleExecutionMessage(message.body as ExecutionMessage);
					break;

				case 'state_info':
					await this.handleStateInfo(message.body as StateInfo);
					break;

				case 'state_update':
					await this.handleStateUpdate(message.data as StateUpdateData);
					break;

				case 'execution_complete':
					await this.handleExecutionComplete(message.data as ExecutionCompleteData);
					break;

				case 'execution_error':
					await this.handleExecutionError(message.data as ExecutionErrorData);
					break;

				case 'agent_message':
					await this.handleAgentMessage(message.data);
					break;

				default:
					console.log('Unknown message type:', message.type, message);
			}
		} catch (error) {
			console.error('Error handling WebSocket message:', error);
		}
	}

	private async handleExecutionMessage(executionMessage: ExecutionMessage | undefined): Promise<void> {
		if (!executionMessage) {
			console.warn('Received execution_message without body');
			return;
		}

		console.log('Execution message received:', executionMessage);
		
		// Add the execution message to chat with appropriate type mapping
		await storeActions.addChatMessage(
			executionMessage.type, 
			executionMessage.content,
			{ timestamp: new Date().toISOString() }
		);

		// Update execution state based on message type
		if (executionMessage.type === 'result') {
			// Result message indicates completion
			this.isAnalysisStarted = false;
			await storeActions.updateExecutionState({ 
				isRunning: false, 
				currentState: 'COMPLETE',
				progress: 100 
			});
		} else {
			// Thinking/action messages indicate the agent is still working
			await storeActions.updateExecutionState({ 
				isRunning: true 
			});
		}
	}

	private async handleStateInfo(stateInfoData: StateInfo | undefined): Promise<void> {
		if (!stateInfoData) {
			console.warn('Received state_info without body');
			return;
		}

		console.log('State info received:', stateInfoData);
		
		// Update the state info store for FSA visualization
		await storeActions.updateStateInfo(stateInfoData);
	}

	private async handleStateUpdate(data: StateUpdateData): Promise<void> {
		console.log('State update received:', data);
		
		// Update execution state with new FSA fields
		const stateUpdates: any = {};
		if (data.current_state) {
			stateUpdates.currentState = data.current_state;
			stateUpdates.isRunning = true;
		}
		if (data.progress !== undefined) {
			stateUpdates.progress = data.progress;
		}
		if (data.state_history) {
			stateUpdates.stateHistory = data.state_history;
		}
		if (data.iteration !== undefined) {
			stateUpdates.iteration = data.iteration;
		}
		
		if (Object.keys(stateUpdates).length > 0) {
			await storeActions.updateExecutionState(stateUpdates);
		}

		// Update entities
		if (data.entities) {
			await storeActions.updateEntities(data.entities);
		}

		// Update relations
		if (data.relations) {
			await storeActions.updateRelations(data.relations);
		}

		// Update context
		if (data.context) {
			context.set(data.context);
		}

		// Add to execution history
		if (data.step) {
			await storeActions.addExecutionStep(data.step);
		}

		// Add chat message for state updates
		if (data.message) {
			await storeActions.addChatMessage('agent-step', data.message, {
				state: data.current_state,
				progress: data.progress,
				iteration: data.iteration
			});
		}
	}

	private async handleExecutionComplete(data: ExecutionCompleteData): Promise<void> {
		console.log('Execution complete:', data);
		this.isAnalysisStarted = false;
		
		const stateUpdates: any = {
			isRunning: false,
			currentState: 'COMPLETE',
			progress: 100
		};
		
		if (data.state_history) {
			stateUpdates.stateHistory = data.state_history;
		}
		if (data.iteration !== undefined) {
			stateUpdates.iteration = data.iteration;
		}
		
		await storeActions.updateExecutionState(stateUpdates);

		// Update final results
		if (data.entities) {
			await storeActions.updateEntities(data.entities);
		}

		if (data.relations) {
			await storeActions.updateRelations(data.relations);
		}

		if (data.context) {
			context.set(data.context);
		}

		if (data.execution_history) {
			executionHistory.set(data.execution_history);
		}

		await storeActions.addChatMessage('agent-action', '✅ Analysis complete! Generated interactive visualizations.');
	}

	private async handleExecutionError(data: ExecutionErrorData): Promise<void> {
		console.error('Execution error:', data);
		this.isAnalysisStarted = false;
		
		const stateUpdates: any = {
			isRunning: false,
			currentState: 'ERROR',
			error: data.error
		};
		
		if (data.state_history) {
			stateUpdates.stateHistory = data.state_history;
		}
		if (data.iteration !== undefined) {
			stateUpdates.iteration = data.iteration;
		}
		
		await storeActions.updateExecutionState(stateUpdates);

		await storeActions.addChatMessage('error', `❌ Error: ${data.error}`);
	}

	private async handleAgentMessage(data: any): Promise<void> {
		await storeActions.addChatMessage(data.type, data.content, data.metadata);
	}

	private attemptReconnect(): void {
		this.reconnectAttempts++;
		const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
		
		console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
		
		setTimeout(() => {
			this.connect(this.currentSessionId).catch((error) => {
				console.error('Reconnection failed:', error);
			});
		}, delay);
	}

	private generateSessionId(): string {
		return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
	}

	// API methods
	async startAnalysis(imageFile: File, query: string): Promise<AnalysisResponse> {
		// Reset state
		this.isAnalysisStarted = false;
		this.disconnect(); // Ensure any existing connection is closed
		
		const formData = new FormData();
		formData.append('image', imageFile);
		formData.append('query', query);

		try {
			console.log('Starting analysis via /api/start');
			const response = await fetch('/api/start', {
				method: 'POST',
				body: formData
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const result: AnalysisResponse = await response.json();
			console.log('Analysis start response:', result);
			
			// Verify we got a valid session ID
			if (!result.session_id) {
				throw new Error('No session ID returned from server');
			}
			
			// Update the current session ID with the one returned from the server
			this.currentSessionId = result.session_id;
			sessionId.set(this.currentSessionId);
			this.isAnalysisStarted = true;
			
			// Add a small delay to ensure backend is ready
			await new Promise(resolve => setTimeout(resolve, 100));
			
			// Connect to WebSocket with the new session ID
			console.log('Connecting to WebSocket with session ID:', this.currentSessionId);
			await this.connect(this.currentSessionId);
			
			return result;
		} catch (error) {
			console.error('Analysis request failed:', error);
			this.isAnalysisStarted = false;
			throw error;
		}
	}

	async stopExecution(): Promise<StopResponse | void> {
		if (!this.currentSessionId) return;

		try {
			this.isAnalysisStarted = false;
			const response = await fetch(`/api/session/${this.currentSessionId}/stop`, {
				method: 'POST'
			});

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Stop execution request failed:', error);
			throw error;
		}
	}

	async getSessionState(): Promise<any> {
		if (!this.currentSessionId) return null;

		try {
			const response = await fetch(`/api/session/${this.currentSessionId}/state`);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error('Get session state request failed:', error);
			throw error;
		}
	}
}

// Create singleton instance
export const websocketService = new WebSocketService(); 