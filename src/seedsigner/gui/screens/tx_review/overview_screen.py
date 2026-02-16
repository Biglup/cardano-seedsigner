"""
Transaction overview screen with animated flow diagram.
"""

from dataclasses import dataclass
from gettext import gettext as _

from PIL import Image, ImageDraw, ImageFilter

from seedsigner.gui.components import (
    GUIConstants,
    Fonts,
    TextArea,
)
from seedsigner.models.threads import BaseThread

from ..screen import ButtonListScreen, ButtonOption
from .utils import calc_bezier_curve, linear_interp


@dataclass
class CardanoTxOverviewScreen(ButtonListScreen):
    """
    Overview screen showing transaction flow diagram.
    """
    spend_amount: int = 0
    num_inputs: int = 0
    destination_addresses: list = None
    num_change_outputs: int = 0
    fee_amount: int = 0
    has_tokens: bool = False
    network: str = "mainnet"

    def __post_init__(self):
        self.title = _("Review Tx")
        self.is_bottom_list = True
        self.button_data = [ButtonOption(_("Review details"))]

        super().__post_init__()

        # Display spend amount at the top
        icon_text_lines_y = self.top_nav.height + GUIConstants.COMPONENT_PADDING

        # ADA amount display
        ada = self.spend_amount / 1_000_000
        ada_formatted = f"{ada:,.6f}".rstrip('0').rstrip('.')
        amount_font_size = GUIConstants.get_top_nav_title_font_size() + 2

        # Display amount text centered
        self.components.append(TextArea(
            text=f"{ada_formatted} ADA",
            font_size=amount_font_size,
            font_color=GUIConstants.ACCENT_TEXT_COLOR,
            screen_x=0,
            screen_y=icon_text_lines_y,
            is_text_centered=True,
            auto_line_break=False,
        ))

        # Prep the transaction flow chart
        self.chart_x = 0
        self.chart_y = self.components[-1].screen_y + self.components[-1].height + int(GUIConstants.COMPONENT_PADDING/2)
        chart_height = self.buttons[0].screen_y - self.chart_y - GUIConstants.COMPONENT_PADDING

        # Supersampling for smooth curves
        ssf = 4

        # Create temp supersampled rendering surface
        image = Image.new(
            "RGB",
            (self.canvas_width * ssf, chart_height * ssf),
            GUIConstants.BACKGROUND_COLOR
        )
        draw = ImageDraw.Draw(image)

        font_size = GUIConstants.BODY_FONT_MIN_SIZE * ssf
        font = Fonts.get_font(GUIConstants.get_body_font_name(), font_size)

        (left, top, right, bottom) = font.getbbox(text="abcdefghijklmnopqrstuvwxyz1234567890", anchor="lt")
        chart_text_height = bottom
        vertical_center = int(image.height/2)
        if vertical_center % 2 == 1:
            vertical_center += 1

        association_line_color = "#666"
        association_line_width = 3*ssf
        curve_steps = 4
        chart_font_color = GUIConstants.ACCENT_TEXT_COLOR

        # Build inputs column
        inputs_column = []
        if self.num_inputs == 1:
            inputs_column.append(_("1 input"))
        elif self.num_inputs > 3:
            inputs_column.append(_("input 1"))
            inputs_column.append(_("[ ... ]"))
            inputs_column.append(_("input {}").format(self.num_inputs))
        else:
            for i in range(0, self.num_inputs):
                inputs_column.append(_("input {}").format(i+1))

        max_inputs_text_width = 0
        for input_text in inputs_column:
            left, top, right, bottom = font.getbbox(input_text)
            tw = right - left
            max_inputs_text_width = max(tw, max_inputs_text_width)

        # Curve and center bar dimensions
        curve_width = 4*GUIConstants.COMPONENT_PADDING*ssf
        center_bar_width = 2*GUIConstants.COMPONENT_PADDING*ssf

        # Build destination column with truncated addresses
        destination_column = []
        if self.destination_addresses:
            num_addrs = len(self.destination_addresses)
            if num_addrs <= 3:
                for addr in self.destination_addresses:
                    truncated = addr[:8] + "..." if len(addr) > 11 else addr
                    destination_column.append(truncated)
            else:
                destination_column.append(self.destination_addresses[0][:8] + "...")
                destination_column.append(_("[ ... ]"))
                destination_column.append(self.destination_addresses[-1][:8] + "...")
        else:
            destination_column.append(_("recipient"))

        destination_column.append(_("fee"))

        if self.num_change_outputs > 0:
            destination_column.append(_("change"))

        max_destination_text_width = 0
        for destination in destination_column:
            left, top, right, bottom = font.getbbox(destination)
            tw = right - left
            max_destination_text_width = max(tw, max_destination_text_width)

        destination_col_x = image.width - (max_destination_text_width + GUIConstants.EDGE_PADDING*ssf)

        # Calculate center bar position
        center_bar_x = GUIConstants.EDGE_PADDING*ssf + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4) + curve_width
        center_bar_width = destination_col_x - int(GUIConstants.COMPONENT_PADDING*ssf/4) - curve_width - center_bar_x

        # Position each input row
        num_rendered_inputs = len(inputs_column)
        if self.num_inputs == 1:
            inputs_y = vertical_center - int(chart_text_height/2)
            inputs_y_spacing = 0
        else:
            inputs_y = int((image.height - num_rendered_inputs*chart_text_height) / (num_rendered_inputs + 1))
            inputs_y_spacing = inputs_y + chart_text_height

        if inputs_y % 2 == 1:
            inputs_y += 1
        if inputs_y_spacing % 2 == 1:
            inputs_y_spacing += 1

        inputs_conjunction_x = center_bar_x
        inputs_x = GUIConstants.EDGE_PADDING*ssf

        input_curves = []
        for input_text in inputs_column:
            left, top, right, bottom = font.getbbox(input_text)
            tw = right - left
            cur_x = inputs_x + max_inputs_text_width - tw
            draw.text(
                (cur_x, inputs_y),
                text=input_text,
                font=font,
                fill=chart_font_color,
                anchor="lt",
            )

            start_pt = (
                inputs_x + max_inputs_text_width + int(GUIConstants.COMPONENT_PADDING*ssf/4),
                inputs_y + int(chart_text_height/2)
            )
            conjunction_pt = (inputs_conjunction_x, vertical_center)
            mid_pt = (
                int(start_pt[0]*0.5 + conjunction_pt[0]*0.5),
                int(start_pt[1]*0.5 + conjunction_pt[1]*0.5)
            )

            if len(inputs_column) == 1:
                bezier_points = [
                    start_pt,
                    linear_interp(start_pt, conjunction_pt, 0.33),
                    linear_interp(start_pt, conjunction_pt, 0.66),
                    conjunction_pt
                ]
            else:
                bezier_points = calc_bezier_curve(
                    start_pt,
                    (mid_pt[0], start_pt[1]),
                    mid_pt,
                    curve_steps
                )
                bezier_points.pop()
                bezier_points += calc_bezier_curve(
                    mid_pt,
                    (mid_pt[0], conjunction_pt[1]),
                    conjunction_pt,
                    curve_steps
                )

            input_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            inputs_y += inputs_y_spacing

        # Render center bar
        draw.line(
            (
                center_bar_x,
                vertical_center,
                center_bar_x + center_bar_width,
                vertical_center
            ),
            fill=association_line_color,
            width=association_line_width
        )

        # Position each destination
        num_rendered_destinations = len(destination_column)
        if num_rendered_destinations == 1:
            destination_y = vertical_center - int(chart_text_height/2)
            destination_y_spacing = 0
        else:
            destination_y = int((image.height - num_rendered_destinations*chart_text_height) / (num_rendered_destinations + 1))
            destination_y_spacing = destination_y + chart_text_height

        if destination_y % 2 == 1:
            destination_y += 1
        if destination_y_spacing % 2 == 1:
            destination_y_spacing += 1

        destination_conjunction_x = center_bar_x + center_bar_width
        recipients_text_x = destination_col_x

        output_curves = []
        for destination in destination_column:
            draw.text(
                (recipients_text_x, destination_y),
                text=destination,
                font=font,
                fill=chart_font_color,
                anchor="lt"
            )

            conjunction_pt = (destination_conjunction_x, vertical_center)
            end_pt = (
                conjunction_pt[0] + curve_width,
                destination_y + int(chart_text_height/2)
            )
            mid_pt = (
                int(conjunction_pt[0]*0.5 + end_pt[0]*0.5),
                int(conjunction_pt[1]*0.5 + end_pt[1]*0.5)
            )

            bezier_points = calc_bezier_curve(
                conjunction_pt,
                (mid_pt[0], conjunction_pt[1]),
                mid_pt,
                curve_steps
            )
            bezier_points.pop()
            bezier_points += calc_bezier_curve(
                mid_pt,
                (int(mid_pt[0]*1.0 + end_pt[0]*0.0), end_pt[1]),
                end_pt,
                curve_steps
            )

            output_curves.append(bezier_points)

            prev_pt = bezier_points[0]
            for pt in bezier_points[1:]:
                draw.line(
                    (prev_pt[0], prev_pt[1], pt[0], pt[1]),
                    fill=association_line_color,
                    width=association_line_width + 1,
                    joint="curve",
                )
                prev_pt = pt

            destination_y += destination_y_spacing

        # Resize and sharpen
        image = image.resize((self.canvas_width, chart_height), Image.Resampling.LANCZOS)
        self.paste_images.append((image.filter(ImageFilter.SHARPEN), (self.chart_x, self.chart_y)))

        # Animation thread
        self.threads.append(
            CardanoTxOverviewScreen.TxExplorerAnimationThread(
                inputs=input_curves,
                outputs=output_curves,
                supersampling_factor=ssf,
                offset_y=self.chart_y,
                renderer=self.renderer
            )
        )

    class TxExplorerAnimationThread(BaseThread):
        def __init__(self, inputs, outputs, supersampling_factor, offset_y, renderer):
            super().__init__()
            ssf = supersampling_factor
            self.inputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in inputs]
            self.outputs = [[(int(i[0]/ssf), int(i[1]/ssf + offset_y)) for i in curve] for curve in outputs]
            self.renderer = renderer

        def run(self):
            pulse_color = GUIConstants.ACCENT_COLOR
            reset_color = "#666"
            line_width = 3

            pulses = []

            start_pt = self.inputs[0][-1]
            end_pt = self.outputs[0][0]
            if start_pt == end_pt:
                center_bar_pts = [end_pt, self.outputs[0][1]]
            else:
                center_bar_pts = [
                    start_pt,
                    linear_interp(start_pt, end_pt, 0.25),
                    linear_interp(start_pt, end_pt, 0.50),
                    linear_interp(start_pt, end_pt, 0.75),
                    end_pt,
                ]

            def draw_line_segment(curves, i, j, color):
                for points in curves:
                    pt1 = points[i]
                    pt2 = points[j]
                    self.renderer.draw.line(
                        (pt1[0], pt1[1], pt2[0], pt2[1]),
                        fill=color,
                        width=line_width
                    )

            prev_color = reset_color
            while self.keep_running:
                with self.renderer.lock:
                    if not pulses or (prev_color == pulse_color and pulses[-1][0] == 10):
                        if prev_color == pulse_color:
                            pulses.append([0, reset_color])
                        else:
                            pulses.append([0, pulse_color])
                        prev_color = pulses[-1][1]

                    for pulse in pulses:
                        i = pulse[0]
                        color = pulse[1]
                        input_segments = len(self.inputs[0]) - 1
                        center_bar_segments = len(center_bar_pts) - 1
                        output_segments = len(self.outputs[0]) - 1

                        if i < input_segments:
                            draw_line_segment(self.inputs, i, i+1, color)
                        elif i < input_segments + center_bar_segments:
                            j = i - input_segments
                            pt1 = center_bar_pts[j]
                            pt2 = center_bar_pts[j+1]
                            self.renderer.draw.line(
                                (pt1[0], pt1[1], pt2[0], pt2[1]),
                                fill=color,
                                width=line_width
                            )
                        elif i < input_segments + center_bar_segments + output_segments:
                            j = i - input_segments - center_bar_segments
                            draw_line_segment(self.outputs, j, j+1, color)

                        pulse[0] += 1

                    total_segments = len(self.inputs[0]) + len(center_bar_pts) + len(self.outputs[0]) - 3
                    pulses = [p for p in pulses if p[0] <= total_segments]

                self.renderer.show_image()

                import time
                time.sleep(0.05)
