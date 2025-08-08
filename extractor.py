import PyPDF2
import pdfplumber
import docx
import os
import requests
import tempfile
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def download_pdf(url):
    try:
        logger.info(f"Downloading PDF from {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_file.write(response.content)
        temp_file.close()
        logger.info(f"PDF downloaded to temporary file: {temp_file.name}")
        return temp_file.name
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}")
        return f"Error downloading PDF: {str(e)}"

def extract_from_pdf(file_path):
    text = ""
    f=open("file.txt","w")

    try:
        # Try pdfplumber first
        logger.info(f"Attempting text extraction with pdfplumber for {file_path}")
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    f.write(page_text)
                    if page_text:
                        text += page_text + "\n\n"
                        logger.info(f"Extracted text from page {i+1} with pdfplumber")
                    else:
                        logger.warning(f"No text extracted from page {i+1} with pdfplumber")
                except Exception as e:
                    logger.error(f"Error extracting page {i+1} with pdfplumber: {str(e)}")
        
        # If no text or partial text, try PyPDF2
        if not text.strip():
            logger.info(f"No text extracted with pdfplumber, falling back to PyPDF2")
            try:
                with open(file_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for i, page in enumerate(reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n\n"
                                f.write(page_text)
                                logger.info(f"Extracted text from page {i+1} with PyPDF2")
                            else:
                                logger.warning(f"No text extracted from page {i+1} with PyPDF2")
                        except Exception as e:
                            logger.error(f"Error extracting page {i+1} with PyPDF2: {str(e)}")
            except Exception as e:
                logger.error(f"Error with PyPDF2: {str(e)}")
        
        # If still no text, try OCR with pytesseract
        if not text.strip():
            logger.info(f"No text extracted with PyPDF2, attempting OCR with pytesseract")
            try:
                images = convert_from_path(file_path)
                for i, image in enumerate(images):
                    try:
                        page_text = pytesseract.image_to_string(image, lang='eng')
                        if page_text:
                            text += page_text + "\n\n"
                            f.write(page_text)
                            logger.info(f"Extracted text from page {i+1} with pytesseract")
                        else:
                            logger.warning(f"No text extracted from page {i+1} with pytesseract")
                    except Exception as e:
                        logger.error(f"Error extracting page {i+1} with pytesseract: {str(e)}")
            except Exception as e:
                logger.error(f"Error with pytesseract: {str(e)}")
        
        return text if text.strip() else "No text extracted from PDF."
    except Exception as e:
        logger.error(f"General error extracting from PDF: {str(e)}")
        return f"Error extracting from PDF: {str(e)}"
    f.close()

def extract_from_docx(file_path):
    try:
        logger.info(f"Extracting text from DOCX: {file_path}")
        doc = docx.Document(file_path)
        text = ""
        f=open("file.txt","w")
        for para in doc.paragraphs:
            text += para.text + "\n"
            f.write(para.text)
        logger.info(f"Successfully extracted text from DOCX")
        return text if text.strip() else "No text extracted from DOCX."
    except Exception as e:
        logger.error(f"Error extracting from DOCX: {str(e)}")
        return f"Error extracting from DOCX: {str(e)}"

def extract_text(input_source, is_url=False):
    temp_file_path = None
    try:
        if is_url:
            result = download_pdf(input_source)
            if "Error" in result:
                return result
            file_path = result
            temp_file_path = file_path
            
        else:
            file_path = input_source
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return "File not found."

        extension = os.path.splitext(file_path)[1].lower() if not is_url else ".pdf"
        if extension == '.pdf':
            return extract_from_pdf(file_path)
        elif extension == '.docx':
            return extract_from_docx(file_path)
        elif extension == '.txt':
            try:
                logger.info(f"Reading TXT file: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except Exception as e:
                logger.error(f"Error reading TXT file: {str(e)}")
                return f"Error reading TXT file: {str(e)}"
        else:
            logger.error(f"Unsupported file format: {extension}")
            return "Unsupported file format. Use PDF, DOCX, or TXT."
    finally:
        if is_url and temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Deleted temporary file: {temp_file_path}")
            except Exception as e:
                logger.error(f"Error deleting temporary file: {str(e)}")

def save_to_file(text, output_path):
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(text)
        logger.info(f"Extracted text saved to: {output_path}")
        print(f"Extracted text saved to: {output_path}")
    except Exception as e:
        logger.error(f"Error saving to file: {str(e)}")
        print(f"Error saving to file: {str(e)}")

if __name__ == "__main__":
    input_type = input("Enter 'file' for local file or 'url' for URL: ").lower()
    f=open('file.txt','r')
    if input_type == 'url':
        input_source = input("Enter the URL of the PDF: ")
        result = extract_text(input_source, is_url=True)
    else:
        input_source = input("Enter the path to the document: ")
        result = extract_text(input_source, is_url=False)
    
    if "Error" not in result and "Unsupported" not in result and "not found" not in result:
        output_file = "extracted_text.txt"
        save_to_file(result, output_file)
    else:
        print(result)
        logger.error(f"Extraction failed: {result}")