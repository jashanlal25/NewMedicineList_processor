import os
from bs4 import BeautifulSoup

def process_html_file(html_path):
    """Process a single HTML file and save extracted data to a text file."""
    with open(html_path, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")
    items = soup.find_all("tr", class_="item")

    # Create output filename (e.g., "OFFER LIST.txt" from "OFFER LIST.HTM")
    output_filename = os.path.splitext(html_path)[0] + "_name_with_%.txt"

    with open(output_filename, "w", encoding="utf-8") as output_file:
        for item in items:
            columns = item.find_all("td")
            if len(columns) >= 4:
                # Extract medicine name and apply title case
                medicine_name = columns[1].text.strip().title()
                discount_rate = columns[3].text.strip()

                # Check if discount is 0.00% and get bonus rate if available
                if discount_rate == "0.00%" and len(columns) >= 5:
                    discount_rate = columns[4].text.strip()

                # Decrease the discount rate by 1%
                try:
                    # Remove the percentage sign and convert to float
                    rate_value = float(discount_rate.strip('%'))
                    # Subtract 1%
                    rate_value -= 1
                    # Ensure the rate doesn't go below 0%
                    rate_value = max(rate_value, 0)
                    # Format back to a percentage string
                    discount_rate = f"{rate_value:.2f}%"
                except ValueError:
                    # Handle cases where the discount rate is not a valid number
                     discount_rate = "0.00%"
                     discount_rate = columns[4].text.strip()

                output_file.write(f"{medicine_name}----- {discount_rate},\n")

def main():
    # Process all .htm/.html files in the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in os.listdir(script_dir):
        if filename.lower().endswith(('.htm', '.html')):
            print(f"Processing: {filename}")
            process_html_file(os.path.join(script_dir, filename))

    print("All files processed! Press Enter to exit...")
    input()  # Pause to show completion

if __name__ == "__main__":
    main()