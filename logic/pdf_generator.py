from fpdf import FPDF
from datetime import datetime
import os
import re
from html import unescape

line_height = 5
spacing_between_records = 2

class CustomPDF(FPDF):
    def __init__(self, printed_on):
        """
        Constructor for CustomPDF class.

        Args:
            printed_on (str): The date in string format when the PDF was printed.

        Initializes the PDF object, sets the automatic page break to False, and
        sets the alias for the total number of pages.
        """
        super().__init__()
        self.printed_on = printed_on
        self.set_auto_page_break(auto=False)
        self.alias_nb_pages()
        self.unifontsubset = False
        
    def footer(self):
        """
        Footer method to print the page number and printed on date at the bottom of each page.

        The method sets the y-coordinate to 6, sets the font to Arial with size 6,
        and then prints the page number and printed on date at the bottom of each page.
        """
        self.set_y(6)
        self.set_font("Arial", size=6)
        self.cell(0, 6, f"Page {self.page_no()} of {{nb}} | Printed on {self.printed_on}", align='R')

def sanitize_text(text):
    """
    Sanitize the input text by ensuring it is in a valid string format and encoding.

    This function converts the input text to a string if it is not already and encodes it in
    'latin-1', replacing any characters that cannot be encoded with a placeholder. It then
    decodes the text back to a string. If the input is None, an empty string is returned.
    If an exception occurs during encoding or decoding, "[Invalid Text]" is returned.

    Args:
        text: The input text to sanitize, which can be of any type.

    Returns:
        A sanitized string, or "[Invalid Text]" if an error occurs.
    """

    try:
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
            
        # Replace special hyphens
        text = text.replace("–", "-").replace("—", "-")
        
        return text.encode("latin-1", "replace").decode("latin-1")
    except Exception:
        return "[Invalid Text]"
    
def strip_html_tags(text: str) -> str:
    """
    Strips HTML tags and entities from a given text.

    This function takes a given string, removes all HTML tags and entities, and returns the
    resulting string. It removes HTML comments, script tags, style tags, and all other HTML tags,
    and then removes any remaining HTML entities (e.g. &nbsp;, &lt;, etc.). It then replaces
    multiple whitespace characters with a single space and removes any leading or trailing
    whitespace.

    Args:
        text (str): The input string to strip HTML tags from.

    Returns:
        str: The resulting string with all HTML tags and entities removed.
    """
    if not isinstance(text, str):
        return ''
    
    # Remueve comentarios HTML
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remueve scripts y estilos
    text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remueve todas las etiquetas HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remueve entidades HTML como &nbsp;, &lt;, etc.
    text = unescape(text)

    # Reemplaza múltiples espacios por uno solo
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def clean_field(field):
    text = sanitize_text(field).strip().lower()
    return text not in ["", "-None"]

def normalize_paragraph(text):
    lines = text.splitlines()
    return ' '.join(line.strip() for line in lines if line.strip())

