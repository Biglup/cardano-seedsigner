"""Shared rejection screen for the transaction and message signing flows."""

from dataclasses import dataclass, field

from seedsigner.gui.components import GUIConstants, TextArea

from ..screen import DireWarningScreen


@dataclass
class RejectionDetailScreen(DireWarningScreen):
    """Dire warning that stacks colored detail lines below the headline.

    ``extra_lines`` is a list of ``(text, color)`` pairs the view supplies to
    explain why a request was rejected. They are centered and stacked below the
    headline component the parent screen renders.
    """
    extra_lines: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()

        last = self.components[-1]
        cur_y = last.screen_y + last.height + GUIConstants.COMPONENT_PADDING

        for text, color in self.extra_lines:
            ta = TextArea(
                text=text,
                font_size=GUIConstants.get_body_font_size(),
                font_color=color,
                screen_x=0,
                screen_y=cur_y,
                is_text_centered=True,
                auto_line_break=False,
            )
            self.components.append(ta)
            cur_y += ta.height + 2
