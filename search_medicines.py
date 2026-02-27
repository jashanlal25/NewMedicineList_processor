import os
import json
from bs4 import BeautifulSoup
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
import re

class MedicineSearcher:
    def __init__(self):
        self.lists_data = []

    def extract_company_and_discount_from_html(self, file_path):
        """Extract company name and potentially discount from the top of HTML files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Try to extract company name from various possible locations
        company_name = None

        # 1. Check JavaScript variables that might contain shop title
        import re
        js_title_pattern = r'var\s+(?:TITLETOTO|shopTitle)\s*=\s*["\']([^"\']+)["\']'
        js_matches = re.findall(js_title_pattern, html_content, re.IGNORECASE)
        if js_matches:
            # Take the first match which is likely the main title
            company_name = js_matches[0].strip()
            if company_name and company_name.lower() not in ['offer list', '']:  # Exclude common generic titles
                return company_name

        # 2. Check for elements with specific class names that suggest shop names
        for element in soup.find_all(['h1', 'h2', 'h3'], class_=re.compile(r'shop', re.I)):
            text = element.get_text().strip()
            if text and 'shop' not in text.lower() and 'list' not in text.lower():
                company_name = text
                return company_name

        # 3. Check title tag
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text().strip()
            # Only use title if it contains shop-related keywords
            if any(keyword in title_text.lower() for keyword in ['offer list', 'list']):
                # Look for the actual shop name elsewhere if title is generic
                pass
            else:
                company_name = title_text

        # 4. Check for common headings that might contain company info
        if not company_name:
            # Look in first 20 heading tags to prioritize early content
            first_h_tags = soup.find_all(['h1', 'h2', 'h3'])[:20]  # Check first 20 heading tags
            for tag in first_h_tags:
                text = tag.get_text().strip()
                # Look for specific patterns that suggest shop names
                # First check if this text contains shop-related keywords and skip design/developed tags
                text_lower = text.lower().replace("'", "").replace('"', "")  # Remove quotes for matching
                if ('design' in text_lower or 'developed' in text_lower or
                    ('by' in text_lower and len(text.split()) <= 4)):  # Likely "Design By X" or "Developed By X"
                    continue
                elif (any(keyword in text_lower for keyword in ['medicos', 'impex', 'pharma', 'pharmacy', 'dealer', 'medical', 'chemist'])
                    and len(text) > 3 and 'list' not in text_lower):
                    company_name = text
                    break

        # 5. Check for common heading elements that might contain shop information
        if not company_name:
            # Look in the beginning of the document for shop-related elements
            first_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'td', 'th', 'p', 'center'])[:20]  # First 20 elements
            for element in first_elements:
                text = element.get_text().strip()
                # Look for text that contains "medicos", "impex", or other shop indicators
                if (any(keyword in text.lower() for keyword in ['medicos', 'impex', 'pharma', 'pharmacy', 'dealer', 'medical', 'chemist'])
                    and len(text) > 3 and 'list' not in text.lower()
                    and 'developed' not in text.lower() and 'design' not in text.lower()):
                    company_name = text
                    break

        # 6. Check for company name in heading elements with specific patterns
        if not company_name:
            for element in soup.find_all(['div', 'td', 'th', 'p', 'center']):
                text = element.get_text().strip()
                if any(keyword in text.lower() for keyword in ['shop', 'company', 'business', 'store', 'trading as']):
                    # Extract the company name from this context
                    if ':' in text:
                        extracted_name = text.split(':')[1].strip()
                        if len(extracted_name) > 3 and not extracted_name.isdigit():
                            company_name = extracted_name
                            break
                    else:
                        # Might be a direct mention
                        siblings = element.find_next_siblings(['div', 'td', 'th', 'p'], limit=3)
                        for sibling in siblings:
                            sibling_text = sibling.get_text().strip()
                            if (sibling_text and 'medicos' in sibling_text.lower() or 'impex' in sibling_text.lower()
                                or 'pharma' in sibling_text.lower() or 'pharmacy' in sibling_text.lower()
                                and len(sibling_text) > 3):
                                company_name = sibling_text
                                break

        return company_name or os.path.basename(file_path)

    def extract_medicines_from_html(self, file_path):
        """Extract medicines from HTML file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            html_content = file.read()

        soup = BeautifulSoup(html_content, "html.parser")
        items = soup.find_all("tr", class_="item")

        medicines = []
        for item in items:
            columns = item.find_all("td")
            if len(columns) >= 3:  # Need at least name column
                # Need to intelligently identify which column contains the medicine name and discount
                medicine_name = ""
                discount = ""

                # Look for the most likely name column (should contain alphabetic characters, not just numbers)
                name_col_idx = -1

                # Look through columns to find the one that looks like a medicine name
                for i in range(min(len(columns), 5)):  # Check first few columns
                    col_text = columns[i].text.strip()
                    # A medicine name usually contains letters and is typically longer descriptive text
                    if col_text and any(c.isalpha() for c in col_text):
                        # Avoid columns that are purely numbers, short codes, or single characters
                        # Medicine codes are typically short (3-6 chars) with letters and numbers,
                        # while medicine names are longer descriptive names
                        if not (col_text.isdigit() or
                                col_text.replace('-', '').isdigit() or
                                (len(col_text.strip()) <= 6 and
                                 col_text.replace('-', '').replace('.', '').replace(' ', '').isalnum() and
                                 any(c.isalpha() for c in col_text) and
                                 any(c.isdigit() for c in col_text)) or  # This checks for short codes like 'Y138', 'F410'
                                (col_text.replace('.', '').replace('-', '').isdigit() and len(col_text) <= 10)):
                            name_col_idx = i
                            medicine_name = col_text.title()
                            break

                # If we still don't have a good name, try default positions (1 or 2)
                if not medicine_name and len(columns) > 1:
                    for i in [1, 2]:
                        if i < len(columns):
                            col_text = columns[i].text.strip()
                            if col_text and any(c.isalpha() for c in col_text):
                                medicine_name = col_text.title()
                                name_col_idx = i
                                break

                # Extract discount intelligently as well
                for i in range(len(columns)):
                    if i == name_col_idx:  # Skip the name column
                        continue
                    col_text = columns[i].text.strip()
                    # Check if this looks like a discount (contains % or looks like a percentage)
                    if col_text and ('%' in col_text.lower() or
                        (col_text.replace('.', '').replace('-', '').isdigit() and
                         col_text.replace('.', '').replace('-', '') != '' and
                         0 <= float(col_text.replace('-', '')) <= 100)):
                        # Prefer columns with % sign
                        if '%' in col_text.lower():
                            discount = col_text
                            break
                        elif not discount:  # Use first numerical discount if no % found yet
                            discount = col_text

                if medicine_name:
                    medicines.append({
                        'name': medicine_name,
                        'discount': discount,
                        'raw_data': str(item)
                    })

        return medicines

    def extract_company_and_discount_from_text(self, file_path):
        """Extract company name from the top of text files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()

        # Look at the first few lines for company information
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            text = line.strip()
            if any(keyword in text.lower() for keyword in ['pharma', 'pharmacy', 'dealer', 'medical', 'chemist', 'shop', 'company']):
                if ':' in text:
                    return text.split(':')[1].strip()
                else:
                    return text
            if text and not text.startswith('#') and not text.startswith('→'):  # Skip comments and special markers
                # If it looks like a header, return it
                if any(keyword in text.lower() for keyword in ['list', 'offer', 'stock', 'price']):
                    return text

        return os.path.basename(file_path)

    def extract_medicines_from_text(self, file_path):
        """Extract medicines from text file"""
        medicines = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        # Look for the pattern: medicine_name----- discount%
        lines = content.split('\n')
        for line in lines:
            if '-----' in line:
                parts = line.split('-----')
                if len(parts) >= 2:
                    medicine_name = parts[0].strip().title()
                    discount = parts[1].strip().rstrip(',')
                    medicines.append({
                        'name': medicine_name,
                        'discount': discount,
                        'raw_data': line
                    })

        return medicines

    def extract_company_and_discount_from_pdf(self, file_path):
        """Extract company name from the top of PDF files"""
        if PyPDF2 is None:
            print("PyPDF2 not available, skipping PDF processing")
            return os.path.basename(file_path)

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                # Extract text from first few pages
                text = ""
                for i in range(min(len(pdf_reader.pages), 2)):  # Check first 2 pages
                    text += pdf_reader.pages[i].extract_text()

                # Look at first few lines for company information
                lines = text.split('\n')
                for line in lines[:20]:  # Check first 20 lines
                    if any(keyword in line.lower() for keyword in ['pharma', 'pharmacy', 'dealer', 'medical', 'chemist', 'shop', 'company']):
                        if ':' in line:
                            return line.split(':')[1].strip()
                        else:
                            return line.strip()
        except Exception as e:
            print(f"Error reading PDF {file_path}: {str(e)}")

        return os.path.basename(file_path)

    def extract_medicines_from_pdf(self, file_path):
        """Extract medicines from PDF file"""
        medicines = []

        if PyPDF2 is None:
            print("PyPDF2 not available, skipping PDF processing")
            return medicines

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()

                # Look for medicine patterns in the text
                # This is a simple approach - could be enhanced based on actual PDF structure
                lines = text.split('\n')
                for line in lines:
                    # Look for potential medicine entries
                    if '-----' in line:
                        parts = line.split('-----')
                        if len(parts) >= 2:
                            medicine_name = parts[0].strip().title()
                            discount = parts[1].strip().rstrip(',')
                            medicines.append({
                                'name': medicine_name,
                                'discount': discount,
                                'raw_data': line
                            })
                    elif re.search(r'[A-Z][a-z]+\d+', line) or re.search(r'\d+[A-Z][a-z]+', line):
                        # Simple pattern detection for medicine names with numbers
                        medicines.append({
                            'name': line.strip(),
                            'discount': 'N/A',
                            'raw_data': line
                        })
        except Exception as e:
            print(f"Error reading PDF {file_path}: {str(e)}")

        return medicines

    def get_shop_name_from_file(self, file_path):
        """Extract shop name from file content or filename"""
        file_ext = os.path.splitext(file_path)[1].lower()

        # Use format-specific extraction methods
        if file_ext in ['.htm', '.html']:
            return self.extract_company_and_discount_from_html(file_path)
        elif file_ext in ['.txt', '.text']:
            return self.extract_company_and_discount_from_text(file_path)
        elif file_ext in ['.pdf']:
            return self.extract_company_and_discount_from_pdf(file_path)
        else:
            # Fallback to filename
            return os.path.basename(file_path)

    def process_file(self, file_path):
        """Process a single file and extract medicines"""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in ['.htm', '.html']:
            medicines = self.extract_medicines_from_html(file_path)
        elif file_ext in ['.txt', '.text']:
            medicines = self.extract_medicines_from_text(file_path)
        elif file_ext in ['.pdf']:
            medicines = self.extract_medicines_from_pdf(file_path)
        else:
            return []

        # Get shop name for this file
        shop_name = self.get_shop_name_from_file(file_path)

        # Add shop name to each medicine entry
        for med in medicines:
            med['shop'] = shop_name
            med['file_path'] = file_path

        return medicines

    def search_medicines(self, file_paths, search_terms):
        """Search for medicines across all provided files"""
        all_medicines = []

        # Process all files
        for file_path in file_paths:
            try:
                medicines = self.process_file(file_path)
                all_medicines.extend(medicines)
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")

        # Search for the requested medicines with improved algorithm
        results = []
        for term in search_terms:
            term_lower = term.lower().strip()
            found_medicines = []

            # Split the search term into individual words
            search_words = [word.strip() for word in term_lower.split() if word.strip()]

            for med in all_medicines:
                med_name_lower = med['name'].lower()

                # Split medicine name into words
                med_words = [word.strip() for word in med_name_lower.split() if word.strip()]

                # 1. Exact match
                if term_lower == med_name_lower:
                    found_medicines.append(med)
                    continue

                # 2. If searching for a specific medicine name with strength (like "azomax 500")
                # only match if the medicine name contains all the words from the search term
                # but be careful not to match "500" alone with unrelated medicines
                if len(search_words) == 1:
                    # Single word search (like "500") - need to be careful
                    search_word = search_words[0]
                    if len(search_word) < 3:
                        # If it's a very short word (likely a strength like "500"), it should be part of a specific medicine
                        # Match only if it's part of a larger name where we expect that strength
                        for med_word in med_words:
                            if search_word == med_word or (search_word in med_word and any(char.isalpha() for char in med_word)):
                                found_medicines.append(med)
                                break
                    else:
                        # If it's a longer word, it might be a medicine name part - allow partial matching
                        if search_word in med_name_lower:
                            found_medicines.append(med)
                else:
                    # Multiple word search (like "azomax 500")
                    # All words should appear in the medicine name
                    all_search_words_found = True
                    for search_word in search_words:
                        word_found = False

                        # For each word in the search term, check if it appears in the medicine name
                        if len(search_word) < 3:
                            # Short word like "500" - should match as part of medicine name or be adjacent to letters
                            for med_word in med_words:
                                if search_word in med_word and any(c.isalpha() for c in med_word):
                                    word_found = True
                                    break
                        else:
                            # Longer words should match as complete words or as parts of medicine names
                            for med_word in med_words:
                                if search_word in med_word.lower():
                                    word_found = True
                                    break

                        if not word_found:
                            all_search_words_found = False
                            break

                    if all_search_words_found:
                        found_medicines.append(med)

            # Add this search term and its results
            results.append({
                'search_term': term,
                'matches': found_medicines
            })

        return results

# Example usage
if __name__ == "__main__":
    searcher = MedicineSearcher()

    # Example:
    # file_paths = ['file1.html', 'file2.txt', 'file3.pdf']
    # search_terms = ['azomax 500', 'caflam', 'collapep']
    # results = searcher.search_medicines(file_paths, search_terms)
    # print(json.dumps(results, indent=2))