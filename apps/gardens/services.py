"""
Services for garden projects including photo quality analysis.
"""

import cv2
import numpy as np


class PhotoQualityChecker:
    """Check photo quality metrics including brightness, blur, color space."""

    # Quality threshold constants
    MIN_BRIGHTNESS = 50  # Laplacian variance threshold for blur detection
    MIN_QUALITY_SCORE = 60  # Minimum acceptable quality score (0-100)

    @staticmethod
    def check_photo_quality(image_file):
        """
        Analyze photo quality and return metrics.

        Args:
            image_file: Django UploadedFile object

        Returns:
            dict: {
                'quality_score': int (0-100),
                'is_acceptable': bool,
                'brightness_level': str,
                'is_blurry': bool,
                'issues': list of dicts with code, label, description
            }
        """
        issues = []
        quality_score = 100

        try:
            # Read image from uploaded file
            image_file.seek(0)
            image_data = image_file.read()
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return {
                    "quality_score": 0,
                    "is_acceptable": False,
                    "brightness_level": "unknown",
                    "is_blurry": False,
                    "issues": [
                        {
                            "code": "INVALID_IMAGE",
                            "label": "Invalid Image Format",
                            "description": "The uploaded file could not be processed. Please try a different image.",
                        }
                    ],
                }

            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 1. Check brightness (underexposure)
            brightness_score = int(np.mean(gray))
            if brightness_score < 50:
                quality_score -= 40
                issues.append(
                    {
                        "code": "LOW_LIGHTING",
                        "label": "Lighting Too Dark",
                        "description": "Your photo appears underexposed. Try taking it in brighter conditions.",
                    }
                )
            elif brightness_score > 220:
                quality_score -= 20
                issues.append(
                    {
                        "code": "OVEREXPOSED",
                        "label": "Photo is Too Bright",
                        "description": "Your photo appears overexposed. Try moving to a shadier spot or reduce exposure.",
                    }
                )

            # 2. Check blur using Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < PhotoQualityChecker.MIN_BRIGHTNESS:
                quality_score -= 30
                issues.append(
                    {
                        "code": "BLURRY",
                        "label": "Photo is Blurry",
                        "description": "The image is not in focus. Please hold your phone steady.",
                    }
                )

            # 3. Check contrast
            contrast = gray.std()
            if contrast < 20:
                quality_score -= 15
                issues.append(
                    {
                        "code": "LOW_CONTRAST",
                        "label": "Low Contrast",
                        "description": "The image has low contrast. Try to improve lighting or composition.",
                    }
                )

            # Clamp quality score between 0 and 100
            quality_score = max(0, min(100, quality_score))

            # Determine brightness level
            if brightness_score < 80:
                brightness_level = "dark"
            elif brightness_score < 150:
                brightness_level = "medium"
            else:
                brightness_level = "bright"

            is_acceptable = quality_score >= PhotoQualityChecker.MIN_QUALITY_SCORE

            return {
                "quality_score": quality_score,
                "is_acceptable": is_acceptable,
                "brightness_level": brightness_level,
                "is_blurry": laplacian_var < PhotoQualityChecker.MIN_BRIGHTNESS,
                "issues": issues,
            }

        except Exception as e:
            return {
                "quality_score": 0,
                "is_acceptable": False,
                "brightness_level": "unknown",
                "is_blurry": False,
                "issues": [
                    {
                        "code": "PROCESSING_ERROR",
                        "label": "Processing Error",
                        "description": f"An error occurred while analyzing the photo: {str(e)}",
                    }
                ],
            }
