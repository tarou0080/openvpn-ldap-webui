#!/usr/bin/env python3
"""
Internationalization (i18n) support module
Simple JSON dictionary-based translation system without Flask-Babel
"""

import json
import os
from flask import request, session
from functools import wraps

# Translation dictionary cache
_translations = {}
_default_language = None  # Will be set from config
_supported_languages = ['ja', 'en']

def load_translations():
    """Load translation dictionaries"""
    global _translations, _default_language
    
    # Import default language from config
    try:
        from config import DEFAULT_LANGUAGE
        _default_language = DEFAULT_LANGUAGE
    except ImportError:
        _default_language = 'en'
    
    translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
    
    for lang in _supported_languages:
        translation_file = os.path.join(translations_dir, f'messages_{lang}.json')
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Translation file not found: {translation_file}")
            _translations[lang] = {}
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse translation file {translation_file}: {e}")
            _translations[lang] = {}

def get_locale():
    """Get current language"""
    # Get language setting from Cookie
    lang = request.cookies.get('lang')
    
    # If not in Cookie, determine from Accept-Language header
    if not lang:
        lang = request.accept_languages.best_match(_supported_languages)
    
    # Fall back to default language
    if not lang or lang not in _supported_languages:
        lang = _default_language
    
    return lang

def _(message, **kwargs):
    """
    Translate message
    
    Args:
        message: Message to translate (key)
        **kwargs: Values to substitute into message placeholders
    
    Returns:
        Translated message
    """
    lang = get_locale()
    
    # Get from translation dictionary
    translated = _translations.get(lang, {}).get(message, message)
    
    # Replace placeholders
    if kwargs:
        try:
            translated = translated.format(**kwargs)
        except KeyError:
            # Return original message if placeholder not found
            pass
    
    return translated

def get_supported_languages():
    """Get list of supported languages"""
    return _supported_languages

def get_current_language():
    """Get current language code"""
    return get_locale()

# Context processor for Jinja2 templates
def inject_i18n():
    """Inject translation function into Jinja2 templates"""
    return {
        '_': _,
        'get_locale': get_locale,
        'current_lang': get_locale()
    }
