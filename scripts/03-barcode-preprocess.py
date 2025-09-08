#!/usr/bin/env python3
"""
Barcode Region Detection and Preprocessing Script

This script detects barcode regions in images and preprocesses them to improve readability.
It extracts potential barcode regions and applies various enhancement techniques.

Requirements:
    pip install opencv-python pyzbar pillow numpy scikit-image

Usage:
    python 03-barcode-preprocess.py --image /path/to/image.jpg --output /path/to/output/
    python 03-barcode-preprocess.py --folder /path/to/images/ --output /path/to/output/
"""

import os
import sys
import argparse
import logging
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from PIL import Image, ImageEnhance
from pyzbar import pyzbar
from pyzbar.pyzbar import ZBarSymbol

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_filename = logs_dir / f'barcode_preprocess_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class BarcodeRegionDetector:
    """Detect and extract barcode regions from images."""
    
    def __init__(self):
        """Initialize the barcode region detector."""
        self.min_area = 100  # Minimum area for barcode candidates
        self.max_area_ratio = 0.8  # Maximum area ratio to image size
        
    def detect_barcode_regions_morphology(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect potential barcode regions using morphological operations.
        
        Args:
            image: Input grayscale image
            
        Returns:
            List of bounding boxes (x, y, w, h) for potential barcode regions
        """
        regions = []
        
        try:
            # Apply gradient to highlight barcode patterns
            grad_x = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3)
            
            # Combine gradients
            gradient = cv2.subtract(grad_x, grad_y)
            gradient = cv2.convertScaleAbs(gradient)
            
            # Blur and threshold
            blurred = cv2.blur(gradient, (9, 9))
            _, thresh = cv2.threshold(blurred, 225, 255, cv2.THRESH_BINARY)
            
            # Morphological operations to close gaps in barcode lines
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
            closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Additional erosion and dilation
            closed = cv2.erode(closed, None, iterations=4)
            closed = cv2.dilate(closed, None, iterations=4)
            
            # Find contours
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            image_area = image.shape[0] * image.shape[1]
            
            for contour in contours:
                # Get bounding box
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # Filter by area and aspect ratio
                if (area > self.min_area and 
                    area < image_area * self.max_area_ratio and
                    w > h):  # Barcodes are typically wider than tall
                    
                    # Add some padding
                    padding = 10
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(image.shape[1] - x, w + 2 * padding)
                    h = min(image.shape[0] - y, h + 2 * padding)
                    
                    regions.append((x, y, w, h))
                    
        except Exception as e:
            logger.error(f"Error in morphological detection: {e}")
            
        return regions
    
    def detect_barcode_regions_lines(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect barcode regions using line detection (Hough transform).
        
        Args:
            image: Input grayscale image
            
        Returns:
            List of bounding boxes for potential barcode regions
        """
        regions = []
        
        try:
            # Edge detection
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            
            # Detect lines
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, 
                                  minLineLength=50, maxLineGap=10)
            
            if lines is not None:
                # Group nearby parallel lines
                line_groups = self._group_parallel_lines(lines, image.shape)
                
                for group in line_groups:
                    if len(group) >= 3:  # Need multiple parallel lines for barcode
                        x, y, w, h = self._get_bounding_box_from_lines(group)
                        
                        # Add padding
                        padding = 15
                        x = max(0, x - padding)
                        y = max(0, y - padding)
                        w = min(image.shape[1] - x, w + 2 * padding)
                        h = min(image.shape[0] - y, h + 2 * padding)
                        
                        if w > 30 and h > 10:  # Minimum size
                            regions.append((x, y, w, h))
                            
        except Exception as e:
            logger.error(f"Error in line detection: {e}")
            
        return regions
    
    def _group_parallel_lines(self, lines: np.ndarray, image_shape: Tuple[int, int]) -> List[List]:
        """Group parallel lines that might belong to the same barcode."""
        if lines is None:
            return []
            
        groups = []
        angle_threshold = 10  # degrees
        distance_threshold = 50  # pixels
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Calculate angle
            angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
            
            # Find matching group or create new one
            added_to_group = False
            for group in groups:
                if group:
                    gx1, gy1, gx2, gy2 = group[0][0]
                    group_angle = np.arctan2(gy2 - gy1, gx2 - gx1) * 180 / np.pi
                    
                    if abs(angle - group_angle) < angle_threshold:
                        # Check distance between lines
                        dist = self._line_distance((x1, y1, x2, y2), (gx1, gy1, gx2, gy2))
                        if dist < distance_threshold:
                            group.append(line)
                            added_to_group = True
                            break
            
            if not added_to_group:
                groups.append([line])
        
        return groups
    
    def _line_distance(self, line1: Tuple[int, int, int, int], 
                      line2: Tuple[int, int, int, int]) -> float:
        """Calculate distance between two lines."""
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        # Use midpoints for simplicity
        mid1 = ((x1 + x2) / 2, (y1 + y2) / 2)
        mid2 = ((x3 + x4) / 2, (y3 + y4) / 2)
        
        return np.sqrt((mid1[0] - mid2[0])**2 + (mid1[1] - mid2[1])**2)
    
    def _get_bounding_box_from_lines(self, lines: List) -> Tuple[int, int, int, int]:
        """Get bounding box from a group of lines."""
        all_points = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            all_points.extend([(x1, y1), (x2, y2)])
        
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    
    def detect_barcode_regions_gradient(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect barcode regions using gradient analysis.
        
        Args:
            image: Input grayscale image
            
        Returns:
            List of bounding boxes for potential barcode regions
        """
        regions = []
        
        try:
            # Calculate gradients
            grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude and direction
            magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Normalize and convert to uint8
            magnitude = np.uint8(255 * magnitude / np.max(magnitude))
            
            # Apply threshold
            _, thresh = cv2.threshold(magnitude, 30, 255, cv2.THRESH_BINARY)
            
            # Morphological operations
            kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 1))
            kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
            
            # Detect horizontal patterns (typical for barcodes)
            horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_h)
            horizontal = cv2.dilate(horizontal, kernel_h, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by size and aspect ratio
                if w > 50 and h > 10 and w > 2 * h:
                    padding = 10
                    x = max(0, x - padding)
                    y = max(0, y - padding)
                    w = min(image.shape[1] - x, w + 2 * padding)
                    h = min(image.shape[0] - y, h + 2 * padding)
                    
                    regions.append((x, y, w, h))
                    
        except Exception as e:
            logger.error(f"Error in gradient detection: {e}")
            
        return regions
    
    def combine_overlapping_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Combine overlapping or nearby regions."""
        if not regions:
            return []
            
        # Sort by x coordinate
        regions = sorted(regions, key=lambda r: r[0])
        combined = []
        
        for region in regions:
            x, y, w, h = region
            merged = False
            
            for i, (cx, cy, cw, ch) in enumerate(combined):
                # Check for overlap or proximity
                if (x < cx + cw + 20 and x + w > cx - 20 and
                    y < cy + ch + 20 and y + h > cy - 20):
                    
                    # Merge regions
                    new_x = min(x, cx)
                    new_y = min(y, cy)
                    new_w = max(x + w, cx + cw) - new_x
                    new_h = max(y + h, cy + ch) - new_y
                    
                    combined[i] = (new_x, new_y, new_w, new_h)
                    merged = True
                    break
            
            if not merged:
                combined.append(region)
        
        return combined

class BarcodePreprocessor:
    """Preprocess barcode images for better readability."""
    
    def __init__(self):
        """Initialize the barcode preprocessor."""
        self.detector = BarcodeRegionDetector()
        
    def enhance_image_quality(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Apply various enhancement techniques to improve barcode readability.
        
        Args:
            image: Input image
            
        Returns:
            List of enhanced images
        """
        enhanced_images = []
        
        # Original image
        enhanced_images.append(image.copy())
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        enhanced_images.append(gray)
        
        # 1. Histogram equalization
        equalized = cv2.equalizeHist(gray)
        enhanced_images.append(equalized)
        
        # 2. CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        clahe_enhanced = clahe.apply(gray)
        enhanced_images.append(clahe_enhanced)
        
        # 3. Gaussian blur + sharpening
        blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
        sharpened = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)
        enhanced_images.append(sharpened)
        
        # 4. Morphological opening (noise reduction)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
        enhanced_images.append(opened)
        
        # 5. Adaptive thresholding
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        enhanced_images.append(adaptive_thresh)
        
        # 6. Otsu thresholding
        _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        enhanced_images.append(otsu_thresh)
        
        # 7. Bilateral filter (edge preserving smoothing)
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        enhanced_images.append(bilateral)
        
        return enhanced_images
    
    def resize_for_optimal_detection(self, image: np.ndarray, target_width: int = 800) -> np.ndarray:
        """
        Resize image to optimal size for barcode detection.
        
        Args:
            image: Input image
            target_width: Target width for resizing
            
        Returns:
            Resized image
        """
        height, width = image.shape[:2]
        
        if width > target_width:
            # Calculate new height maintaining aspect ratio
            aspect_ratio = height / width
            new_height = int(target_width * aspect_ratio)
            
            # Resize image
            resized = cv2.resize(image, (target_width, new_height), interpolation=cv2.INTER_AREA)
            return resized
        
        return image
    
    def process_image(self, image_path: Path, output_dir: Path, 
                     save_regions: bool = True, save_enhanced: bool = True) -> Dict:
        """
        Process an image to detect and enhance barcode regions.
        
        Args:
            image_path: Path to input image
            output_dir: Directory to save processed images
            save_regions: Whether to save detected regions
            save_enhanced: Whether to save enhanced versions
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing image: {image_path}")
        
        try:
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                # Try with PIL for other formats
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if image is None:
                return {"success": False, "error": "Could not load image"}
            
            original_image = image.copy()
            
            # Resize if too large
            image = self.resize_for_optimal_detection(image)
            
            # Convert to grayscale for detection
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Detect barcode regions using multiple methods
            regions_morph = self.detector.detect_barcode_regions_morphology(gray)
            regions_lines = self.detector.detect_barcode_regions_lines(gray)
            regions_grad = self.detector.detect_barcode_regions_gradient(gray)
            
            # Combine all detected regions
            all_regions = regions_morph + regions_lines + regions_grad
            
            # Remove duplicates and overlaps
            unique_regions = self.detector.combine_overlapping_regions(all_regions)
            
            logger.info(f"Detected {len(unique_regions)} barcode region(s)")
            
            # Create output directory for this image
            image_output_dir = output_dir / image_path.stem
            image_output_dir.mkdir(parents=True, exist_ok=True)
            
            processed_regions = []
            
            # Process each detected region
            for i, (x, y, w, h) in enumerate(unique_regions):
                logger.info(f"Processing region {i+1}: ({x}, {y}, {w}, {h})")
                
                # Extract region
                region = gray[y:y+h, x:x+w]
                
                if region.size == 0:
                    continue
                
                # Enhance the region
                enhanced_regions = self.enhance_image_quality(region)
                
                # Test which enhancement works best for barcode detection
                best_enhancement = None
                best_score = 0
                
                for j, enhanced in enumerate(enhanced_regions):
                    # Try to detect barcode in this enhancement
                    try:
                        barcodes = pyzbar.decode(enhanced)
                        if barcodes:
                            score = len(barcodes) + 1  # Prefer versions with detected barcodes
                        else:
                            # Score based on image properties
                            score = self._score_image_quality(enhanced)
                        
                        if score > best_score:
                            best_score = score
                            best_enhancement = (j, enhanced.copy())
                            
                    except:
                        continue
                
                # Save the region and its enhancements
                region_info = {
                    "index": i + 1,
                    "bbox": (x, y, w, h),
                    "enhancements_saved": 0,
                    "best_enhancement": None
                }
                
                if save_regions:
                    # Save original region
                    region_path = image_output_dir / f"region_{i+1:02d}_original.png"
                    cv2.imwrite(str(region_path), region)
                    
                    # Save all enhanced versions if requested
                    if save_enhanced:
                        for j, enhanced in enumerate(enhanced_regions):
                            enhanced_path = image_output_dir / f"region_{i+1:02d}_enhanced_{j:02d}.png"
                            cv2.imwrite(str(enhanced_path), enhanced)
                            region_info["enhancements_saved"] += 1
                    
                    # Save best enhancement separately
                    if best_enhancement:
                        best_idx, best_img = best_enhancement
                        best_path = image_output_dir / f"region_{i+1:02d}_BEST.png"
                        cv2.imwrite(str(best_path), best_img)
                        region_info["best_enhancement"] = best_idx
                
                processed_regions.append(region_info)
            
            # Save annotated original image
            annotated = original_image.copy()
            for i, (x, y, w, h) in enumerate(unique_regions):
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(annotated, f"R{i+1}", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
            annotated_path = image_output_dir / f"{image_path.stem}_annotated.png"
            cv2.imwrite(str(annotated_path), annotated)
            
            return {
                "success": True,
                "image_path": str(image_path),
                "output_dir": str(image_output_dir),
                "regions_detected": len(unique_regions),
                "regions_processed": processed_regions
            }
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return {"success": False, "error": str(e)}
    
    def _score_image_quality(self, image: np.ndarray) -> float:
        """Score image quality based on contrast and sharpness."""
        try:
            # Calculate contrast (standard deviation)
            contrast = np.std(image)
            
            # Calculate sharpness (variance of Laplacian)
            laplacian = cv2.Laplacian(image, cv2.CV_64F)
            sharpness = laplacian.var()
            
            # Combine scores (you can adjust weights)
            score = contrast * 0.5 + sharpness * 0.5
            return score
            
        except:
            return 0.0

def main():
    """Main function to handle command line arguments and execute preprocessing."""
    parser = argparse.ArgumentParser(description="Preprocess images to extract and enhance barcode regions")
    parser.add_argument("--image", "-i", type=str,
                       help="Path to a single image file")
    parser.add_argument("--folder", "-f", type=str,
                       help="Path to folder containing images")
    parser.add_argument("--output", "-o", type=str, required=True,
                       help="Output directory for processed images")
    parser.add_argument("--extensions", type=str, nargs="+",
                       default=['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'],
                       help="Image file extensions to process")
    parser.add_argument("--no-regions", action="store_true",
                       help="Don't save individual region images")
    parser.add_argument("--no-enhanced", action="store_true",
                       help="Don't save all enhanced versions (only best)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.image and not args.folder:
        logger.error("Either --image or --folder must be specified")
        sys.exit(1)
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    preprocessor = BarcodePreprocessor()
    
    try:
        if args.image:
            # Process single image
            image_path = Path(args.image)
            if not image_path.exists():
                logger.error(f"Image file not found: {image_path}")
                sys.exit(1)
            
            result = preprocessor.process_image(
                image_path, output_dir,
                save_regions=not args.no_regions,
                save_enhanced=not args.no_enhanced
            )
            
            if result["success"]:
                logger.info(f"\n{'='*60}")
                logger.info(f"PREPROCESSING RESULTS FOR: {image_path.name}")
                logger.info(f"{'='*60}")
                logger.info(f"Regions detected: {result['regions_detected']}")
                logger.info(f"Output directory: {result['output_dir']}")
                
                for region in result["regions_processed"]:
                    logger.info(f"\nRegion {region['index']}:")
                    logger.info(f"  Location: {region['bbox']}")
                    logger.info(f"  Enhancements saved: {region['enhancements_saved']}")
                    if region['best_enhancement'] is not None:
                        logger.info(f"  Best enhancement: #{region['best_enhancement']}")
            else:
                logger.error(f"Failed to process image: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        elif args.folder:
            # Process folder of images
            folder_path = Path(args.folder)
            if not folder_path.exists():
                logger.error(f"Folder does not exist: {folder_path}")
                sys.exit(1)
            
            # Find image files
            file_extensions = [ext.lower() if ext.startswith('.') else f'.{ext}'.lower() 
                              for ext in args.extensions]
            
            image_files = []
            for ext in file_extensions:
                image_files.extend(folder_path.glob(f"*{ext}"))
                image_files.extend(folder_path.glob(f"*{ext.upper()}"))
            
            if not image_files:
                logger.error(f"No image files found in {folder_path}")
                sys.exit(1)
            
            logger.info(f"Found {len(image_files)} images to process")
            
            total_regions = 0
            successful = 0
            failed = 0
            
            for image_path in image_files:
                result = preprocessor.process_image(
                    image_path, output_dir,
                    save_regions=not args.no_regions,
                    save_enhanced=not args.no_enhanced
                )
                
                if result["success"]:
                    successful += 1
                    total_regions += result["regions_detected"]
                    logger.info(f"✓ {image_path.name}: {result['regions_detected']} regions")
                else:
                    failed += 1
                    logger.error(f"✗ {image_path.name}: {result.get('error', 'Unknown error')}")
            
            logger.info(f"\n{'='*60}")
            logger.info(f"BATCH PREPROCESSING SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"Images processed: {len(image_files)}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Total regions detected: {total_regions}")
            logger.info(f"Output directory: {output_dir}")
            
            if failed > 0:
                sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
