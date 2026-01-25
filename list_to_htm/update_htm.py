import re

def parse_data_txt(filepath):
    """Parse data.txt and return list of (item_name, discount_or_bonus)"""
    items = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if '→' in line:
                line = line.split('→', 1)[1]
            if '-----' in line:
                parts = line.split('-----')
                item_name = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else ''
                items.append((item_name, value))
    return items

def parse_discount_value(value):
    """Parse discount/bonus value and return (discount_num, bonus_str)

    The '/' character is used as a separator between discount and bonus.
    Examples:
        - "10%/5+5" → discount=10.0, bonus="5+5"
        - "TP,/something" → discount=0.0, bonus="TP,/something" (TP with bonus)
        - "15" → discount=15.0, bonus=""
    """
    # First, check if '/' is used as separator for bonus
    bonus_part = ""
    main_value = value
    if '/' in value:
        slash_pos = value.find('/')
        main_value = value[:slash_pos].strip()
        bonus_part = value[slash_pos+1:].strip()

    # Check if it's a "NET" value (which typically comes with numbers like "140 NET")
    if 'net' in main_value.lower():
        # For values like "140 NET", treat the number as discount and "NET" as additional info
        # Split by space and try to find the numeric part
        parts = main_value.split()
        for part in parts:
            if any(c.isdigit() for c in part):
                try:
                    # Extract the numeric part
                    num_str = ''.join(c for c in part if c.isdigit() or c == '.')
                    discount = float(num_str) if num_str else 0.0
                    # Return the whole value as additional info since it's a net price
                    return discount, main_value.strip() if not bonus_part else bonus_part
                except:
                    pass
        # If we can't parse it as a number, treat it as a special case
        net_match = re.search(r'net(.*)', main_value, re.IGNORECASE)
        if net_match:
            additional_part = net_match.group(1).strip()
            return 0.0, f"net{additional_part}" if not bonus_part else bonus_part
        else:
            return 0.0, main_value if not bonus_part else bonus_part

    elif '%' in main_value:
        # Extract numeric part from percentage
        percent_pos = main_value.find('%')
        num_part = main_value[:percent_pos]  # Before the % sign
        num = num_part.strip()
        try:
            discount = float(num)
        except:
            discount = 0.0
        # If there's content after % in main_value (before /), include it
        after_percent = main_value[percent_pos+1:].strip()
        if bonus_part:
            # '/' was used, so bonus_part is the bonus
            return discount, bonus_part
        elif after_percent:
            # No '/', but there's text after % - treat as additional info
            return discount, after_percent
        else:
            return discount, ""
    elif 'TP' in main_value.upper():
        # Return TP value (preserving any separators like "TP," or "Tp,")
        # If bonus_part exists, combine main_value with bonus info
        if bonus_part:
            return 0.0, f"{main_value}/{bonus_part}"
        return 0.0, main_value.strip()
    else:
        try:
            discount = float(main_value)
            return discount, bonus_part
        except:
            return 0.0, value

def generate_item_row(serial, item_name, value):
    """Generate HTML for a single item row"""
    display_name = '          ' + item_name.upper().ljust(28)
    hidden_name = item_name.upper().ljust(50)
    discount, bonus = parse_discount_value(value)

    # Check if '/' was used in original value (bonus separator)
    has_slash_separator = '/' in value

    # Check if the original value contains "net" to handle "140 NET" type values specially
    original_value_lower = value.lower().strip()

    if 'net' in original_value_lower and any(c.isdigit() for c in value):
        # For values like "140 NET", display the original value in the discount column
        if has_slash_separator:
            # Extract main part before /
            main_part = value.split('/')[0].strip()
            discount_str = f'{main_part}'.rjust(len(main_part))
            bonus_str = bonus.ljust(44) if bonus else ' ' * 44
        else:
            discount_str = f'{value}'.rjust(len(value))
            bonus_str = ' ' * 44
    elif bonus and 'TP' in bonus.upper() and '/' in bonus:
        # Handle TP values with bonus separator like "TP,/something"
        tp_part, bonus_after = bonus.split('/', 1)
        discount_str = f'{tp_part}'.rjust(9)
        bonus_str = bonus_after.ljust(44) if bonus_after else ' ' * 44
    elif bonus and 'TP' in bonus.upper():
        # Handle TP values without separator (just "TP" or "TP,")
        discount_str = f'{bonus}'.rjust(9)
        bonus_str = ' ' * 44
    elif has_slash_separator and bonus:
        # '/' was used as separator - bonus goes in bonus column
        discount_str = f'{discount:.2f}%'.rjust(9)
        bonus_str = bonus.ljust(44)
    elif bonus:
        # No '/' separator but there's text after % - append to discount
        if discount > 0:
            discount_str = f'{discount:.2f}%{bonus}'.rjust(9 + len(bonus))
            bonus_str = ' ' * 44
        else:
            discount_str = f'0.00%{bonus}'.rjust(9 + len(bonus))
            bonus_str = ' ' * 44
    else:
        discount_str = f'{discount:.2f}%'.rjust(9)
        bonus_str = ' ' * 44

    return f'''<tr class="item"><td align="center">
 {str(serial).ljust(4)}
</td><td style=" text-align: left;" >
{display_name}
<input type="hidden" id="itnameid{serial}" value='{hidden_name}'>
</td><td align="center">
<input type="number" min="0" max="1000" class="qty" placeholder="Qty" id="nameid{serial}">
</td><td align="center">{discount_str}
</td><td colspan="3" align="center">
{bonus_str}
</td></tr>
'''

