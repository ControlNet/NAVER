<script lang="ts">
    import { onMount } from 'svelte';
    import { entities, relations, attributes } from '../contextStore';

    export let src: string;             // Image URL
    export let alt: string;
    export let className: string;

    let imgEl: HTMLImageElement;
    let containerEl: HTMLDivElement;
    let displayWidth = 1;
    let displayHeight = 1;
    let originalWidth = 1;
    let originalHeight = 1;

    // State for interactive features
    let hoveredEntityId: string | null = null;
    let selectedEntityId: string | null = null;
    let hoveredRelationId: string | null = null;
    let tooltip: { x: number; y: number; entity: any; isFixed: boolean } | null = null;
    let relationTooltip: { x: number; y: number; relation: any } | null = null;
    
    // Tooltip dragging state
    let isDraggingTooltip = false;
    let dragOffset = { x: 0, y: 0 };

    // listen to the image size change
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
        
        // Global mouse events for tooltip dragging
        window.addEventListener('mousemove', handleTooltipMouseMove);
        window.addEventListener('mouseup', handleTooltipMouseUp);
        
        return () => {
            window.removeEventListener('mousemove', handleTooltipMouseMove);
            window.removeEventListener('mouseup', handleTooltipMouseUp);
        };
    });

    // Helper function to convert the bbox of original image to actual canvas' bbox (in px)
    const scale = (v:number, total:number, disp:number) => (v/total)*disp;

    // Get center point of an entity's bounding box
    function getEntityCenter(entity: any) {
        const x = scale((entity.bbox[0] + entity.bbox[2]) / 2, originalWidth, displayWidth);
        const y = scale((entity.bbox[1] + entity.bbox[3]) / 2, originalHeight, displayHeight);
        return { x, y };
    }

    // Get relations for a specific entity
    function getEntityRelations(entityId: string) {
        console.log('getEntityRelations', entityId);
        return $relations.filter(rel => 
            rel.object_entity_id === entityId || rel.subject_entity_id === entityId
        );
    }

    // Get attributes for a specific entity
    function getEntityAttributes(entityId: string) {
        return $attributes.filter(attr => attr.entity_id === entityId);
    }

    // Handle entity hover
    function handleEntityHover(entity: any, event: MouseEvent) {
        // Don't show hover tooltip if another entity is already selected
        if (selectedEntityId && selectedEntityId !== entity.id) {
            return;
        }
        
        hoveredEntityId = entity.id;
        const rect = containerEl.getBoundingClientRect();
        
        // If this entity is selected, don't update the tooltip position (it's fixed)
        if (selectedEntityId === entity.id && tooltip?.isFixed) {
            return;
        }
        
        tooltip = {
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
            entity,
            isFixed: false
        };
    }

    // Handle entity hover leave
    function handleEntityHoverLeave() {
        if (selectedEntityId === null) {
            hoveredEntityId = null;
            tooltip = null;
        } else if (selectedEntityId === hoveredEntityId) {
            // Keep the selected entity hovered, but stop following mouse
            // Tooltip remains fixed at current position
        } else {
            hoveredEntityId = null;
        }
    }
    
    // Handle mouse movement for tooltip following
    function handleEntityMouseMove(entity: any, event: MouseEvent) {
        // Only update tooltip position if not selected or not dragging
        if (selectedEntityId !== entity.id && !isDraggingTooltip) {
            const rect = containerEl.getBoundingClientRect();
            if (tooltip && !tooltip.isFixed) {
                tooltip = {
                    ...tooltip,
                    x: event.clientX - rect.left,
                    y: event.clientY - rect.top
                };
            }
        }
    }

    // Handle entity click
    function handleEntityClick(entity: any) {
        if (selectedEntityId === entity.id) {
            // Deselect if clicking the same entity
            selectedEntityId = null;
            hoveredEntityId = null;
            tooltip = null;
        } else {
            selectedEntityId = entity.id;
            hoveredEntityId = entity.id;
            
            // Make tooltip fixed at current position if it exists
            if (tooltip) {
                tooltip = {
                    ...tooltip,
                    isFixed: true
                };
            }
        }
    }
    
    // Handle tooltip drag start
    function handleTooltipMouseDown(event: MouseEvent) {
        if (tooltip?.isFixed) {
            isDraggingTooltip = true;
            dragOffset = {
                x: event.clientX - tooltip.x,
                y: event.clientY - tooltip.y
            };
            event.preventDefault();
            event.stopPropagation(); // Prevent event bubbling that might clear the tooltip
        }
    }
    
    // Handle tooltip dragging
    function handleTooltipMouseMove(event: MouseEvent) {
        if (isDraggingTooltip && tooltip?.isFixed) {
            const rect = containerEl.getBoundingClientRect();
            tooltip = {
                ...tooltip,
                x: event.clientX - rect.left - dragOffset.x,
                y: event.clientY - rect.top - dragOffset.y
            };
        }
    }
    
    // Handle tooltip drag end
    function handleTooltipMouseUp() {
        isDraggingTooltip = false;
    }

    // Handle relation line hover
    function handleRelationHover(relation: any, event: MouseEvent) {
        // Only show relation tooltip if an entity is selected (not just hovered)
        if (selectedEntityId) {
            hoveredRelationId = relation.id;
            const rect = containerEl.getBoundingClientRect();
            relationTooltip = {
                x: event.clientX - rect.left,
                y: event.clientY - rect.top,
                relation
            };
        }
    }

    // Handle relation hover leave
    function handleRelationHoverLeave() {
        hoveredRelationId = null;
        relationTooltip = null;
    }

    // Get active entity (either hovered or selected)
    $: activeEntityId = selectedEntityId || hoveredEntityId;

    // Get relations to display
    $: activeRelations = activeEntityId ? getEntityRelations(activeEntityId) : [];
