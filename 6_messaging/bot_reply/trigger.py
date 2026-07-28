"""Pure decision function for whether an incoming message should get an AI-drafted
reply. No Telethon objects in the signature — trigger.py is testable standalone."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChatConfig:
    enabled: bool
    trigger_mode: Optional[str] = None  # None = inherit global; 'always' | 'mentions' | 'off'
    member_count: Optional[int] = None


@dataclass
class GlobalSettings:
    trigger_mode: str = "mentions"  # 'always' | 'mentions' | 'off'
    small_group_max_size: int = 50


@dataclass
class MessageMeta:
    is_own_message: bool = False
    is_from_bot: bool = False
    is_mention: bool = False
    is_reply_to_operator: bool = False


def should_reply(chat_cfg: ChatConfig, globals_: GlobalSettings, msg_meta: MessageMeta) -> bool:
    if not chat_cfg.enabled:
        return False
    if msg_meta.is_own_message or msg_meta.is_from_bot:
        return False

    mode = chat_cfg.trigger_mode or globals_.trigger_mode
    if mode == "off":
        return False

    mentioned = msg_meta.is_mention or msg_meta.is_reply_to_operator
    if mode == "mentions":
        return mentioned
    if mode == "always":
        if chat_cfg.member_count is not None and chat_cfg.member_count > globals_.small_group_max_size:
            return mentioned  # large group: downgrade to mentions-only
        return True
    return False


if __name__ == "__main__":
    g = GlobalSettings(trigger_mode="mentions", small_group_max_size=50)

    # disabled chat never replies, regardless of mode
    assert should_reply(ChatConfig(enabled=False, trigger_mode="always"), g, MessageMeta()) is False

    # own messages and bot messages never trigger a reply
    assert should_reply(ChatConfig(enabled=True, trigger_mode="always"), g,
                         MessageMeta(is_own_message=True)) is False
    assert should_reply(ChatConfig(enabled=True, trigger_mode="always"), g,
                         MessageMeta(is_from_bot=True)) is False

    # explicit 'off' on the chat wins over an 'always' global
    assert should_reply(ChatConfig(enabled=True, trigger_mode="off"), g, MessageMeta()) is False

    # 'mentions' mode requires a mention or a reply-to-operator
    assert should_reply(ChatConfig(enabled=True, trigger_mode="mentions"), g, MessageMeta()) is False
    assert should_reply(ChatConfig(enabled=True, trigger_mode="mentions"), g,
                         MessageMeta(is_mention=True)) is True
    assert should_reply(ChatConfig(enabled=True, trigger_mode="mentions"), g,
                         MessageMeta(is_reply_to_operator=True)) is True

    # 'always' mode in a small group replies to everything
    assert should_reply(ChatConfig(enabled=True, trigger_mode="always", member_count=10), g,
                         MessageMeta()) is True

    # 'always' mode in a large group downgrades to mentions-only
    assert should_reply(ChatConfig(enabled=True, trigger_mode="always", member_count=500), g,
                         MessageMeta()) is False
    assert should_reply(ChatConfig(enabled=True, trigger_mode="always", member_count=500), g,
                         MessageMeta(is_mention=True)) is True

    # chat_cfg.trigger_mode=None inherits the global mode
    assert should_reply(ChatConfig(enabled=True, trigger_mode=None), g, MessageMeta()) is False
    g_always = GlobalSettings(trigger_mode="always", small_group_max_size=50)
    assert should_reply(ChatConfig(enabled=True, trigger_mode=None, member_count=5),
                         g_always, MessageMeta()) is True

    print("trigger.py smoke check OK")
