import re
from datetime import datetime
from pathlib import Path
from threading import Thread
from urllib.parse import quote, urljoin

import flet as ft
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

BASE_URL = "https://snkrdunk.com"
SEARCH_URL = f"{BASE_URL}/search?keywords={{}}"
SEARCH_CONTAINER_CLASS = "styles-module-scss-module__TqY8kG__scrollContainer"
SIZE_CONTAINER_CLASS = "styles-module-scss-module__YOqw-G__container"
PRODUCT_NAME_CLASSES = (
    "styles-module-scss-module__U2cbAq__name",  # apparels
    "styles-module-scss-module__gLiF1G__name",  # products
)
OUTPUT_DIR = Path(__file__).resolve().parent

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_search_links(session: requests.Session, product_id: str) -> list[str]:
    url = SEARCH_URL.format(quote(product_id))
    response = session.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find("div", class_=SEARCH_CONTAINER_CLASS)
    if container is None:
        return []

    links = []
    seen = set()
    for anchor in container.select("a[href]"):
        href = urljoin(BASE_URL, anchor["href"])
        if href not in seen:
            seen.add(href)
            links.append(href)
    return links


def parse_variant_text(variant_text: str) -> tuple[str, int | None]:
    match = re.match(r"^(.*?)\s*\((\d+)\)\s*$", variant_text)
    if not match:
        return variant_text.strip(), None
    return match.group(1).strip(), int(match.group(2))


def parse_price_text(price_text: str) -> int | float | None:
    match = re.search(r"[\d,]+(?:\.\d+)?", price_text)
    if not match:
        return None

    raw_price = match.group(0).replace(",", "")
    try:
        return float(raw_price) if "." in raw_price else int(raw_price)
    except ValueError:
        return None


def get_product_data(
    page: Page, product_url: str
) -> tuple[str, list[dict[str, str | int | float | None]]]:
    page.goto(product_url, wait_until="domcontentloaded", timeout=30_000)

    name_selectors = [
        f'h1[class="{class_name}"]' for class_name in PRODUCT_NAME_CLASSES
    ]
    name_selector = ", ".join(name_selectors)
    container_selector = f'div[class="{SIZE_CONTAINER_CLASS}"]'

    try:
        page.locator(name_selector).first.wait_for(state="visible", timeout=15_000)
    except PlaywrightTimeoutError:
        pass

    try:
        page.locator(container_selector).first.wait_for(
            state="visible", timeout=15_000
        )
    except PlaywrightTimeoutError:
        return "", []

    page.wait_for_timeout(1_500)

    # SNKRDUNK dùng 2 class tên khác nhau:
    # U2cbAq__name cho apparels và gLiF1G__name cho products.
    product_name = ""
    for selector in name_selectors:
        name_locator = page.locator(selector).first
        if name_locator.count():
            text = name_locator.inner_text().strip()
            if text:
                product_name = text
                break

    results = []
    containers = page.locator(container_selector)

    for container_index in range(containers.count()):
        container = containers.nth(container_index)
        buttons = container.locator("button")

        for button_index in range(buttons.count()):
            button = buttons.nth(button_index)
            variant = button.locator('p[class$="__variant"]').first
            price = button.locator('p[class$="__price"]').first

            variant_text = variant.inner_text().strip() if variant.count() else ""
            price_text = price.inner_text().strip() if price.count() else ""

            size, quantity = parse_variant_text(variant_text)
            price_number = parse_price_text(price_text)

            if not variant_text and price_number is None:
                continue

            results.append({
                "size": size,
                "quantity": quantity,
                "price": price_number,
            })

    return product_name, results


def create_workbook() -> tuple[Workbook, object]:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "SNKRDUNK"

    headers = [
        "Mã sản phẩm",
        "Tên sản phẩm",
        "Size",
        "Giá tiền (¥)",
        "Số sản phẩm hiện có",
        "Thời gian quét",
    ]
    worksheet.append(headers)

    for cell in worksheet[1]:
        cell.font = Font(bold=True)

    worksheet.freeze_panes = "A2"
    widths = {"A": 20, "B": 60, "C": 15, "D": 18, "E": 24, "F": 22}
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width

    return workbook, worksheet


