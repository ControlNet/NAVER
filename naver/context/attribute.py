from dataclasses import dataclass

@dataclass
class Attribute:
    entity_id: str
    attribute_name: str
    prob: float

    @classmethod
    def to_scallop_type(cls):
        return "type attribute(entity_id: String, attribute_name: String)"
    
    @classmethod
    def to_problog_type(cls):
        return r"% attribute(entity_id: str, attribute_name: str)"

    def to_scallop_rel(self):
        return f"""rel {self.prob}::attribute("{self.entity_id}", "{self.attribute_name}")"""
    
    def to_problog_rel(self):
        return f"""{self.prob}::attribute("{self.entity_id}", "{self.attribute_name}")."""
    
    def to_statement(self):
        return f"""{self.entity_id}: the object has the attribute {self.attribute_name} (confidence: {round(self.prob * 100, 2)}%)."""
