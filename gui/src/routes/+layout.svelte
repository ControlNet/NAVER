<script lang="ts">
	import './app.css';
	
	let { children } = $props();
</script>

<main>
	{@render children()}
</main>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		background: #f8f9fa;
		color: #212529;
	}

	:global(*) {
		box-sizing: border-box;
	}

	main {
		width: 100%;
		min-height: 100vh;
		overflow-y: auto;
	}

	/* Dark mode support */
	@media (prefers-color-scheme: dark) {
		:global(body) {
			background: #1a1a1a;
			color: #ffffff;
		}
	}
</style>