def scan_products(product_id: str, progress_callback, log_callback):
    """Quét dữ liệu; callback được gọi để cập nhật UI từ thread nền."""
    search_url = SEARCH_URL.format(quote(product_id))
    log_callback(f"Đang tìm kiếm: {search_url}")

    with requests.Session() as session:
        links = get_search_links(session, product_id)

    if not links:
        raise RuntimeError("Không tìm thấy đường link sản phẩm.")

    log_callback(f"Tìm thấy {len(links)} đường link sản phẩm.")

    scan_time = datetime.now()
    output_file = OUTPUT_DIR / f"snkrdunk_results_{scan_time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    workbook, worksheet = create_workbook()
    total_rows = 0
    failed_links = 0

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={"Accept-Language": HEADERS["Accept-Language"]},
        )

        try:
            for index, link in enumerate(links, start=1):
                log_callback(f"[{index}/{len(links)}] Đang quét: {link}")

                try:
                    product_name, sizes = get_product_data(page, link)
                    if not sizes:
                        failed_links += 1
                        log_callback(f"[{index}/{len(links)}] Không có dữ liệu size/giá.")
                    else:
                        log_callback(f"[{index}/{len(links)}] {product_name or 'Không có tên'} — {len(sizes)} size")
                        for item in sizes:
                            worksheet.append([
                                product_id,
                                product_name,
                                item["size"],
                                item["price"],
                                item["quantity"],
                                scan_time,
                            ])
                            total_rows += 1
                except Exception as exc:
                    failed_links += 1
                    log_callback(f"[{index}/{len(links)}] Lỗi: {exc}")

                # Tăng đúng 1 bước sau khi đã xử lý xong một URL.
                progress_callback(index, len(links))
        finally:
            browser.close()

    worksheet.auto_filter.ref = worksheet.dimensions
    for row in worksheet.iter_rows(min_row=2, min_col=6, max_col=6):
        row[0].number_format = "yyyy-mm-dd hh:mm:ss"

    workbook.save(output_file)
    return len(links), total_rows, failed_links, output_file


def main(page: ft.Page):
    page.title = "SNKRDUNK Checker"
    page.window.width = 850
    page.window.height = 650
    page.padding = 30
    page.theme_mode = ft.ThemeMode.LIGHT

    title = ft.Text("SNKRDUNK Checker", size=30, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text("Nhập mã sản phẩm để quét thông tin size, giá và số lượng.", size=14)

    product_id = ft.TextField(
        label="Mã sản phẩm",
        hint_text="Ví dụ: CW2288-111",
        expand=True,
        autofocus=True,
    )

    progress = ft.ProgressBar(value=0, visible=False)
    progress_text = ft.Text("Chưa bắt đầu", size=13)
    status = ft.Text("Sẵn sàng", size=14)
    log_view = ft.ListView(expand=True, spacing=5, auto_scroll=True)

    def log(message: str):
        log_view.controls.append(ft.Text(message, size=12))
        page.update()

    def update_progress(current: int, total: int):
        progress.value = current / total if total else 0
        progress_text.value = f"Đã quét {current}/{total} đường link ({progress.value:.0%})"
        page.update()

    def set_busy(busy: bool):
        product_id.disabled = busy
        scan_button.disabled = busy
        progress.visible = busy
        page.update()

    def show_result(title_text: str, message: str, success: bool):
        # SnackBar là thông báo nổi phía dưới giao diện.
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text(title_text),
                content=ft.Text(message),
                actions=[ft.TextButton("Đóng", on_click=lambda e: page.pop_dialog())],
            )
        )

    def scan_thread():
        value = product_id.value.strip()
        if not value:
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Thiếu mã sản phẩm"),
                    content=ft.Text("Vui lòng nhập mã sản phẩm trước khi quét."),
                    actions=[ft.TextButton("Đóng", on_click=lambda e: page.pop_dialog())],
                )
            )
            return

        set_busy(True)
        progress.value = 0
        progress_text.value = "Đang khởi động..."
        status.value = "Đang quét..."
        log_view.controls.clear()
        page.update()

        try:
            links_count, rows_count, failed_count, output_file = scan_products(
                value, update_progress, log
            )
            status.value = "Hoàn thành"
            progress.value = 1
            progress_text.value = f"Đã quét {links_count}/{links_count} đường link (100%)"
            message = (
                f"Quét thành công.\n\n"
                f"• Đường link: {links_count}\n"
                f"• Dòng dữ liệu: {rows_count}\n"
                f"• Link lỗi/không có dữ liệu: {failed_count}\n\n"
                f"File Excel:\n{output_file}"
            )
            show_result("Quét thành công", message, True)
        except Exception as exc:
            status.value = "Thất bại"
            log(f"Lỗi tổng quát: {exc}")
            show_result("Quét thất bại", str(exc), False)
        finally:
            set_busy(False)
            page.update()

    def on_scan_click(e):
        Thread(target=scan_thread, daemon=True).start()

    scan_button = ft.ElevatedButton(
        "Bắt đầu quét",
        icon=ft.Icons.SEARCH,
        on_click=on_scan_click,
        height=50,
    )

    page.add(
        title,
        subtitle,
        ft.Container(height=15),
        ft.Row([product_id, scan_button]),
        ft.Container(height=15),
        progress,
        progress_text,
        status,
        ft.Divider(),
        ft.Text("Tiến trình", size=16, weight=ft.FontWeight.BOLD),
        ft.Container(content=log_view, expand=True, border=ft.Border.all(1), padding=12),
    )


if __name__ == "__main__":
    ft.app(target=main)
