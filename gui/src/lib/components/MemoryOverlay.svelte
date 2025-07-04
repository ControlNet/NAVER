<script lang="ts">
	import { entities, currentImage } from '$lib/stores.js';
	import { onDestroy } from 'svelte';
    import ImageWithBoxes from "$lib/components/ImageWithBoxes.svelte";
	
	let imageUrl: string | null = null;
	
	// Clean reactive statement to create URL from File object
	$: {
		// Clean up previous URL if it exists
		if (imageUrl) {
			URL.revokeObjectURL(imageUrl);
			imageUrl = null;
		}
		
		// Create new URL if we have a current image
		if ($currentImage) {
			imageUrl = URL.createObjectURL($currentImage);
		}
	}
	
	// Cleanup on component destroy
	onDestroy(() => {
		if (imageUrl) {
			URL.revokeObjectURL(imageUrl);
		}
	});
</script>

<div class="memory-overlay">
	<div class="panel-header">
		🧠 Logical Context Memory
	</div>
	<div class="panel-content">
		{#if imageUrl}
            <ImageWithBoxes src={imageUrl} alt="Current" className="image-display" />
		{:else}
			<div class="placeholder">No image loaded</div>
		{/if}
		<p>Entities: {$entities.length}</p>
	</div>
</div>

<style>
	.memory-overlay {
		height: 100%;
		display: flex;
		flex-direction: column;
	}

	.panel-content {
		flex: 1;
		padding: 1rem;
	}

	.image-display {
		max-width: 100%;
		max-height: 200px;
		object-fit: contain;
	}

	.placeholder {
		color: var(--text-secondary);
		text-align: center;
		padding: 2rem;
	}
</style> 