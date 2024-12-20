from typing import List, Tuple
from thefuzz import fuzz
from dataclasses import dataclass
from core.contact_manager import Contact

@dataclass
class MatchScore:
    confidence: float
    match_reason: str
    fields_matched: List[str]

class ContactMatcher:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
    
    def find_matches(self, contacts: List[Contact]) -> List[Tuple[Contact, Contact, MatchScore]]:
        matches = []
        
        for i, contact1 in enumerate(contacts):
            for contact2 in contacts[i+1:]:
                score = self._calculate_match_score(contact1, contact2)
                if score.confidence >= self.threshold:
                    matches.append((contact1, contact2, score))
        
        return matches
    
    def _calculate_match_score(self, contact1: Contact, contact2: Contact) -> MatchScore:
        scores = []
        matched_fields = []
        
        # Email exact match
        if contact1.email and contact2.email and contact1.email == contact2.email:
            scores.append(1.0)
            matched_fields.append('email')
        
        # Name fuzzy match
        if contact1.first_name and contact2.first_name:
            name_score = fuzz.ratio(contact1.first_name.lower(), contact2.first_name.lower()) / 100
            if name_score > 0.8:
                scores.append(name_score)
                matched_fields.append('first_name')
        
        # Phone number matching (normalized)
        if contact1.phone and contact2.phone:
            normalized_phone1 = self._normalize_phone(contact1.phone)
            normalized_phone2 = self._normalize_phone(contact2.phone)
            if normalized_phone1 == normalized_phone2:
                scores.append(1.0)
                matched_fields.append('phone')
        
        if not scores:
            return MatchScore(0.0, "No matching fields", [])
        
        return MatchScore(
            confidence=sum(scores) / len(scores),
            match_reason=f"Matched on {', '.join(matched_fields)}",
            fields_matched=matched_fields
        ) 
    
    def _normalize_phone(self, phone: str) -> str:
        """Remove all non-digit characters from phone number."""
        return ''.join(filter(str.isdigit, phone))