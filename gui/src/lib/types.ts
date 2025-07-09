// Type definitions for NAVER Agent Execution Platform

export interface Entity {
	id: string;
	type: string;
	confidence: number;
	bbox?: number[];
	attributes?: Record<string, any>;
	color?: string; // Added by frontend for visualization
}

export interface Relation {
	id: string;
	from_entity: string;
	to_entity: string;
	type: string;
	confidence: number;
	attributes?: Record<string, any>;
}

// Context data structure including final result
export interface ContextData {
	entities: Entity[];
	relations: Relation[];
	attributes: any[];
	final_result?: {
		id: string;
		category: string;
		bbox: number[];
		bbox_confidence: number;
	};
}

export interface ExecutionState {
	isRunning: boolean;
	currentState: string;
	progress: number;
	error?: string | null;
	stateHistory: StateTransition[];
	iteration: number;
}

export interface StateTransition {
	from: string | null;
	to: string;
	timestamp: number;
	result?: string;
	feedback?: string;
	skip_top?: number;
}

// New StateInfo type from backend
export interface StateInfo {
	current_state: string | null;
	history: string[];
}

export interface ExecutionStep {
	id: number;
	step: string;
	timestamp: string;
	message: string;
	metadata?: Record<string, any>;
}

export interface ChatMessage {
	id: number;
	type: 'user' | 'agent-step' | 'agent-action' | 'system' | 'error' | 'thinking' | 'action' | 'result';
	content: string;
	metadata?: Record<string, any>;
	timestamp: string;
}

// New ExecutionMessage type from backend
export interface ExecutionMessage {
	type: 'thinking' | 'action' | 'result';
	content: string;
}

export interface WebSocketMessage {
	type: 'ping' | 'pong' | 'state_update' | 'execution_complete' | 'execution_error' | 'agent_message' | 'execution_message' | 'state_info' | 'context';
	data?: any;
	body?: ExecutionMessage | StateInfo | ContextData; // Updated to include ContextData
	timestamp?: number;
}

export interface StateUpdateData {
	current_state?: string;
	progress?: number;
	message?: string;
	entities?: Entity[];
	relations?: Relation[];
	context?: any;
	step?: ExecutionStep;
	state_history?: StateTransition[];
	iteration?: number;
}

export interface ExecutionCompleteData {
	entities?: Entity[];
	relations?: Relation[];
	context?: any;
	execution_history?: ExecutionStep[];
	message?: string;
	state_history?: StateTransition[];
	iteration?: number;
}

export interface ExecutionErrorData {
	error: string;
	current_state?: string;
	state_history?: StateTransition[];
	iteration?: number;
} 