def generate_section_header(letter):
    return f'<tr><td colspan="7" align="center" style=" background: rgb(12,146,252); background: radial-gradient(circle, rgba(12,146,252,1) 50%, rgba(255,255,255,1) 100%); color:white;" ><b>{letter}</b></td></tr>'

def generate_js_vars_full(data_items):
    """Generate JS variables for Printf and myfun (with ITMBONUS and ITMDISC)"""
    js_vars = ""
    for i, (item_name, value) in enumerate(data_items, 1):
        discount, bonus = parse_discount_value(value)
        has_slash = '/' in value

        # Special handling for "TP" and similar non-numeric values
        if 'TP' in value.upper():
            if has_slash and '/' in bonus:
                # TP with bonus separator like "TP,/5+5"
                tp_part, bonus_after = bonus.split('/', 1)
                discount_str = f'"{tp_part}"'
                bonus_str = f'"{bonus_after}"' if bonus_after else '""'
            else:
                # Plain TP or TP with comma
                discount_str = f'"{value}"'
                bonus_str = '""'
            js_vars += f'''
var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = {discount_str};
var namevar{i}=document.getElementById("nameid{i}").value;
'''
        elif 'net' in value.lower():
            # For NET values like "330 NET", keep the original value
            if has_slash:
                main_part = value.split('/')[0].strip()
                discount_str = f'"{main_part}"'
                bonus_str = f'"{bonus}"' if bonus else '""'
            else:
                discount_str = f'"{value}"'
                bonus_str = '""'
            js_vars += f'''
var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = {discount_str};
var namevar{i}=document.getElementById("nameid{i}").value;
'''
        else:
            # For numeric values
            bonus_str = f'"{bonus}"' if bonus else '""'
            js_vars += f'''
var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = "{discount:.2f}";
var namevar{i}=document.getElementById("nameid{i}").value;
'''
    return js_vars

def generate_js_vars_createrows(data_items):
    """Generate JS variables for createRows function (PDF generation)"""
    js_vars = ""
    for i, (item_name, value) in enumerate(data_items, 1):
        discount, bonus = parse_discount_value(value)
        has_slash = '/' in value

        # Special handling for "TP" and similar non-numeric values
        if 'TP' in value.upper():
            if has_slash and '/' in bonus:
                # TP with bonus separator like "TP,/5+5"
                tp_part, bonus_after = bonus.split('/', 1)
                discount_str = f'"{tp_part}"'
                bonus_str = f'"{bonus_after}"' if bonus_after else '""'
            else:
                discount_str = f'"{value}"'
                bonus_str = '""'
            js_vars += f'''var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = {discount_str};
var namevar{i}=document.getElementById("nameid{i}").value;

var namevarr{i} = " ";
// Don't append % to non-numeric values like TP
'''
        elif 'net' in value.lower():
            # For NET values like "330 NET"
            if has_slash:
                main_part = value.split('/')[0].strip()
                discount_str = f'"{main_part}"'
                bonus_str = f'"{bonus}"' if bonus else '""'
            else:
                discount_str = f'"{value}"'
                bonus_str = '""'
            js_vars += f'''var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = {discount_str};
var namevar{i}=document.getElementById("nameid{i}").value;

var namevarr{i} = " ";
// Don't append % to NET values
'''
        else:
            # For numeric values
            bonus_str = f'"{bonus}"' if bonus else '""'
            js_vars += f'''var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = "{discount:.2f}%";
var namevar{i}=document.getElementById("nameid{i}").value;

var namevarr{i} = " ";
'''
    return js_vars

