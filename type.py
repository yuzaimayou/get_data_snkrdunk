import re 
def get_product_type(product_id):
    product_id = str(product_id).strip().upper()

    # ID của products: CZ0790-102
    if re.fullmatch(r'[A-Z0-9]+-\d{3}', product_id):
        return "products"

    # ID của apparels: HM-FW26-WEEK5-008
    if re.fullmatch(r'[A-Z]+-[A-Z0-9]+-WEEK\d+-\d+', product_id):
        return "apparels"

    return "unknown"