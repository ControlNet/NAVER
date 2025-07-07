import { writable } from 'svelte/store';

export interface Entity {
    id: string;
    category: string;
    bbox: [number, number, number, number];  // [x1,y1,x2,y2]
    bbox_confidence: number;
}

export const entities = writable<Entity[]>([]);
export const relations = writable<any[]>([]);   // keep it now

export function handleContext(msg: any) {
    entities.set(msg.body.entities ?? []);
    relations.set(msg.body.relations ?? []);
}
