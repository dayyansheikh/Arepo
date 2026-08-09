"""Safe repeated-card rendering for the published Arepo Signals Digest shell."""
from __future__ import annotations

import html

from ..accounts.email import SignalDigestPreparation
from ..accounts.models import DigestEntry


def _direction(entry: DigestEntry) -> str:
    outcome = (entry.outcome_name or "This outcome").strip()
    return (
        f"{outcome} repricing higher"
        if entry.direction == "up"
        else f"{outcome} repricing lower"
    )


def render_signal_cards(entries: list[DigestEntry]) -> tuple[str, str]:
    """Return trusted HTML + plain text; every stored upstream string is escaped locally."""
    html_cards: list[str] = []
    text_cards: list[str] = []
    for entry in entries:
        canonical_url = SignalDigestPreparation.market_url(entry.market_id)
        url = html.escape(canonical_url, quote=True)
        question = html.escape(entry.market_question)
        category = html.escape(entry.category)
        direction = html.escape(_direction(entry))
        strength = round(entry.strength * 100)
        html_cards.append(
            '<span style="display:block;margin:0 0 12px 0;padding:16px 18px;'
            'border:1px solid #ECE9E4;border-radius:10px;background:#FFFFFF;text-align:left">'
            f'<a href="{url}" style="color:#111111;text-decoration:none;font-weight:600" '
            f'target="_blank">{question}</a>'
            f'<span style="display:block;margin-top:6px;color:#746F68;font-size:12px">'
            f'{category} · {direction}</span>'
            f'<span style="display:block;margin-top:4px;color:#3F3D39;font-size:12px">'
            f'Priority {entry.research_priority}/100 · Signal strength {strength}%</span>'
            f'<a href="{url}" style="display:inline-block;margin-top:9px;color:#B20A0C;'
            'font-size:12px;font-weight:600;text-decoration:underline" target="_blank">'
            'Open market</a></span>'
        )
        text_cards.append(
            f"{entry.rank}. {entry.market_question}\n"
            f"{entry.category} · {_direction(entry)} · Priority {entry.research_priority}/100 · "
            f"Signal strength {strength}%\n{canonical_url}"
        )
    return "".join(html_cards), "\n\n".join(text_cards)
