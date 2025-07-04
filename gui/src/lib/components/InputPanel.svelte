<script lang="ts">
	import { executionState } from '$lib/stores.js';

	export let disabled: boolean = false;
	export let onstartExecution: ((event: { detail: { imageFile: File; query: string } }) => void) | null = null;
	export let onstopExecution: ((event: { detail: {} }) => void) | null = null;
	export let onclearAll: ((event: { detail: {} }) => void) | null = null;

	let imageFile: File | null = null;
	let query: string = '';
	let fileInput: HTMLInputElement;
	let imagePreview: string | null = null;

	function handleFileSelect(event: Event): void {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		if (file && file.type.startsWith('image/')) {
			imageFile = file;
			imagePreview = URL.createObjectURL(file);
		}
	}

	function handleDrop(event: DragEvent): void {
		event.preventDefault();
		const file = event.dataTransfer?.files[0];
		if (file && file.type.startsWith('image/')) {
			imageFile = file;
			imagePreview = URL.createObjectURL(file);
			if (fileInput && event.dataTransfer) {
			fileInput.files = event.dataTransfer.files;
			}
		}
	}

	function handleDragOver(event: DragEvent): void {
		event.preventDefault();
	}

	function startExecution(): void {
		if (imageFile && query.trim() && onstartExecution) {
				onstartExecution({ detail: { imageFile, query } });
		}
	}

	function stopExecution(): void {
		if (onstopExecution) {
			onstopExecution({ detail: {} });
		}
	}

	function clearAll(): void {
		imageFile = null;
		query = '';
		if (imagePreview) {
			URL.revokeObjectURL(imagePreview);
			imagePreview = null;
		}
		if (fileInput) {
			fileInput.value = '';
		}
		if (onclearAll) {
			onclearAll({ detail: {} });
		}
	}

	$: canStart = !disabled && imageFile && query.trim() && !$executionState.isRunning;
	$: canStop = !disabled && $executionState.isRunning;
</script>

<div class="input-panel">
	<div class="panel-header">
		📤 Input
	</div>
	
	<div class="panel-content">
		<!-- Main Content Area - Horizontal Layout -->
		<div class="main-content-area">
			<!-- Image Upload -->
			<div class="image-section">
				<label class="image-upload" for="image-input">
					<div 
						class="drop-zone" 
						class:has-image={imagePreview}
						ondrop={handleDrop}
						ondragover={handleDragOver}
						role="button"
						tabindex="0"
						aria-label="Upload image by drag and drop or click to select"
					>
						{#if imagePreview}
							<img src={imagePreview} alt="Preview" class="image-preview" />
						{:else}
							<div class="upload-placeholder">
								<div class="upload-icon">📷</div>
								<div class="upload-text">
									<strong>Upload Image</strong><br>
									Drag & drop or click to select
								</div>
							</div>
						{/if}
					</div>
				</label>
				<input 
					id="image-input"
					type="file" 
					accept="image/*" 
					bind:this={fileInput}
					onchange={handleFileSelect}
					{disabled}
					style="display: none;"
				>
			</div>

			<!-- Query Input -->
			<div class="query-section">
				<label for="query-input">💬 Query</label>
				<textarea 
					id="query-input"
					bind:value={query}
					placeholder="Describe what you want the agent to find or analyze..."
					{disabled}
				></textarea>
			</div>
		</div>

		<!-- Action Buttons -->
		<div class="action-buttons">
			<button 
				class="btn btn-primary"
				onclick={startExecution}
				disabled={!canStart}
			>
				🚀 Start Agent Execution
			</button>
			
			<button 
				class="btn btn-danger"
				onclick={stopExecution}
				disabled={!canStop}
			>
				⏹️ Stop
			</button>
			
			<button 
				class="btn"
				onclick={clearAll}
				{disabled}
			>
				🗑️ Clear
			</button>
		</div>

		<!-- Status Display -->
		{#if $executionState.isRunning}
			<div class="status-display">
				<div class="status-indicator pulse">
					🔄 {$executionState.currentState}
				</div>
				{#if $executionState.progress > 0}
					<div class="progress-bar">
						<div class="progress-fill" style="width: {$executionState.progress}%"></div>
					</div>
				{/if}
			</div>
		{/if}

		{#if $executionState.error}
			<div class="error-display">
				❌ {$executionState.error}
			</div>
		{/if}
	</div>
</div>

<style>
	.input-panel {
		height: 100%;
		max-height: 400px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.panel-content {
		flex: 1;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		overflow: hidden;
	}

	.main-content-area {
		flex: 1;
		display: flex;
		gap: 1rem;
		overflow: hidden;
	}

	.image-section {
		flex: 0 0 250px;
		max-height: 100%;
		overflow: hidden;
	}

	.image-upload {
		display: block;
		cursor: pointer;
		height: 100%;
		width: 100%;
	}

	.drop-zone {
		height: 100%;
		width: 100%;
		border: 2px dashed var(--border-color);
		border-radius: 8px;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
		background: var(--bg-tertiary);
		overflow: hidden;
	}

	.drop-zone:hover {
		border-color: var(--accent-blue);
		background: var(--bg-secondary);
	}

	.drop-zone.has-image {
		border-style: solid;
		border-color: var(--accent-green);
	}

	.upload-placeholder {
		text-align: center;
		color: var(--text-secondary);
	}

	.upload-icon {
		font-size: 2rem;
		margin-bottom: 0.5rem;
	}

	.upload-text {
		font-size: 0.875rem;
		line-height: 1.4;
	}

	.image-preview {
		max-width: 100%;
		max-height: 100%;
		object-fit: contain;
		border-radius: 6px;
	}

	.query-section {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.query-section label {
		display: block;
		margin-bottom: 0.5rem;
		font-weight: 500;
		color: var(--text-primary);
		flex: 0 0 auto;
	}

	.query-section textarea {
		flex: 1;
		resize: none;
		min-height: 100px;
		width: 100%;
		overflow-y: auto;
	}

	.action-buttons {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
		flex: 0 0 auto;
	}

	.action-buttons .btn {
		flex: 1;
		min-width: 120px;
	}

	.status-display {
		flex: 0 0 auto;
		padding: 0.75rem;
		background: var(--bg-secondary);
		border-radius: 6px;
		border-left: 4px solid var(--accent-blue);
	}

	.status-indicator {
		font-weight: 500;
		color: var(--accent-blue);
		margin-bottom: 0.5rem;
	}

	.progress-bar {
		height: 4px;
		background: var(--bg-tertiary);
		border-radius: 2px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--accent-blue);
		transition: width 0.3s ease;
	}

	.error-display {
		flex: 0 0 auto;
		padding: 0.75rem;
		background: var(--bg-secondary);
		border-radius: 6px;
		border-left: 4px solid var(--accent-red);
		color: var(--accent-red);
		font-weight: 500;
	}

	@media (max-width: 1024px) {
		.image-section {
			flex: 0 0 200px;
		}
	}

	@media (max-width: 768px) {
		.main-content-area {
			flex-direction: column;
		}

		.image-section {
			flex: 0 0 150px;
			max-height: 150px;
		}

		.query-section textarea {
			min-height: 80px;
		}

		.action-buttons {
			flex-direction: column;
		}

		.action-buttons .btn {
			min-width: auto;
		}
	}
</style> 