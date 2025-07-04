<script lang="ts">
    import { onMount } from 'svelte';
    import { entities } from '../contextStore';

    export let src: string;             // Image URL
    export let alt: string;
    export let className: string;

    let imgEl: HTMLImageElement;
    let displayWidth = 1;
    let displayHeight = 1;
    let originalWidth = 1;
    let originalHeight = 1;

    // ① 监听图片尺寸变化（首次加载 & 窗口 resize）
    function updateSize() {
        if (!imgEl) return;
        displayWidth = imgEl.clientWidth;
        displayHeight = imgEl.clientHeight;
        originalWidth  = imgEl.naturalWidth;
        originalHeight  = imgEl.naturalHeight;
    }
    onMount(() => {
        updateSize();
        window.addEventListener('resize', updateSize);
        imgEl.addEventListener('load', updateSize);
    });

    // Helper function to convert the bbox of original image to actual canvas' bbox (in px)
    const scale = (v:number, total:number, disp:number) => (v/total)*disp;
</script>

<style>
    .wrapper { position: relative; display:inline-block; }
    .bbox    {
        position:absolute;
        border:2px solid #22c55e;          /* emerald-500 */
        background:rgba(34,197,94,.15);    /* transparent filling */
        box-sizing:border-box;
        pointer-events:none;
        border-radius:2px;
    }
    .tag {
        position:absolute;
        top:-1.2rem; left:0;
        font-size:.75rem; color:#fff;
        background:#22c55e; padding:0 .25rem;
        border-radius:2px;
        white-space:nowrap;
    }
</style>

<div class="wrapper">
    <img bind:this={imgEl} src={src} alt={alt} class={className} style="max-width:100%; height:auto;" />

    {#each $entities as e}
        {#if originalWidth && originalHeight}
            <div
                    class="bbox"
                    style="
          left:{scale(e.bbox[0], originalWidth, displayWidth)}px;
          top:{scale(e.bbox[1], originalHeight, displayHeight)}px;
          width:{scale(e.bbox[2]-e.bbox[0], originalWidth, displayWidth)}px;
          height:{scale(e.bbox[3]-e.bbox[1], originalHeight, displayHeight)}px;
        ">
                <span class="tag">{e.category}</span>
            </div>
        {/if}
    {/each}
</div>
