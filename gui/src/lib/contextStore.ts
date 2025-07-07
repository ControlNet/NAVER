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

export function handleContext(msg: any) {
    entities.set(msg.body.entities ?? []);
    relations.set(msg.body.relations ?? []);
    attributes.set(msg.body.attributes ?? []);
}
