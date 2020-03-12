def convert_alphabet_no_index(alphabet):
    # converts a;phabet to ASCII equivalent and subtract 48 from it
    encoded_alphabet = alphabet.encode('utf-8')
    return int(encoded_alphabet.hex(), 16) - 65

def populate_shipment_data(shipping_type, sheet):
    if shipping_type == 'air':
        return populate_shipment_data_for_aircargo(sheet)
    else:
        return populate_shipment_data_for_shipfrieght(sheet)


def populate_shipping_items_data(shipping_type, sheet):
    if shipping_type == 'air':
        return populate_shipping_items_data_for_aircago(sheet)
    else:
        return populate_shipping_items_data_for_shipfreight(sheet)

def populate_shipment_data_for_aircargo(sheet):
    data = {}
    field_cells = {
        'mawb_no': (2, 'A'),
        'discharge_port': (2, 'B'),
        'flt_no': (4, 'B'),
        'arrival_date': (4, 'G'),
        'consign_to': (5, 'B'),
        'departure_date': (5, 'G'),
        'shipped_by': (6, 'B')
    }
    for cell_key in field_cells:
          cell_position = field_cells[cell_key]
          row, col = cell_position[0] - \
                1, convert_alphabet_no_index(cell_position[1])
          data[cell_key] = sheet.cell(row, col).value
    return data


def populate_shipment_data_for_shipfrieght(sheet):
    data = {}
    field_cells = {
        'shipping_id': (2, 'A'),
        'departure_date': (2, 'K'),
        'groupage': (2, 'F'),
        'remark': (2, 'I')
    }
    for cell_key in field_cells:
        cell_position = field_cells[cell_key]
        row, col = cell_position[0] - \
            1, convert_alphabet_no_index(cell_position[1])
        data[cell_key] = sheet.cell(row, col).value
    return data


def populate_shipping_items_data_for_aircago(sheet):
    rows = []
    shipping_item_row_positions = {
        'hawb_no': 'A',
        'pkgs': 'B',
        'wkg': 'C',
        'vol': 'D',
        'commodity': 'E',
        'marks': 'F',
        'shipper': 'G',
        'name': 'H',
        'payment': 'I',
        'quantity': 'J',
        'sign': 'K',
    }
    # Start from row 8 and end at the second to the last row
    # Last row is for total and the first seven rows are general data
    for rowx, row in enumerate(map(sheet.row, range(8, sheet.nrows - 1))):
        row_data = {}
        for (key, value) in shipping_item_row_positions.items():
            row_data[key] = row[convert_alphabet_no_index(value)].value
        rows.append(row_data)
    return rows


def populate_shipping_items_data_for_shipfreight(sheet):
    rows = []
    shipping_item_row_positions = {
        'hbl': 'A',
        'marks': 'B',
        'shipping_order': 'C',
        'shipper': 'D',
        'goods_description': 'E',
        'pkgs': 'F',
        'total_cbm': 'G',
        'wkg': 'H',
        'consignee': 'I',
        'dest_port': 'J',
        'payment': 'L',
        'remark': 'M',
    }
    # Start from row 3 and end at the second to the last row
    # Last row is for total and the first seven rows are general data
    for rowx, row in enumerate(map(sheet.row, range(3, sheet.nrows - 1))):
        row_data = {}
        for (key, value) in shipping_item_row_positions.items():
            row_data[key] = row[convert_alphabet_no_index(value)].value
        rows.append(row_data)
    return rows
