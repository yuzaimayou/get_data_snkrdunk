from openpyxl import load_workbook
from database import get_or_fetch_url
from type import get_product_type
from request import get_data_products,get_data_apparels
wb=load_workbook('snkrdunk_results.xlsx')
sheet=wb[wb.sheetnames[0]]
maxRow=sheet.max_row
idCheck=""
nameCheck=""
dataCheck=""
for i in range(2,maxRow+1):
    id=sheet.cell(row=i,column=1).value
    name=sheet.cell(row=i,column=2).value
    size=sheet.cell(row=i,column=3).value
    price=sheet.cell(row=i,column=4).value
    if(id!=idCheck and name!=nameCheck):
        print()
    elif(nameCheck==name):
        continue

    type=get_product_type(id)

    if(type=="products"):
        data=get_data_products(id)
    else:
        data=get_data_apparels(get_or_fetch_url(id,name))

    print(f'Id: {id}, Name: {name}, size:{size}, price: ', end="")
    
    if data and size!=None:
        if data[size]==None and price!=None:
            print("Hàng đã bị bán")
        elif data[size]<price:
            print("Giá đã giảm")
        elif data[size]>price:
            print("Giá đã tăng")
        else:
            print("Giá không đổi")
    else:
        print("error")
    idCheck=id
    nameCheck=name
print(wb.sheetnames[0])