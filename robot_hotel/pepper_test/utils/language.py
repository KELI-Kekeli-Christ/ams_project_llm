#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Language utilities for pepper_test module.
Contains language code mapping for TTS.
"""

# Default robot language configuration
DEFAULT_LANGUAGE = "French"


def map_language_code_to_ald_label(code):
    """Map common ISO language codes to ALTextToSpeech language labels.

    Returns a label expected by ALTextToSpeech.setLanguage (best-effort).
    """
    try:
        if not code:
            return DEFAULT_LANGUAGE
        s = str(code).lower()
        if s.startswith('fr'):
            return 'French'
        if s.startswith('en'):
            return 'English'
        if s.startswith('es'):
            return 'Spanish'
        if s.startswith('de'):
            return 'German'
        if s.startswith('it'):
            return 'Italian'
        if s.startswith('pt'):
            return 'Portuguese'
        if s.startswith('nl'):
            return 'Dutch'
        if s.startswith('ru'):
            return 'Russian'
        if s.startswith('ja'):
            return 'Japanese'
        if s.startswith('ko'):
            return 'Korean'
        if s.startswith('zh'):
            return 'Chinese'
        # Fallback: return configured default
        return DEFAULT_LANGUAGE
    except Exception:
        return DEFAULT_LANGUAGE


def get_language_from_code(code):
    """Get human-readable language name from ISO code.
    
    Args:
        code: ISO language code (e.g., 'fr', 'en', 'es')
    
    Returns:
        str: Human-readable language name
    """
    language_map = {
        'fr': 'Français',
        'en': 'English',
        'es': 'Español',
        'de': 'Deutsch',
        'it': 'Italiano',
        'pt': 'Português',
        'nl': 'Nederlands',
        'ru': 'Русский',
        'ja': '日本語',
        'ko': '한국어',
        'zh': '中文',
    }
    return language_map.get(code.lower()[:2], code)

