import flet as ft
def main(page: ft.Page):
    # Cấu hình thuộc tính của trang (Page)
    page.title = "Ứng dụng Flet đầu tiên"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    # Tạo một thành phần giao diện (Control)
    text_hello = ft.Text(value="Xin chào, Flet!", size=30)
    
    # Thêm thành phần vào trang và cập nhật
    page.add(text_hello)

# Lệnh này khởi chạy vòng lặp sự kiện (Event Loop) của ứng dụng
ft.app(target=main)