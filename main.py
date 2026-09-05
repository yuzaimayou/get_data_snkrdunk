from __future__ import annotations

import asyncio

import flet as ft

from api import (
    ConnectionError_,
    InvalidProductIdError,
    InvalidResponseError,
    RequestTimeoutError,
    SnkrdunkApiError,
    fetch_size_listings,
)
from excel import ExcelStorageError, append_listings_to_excel
from models import SizeListing


BG = ft.Colors.SURFACE
TEXT = ft.Colors.ON_SURFACE
MUTED = ft.Colors.ON_SURFACE_VARIANT
PRIMARY = ft.Colors.BLUE


def format_price(value: int | float | None) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float) and not value.is_integer():
        return f"¥{value:,.2f}"
    return f"¥{int(value):,}"


def build_table(listings: list[SizeListing]) -> ft.DataTable:
    rows = [
        ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(item.size, weight=ft.FontWeight.W_500)),
                ft.DataCell(ft.Text(format_price(item.min_listing_price))),
                ft.DataCell(ft.Text(f"{item.listing_item_count:,}")),
            ]
        )
        for item in listings
    ]
    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Size", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Min Listing Price", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Listing Item Count", weight=ft.FontWeight.W_600)),
        ],
        rows=rows,
        column_spacing=48,
        horizontal_margin=18,
        heading_row_height=48,
        data_row_min_height=46,
        data_row_max_height=54,
    )


