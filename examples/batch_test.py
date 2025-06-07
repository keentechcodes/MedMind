# Script to convert multiple PDFs to markdown using marker-pdf

import os
import json
import glob
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from PIL import Image

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Define input and output paths
input_dir = "../../../LectureNotes/"  # Directory containing PDFs
output_base_dir = "./output/"  # Base output directory

# Set up configuration with Gemini model
config = {
    "output_format": "markdown",
    "use_llm": True,
    "llm_service": "marker.services.gemini.GoogleGeminiService",
    "GoogleGeminiService_gemini_model_name": "gemini-2.5-flash-preview-04-17",
    "GoogleGeminiService_gemini_api_key": os.getenv("GEMINI_API_KEY"),
}

# Setup the converter
from marker.config.parser import ConfigParser
config_parser = ConfigParser(config)
converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    llm_service=config_parser.get_llm_service()
)

# Get all PDF files from the input directory
pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
print(f"Found {len(pdf_files)} PDF files to process")

# Process each PDF file one by one
for pdf_file in pdf_files:
    # Get base filename without extension
    base_filename = os.path.basename(pdf_file)
    filename_without_ext = os.path.splitext(base_filename)[0]
    
    # Create output directory for this specific PDF
    output_dir = os.path.join(output_base_dir, filename_without_ext)
    images_dir = output_dir
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    
    print(f"Processing: {base_filename}")
    
    try:
        # Convert the PDF
        rendered = converter(pdf_file)
        
        # Extract markdown content and images
        markdown_text, _, image_data_dict = text_from_rendered(rendered)
        
        # Save markdown content
        with open(os.path.join(output_dir, f"{filename_without_ext}.md"), "w", encoding="utf-8") as f:
            f.write(markdown_text)
        
        # Save images
        if isinstance(image_data_dict, dict) and image_data_dict:
            for img_filename, pil_image_object in image_data_dict.items():
                target_image_path = os.path.join(images_dir, img_filename)
                if isinstance(pil_image_object, Image.Image):
                    pil_image_object.save(target_image_path)
        
        # Save metadata to a text file
        metadata = rendered.metadata
        with open(os.path.join(output_dir, "metadata.txt"), "w", encoding="utf-8") as f:
            f.write(json.dumps(metadata, indent=2))
        
        print(f"Conversion complete for {base_filename}. Output saved to {output_dir}")
    
    except Exception as e:
        print(f"Error processing {base_filename}: {str(e)}")
        continue

print("All PDFs processed")
