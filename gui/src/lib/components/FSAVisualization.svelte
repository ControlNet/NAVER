<script lang="ts">
	import { executionState, stateInfo } from '$lib/stores.js';
	import type { StateTransition } from '$lib/types.js';

	interface StatePosition {
		x: number;
		y: number;
		color: string;
		label: string;
	}

	// NAVER FSA states and their positions (for graph layout)
	const statePositions: Record<string, StatePosition> = {
		'_PerceptionState': { x: 200, y: 150, color: '#3b82f6', label: 'Perception' },
		'_LogicGenerationState': { x: 600, y: 150, color: '#8b5cf6', label: 'Logic Generation' },
		'_LogicReasoningState': { x: 600, y: 300, color: '#f59e0b', label: 'Logic Reasoning' },
		'_AnsweringState': { x: 400, y: 400, color: '#10b981', label: 'Answering' },
		'Output': { x: 400, y: 500, color: '#06b6d4', label: 'Output' }
	};

	// Map backend state names to display names
	const stateNameMap: Record<string, string> = {
		'_PerceptionState': 'Perception',
		'_LogicGenerationState': 'Logic Generation',
		'_LogicReasoningState': 'Logic Reasoning',
		'_AnsweringState': 'Answering',
		'Output': 'Output'
	};

	// Define possible transitions based on NAVER automaton logic
	const possibleTransitions = [
		// From Perception
		{ from: '_PerceptionState', to: '_LogicGenerationState', label: 'multi_objects', color: '#3b82f6' },
		{ from: '_PerceptionState', to: '_AnsweringState', label: 'single/no_object', color: '#3b82f6' },
		{ from: '_PerceptionState', to: '_PerceptionState', label: 'retry', color: '#ef4444', curved: true },
		
		// From Logic Generation
		{ from: '_LogicGenerationState', to: '_LogicReasoningState', label: 'success', color: '#8b5cf6' },
		{ from: '_LogicGenerationState', to: '_LogicGenerationState', label: 'retry', color: '#ef4444', curved: true },
		
		// From Logic Reasoning
		{ from: '_LogicReasoningState', to: '_AnsweringState', label: 'success', color: '#f59e0b' },
		{ from: '_LogicReasoningState', to: '_LogicGenerationState', label: 'self_correct', color: '#ef4444', curved: true },
		
		// From Answering
		{ from: '_AnsweringState', to: 'Output', label: 'valid', color: '#10b981' },
		{ from: '_AnsweringState', to: '_LogicReasoningState', label: 'invalid', color: '#ef4444', curved: true },
		{ from: '_AnsweringState', to: 'Output', label: 'fallback', color: '#f59e0b' }
	];

	function isStateActive(stateName: string): boolean {
		return $stateInfo.current_state === stateName;
	}

	function isStateInHistory(stateName: string): boolean {
		return $stateInfo.history.includes(stateName);
	}

	function getTransitionOpacity(transition: any): number {
		// Check if this transition actually happened based on state history
		const history = $stateInfo.history;
		const current = $stateInfo.current_state;
		
		// Build the full state sequence including current state
		const fullSequence = [...history];
		if (current) {
			fullSequence.push(current);
		}
		
		// Check if this transition exists in the sequence
		for (let i = 0; i < fullSequence.length - 1; i++) {
			if (fullSequence[i] === transition.from && fullSequence[i + 1] === transition.to) {
				return 1.0;
			}
		}
		
		return 0.3;
	}

	function createPath(from: string, to: string, curved: boolean = false): string {
		const fromState = statePositions[from];
		const toState = statePositions[to];
		
		if (!fromState || !toState) return '';
		
		const dx = toState.x - fromState.x;
		const dy = toState.y - fromState.y;
		const distance = Math.sqrt(dx * dx + dy * dy);
		
		// Calculate connection points on circle edges (radius = 35)
		const radius = 35;
		const angle = Math.atan2(dy, dx);
		
		const fromX = fromState.x + Math.cos(angle) * radius;
		const fromY = fromState.y + Math.sin(angle) * radius;
		const toX = toState.x - Math.cos(angle) * radius;
		const toY = toState.y - Math.sin(angle) * radius;
		
		if (curved) {
			// Create curved path for self-correction loops
			const controlOffset = 40;
			const midX = (fromX + toX) / 2;
			const midY = (fromY + toY) / 2;
			const perpAngle = angle + Math.PI / 2;
			const controlX = midX + Math.cos(perpAngle) * controlOffset;
			const controlY = midY + Math.sin(perpAngle) * controlOffset;
			
			return `M ${fromX} ${fromY} Q ${controlX} ${controlY} ${toX} ${toY}`;
		} else {
			return `M ${fromX} ${fromY} L ${toX} ${toY}`;
		}
	}

	function getArrowPosition(from: string, to: string, curved: boolean = false): { x: number, y: number, angle: number } {
		const fromState = statePositions[from];
		const toState = statePositions[to];
		
		if (!fromState || !toState) return { x: 0, y: 0, angle: 0 };
		
		const dx = toState.x - fromState.x;
		const dy = toState.y - fromState.y;
		const angle = Math.atan2(dy, dx);
		
		const radius = 35;
		const arrowX = toState.x - Math.cos(angle) * radius;
		const arrowY = toState.y - Math.sin(angle) * radius;
		
		return {
			x: arrowX,
			y: arrowY,
			angle: (angle * 180 / Math.PI) + (curved ? 15 : 0)
		};
	}

	// Create dynamic states list based on backend data
	$: dynamicStates = (() => {
		const states: Record<string, StatePosition> = {};
		
		// Add states from history and current state
		[...$stateInfo.history, $stateInfo.current_state].forEach(stateName => {
			if (stateName && statePositions[stateName]) {
				states[stateName] = statePositions[stateName];
			}
		});
		
		return states;
	})();

	$: currentStateColor = $stateInfo.current_state ? statePositions[$stateInfo.current_state]?.color || '#6b7280' : '#6b7280';
	$: currentStateLabel = $stateInfo.current_state ? stateNameMap[$stateInfo.current_state] || $stateInfo.current_state : 'IDLE';

	// Pre-calculate transition data to avoid complex expressions in each blocks
	$: transitionData = possibleTransitions.map(transition => ({
		...transition,
		opacity: getTransitionOpacity(transition),
		arrowPos: getArrowPosition(transition.from, transition.to, transition.curved),
		path: createPath(transition.from, transition.to, transition.curved),
		shouldShow: dynamicStates[transition.from] && dynamicStates[transition.to]
	}));

	// Pre-calculate state data to avoid complex expressions in each blocks
	$: stateData = Object.entries(dynamicStates).map(([stateName, state]) => ({
		stateName,
		state,
		isActive: isStateActive(stateName),
		inHistory: isStateInHistory(stateName),
		displayName: stateNameMap[stateName] || state.label
	}));

    let fullHistory: string[] = [];

    $: if (stateInfo) {
        fullHistory = $stateInfo.history ?? []
    }

