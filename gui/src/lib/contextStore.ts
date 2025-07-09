import { writable } from 'svelte/store';

export interface Entity {
    id: string;
    category: string;
    bbox: [number, number, number, number];  // [x1,y1,x2,y2]
    bbox_confidence: number;
}

// the type of RelationName, it is a list of 2 elements, the first is the relation name, the second is the confidence
export type RelationName = [string, number];

export interface Relation {
    object_entity_id: string;
    subject_entity_id: string;
    relation_name: RelationName[];
}

export interface Attribute {
    entity_id: string;
    attribute_name: string;
    prob: number;
}

export const entities = writable<Entity[]>([]);
export const relations = writable<Relation[]>([]);   // keep it now
export const attributes = writable<Attribute[]>([]);
export const finalResultEntityId = writable<string | null>(null);
export const finalResultIoU = writable<number | null>(null);

function calculateIoU(bbox1: number[], bbox2: number[]): number {
    const [x1_1, y1_1, x2_1, y2_1] = bbox1;
    const [x1_2, y1_2, x2_2, y2_2] = bbox2;
    
    // Calculate intersection area
    const x1_inter = Math.max(x1_1, x1_2);
    const y1_inter = Math.max(y1_1, y1_2);
    const x2_inter = Math.min(x2_1, x2_2);
    const y2_inter = Math.min(y2_1, y2_2);
    
    // Check if there's no intersection
    if (x1_inter >= x2_inter || y1_inter >= y2_inter) {
        return 0;
    }
    
    const intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter);
    
    // Calculate union area
    const area1 = (x2_1 - x1_1) * (y2_1 - y1_1);
    const area2 = (x2_2 - x1_2) * (y2_2 - y1_2);
    const union = area1 + area2 - intersection;
    
    return union > 0 ? intersection / union : 0;
}

function findBestMatchingEntity(finalResultBbox: number[], contextEntities: Entity[]): { entityId: string | null, iou: number | null } {
    let bestMatch: string | null = null;
    let highestIoU = 0;
    const IoU_THRESHOLD = 0.5;
    
    for (const entity of contextEntities) {
        const iou = calculateIoU(finalResultBbox, entity.bbox);
        if (iou > highestIoU && iou > IoU_THRESHOLD) {
            highestIoU = iou;
            bestMatch = entity.id;
        }
    }
    
    return {
        entityId: bestMatch,
        iou: bestMatch ? highestIoU : null
    };
}

export function handleContext(msg: any) {
    const contextEntities = msg.body.entities ?? [];
    const finalResultEntityPrefix = '__final_result__';
    
    // Handle final result with soft matching
    if (msg.body.final_result) {
        const finalResultBbox = msg.body.final_result.bbox;
        const matchResult = findBestMatchingEntity(finalResultBbox, contextEntities);
        
        console.log('Final result bbox:', finalResultBbox);
        console.log('Matched entity ID:', matchResult.entityId);
        console.log('Match IoU:', matchResult.iou);
        
        let updatedEntities = [...contextEntities];
        let finalEntityId: string | null = null;
        
        if (matchResult.entityId) {
            // Found a matching entity, use it
            finalEntityId = matchResult.entityId;
        } else {
            // No matching entity found, create a new one for the final result
            const finalResultEntity: Entity = {
                id: finalResultEntityPrefix + '0',
                category: msg.body.final_result.category,
                bbox: finalResultBbox as [number, number, number, number],
                bbox_confidence: msg.body.final_result.bbox_confidence
            };
            updatedEntities.push(finalResultEntity);
            finalEntityId = finalResultEntity.id;
        }
        
        entities.set(updatedEntities);
        finalResultEntityId.set(finalEntityId);
        finalResultIoU.set(matchResult.iou);
    } else {
        // No final result, just set the context entities
        entities.set(contextEntities);
        finalResultEntityId.set(null);
        finalResultIoU.set(null);
    }
    
    relations.set(msg.body.relations ?? []);
    attributes.set(msg.body.attributes ?? []);
}