def main(page: ft.Page) -> None:
    page.title = "SNKRDUNK Price Viewer"
    page.padding = 0
    page.bgcolor = BG
    page.window.width = 900
    page.window.height = 650
    page.window.min_width = 720
    page.window.min_height = 560

    product_id = ft.TextField(
        label="Product ID",
        hint_text="Enter SNKRDUNK product ID...",
        prefix_icon=ft.Icons.INVENTORY_2_OUTLINED,
        expand=True,
        dense=True,
        border_radius=12,
        border_width=1,
        autofocus=True,
        on_submit=lambda _: page.run_task(search),
    )

    excel_path: str | None = None
    excel_file_text = ft.Text("No Excel file selected", color=MUTED, size=13, expand=True)
    # FilePicker is a Flet service in the current API and must be
    # registered with page.services before it can be used.
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    select_excel_button = ft.OutlinedButton(
        content="Select Excel File",
        icon=ft.Icons.UPLOAD_FILE,
        height=46,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )

    search_button = ft.FilledButton(
        content="Search Product",
        icon=ft.Icons.SEARCH,
        height=46,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )
    clear_button = ft.OutlinedButton(
        content="Clear",
        icon=ft.Icons.CLEAR,
        height=46,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
    )
    progress = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
    status_icon = ft.Icon(ft.Icons.INFO_OUTLINE, color=MUTED, size=20)
    status_text = ft.Text("Enter a product ID to begin.", color=MUTED, size=13)
    status_row = ft.Row([status_icon, status_text], spacing=8)

    summary = ft.Container(visible=False)
    results = ft.Container(visible=False)

    def set_status(message: str, icon: str, color: str) -> None:
        status_icon.name = icon
        status_icon.color = color
        status_text.value = message
        status_text.color = color

    def set_loading(loading: bool) -> None:
        search_button.disabled = loading
        clear_button.disabled = loading
        select_excel_button.disabled = loading
        product_id.disabled = loading
        progress.visible = loading

    async def select_excel() -> None:
        nonlocal excel_path
        try:
            selected_files = await file_picker.pick_files(
                dialog_title="Select Excel workbook",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx"],
                allow_multiple=False,
            )
            if not selected_files:
                return

            selected = selected_files[0]
            if not selected.path:
                set_status("Unable to access the selected Excel file.", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
                page.update()
                return

            excel_path = selected.path
            excel_file_text.value = selected.path
            excel_file_text.color = TEXT
            set_status("Excel file selected.", ft.Icons.CHECK_CIRCLE_OUTLINE, ft.Colors.GREEN_700)
            page.update()
        except Exception:
            set_status("Unable to select the Excel file.", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
            page.update()

    async def search() -> None:
        value = product_id.value.strip() if product_id.value else ""
        if not value:
            set_status("Please enter a product ID.", ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.ORANGE_700)
            results.visible = False
            summary.visible = False
            page.update()
            return

        if not excel_path:
            set_status("Please select an Excel file first.", ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.ORANGE_700)
            page.update()
            return

        set_loading(True)
        results.visible = False
        summary.visible = False
        set_status("Loading product size listings...", ft.Icons.HOURGLASS_TOP, PRIMARY)
        page.update()

        try:
            listings = await asyncio.to_thread(fetch_size_listings, value)
            total = sum(item.listing_item_count for item in listings)
            summary.content = ft.Row(
                [
                    ft.Text(f"Product ID: {value}", weight=ft.FontWeight.W_600),
                    ft.Text(f"Total Sizes: {len(listings)}", color=MUTED),
                    ft.Text(f"Total Listings: {total:,}", color=MUTED),
                ],
                spacing=24,
                wrap=True,
            )
            results.content = ft.Container(
                content=ft.Column([build_table(listings)], scroll=ft.ScrollMode.AUTO),
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                border_radius=14,
                padding=8,
                expand=True,
            )
            summary.visible = True
            results.visible = True

            try:
                written_rows = await asyncio.to_thread(
                    append_listings_to_excel,
                    excel_path,
                    value,
                    listings,
                )
            except ExcelStorageError as exc:
                set_status(str(exc), ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
            else:
                set_status(
                    f"Data loaded and saved to Excel ({written_rows} rows).",
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    ft.Colors.GREEN_700,
                )
        except InvalidProductIdError as exc:
            set_status(str(exc), ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
        except RequestTimeoutError as exc:
            set_status(str(exc), ft.Icons.TIMER_OUTLINED, ft.Colors.RED_700)
        except ConnectionError_ as exc:
            set_status(str(exc), ft.Icons.WIFI_OFF_OUTLINED, ft.Colors.RED_700)
        except InvalidResponseError as exc:
            set_status(str(exc), ft.Icons.DATA_OBJECT, ft.Colors.RED_700)
        except SnkrdunkApiError as exc:
            set_status(str(exc), ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
        except Exception:
            # Last-resort UI protection: no unexpected exception should kill the desktop UI.
            set_status("Unexpected error. Please try again.", ft.Icons.ERROR_OUTLINE, ft.Colors.RED_700)
        finally:
            set_loading(False)
            page.update()

    def clear() -> None:
        product_id.value = ""
        results.visible = False
        summary.visible = False
        set_status("Enter a product ID to begin.", ft.Icons.INFO_OUTLINE, MUTED)
        product_id.focus()
        page.update()

    select_excel_button.on_click = lambda _: page.run_task(select_excel)
    search_button.on_click = lambda _: page.run_task(search)
    clear_button.on_click = lambda _: clear()

    summary.padding = ft.Padding(left=4, right=4, top=10, bottom=10)
    summary.border_radius = 10

    page.add(
        ft.Container(
            expand=True,
            padding=ft.Padding(left=56, right=56, top=42, bottom=42),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("SNKRDUNK Price Viewer", size=30, weight=ft.FontWeight.W_700, color=TEXT),
                                ft.Text("Check product size listings and prices", size=14, color=MUTED),
                            ],
                            spacing=5,
                        ),
                        margin=ft.Margin(bottom=26),
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([product_id], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                ft.Row(
                                    [select_excel_button, excel_file_text],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    spacing=12,
                                ),
                                ft.Row(
                                    [search_button, progress, clear_button],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=10,
                                ),
                                status_row,
                            ],
                            spacing=14,
                        ),
                        padding=22,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                        border_radius=16,
                    ),
                    ft.Container(
                        content=ft.Text("Product Size Listings", size=18, weight=ft.FontWeight.W_600),
                        margin=ft.Margin(top=28, bottom=2),
                    ),
                    summary,
                    results,
                ],
                spacing=0,
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            ),
        )
    )


if __name__ == "__main__":
    ft.run(main)
