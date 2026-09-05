# SNKRDUNK Price Viewer

Desktop tool nhỏ bằng Python + Flet để tra cứu size, giá listing thấp nhất và số lượng listing của sản phẩm SNKRDUNK.

## Cấu trúc

```text
snkrdunk_checker/
├── main.py
├── api.py
├── models.py
├── excel.py
├── requirements.txt
└── README.md
```

## Yêu cầu

- Python 3.9+
- Có kết nối Internet

## Cài đặt

Clone/download project rồi mở terminal tại thư mục project:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```bat
.venv\Scripts\activate
```

Cài dependency:

```bash
pip install -r requirements.txt
```

Dependency `openpyxl` được dùng để đọc và cập nhật file Excel `.xlsx`.

## Chạy ứng dụng

```bash
python main.py
```

## Sử dụng

1. Chọn file Excel `.xlsx` bằng `Select Excel File`.
2. Nhập Product ID của sản phẩm SNKRDUNK vào ô `Product ID`.
3. Nhấn `Search Product` hoặc Enter.
4. Tool gọi endpoint:

```text
https://snkrdunk.com/v1/apparels/{id}/sizes
```

Trong đó `{id}` là Product ID dùng bởi endpoint, không nhất thiết là mã SKU/official product code hiển thị trên trang sản phẩm.

Kết quả gồm:

- `Size`
- `Min Listing Price` (`minListingPrice`), hiển thị theo định dạng Yen như `¥12,000`
- `Listing Item Count` (`listingItemCount`)
- Tổng số size và tổng số listing

## Lưu dữ liệu vào Excel

Sau khi API trả dữ liệu thành công, tool tự động cập nhật workbook Excel đã chọn:

- Mỗi Product ID có một worksheet riêng, tên worksheet là Product ID.
- Nếu worksheet chưa tồn tại, tool tạo worksheet mới.
- Hàng 1 chứa header: `Scanned At`, `Size`, `Min Listing Price`, `Listing Item Count`.
- Dữ liệu của lần quét đầu tiên bắt đầu từ hàng 2.
- Nếu worksheet đã tồn tại, dữ liệu mới được thêm ngay sau hàng cuối cùng hiện có.
- Mỗi size là một hàng; vì vậy một lần quét có nhiều size sẽ thêm nhiều hàng liên tiếp.
- `Scanned At` giúp phân biệt các lần quét khác nhau.
- Nếu file Excel đang được mở bởi Excel/LibreOffice và bị khóa, UI sẽ báo lỗi thay vì làm crash ứng dụng.

Ví dụ worksheet `123456`:

| Scanned At | Size | Min Listing Price | Listing Item Count |
|---|---|---:|---:|
| 2026-09-05 23:50:00 | S | 11000 | 32 |
| 2026-09-05 23:50:00 | M | 13200 | 45 |
| 2026-09-05 23:55:00 | S | 10800 | 35 |
| 2026-09-05 23:55:00 | M | 13000 | 47 |

Như vậy mỗi lần quét mới được append, không ghi đè dữ liệu cũ.

## API và parser

`api.py` chỉ chịu trách nhiệm validate ID, gọi HTTP bằng `requests`, xử lý HTTP/network/JSON errors và chuyển dữ liệu sang parser.

`models.py` chứa `SizeListing` và parser `parse_size_listings()`. Parser không khóa vào một vị trí JSON duy nhất: nó đệ quy tìm collection có các object chứa `size` cùng với `minListingPrice`/`listingItemCount`, sau đó chuẩn hóa thành `SizeListing`.

Nếu response không chứa dữ liệu có cấu trúc nhận diện được, UI báo:

```text
Không thể phân tích dữ liệu size từ API.
```

## Xử lý lỗi

Ứng dụng xử lý riêng các trường hợp:

- Product ID rỗng → `Please enter a product ID.`
- Product ID sai định dạng → `Invalid product ID.`
- Timeout → `Request timed out. Please try again.`
- Connection error → `Unable to connect to SNKRDUNK.`
- HTTP 404 → `Product not found.`
- HTTP 429 → thông báo rate limit
- HTTP 5xx → thông báo lỗi server
- JSON lỗi → `Invalid response received from SNKRDUNK.`
- Không nhận diện được size data → `Không thể phân tích dữ liệu size từ API.`

Không sử dụng Selenium, Playwright, browser automation, cookie/session của người dùng, backend hoặc database.

## Kiểm tra endpoint thực tế

Trong quá trình triển khai, endpoint được kiểm tra trực tiếp với các Product ID lấy từ trang SNKRDUNK. Các mã dạng SKU như `LB3787` trả HTTP 400 (`bad_input`), còn ID nội bộ được nhúng trong trang sản phẩm đã được thử và trả HTTP 404 tại thời điểm kiểm tra. Vì vậy README và UI dùng thuật ngữ **Product ID dùng cho endpoint**, không coi SKU/official product code là ID API một cách tự động.

Nếu SNKRDUNK thay đổi endpoint hoặc yêu cầu thêm tham số/header, chỉ cần cập nhật `api.py`; UI và model không cần thay đổi.