def generate_js_vars_simple(data_items):
    """Generate JS variables for mywht (including ITMCODE, ITMNAME, ITMBONUS, ITMDISC, namevar)"""
    js_vars = ""
    for i, (item_name, value) in enumerate(data_items, 1):
        discount, bonus = parse_discount_value(value)
        has_slash = '/' in value

        # Special handling for "TP" and similar non-numeric values
        if 'TP' in value.upper():
            if has_slash and '/' in bonus:
                # TP with bonus separator like "TP,/5+5"
                tp_part, bonus_after = bonus.split('/', 1)
                discount_str = f'"{tp_part}"'
                bonus_str = f'"{bonus_after}"' if bonus_after else '""'
            else:
                discount_str = f'"{value}"'
                bonus_str = '""'
            js_vars += f'''
var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} = {discount_str};
var namevar{i}=document.getElementById("nameid{i}").value;
'''
        else:
            # For numeric values
            bonus_str = f'"{bonus}"' if bonus else '""'
            js_vars += f'''
var ITMCODE{i} = "{i}";
var ITMNAME{i} =document.getElementById("itnameid{i}").value;
var ITMBONUS{i} = {bonus_str};
var ITMDISC{i} =       {discount:8.2f}    ;
var namevar{i}=document.getElementById("nameid{i}").value;
'''
    return js_vars

def generate_js_if_blocks(data_items, window_var='mywindow'):
    """Generate JS if blocks for Printf and myfun"""
    js_blocks = ""
    for i in range(1, len(data_items) + 1):
        item_value = data_items[i-1][1]  # Get the original value
        is_special = 'TP' in item_value.upper() or 'net' in item_value.lower()

        if is_special:
            # For TP and NET values, don't append %
            js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{

var serial = (serial+1);
 {window_var}.document.write('<tr class="item"><td align="center">');
 {window_var}.document.write(ITMCODE{i});
 {window_var}.document.write('</td><td style="text-align:left;">');
 {window_var}.document.write(ITMNAME{i});
 {window_var}.document.write('</td><td align="right">');
 {window_var}.document.write(namevar{i});
 {window_var}.document.write('</td><td align="right">');
 {window_var}.document.write(ITMDISC{i});
 {window_var}.document.write('</td><td align="center">');
 {window_var}.document.write(ITMBONUS{i});
 {window_var}.document.write('</td></tr>');
}}
'''
        else:
            # For regular percentage values, append %
            js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{

var serial = (serial+1);
 {window_var}.document.write('<tr class="item"><td align="center">');
 {window_var}.document.write(ITMCODE{i});
 {window_var}.document.write('</td><td style="text-align:left;">');
 {window_var}.document.write(ITMNAME{i});
 {window_var}.document.write('</td><td align="right">');
 {window_var}.document.write(namevar{i});
 {window_var}.document.write('</td><td align="right">');
 {window_var}.document.write(ITMDISC{i});
 {window_var}.document.write(' %</td><td align="center">');
 {window_var}.document.write(ITMBONUS{i});
 {window_var}.document.write('</td></tr>');
}}
'''
    return js_blocks

