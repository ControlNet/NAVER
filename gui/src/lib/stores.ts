import { writable, type Writable } from 'svelte/store';
import { tick } from 'svelte';
import type { 
	Entity, 
	Relation, 
	ExecutionState, 
	ExecutionStep, 
	ChatMessage, 
	StateInfo
} from './types';

// WebSocket connection store
export const wsConnection: Writable<WebSocket | null> = writable(null);
export const isConnected: Writable<boolean> = writable(false);

// Session management
export const sessionId: Writable<string | null> = writable(null);

// Application state
export const executionState: Writable<ExecutionState> = writable({
	isRunning: false,
	currentState: 'IDLE',
	progress: 0,
	error: null,
	stateHistory: [],
	iteration: 0
});

// State info from backend for FSA visualization
export const stateInfo: Writable<StateInfo> = writable({
	current_state: null,
	history: []
});

// NAVER execution data
export const currentImage: Writable<File | null> = writable(null);
export const currentQuery: Writable<string> = writable('');

// Entity and context data (kept for websocket compatibility)
export const entities: Writable<Entity[]> = writable([]);
export const relations: Writable<Relation[]> = writable([]);
export const context: Writable<any> = writable(null);

// Execution history
export const executionHistory: Writable<ExecutionStep[]> = writable([]);

// Chat messages for agent execution stream
export const chatMessages: Writable<ChatMessage[]> = writable([]);

// Counter for unique message IDs
let messageIdCounter = 0;

// Store actions
export const storeActions = {
	// Reset all stores to initial state
	async reset(): Promise<void> {
		messageIdCounter = 0; // Reset message counter
		executionState.set({
			isRunning: false,
			currentState: 'IDLE',
			progress: 0,
			error: null,
			stateHistory: [],
			iteration: 0
		});
		await tick();
		stateInfo.set({
			current_state: null,
			history: []
		});
		await tick();
		entities.set([]);
		relations.set([]);
		context.set(null);
		executionHistory.set([]);
		chatMessages.set([]);
		await tick();
	},

	// Add chat message with proper sequencing
	async addChatMessage(
		type: ChatMessage['type'], 
		content: string, 
		metadata: Record<string, any> = {}
	): Promise<void> {
		// Generate unique ID using counter + timestamp to avoid conflicts
		const id = ++messageIdCounter;
		const message: ChatMessage = {
			id,
			type,
			content,
			metadata,
			timestamp: new Date().toLocaleTimeString()
		};
		
		// Use proper synchronous update to avoid race conditions
		chatMessages.update(messages => [...messages, message]);
		await tick(); // Ensure DOM update completes
	},

	// Update execution state with proper sequencing
	async updateExecutionState(updates: Partial<ExecutionState>): Promise<void> {
		executionState.update(state => ({ ...state, ...updates }));
		await tick();
	},

	// Update state info from backend with proper sequencing
	async updateStateInfo(newStateInfo: StateInfo): Promise<void> {
		stateInfo.set(newStateInfo);
		await tick();
	},

	// Add execution step to history with proper sequencing
	async addExecutionStep(step: Omit<ExecutionStep, 'id' | 'timestamp'>): Promise<void> {
		const newStep: ExecutionStep = {
			...step,
			timestamp: new Date().toISOString(),
			id: ++messageIdCounter
		};
		
		executionHistory.update(history => [...history, newStep]);
		await tick();
	},

	// Update entities from backend with proper sequencing
	async updateEntities(newEntities: Entity[]): Promise<void> {
		const entitiesWithColors = newEntities.map(entity => ({
			...entity,
			color: `hsl(${(entity.id.length * 137.5) % 360}, 70%, 50%)`
		}));
		
		entities.set(entitiesWithColors);
		await tick();
	},

	// Update relations from backend with proper sequencing
	async updateRelations(newRelations: Relation[]): Promise<void> {
		relations.set(newRelations);
		await tick();
	}
}; 