#new op2
def write_wrapped_value(pdf, value, value_width, label_y_end, label_width):
    """
    Escribe el 'value' como párrafo, ocupando el espacio disponible, y continuando en otra página si no cabe.
    Devuelve la posición final del cursor (get_y).
    """
    original_y = label_y_end - line_height
    pdf.set_xy(pdf.l_margin + label_width + 2, original_y)
    lines = pdf.multi_cell(value_width, line_height, value, split_only=True)
    
    available_lines = int((pdf.h - pdf.b_margin - label_y_end) // line_height)
    
    if available_lines > 0:
        text_part_1 = "\n".join(lines[:available_lines])
        pdf.set_xy(pdf.l_margin + label_width + 2, original_y)
        pdf.multi_cell(value_width, line_height, text_part_1)
    
    remaining_lines = lines[available_lines:]
    if remaining_lines:
        text_part_2 = "\n".join(remaining_lines)
        pdf.add_page()
        pdf.set_xy(pdf.l_margin + label_width + 2, pdf.get_y())
        pdf.multi_cell(value_width, line_height, text_part_2)
    
    return pdf.get_y()

def simulate_title_and_line_height(pdf, title, label_width, value_width):
    y_start = pdf.get_y()
    pdf.set_font("Arial", 'B', 9)
    pdf.multi_cell(0, 6, title, align="C")
    pdf.set_font("Arial", '', 9)
    pdf.multi_cell(label_width, line_height)
    pdf.multi_cell(value_width, line_height)
    return pdf.get_y() - y_start

def write_transposed_data(pdf, data, filename_base, sheet_name):
    label_width = pdf.w * 0.20
    value_width = pdf.w - pdf.l_margin - pdf.r_margin - label_width - 2

    for i, record in enumerate(data):
        title = sanitize_text(f"{filename_base} - {sheet_name} - Record #{i + 1}")

        if pdf.page_no() == 0:
            pdf.add_page()

        # print label
        y_before = pdf.get_y()
        required_height = simulate_title_and_line_height(pdf, title, label_width, value_width)
        pdf.set_y(y_before)

        if pdf.get_y() + required_height > pdf.h - pdf.b_margin:
            pdf.add_page()

        pdf.set_font("Arial", 'B', 9)
        pdf.multi_cell(0, 6, title, align="C")
        pdf.set_font("Arial", '', 9)

        for field, value in record:
            field = sanitize_text(field).strip()
            value = sanitize_text(strip_html_tags(value)).strip()

            if not clean_field(field) and not clean_field(value):
                continue

            value = normalize_paragraph(value)

            label_text = f"{field}:"
            # y_start = pdf.get_y()

            # if y_start + line_height > pdf.h - pdf.b_margin:
            #     pdf.add_page()
            #     y_start = pdf.get_y()

            # pdf.set_xy(pdf.l_margin, y_start)
            # label_y_start = pdf.get_y()
            # pdf.multi_cell(label_width, line_height, label_text, align="L")
            # label_y_end = pdf.get_y()

            # # this is previous version and works
            # # pdf.set_xy(pdf.l_margin + label_width + 2, label_y_end - line_height)
            # # pdf.multi_cell(value_width, line_height, value)
            # # value_y_end = pdf.get_y()
            # #  pdf.set_y(max(label_y_end, value_y_end))
            
            # #new opt2
            # value_y_end = write_wrapped_value(pdf, value, value_width, label_y_end, label_width)
            # pdf.set_y(value_y_end)
            
            # Simular líneas del value
            simulated_lines = pdf.multi_cell(value_width, line_height, value, split_only=True)
            simulated_value_line_height = line_height * len(simulated_lines)

            # ¿Cabe el label + al menos una línea del value?
            space_remaining = pdf.h - pdf.b_margin - pdf.get_y()
            minimum_required = line_height + line_height  # label + una línea del value

            if space_remaining < minimum_required:
                pdf.add_page()

            # Ahora sí, imprimir label
            y_start = pdf.get_y()
            pdf.set_xy(pdf.l_margin, y_start)
            label_y_start = pdf.get_y()
            pdf.multi_cell(label_width, line_height, label_text, align="L")
            label_y_end = pdf.get_y()

            # Imprimir value correctamente (se dividirá si es necesario)
            value_y_end = write_wrapped_value(pdf, value, value_width, label_y_end, label_width)
            pdf.set_y(value_y_end)

            
        if i != len(data) - 1:
            if pdf.get_y() + spacing_between_records < pdf.h - pdf.b_margin:
                pdf.ln(spacing_between_records)


def generate_pdf(data, output_path, source_filename, sheet_name, pdf=None, log_callback=None):
    created_pdf = False
    if pdf is None:
        printed_on = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf = CustomPDF(printed_on)
        pdf.set_font("Arial", '', 9)
        created_pdf = True

    os.makedirs(output_path, exist_ok=True)
    filename_base = "".join(c for c in os.path.splitext(source_filename)[0] if c.isalnum() or c in " _-")
    clean_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in " _-")

    write_transposed_data(pdf, data, filename_base, clean_sheet_name)

    if created_pdf:
        if pdf.page_no() == 0:
            raise Exception("No pages were generated.")
        output_filename = f"{filename_base}_{clean_sheet_name}_transposed.pdf"
        output_file = os.path.join(output_path, output_filename)
        pdf.output(output_file)
        return output_file
    return pdf

def generate_combined_pdf(all_data, output_path, log_callback=None):
    try:
        printed_on = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf = CustomPDF(printed_on)
        pdf.set_font("Arial", '', 9)

        for title, records in all_data:
            filename, sheet = title.split(" - ", 1)
            filename_base = "".join(c for c in filename if c.isalnum() or c in " _-")
            clean_sheet_name = "".join(c for c in sheet if c.isalnum() or c in " _-")
            write_transposed_data(pdf, records, filename_base, clean_sheet_name)

        combined_file = os.path.join(output_path, "DataFlipper_Export.pdf")
        pdf.output(combined_file)
    except Exception as e:
        raise Exception(f"PDF generation error (Combined): {str(e)}")

def generate_pdf_per_excel(data_by_excel_file, output_path, log_callback=None):
    try:
        for filename, sheets_data in data_by_excel_file.items():
            printed_on = datetime.now().strftime("%Y-%m-%d %H:%M")
            pdf = CustomPDF(printed_on)
            pdf.set_font("Arial", '', 9)

            for sheet_title, records in sheets_data:
                filename_base = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in " _-")
                clean_sheet_name = "".join(c for c in sheet_title if c.isalnum() or c in " _-")
                write_transposed_data(pdf, records, filename_base, clean_sheet_name)

            output_filename = os.path.splitext(filename)[0] + "_Export.pdf"
            output_file = os.path.join(output_path, output_filename)
            pdf.output(output_file)
    except Exception as e:
        raise Exception(f"PDF generation error (Per Excel File): {str(e)}")