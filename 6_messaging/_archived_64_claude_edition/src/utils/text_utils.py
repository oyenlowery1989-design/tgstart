
"""
FILE: src/utils/text_utils.py
PURPOSE: Utility functions for text processing, Mention regex, and Diff generation.
"""
import re
import difflib
from telethon import types

# Regex for mentions
MENTION_RE = re.compile(r"@([A-Za-z0-9_]{4,32})")

def extract_mentions(message_obj):
    """
    Returns a set of usernames (without @) mentioned in the message.
    """
    mentions = set()
    text = message_obj.message or ""
    
    # Regex fallback
    for m in MENTION_RE.finditer(text):
        mentions.add(m.group(1))

    # Entities (more accurate)
    if message_obj.entities:
        for ent in message_obj.entities:
            if isinstance(ent, types.MessageEntityMention):
                offset = ent.offset
                length = ent.length
                username = text[offset+1 : offset+length]
                if username:
                    mentions.add(username)
    
    return mentions

def generate_diff_text(old, new):
    """
    Generates a visual diff with character-level precision for small changes,
    word-level for large changes.
    """
    if old.strip() == new.strip():
        return None
    
    # Use character-level diff for small edits (< 100 chars difference)
    if abs(len(old) - len(new)) < 100:
        return generate_char_diff(old, new)
    else:
        return generate_word_diff(old, new)

def generate_char_diff(old, new):
    """Character-level diff for precise small edits."""
    output = []
    matcher = difflib.SequenceMatcher(None, old, new)
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'delete':
            deleted = old[a0:a1]
            output.append(f"~-{deleted}-~")
        elif opcode == 'insert':
            inserted = new[b0:b1]
            output.append(f"_+{inserted}+_")
        elif opcode == 'replace':
            deleted = old[a0:a1]
            inserted = new[b0:b1]
            output.append(f"~-{deleted}-~")
            output.append(f"_+{inserted}+_")
    
    return "\n".join(output) if output else None

def generate_word_diff(old, new):
    """Word-level diff for large edits."""
    output = []
    matcher = difflib.SequenceMatcher(None, old.split(), new.split())
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == 'delete':
            deleted = " ".join(old.split()[a0:a1])
            output.append(f"~-{deleted}-~")
        elif opcode == 'insert':
            inserted = " ".join(new.split()[b0:b1])
            output.append(f"_+{inserted}+_")
        elif opcode == 'replace':
            deleted = " ".join(old.split()[a0:a1])
            inserted = " ".join(new.split()[b0:b1])
            output.append(f"~-{deleted}-~")
            output.append(f"_+{inserted}+_")
    
    return "\n".join(output) if output else None
