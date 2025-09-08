#!/usr/bin/env python3
"""
Barcode Detection and Reading Script

This script identifies and reads one or more barcodes from images.
Supports various barcode formats including QR codes, Code128, Code39, EAN13, UPC, PDF417, DataBar, etc.

Requirements:
    pip install opencv-python pyzbar pillow numpy

Usage:
    python 03-barcode-read-test.py --image /path/to/image.jpg
    python 03-barcode-read-test.py --folder /path/to/images/ --extensions jpg png tiff
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import cv2
import numpy as np
from PIL import Image
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_filename = logs_dir / f'barcode_read_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BarcodeReader:
    """Handle barcode detection and reading from images."""
    
    def __init__(self):
        """Initialize the barcode reader."""
        self.supported_formats = {
            ZBarSymbol.QRCODE: "QR Code",
            ZBarSymbol.CODE128: "Code 128",
            ZBarSymbol.CODE39: "Code 39",
            ZBarSymbol.CODE93: "Code 93",
            ZBarSymbol.EAN13: "EAN-13",
            ZBarSymbol.EAN8: "EAN-8",
            ZBarSymbol.UPCA: "UPC-A",
            ZBarSymbol.UPCE: "UPC-E",
            ZBarSymbol.I25: "Interleaved 2 of 5",
            ZBarSymbol.CODABAR: "Codabar",
            ZBarSymbol.PDF417: "PDF417",
            ZBarSymbol.DATABAR: "DataBar",
            ZBarSymbol.DATABAR_EXP: "DataBar Expanded"
        }
        
    def preprocess_image(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Preprocess image to improve barcode detection.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of processed images to try for barcode detection
        """
        processed_images = []
        
        # Original image
        processed_images.append(image)
        
        # Convert to grayscale if color
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            processed_images.append(gray)
        else:
            gray = image
            
        # Apply different preprocessing techniques
        
        # 1. Gaussian blur + threshold
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed_images.append(thresh1)
        
        # 2. Adaptive threshold
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        processed_images.append(adaptive_thresh)
        
        # 3. Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        processed_images.append(morph)
        
        # 4. Histogram equalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        equalized = clahe.apply(gray)
        processed_images.append(equalized)
        
        return processed_images
    
    def detect_barcodes_opencv(self, image: np.ndarray) -> List[Dict]:
        """
        Detect barcodes using OpenCV's built-in detector.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of detected barcode information
        """
        barcodes = []
        
        try:
            # Try QR code detection with OpenCV
            qr_detector = cv2.QRCodeDetector()
            data, bbox, _ = qr_detector.detectAndDecode(image)
            
            if data and bbox is not None:
                # Convert bbox to integer coordinates
                bbox = bbox.astype(int)
                x, y, w, h = cv2.boundingRect(bbox)
                
                barcodes.append({
                    'type': 'QR Code (OpenCV)',
                    'data': data,
                    'bbox': (x, y, w, h),
                    'confidence': 1.0
                })
                logger.info(f"OpenCV QR Code detected: {data}")
                
        except Exception as e:
            logger.debug(f"OpenCV detection failed: {e}")
            
        return barcodes
    
    def detect_barcodes_pyzbar(self, image: np.ndarray) -> List[Dict]:
        """
        Detect barcodes using pyzbar library.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of detected barcode information
        """
        barcodes = []
        
        try:
            # Detect barcodes
            detected_barcodes = pyzbar.decode(image)
            
            for barcode in detected_barcodes:
                # Extract barcode data
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = self.supported_formats.get(barcode.type, str(barcode.type))
                
                # Get bounding box
                x, y, w, h = barcode.rect
                
                barcodes.append({
                    'type': barcode_type,
                    'data': barcode_data,
                    'bbox': (x, y, w, h),
                    'confidence': 1.0,  # pyzbar doesn't provide confidence
                    'polygon': barcode.polygon
                })
                
                logger.info(f"Pyzbar {barcode_type} detected: {barcode_data}")
                
        except Exception as e:
            logger.debug(f"Pyzbar detection failed: {e}")
            
        return barcodes
    
    def read_barcodes_from_image(self, image_path: Path, 
                                save_annotated: bool = False) -> Dict:
        """
        Read all barcodes from an image file.
        
        Args:
            image_path: Path to the image file
            save_annotated: Whether to save an annotated version of the image
            
        Returns:
            Dictionary containing detection results
        """
        logger.info(f"Processing image: {image_path}")
        
        if not image_path.exists():
            logger.error(f"Image file not found: {image_path}")
            return {"success": False, "error": "File not found", "barcodes": []}
        
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                # Try with PIL for other formats
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return {"success": False, "error": "Could not load image", "barcodes": []}
            
            original_image = image.copy()
            all_barcodes = []
            
            # Get preprocessed versions of the image
            processed_images = self.preprocess_image(image)
            
            # Try detection on each processed image
            for i, proc_img in enumerate(processed_images):
                logger.debug(f"Trying detection on processed image {i+1}/{len(processed_images)}")
                
                # Try OpenCV detection
                opencv_barcodes = self.detect_barcodes_opencv(proc_img)
                for barcode in opencv_barcodes:
                    barcode['preprocessing'] = f'Method {i+1}'
                    if barcode not in all_barcodes:  # Avoid duplicates
                        all_barcodes.append(barcode)
                
                # Try pyzbar detection
                pyzbar_barcodes = self.detect_barcodes_pyzbar(proc_img)
                for barcode in pyzbar_barcodes:
                    barcode['preprocessing'] = f'Method {i+1}'
                    # Check for duplicates based on data and position
                    is_duplicate = False
                    for existing in all_barcodes:
                        if (existing['data'] == barcode['data'] and 
                            abs(existing['bbox'][0] - barcode['bbox'][0]) < 10 and
                            abs(existing['bbox'][1] - barcode['bbox'][1]) < 10):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        all_barcodes.append(barcode)
            
            # Remove duplicates and sort by position
            unique_barcodes = []
            for barcode in all_barcodes:
                is_duplicate = False
                for existing in unique_barcodes:
                    if (existing['data'] == barcode['data'] and 
                        abs(existing['bbox'][0] - barcode['bbox'][0]) < 20 and
                        abs(existing['bbox'][1] - barcode['bbox'][1]) < 20):
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_barcodes.append(barcode)
            
            # Sort by position (top to bottom, left to right)
            unique_barcodes.sort(key=lambda b: (b['bbox'][1], b['bbox'][0]))
            
            # Save annotated image if requested
            if save_annotated and unique_barcodes:
                self.save_annotated_image(original_image, unique_barcodes, image_path)
            
            logger.info(f"Found {len(unique_barcodes)} unique barcode(s) in {image_path}")
            
            return {
                "success": True,
                "image_path": str(image_path),
                "barcodes": unique_barcodes,
                "total_found": len(unique_barcodes)
            }
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return {"success": False, "error": str(e), "barcodes": []}
    
    def save_annotated_image(self, image: np.ndarray, barcodes: List[Dict], 
                           original_path: Path):
        """
        Save an annotated version of the image with barcode locations marked.
        
        Args:
            image: Original image
            barcodes: List of detected barcodes
            original_path: Path to original image
        """
        try:
            annotated = image.copy()
            
            for i, barcode in enumerate(barcodes):
                x, y, w, h = barcode['bbox']
                
                # Draw bounding box
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Add label
                label = f"{i+1}: {barcode['type']}"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                cv2.rectangle(annotated, (x, y - label_size[1] - 10), 
                             (x + label_size[0], y), (0, 255, 0), -1)
                cv2.putText(annotated, label, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Save annotated image
            output_path = original_path.parent / f"{original_path.stem}_annotated{original_path.suffix}"
            cv2.imwrite(str(output_path), annotated)
            logger.info(f"Saved annotated image: {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving annotated image: {e}")

def process_single_image(image_path: Path, save_annotated: bool = False) -> Dict:
    """Process a single image file."""
    reader = BarcodeReader()
    return reader.read_barcodes_from_image(image_path, save_annotated)

def process_image_folder(folder_path: Path, file_extensions: Optional[List[str]] = None,
                        save_annotated: bool = False) -> Dict:
    """Process all images in a folder."""
    if file_extensions is None:
        file_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    # Normalize extensions
    file_extensions = [ext.lower() if ext.startswith('.') else f'.{ext}'.lower() 
                      for ext in file_extensions]
    
    reader = BarcodeReader()
    results = {"total_images": 0, "successful": 0, "failed": 0, "results": []}
    
    # Find all image files
    image_files = []
    for ext in file_extensions:
        image_files.extend(folder_path.glob(f"*{ext}"))
        image_files.extend(folder_path.glob(f"*{ext.upper()}"))
    
    results["total_images"] = len(image_files)
    logger.info(f"Found {len(image_files)} image files to process")
    
    for image_path in image_files:
        result = reader.read_barcodes_from_image(image_path, save_annotated)
        results["results"].append(result)
        
        if result["success"]:
            results["successful"] += 1
        else:
            results["failed"] += 1
    
    return results

def main():
    """Main function to handle command line arguments and execute barcode reading."""
    parser = argparse.ArgumentParser(description="Detect and read barcodes from images")
    parser.add_argument("--image", "-i", type=str,
                       help="Path to a single image file")
    parser.add_argument("--folder", "-f", type=str,
                       help="Path to folder containing images")
    parser.add_argument("--extensions", type=str, nargs="+",
                       default=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'],
                       help="Image file extensions to process (default: jpg jpeg png bmp tiff tif)")
    parser.add_argument("--save-annotated", action="store_true",
                       help="Save annotated images with barcode locations marked")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.image and not args.folder:
        logger.error("Either --image or --folder must be specified")
        sys.exit(1)
    
    try:
        if args.image:
            # Process single image
            image_path = Path(args.image)
            result = process_single_image(image_path, args.save_annotated)
            
            if result["success"]:
                logger.info(f"\n{'='*60}")
                logger.info(f"BARCODE DETECTION RESULTS FOR: {image_path.name}")
                logger.info(f"{'='*60}")
                
                if result["barcodes"]:
                    for i, barcode in enumerate(result["barcodes"], 1):
                        logger.info(f"\nBarcode {i}:")
                        logger.info(f"  Type: {barcode['type']}")
                        logger.info(f"  Data: {barcode['data']}")
                        logger.info(f"  Position: ({barcode['bbox'][0]}, {barcode['bbox'][1]})")
                        logger.info(f"  Size: {barcode['bbox'][2]} x {barcode['bbox'][3]} pixels")
                else:
                    logger.info("No barcodes detected in the image")
                    
            else:
                logger.error(f"Failed to process image: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        elif args.folder:
            # Process folder of images
            folder_path = Path(args.folder)
            if not folder_path.exists():
                logger.error(f"Folder does not exist: {folder_path}")
                sys.exit(1)
            
            results = process_image_folder(folder_path, args.extensions, args.save_annotated)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH PROCESSING RESULTS")
            logger.info(f"{'='*60}")
            logger.info(f"Total images processed: {results['total_images']}")
            logger.info(f"Successful: {results['successful']}")
            logger.info(f"Failed: {results['failed']}")
            
            total_barcodes = 0
            for result in results["results"]:
                if result["success"]:
                    total_barcodes += result["total_found"]
                    if result["total_found"] > 0:
                        logger.info(f"\n{Path(result['image_path']).name}: {result['total_found']} barcode(s)")
                        for i, barcode in enumerate(result["barcodes"], 1):
                            logger.info(f"  {i}. {barcode['type']}: {barcode['data']}")
            
            logger.info(f"\nTotal barcodes found: {total_barcodes}")
            
            if results['failed'] > 0:
                sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