def generate_js_if_blocks_pdf(data_items):
    """Generate JS if blocks for myfun PDF (rows.push)"""
    js_blocks = ""
    for i in range(1, len(data_items) + 1):
        js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{

var serial = (serial+1);
rows.push([ITMCODE{i}, ITMNAME{i}, namevar{i}, ITMDISC{i}]);
}}
'''
    return js_blocks

def generate_js_if_blocks_whatsapp(data_items):
    """Generate JS if blocks for mywht (WhatsApp)"""
    js_blocks = ""

    for i in range(1, len(data_items) + 1):
        # Check if this is a special case like "TP" that shouldn't get % appended
        item_value = data_items[i-1][1]  # Get the original value
        is_special_value = item_value.upper() == 'TP' or 'TP' in item_value.upper()

        if i <= 3:  # Add header check to first few items to ensure it gets added
            # For the first few items, add header if it hasn't been added yet
            if is_special_value:
                # For special values like TP, don't add % to discText
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
// Add header once at the beginning if it hasn't been added yet
if(text == "") {{
 text = "*Name* :%0a*List no* :000085(1)%0a--------------------%0a|%20*Code*%20|%20*QTY*%20|%20*ITM*%20|%20*DISC*%20|%20*Bonus*%20|%0a--------------------%0a";
}}
var serial = (serial+1);

 // For special values like TP, don't append %
 var discText = ITMDISC{i};
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMBONUS{i};
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a";
}}
'''
            else:
                # For numeric values, use original logic
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
// Add header once at the beginning if it hasn't been added yet
if(text == "") {{
 text = "*Name* :%0a*List no* :000085(1)%0a--------------------%0a|%20*Code*%20|%20*QTY*%20|%20*ITM*%20|%20*DISC*%20|%20*Bonus*%20|%0a--------------------%0a";
}}
var serial = (serial+1);

 // Show discount with % if non-zero, otherwise show empty in discount column
 var discText = ITMDISC{i} != 0 ? ITMDISC{i} + "%" : "";
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMDISC{i} == 0 ? ITMBONUS{i} : "";
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a";
}}
'''
        elif i == len(data_items):
            # For the last item, add the item and total
            if is_special_value:
                # For special values like TP, don't add % to discText
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
var serial = (serial+1);

 // For special values like TP, don't append %
 var discText = ITMDISC{i};
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMBONUS{i};
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a"+"%0a*Total* *Items* : "+serial;
}}
'''
            else:
                # For numeric values, use original logic
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
var serial = (serial+1);

 // Show discount with % if non-zero, otherwise show empty in discount column
 var discText = ITMDISC{i} != 0 ? ITMDISC{i} + "%" : "";
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMDISC{i} == 0 ? ITMBONUS{i} : "";
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a"+"%0a*Total* *Items* : "+serial;
}}
'''
        else:
            # For other items, just add the item
            if is_special_value:
                # For special values like TP, don't add % to discText
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
var serial = (serial+1);

 // For special values like TP, don't append %
 var discText = ITMDISC{i};
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMBONUS{i};
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a";
}}
'''
            else:
                # For numeric values, use original logic
                js_blocks += f'''if(namevar{i}==0 ){{
}}
else {{
var serial = (serial+1);

 // Show discount with % if non-zero, otherwise show empty in discount column
 var discText = ITMDISC{i} != 0 ? ITMDISC{i} + "%" : "";
 // Show bonus in bonus column if discount is 0, otherwise show empty
 var bonusText = ITMDISC{i} == 0 ? ITMBONUS{i} : "";
 var text=text+"|"+ITMCODE{i}+"%20|%20"+namevar{i}+"%20|%20"+ITMNAME{i}+"%20|%20"+discText+"%20|%20"+bonusText+"%20|%0a--------------------%0a";
}}
'''
    return js_blocks

