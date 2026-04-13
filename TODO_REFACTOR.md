# Refactoring Plan: Split pepper_test/main.py into smaller modules

## Objective
Refactor only `robot_hotel/pepper_test/main.py` into smaller, maintainable modules.

---

## Part 2: robot_hotel/pepper_test/main.py (Pepper Client)

### Current: Single file with all robot logic (~1500 lines)

### Proposed Structure:
```
robot_hotel/pepper_test/
├── config.py               # Already exists - keep configuration
├── utils/
│   ├── __init__.py
│   ├── helpers.py         # safe_print, escape_html, transliterate, etc.
│   └── language.py        # Language code mapping
├── pepper/
│   ├── __init__.py
│   ├── robot_manager.py   # RobotManager class
│   ├── tts.py             # Text-to-speech functions
│   ├── tablet.py           # Tablet display functions
│   └── camera.py          # Camera/video functions
├── api/
│   ├── __init__.py
│   ├── client.py          # record_audio, transcribe, chat functions
│   └── flask_check.py     # Flask server check/start
├── conversation/
│   ├── __init__.py
│   ├── flow.py            # Main conversation loop
│   └── context.py         # Conversation context management
├── ui/
│   ├── __init__.py
│   └── tablet_html.py     # HTML generation for tablet
└── main.py                # Entry point (imports and calls conversation)
```

### Steps:
- [x] 2.1 Create `robot_hotel/pepper_test/utils/__init__.py`
- [x] 2.2 Create `robot_hotel/pepper_test/utils/helpers.py` - Extract helper functions
- [x] 2.3 Create `robot_hotel/pepper_test/utils/language.py` - Language mapping
- [x] 2.4 Create `robot_hotel/pepper_test/pepper/__init__.py`
- [x] 2.5 Create `robot_hotel/pepper_test/pepper/robot_manager.py` - RobotManager class
- [x] 2.6 Create `robot_hotel/pepper_test/pepper/tts.py` - TTS functions
- [x] 2.7 Create `robot_hotel/pepper_test/pepper/tablet.py` - Tablet functions
- [x] 2.8 Create `robot_hotel/pepper_test/pepper/camera.py` - Camera functions
- [x] 2.9 Create `robot_hotel/pepper_test/api/__init__.py`
- [x] 2.10 Create `robot_hotel/pepper_test/api/client.py` - API client functions
- [x] 2.11 Create `robot_hotel/pepper_test/api/flask_check.py` - Flask check/start
- [x] 2.12 Create `robot_hotel/pepper_test/conversation/__init__.py`
- [x] 2.13 Create `robot_hotel/pepper_test/conversation/context.py` - Context class
- [x] 2.14 Create `robot_hotel/pepper_test/conversation/flow.py` - Main loop
- [x] 2.15 Create `robot_hotel/pepper_test/ui/__init__.py`
- [x] 2.16 Create `robot_hotel/pepper_test/ui/tablet_html.py` - HTML generation
- [x] 2.17 Create `robot_hotel/pepper_test/config.py` - Configuration
- [x] 2.18 Simplify `robot_hotel/pepper_test/main.py` - Entry point

