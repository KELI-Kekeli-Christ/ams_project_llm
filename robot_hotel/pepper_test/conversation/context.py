#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conversation context management for pepper_test module.
"""

class ConversationContext:
    """Gère le contexte de la conversation pour les réservations"""
    
    def __init__(self):
        """Initialise le contexte de conversation"""
        self.in_reservation_mode = False
        self.collected_info = {}
        self.missing_fields = []
    
    def reset(self):
        """Réinitialise le contexte"""
        self.in_reservation_mode = False
        self.collected_info = {}
        self.missing_fields = []
    
    def start_reservation(self):
        """Démarre le mode réservation"""
        self.in_reservation_mode = True
    
    def end_reservation(self):
        """Termine le mode réservation"""
        self.in_reservation_mode = False
    
    def update_info(self, key, value):
        """Met à jour une information collectée"""
        if value and value.lower() not in ["inconnu", ""]:
            self.collected_info[key] = value
    
    def get_info(self, key, default=None):
        """Récupère une information collectée"""
        return self.collected_info.get(key, default)
    
    def set_missing_fields(self, fields):
        """Définit les champs manquants"""
        self.missing_fields = fields
    
    def has_missing_fields(self):
        """Vérifie s'il y a des champs manquants"""
        return len(self.missing_fields) > 0
    
    def to_dict(self):
        """Convertit le contexte en dictionnaire"""
        return {
            "in_reservation_mode": self.in_reservation_mode,
            "collected_info": self.collected_info.copy(),
            "missing_fields": self.missing_fields.copy()
        }
    
    def __repr__(self):
        return "ConversationContext(in_reservation_mode={}, collected_info={}, missing_fields={})".format(
            self.in_reservation_mode,
            self.collected_info,
            self.missing_fields
        )

