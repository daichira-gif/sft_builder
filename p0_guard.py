from typing import Any, Dict, List, Tuple

from .config import MAX_SEQ_LEN, MODEL_NAME, REJECT_LOG
from .utils import append_jsonl, now_ms


class P0Guard:
    """Boundary-based 0-valid reject filter.

    If tokenizer is unavailable (e.g., offline local run), you can disable
    the guard by passing disabled=True.
    """

    def __init__(self, disabled: bool = False):
        self.disabled = disabled
        self.tokenizer = None

    def load_tokenizer(self):
        if self.disabled or self.tokenizer is not None:
            return
        from transformers import AutoTokenizer

        tok = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        if tok.pad_token_id is None and tok.eos_token_id is not None:
            tok.pad_token = tok.eos_token
        self.tokenizer = tok

    def _apply_chat(self, messages, add_generation_prompt: bool, max_length: int):
        t = self.tokenizer
        if hasattr(t, "apply_chat_template") and getattr(t, "chat_template", None):
            return t.apply_chat_template(
                messages,
                add_generation_prompt=add_generation_prompt,
                tokenize=True,
                truncation=True,
                max_length=max_length,
            )
        # Fallback
        text = ""
        for m in messages:
            text += f"[{m.get('role','')}]\n{m.get('content','')}\n"
        if add_generation_prompt:
            text += "[assistant]\n"
        return t(text, truncation=True, max_length=max_length).get("input_ids", [])

    def estimate_boundary(self, messages: List[Dict[str, Any]], max_length: int) -> Tuple[int, int, int, Dict[str, Any]]:
        if (not isinstance(messages, list)) or len(messages) == 0:
            return -1, -1, 0, {"reason": "messages_not_list_or_empty"}

        last = messages[-1]
        if last.get("role") != "assistant":
            return -1, -1, 0, {"reason": "last_role_not_assistant", "last_role": last.get("role")}

        assistant_text = str(last.get("content", "") or "")
        if assistant_text.strip() == "":
            return -1, -1, 0, {"reason": "assistant_empty"}

        prefix_ids = self._apply_chat(messages[:-1], add_generation_prompt=True, max_length=max_length)
        full_ids = self._apply_chat(messages, add_generation_prompt=False, max_length=max_length)

        boundary = len(prefix_ids)
        full_len = len(full_ids)
        supervised = max(0, full_len - boundary)

        reason = "ok"
        if boundary <= 0:
            reason = "boundary_le_0"
        elif boundary >= full_len:
            reason = "boundary_ge_full_len"
        elif supervised <= 0:
            reason = "supervised_le_0"

        dbg = {
            "reason": reason,
            "boundary": boundary,
            "full_len": full_len,
            "supervised_tokens": supervised,
            "max_length": max_length,
        }
        return boundary, full_len, supervised, dbg

    def reject_if_0valid(self, messages: List[Dict[str, Any]], sample_meta: dict) -> Tuple[bool, Dict[str, Any]]:
        if self.disabled:
            return True, {"reason": "disabled"}
        if self.tokenizer is None:
            self.load_tokenizer()
        boundary, full_len, supervised, dbg = self.estimate_boundary(messages, max_length=MAX_SEQ_LEN)
        keep = (dbg.get("reason") == "ok")
        if not keep:
            append_jsonl(
                REJECT_LOG,
                {
                    "ts_ms": now_ms(),
                    "reason": dbg.get("reason"),
                    "boundary": boundary,
                    "full_len": full_len,
                    "supervised_tokens": supervised,
                    "meta": sample_meta,
                    "messages_tail": messages[-3:] if isinstance(messages, list) else None,
                },
            )
        return keep, dbg