</script>

<style>
    .wrapper { 
        position: relative; 
        display: inline-block; 
    }
    
    .bbox {
        position: absolute;
        border: 2px solid #22c55e;          /* emerald-500 */
        background: rgba(34,197,94,.15);    /* transparent filling */
        box-sizing: border-box;
        pointer-events: auto;
        border-radius: 2px;
        cursor: pointer;
        transition: all 0.2s ease;
        z-index: 10;  /* Ensure bounding boxes are above relation lines */
    }
    
    .bbox:hover {
        border-color: #16a34a;
        background: rgba(34,197,94,.25);
        transform: scale(1.02);
    }
    
    .bbox.selected {
        border-color: #dc2626;
        background: rgba(220,38,38,.2);
        border-width: 3px;
    }
    
    .tag {
        position: absolute;
        top: -1.2rem; 
        left: 0;
        font-size: .75rem; 
        color: #fff;
        background: #22c55e; 
        padding: 0 .25rem;
        border-radius: 2px;
        white-space: nowrap;
        pointer-events: none;
    }

    .selected .tag {
        background: #dc2626;
    }

    .relation-line {
        position: absolute;
        background: #3b82f6;
        transform-origin: left center;
        pointer-events: auto;
        cursor: pointer;
        opacity: 0.7;
        transition: opacity 0.2s ease;
    }

    .relation-line:hover {
        opacity: 1;
        background: #1d4ed8;
    }

    .relation-line.persistent {
        background: #dc2626;
        opacity: 0.8;
    }

    .relation-line.persistent:hover {
        background: #b91c1c;
        opacity: 1;
    }

    .tooltip {
        position: absolute;
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 0.875rem;
        max-width: 250px;
        z-index: 1000;
        pointer-events: none;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        user-select: none;
    }
    
    .tooltip.fixed {
        pointer-events: auto;
        cursor: move;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    .tooltip.dragging {
        opacity: 0.8;
        transform: scale(1.02);
    }

    .tooltip-title {
        font-weight: bold;
        margin-bottom: 4px;
        color: #22c55e;
    }

    .tooltip-content {
        line-height: 1.4;
    }

    .relation-tooltip {
        position: absolute;
        background: rgba(59, 130, 246, 0.95);
        color: white;
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 1000;
        pointer-events: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
</style>

<div class="wrapper" bind:this={containerEl}>
    <img bind:this={imgEl} src={src} alt={alt} class={className} style="max-width:100%; height:auto;" />

    <!-- Entity bounding boxes -->
    {#each $entities as entity}
        {#if originalWidth && originalHeight}
            <div
                class="bbox {selectedEntityId === entity.id ? 'selected' : ''}"
                style="
                    left:{scale(entity.bbox[0], originalWidth, displayWidth)}px;
                    top:{scale(entity.bbox[1], originalHeight, displayHeight)}px;
                    width:{scale(entity.bbox[2]-entity.bbox[0], originalWidth, displayWidth)}px;
                    height:{scale(entity.bbox[3]-entity.bbox[1], originalHeight, displayHeight)}px;
                "
                tabindex="0"
                role="button"
                aria-label="Entity: {entity.category}"
                on:mouseenter={(e) => handleEntityHover(entity, e)}
                on:mousemove={(e) => handleEntityMouseMove(entity, e)}
                on:mouseleave={handleEntityHoverLeave}
                on:click={() => handleEntityClick(entity)}
                on:keydown={(e) => e.key === 'Enter' || e.key === ' ' ? handleEntityClick(entity) : null}
            >
                <span class="tag">{entity.category}</span>
            </div>
        {/if}
    {/each}

    <!-- Relation lines -->
    {#each activeRelations as relation}
        {#if originalWidth && originalHeight}
            {@const fromEntity = $entities.find(e => e.id === relation.subject_entity_id)}
            {@const toEntity = $entities.find(e => e.id === relation.object_entity_id)}
            {#if fromEntity && toEntity}
                {@const fromCenter = getEntityCenter(fromEntity)}
                {@const toCenter = getEntityCenter(toEntity)}
                {@const dx = toCenter.x - fromCenter.x}
                {@const dy = toCenter.y - fromCenter.y}
                {@const distance = Math.sqrt(dx * dx + dy * dy)}
                {@const angle = Math.atan2(dy, dx) * 180 / Math.PI}
                <div
                    class="relation-line {selectedEntityId ? 'persistent' : ''}"
                    style="
                        left: {fromCenter.x}px;
                        top: {fromCenter.y}px;
                        width: {distance}px;
                        height: 2px;
                        transform: rotate({angle}deg);
                    "
                    role="img"
                    aria-label="Relations from {relation.subject_entity_id} to {relation.object_entity_id}: {relation.relation_name.filter((r: [string, number]) => r[1] > 0.1).map((r: [string, number]) => r[0]).join(', ')}"
                    on:mouseenter={(e) => handleRelationHover(relation, e)}
                    on:mouseleave={handleRelationHoverLeave}
                ></div>
            {/if}
        {/if}
    {/each}

    <!-- Entity tooltip -->
    {#if tooltip}
        {@const entityAttributes = getEntityAttributes(tooltip.entity.id)}
        <div 
            class="tooltip {tooltip.isFixed ? 'fixed' : ''} {isDraggingTooltip ? 'dragging' : ''}" 
            style="left: {tooltip.x + 10}px; top: {tooltip.y - 10}px;"
            on:mousedown={handleTooltipMouseDown}
            on:click={(e) => { e.preventDefault(); e.stopPropagation(); }}
            on:keydown={(e) => { e.preventDefault(); e.stopPropagation(); }}
            tabindex="-1"
            role="dialog"
            aria-label="Entity information tooltip"
        >
            <div class="tooltip-title">{tooltip.entity.category}</div>
            <div class="tooltip-content">
                <div><strong>ID:</strong> {tooltip.entity.id}</div>
                <div><strong>Confidence:</strong> {(tooltip.entity.bbox_confidence * 100).toFixed(1)}%</div>
                <div><strong>BBox:</strong> [{tooltip.entity.bbox.map((b: number) => b.toFixed(0)).join(', ')}]</div>
                {#if activeRelations.length > 0}
                    <div><strong>Relations:</strong> {activeRelations.length}</div>
                {/if}
                {#if entityAttributes.length > 0}
                    <div style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 4px;">
                        <div style="color: #fbbf24; font-weight: bold; margin-bottom: 2px;">Attributes:</div>
                        {#each entityAttributes as attr}
                            <div style="font-size: 0.8rem; margin: 1px 0;">
                                <span style="color: #a3a3a3;">{attr.attribute_name}:</span> {(attr.prob * 100).toFixed(1)}%
                            </div>
                        {/each}
                    </div>
                {/if}
            </div>
        </div>
    {/if}

    <!-- Relation tooltip -->
    {#if relationTooltip}
        {@const significantRelations = relationTooltip.relation.relation_name.filter((r: [string, number]) => r[1] > 0.05).sort((a: [string, number], b: [string, number]) => b[1] - a[1])}
        <div 
            class="relation-tooltip" 
            style="left: {relationTooltip.x + 10}px; top: {relationTooltip.y - 10}px;"
        >
            <div><strong>Relations</strong></div>
            <div>From: {relationTooltip.relation.subject_entity_id}</div>
            <div>To: {relationTooltip.relation.object_entity_id}</div>
            <div style="margin-top: 6px;">
                {#each significantRelations as [relName, confidence]}
                    <div style="font-size: 0.75rem; margin: 2px 0;">
                        <span style="color: #fbbf24;">{relName}:</span> {(confidence * 100).toFixed(1)}%
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