def update_htm(htm_filepath, data_items, output_filepath):
    """Update list.HTM with all items from data.txt"""
    with open(htm_filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    total_count = len(data_items)

    # 1. Replace "Code" header with "Sr#"
    content = re.sub(
        r'(<td style="text-align: center; border-radius: 16px 0px 0px 0px;">)(Code|Sr#)(</td>)',
        r'\1Sr#\3',
        content
    )

    # 2. Update tbody
    tbody_start = content.find('<tbody id="myTable">')
    tbody_end = content.find('</tbody>')

    if tbody_start == -1 or tbody_end == -1:
        print("ERROR: Could not find tbody section")
        return

    items_html = ""
    current_letter = ""
    for i, (item_name, value) in enumerate(data_items, 1):
        first_letter = item_name[0].upper() if item_name else "?"
        if first_letter != current_letter:
            current_letter = first_letter
            items_html += generate_section_header(current_letter)
        items_html += generate_item_row(i, item_name, value)

    items_html += f'''<tr class="heading2"> <td style=" text-align: CENTER; border-radius: 0px 0px 16px 16px; padding-left: 10px;" colspan="5" >Total Products :
  {total_count}
</td></tr>
'''

    content = content[:tbody_start + len('<tbody id="myTable">')] + items_html + content[tbody_end:]

    # 3. Generate new JS content
    js_vars_full = generate_js_vars_full(data_items)
    js_vars_simple = generate_js_vars_simple(data_items)
    js_if_blocks_printf = generate_js_if_blocks(data_items, 'mywindow')
    js_if_blocks_myfun = generate_js_if_blocks(data_items, 'myWindow')
    js_if_whatsapp = generate_js_if_blocks_whatsapp(data_items)

    # 4. Update Printf function
    # Variables: from "var serial = 0;" to "var mywindow = window.open"
    content = re.sub(
        r'(function Printf\(\)\{\nvar ITDATE = "[^"]*";\nvar LSTNO = "[^"]*";\nvar custname = document\.getElementById\("cstname"\)\.value;\nvar serial = 0;\n)'
        r'.*?'
        r'(\n\n\n var mywindow = window\.open)',
        r'\1' + js_vars_full + r'\2',
        content,
        flags=re.DOTALL
    )

    # Printf if blocks: from "if(namevar1==0" to before "mywindow.document.write('<tr class=\"heading2\">"
    content = re.sub(
        r"if\(namevar1==0 \)\{\n\}\nelse \{\n\nvar serial = \(serial\+1\);\n mywindow\.document\.write\('<tr class=\"item\">.*?"
        r"( mywindow\.document\.write\('<tr class=\"heading2\"> <td)",
        js_if_blocks_printf + r'\1',
        content,
        flags=re.DOTALL,
        count=1
    )

    # 5. Update mywht function
    # Variables: from "var serial = 0;" to before "if(namevar1==0"
    content = re.sub(
        r'(function mywht\(\)\{\nvar ITDATE = "[^"]*";\nvar LSTNO = "[^"]*";\nvar custname = document\.getElementById\("cstname"\)\.value;\nvar text= "";\n\nvar serial = 0;\n)'
        r'.*?'
        r'(if\(namevar1==0 \))',
        r'\1' + js_vars_simple + r'\n\2',
        content,
        flags=re.DOTALL
    )

    # mywht if blocks: from first if to before "var url="
    content = re.sub(
        r'(function mywht\(\)\{.*?var serial = 0;\n)'
        r'.*?'
        r'(\nvar url="https://wa\.me)',
        r'\1' + js_vars_simple + '\n' + js_if_whatsapp + r'\2',
        content,
        flags=re.DOTALL
    )

    # 6. Update myfun function
    # Variables: from "var serial = 0;" to "myWindow=window.open"
    content = re.sub(
        r'(function myfun\(\)\{\nvar ITDATE = "[^"]*";\nvar LSTNO = "[^"]*";\nvar custname = document\.getElementById\("cstname"\)\.value;\nvar serial = 0;\n)'
        r'.*?'
        r'(\nmyWindow=window\.open)',
        r'\1' + js_vars_full + r'\2',
        content,
        flags=re.DOTALL
    )

    # myfun if blocks (preview): from "if(namevar1==0" to before "myWindow.document.write('<tr class=\"heading2\">"
    content = re.sub(
        r"if\(namevar1==0 \)\{\n\}\nelse \{\n\nvar serial = \(serial\+1\);\n myWindow\.document\.write\('<tr class=\"item\">.*?"
        r"( myWindow\.document\.write\('<tr class=\"heading2\"> <td)",
        js_if_blocks_myfun + r'\1',
        content,
        flags=re.DOTALL,
        count=1
    )

    # 7. Update createRows function (PDF generation)
    js_vars_createrows = generate_js_vars_createrows(data_items)
    js_if_blocks_pdf = generate_js_if_blocks_pdf(data_items)

    # Update createRows variables: from "const rows = [];" to "var serial = 0;"
    content = re.sub(
        r'(function createRows\(count\) \{\n  const rows = \[\];\n\n)'
        r'.*?'
        r'(var serial = 0;)',
        r'\1' + js_vars_createrows + r'\2',
        content,
        flags=re.DOTALL
    )

    # Update createRows if blocks (PDF): rows.push blocks
    content = re.sub(
        r"if\(namevar1==0 \)\{\n\}\nelse \{\n\nvar serial = \(serial\+1\);\nrows\.push.*?"
        r"(\nvar totitem=)",
        js_if_blocks_pdf + r'\1',
        content,
        flags=re.DOTALL,
        count=1
    )

    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Generated {total_count} items in table")
    print(f"Updated Printf, mywht, myfun, createRows functions")
    print(f"Total Products: {total_count}")

if __name__ == '__main__':
    data_file = 'data.txt'
    htm_file = 'list.HTM'

    print("Reading data.txt...")
    data_items = parse_data_txt(data_file)
    print(f"Found {len(data_items)} items in data.txt")

    print("\nUpdating list.HTM...")
    update_htm(htm_file, data_items, htm_file)

    print("\nDone!")