</script>

<div class="fsa-visualization">
	<div class="panel-header">
		🔄 Execution Flow (FSA) {$executionState.iteration}
	</div>
	<div class="panel-content">
		<div class="fsa-info">
			<div class="state-info">
                {#if $executionState.error}
                    <span class="current-state error-state">
                        ⚠️ {$executionState.error}
                    </span>
                {:else}
                    <span class="current-state" style="color: {currentStateColor}">
                        ● {currentStateLabel}
                    </span>
                {/if}
				<span class="progress">{$executionState.progress}%</span>
			</div>
			
			<!-- State History Display -->
			{#if $stateInfo.history.length > 0}
				<div class="state-history">
					<strong>State History:</strong>
					{#each fullHistory as historyState, index (index)}
						<span class="history-state">
							{stateNameMap[historyState] || historyState}
							{#if index < fullHistory.length - 1}→{/if}
						</span>
					{/each}
					{#if $stateInfo.current_state}
						→ <span class="current-history-state">{currentStateLabel}</span>
					{/if}
				</div>
			{/if}
		</div>
		
		<svg class="fsa-graph" viewBox="0 0 800 800" xmlns="http://www.w3.org/2000/svg">
			<!-- Define arrow marker -->
			<defs>
				<marker id="arrowhead" markerWidth="10" markerHeight="7" 
						refX="9" refY="3.5" orient="auto">
					<polygon points="0 0, 10 3.5, 0 7" fill="#666" />
				</marker>
				<marker id="arrowhead-active" markerWidth="10" markerHeight="7" 
						refX="9" refY="3.5" orient="auto">
					<polygon points="0 0, 10 3.5, 0 7" fill="#000" />
				</marker>
			</defs>
			
			<!-- Draw transitions (edges) -->
			{#each transitionData as { opacity, arrowPos, path, shouldShow, label, color }, index (index)}
				{#if shouldShow}
					<g class="transition" style="opacity: {opacity}">
						<path
							d={path}
							stroke={color}
							stroke-width="2"
							fill="none"
							marker-end={opacity > 0.5 ? "url(#arrowhead-active)" : "url(#arrowhead)"}
						/>
						<!-- Transition label -->
						<text
							x={arrowPos.x}
							y={arrowPos.y - 8}
							text-anchor="middle"
							class="transition-label"
							fill={color}
							font-size="10"
						>
							{label}
						</text>
					</g>
				{/if}
			{/each}
			
			<!-- Draw states (nodes) -->
			{#each stateData as { stateName, state, isActive, inHistory, displayName } (stateName)}
				<g class="state" class:active={isActive} class:in-history={inHistory}>
					<!-- State circle -->
					<circle
						cx={state.x}
						cy={state.y}
						r="35"
						fill={isActive ? state.color : (inHistory ? state.color + '80' : state.color + '20')}
						stroke={isActive ? '#000' : state.color}
						stroke-width={isActive ? '3' : '2'}
					/>
					
					<!-- State label -->
					<text
						x={state.x}
						y={state.y + 5}
						text-anchor="middle"
						class="state-label"
						fill="#000"
						font-weight={isActive ? 'bold' : 'normal'}
					>
						{displayName}
					</text>
					
					<!-- Active state indicator -->
					{#if isActive}
						<circle
							cx={state.x}
							cy={state.y}
							r="45"
							fill="none"
							stroke={state.color}
							stroke-width="2"
							stroke-dasharray="5,5"
							opacity="0.8"
						>
							<animateTransform
								attributeName="transform"
								type="rotate"
								values="0 {state.x} {state.y};360 {state.x} {state.y}"
								dur="2s"
								repeatCount="indefinite"
							/>
						</circle>
					{/if}
				</g>
			{/each}
		</svg>
	</div>
</div>

<style>
	.fsa-visualization {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--bg-secondary);
		border-radius: 8px;
		overflow: hidden;
	}

	.panel-header {
		padding: 0.75rem 1rem;
		background: var(--bg-tertiary);
		border-bottom: 1px solid var(--border-color);
		font-weight: 600;
		font-size: 0.875rem;
		color: var(--text-primary);
	}

	.panel-content {
		flex: 1;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.fsa-info {
		margin-bottom: 1rem;
	}

	.state-info {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.5rem;
	}

	.current-state {
		font-weight: bold;
		font-size: 1rem;
	}

    .error-state {
        color: var(--accent-red);
    }


	.progress {
		font-size: 0.875rem;
		color: var(--text-secondary);
		background: var(--bg-tertiary);
		padding: 0.25rem 0.5rem;
		border-radius: 12px;
	}

	.error {
		color: var(--accent-red);
		font-size: 0.875rem;
		margin-top: 0.5rem;
	}

	.state-history {
		font-size: 0.75rem;
		color: var(--text-secondary);
		margin-top: 0.5rem;
		line-height: 1.4;
	}

	.history-state {
		color: var(--text-primary);
		background: var(--bg-tertiary);
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		margin: 0 0.125rem;
	}

	.current-history-state {
		color: var(--accent-blue);
		background: color-mix(in srgb, var(--accent-blue) 20%, var(--bg-tertiary));
		padding: 0.125rem 0.375rem;
		border-radius: 4px;
		font-weight: 500;
	}

	.fsa-graph {
		flex: 1;
		width: 100%;
		height: 100%;
		min-height: 200px;
        display: block;
	}

	.state {
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.state:hover {
		opacity: 0.8;
	}

	.state.active {
		filter: drop-shadow(0 0 8px rgba(0, 0, 0, 0.3));
	}

	.state-label {
		font-size: 11px;
		font-weight: 500;
		user-select: none;
		pointer-events: none;
	}

	.transition {
		transition: opacity 0.3s ease;
	}

	.transition-label {
		font-weight: 500;
		user-select: none;
		pointer-events: none;
	}

	.transition:hover {
		opacity: 1 !important;
	}
</style> 