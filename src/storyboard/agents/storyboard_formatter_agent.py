import logging
import os
from typing import Dict, Any, List
from datetime import datetime
import json
from fpdf import FPDF
import base64
from PIL import Image
import io

logger = logging.getLogger(__name__)

class StoryboardFormatterAgent:
    """Agent responsible for formatting storyboard data for display and export."""
    
    def __init__(self):
        """Initialize the StoryboardFormatterAgent."""
        logger.info("Initializing StoryboardFormatterAgent")
        self.annotations = {}  # Store annotations by panel_id
    
    async def format_storyboard(
        self,
        scene_data: Dict[str, Any],
        prompts: List[Dict[str, Any]],
        image_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format storyboard data for display and export."""
        logger.info("Formatting storyboard data")
        
        formatted = {
            "title": scene_data.get("metadata", {}).get("title", "Untitled Script"),
            "timestamp": datetime.now().isoformat(),
            "scenes": [],
            "status": "success",
            "sequence_order": [],  # Track panel sequence
            "annotations": {}  # Store panel annotations
        }
        
        for image_result in image_results:
            scene_id = image_result.get("scene_id")
            prompt_data = next((p for p in prompts if p.get("scene_id") == scene_id), {})
            
            scene_entry = {
                "scene_id": scene_id,
                "scene_heading": prompt_data.get("scene_heading", ""),
                "description": prompt_data.get("scene_description", ""),
                "prompt": prompt_data.get("prompt", ""),
                "revised_prompt": image_result.get("revised_prompt"),
                "status": image_result.get("status", "error"),
                "image_path": None,
                "web_path": None,
                "image_url": None,
                "technical_params": prompt_data.get("technical_params", {}),
                "annotations": [],
                "sequence_number": len(formatted["scenes"]) + 1
            }
            
            if image_result.get("status") == "success":
                scene_entry.update({
                    "image_path": image_result.get("local_file_path"),
                    "web_path": image_result.get("web_path"),
                    "image_url": image_result.get("image_url"),
                    "image_data": image_result.get("image_data")
                })
            else:
                scene_entry["error"] = image_result.get("error", "Unknown error")
            
            formatted["scenes"].append(scene_entry)
            formatted["sequence_order"].append(scene_id)
        
        formatted["metadata"] = {
            "scene_count": len(formatted["scenes"]),
            "source_data": scene_data.get("metadata", {}),
            "generation_config": {
                "image_model": "dall-e-3",
                "quality": "standard",
                "style": "natural",
                "size": "1024x1024"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        successful_scenes = sum(1 for scene in formatted["scenes"] if scene.get("status") == "success")
        formatted["metadata"]["success_rate"] = f"{(successful_scenes / len(formatted['scenes'])) * 100:.1f}%"
        
        logger.info(f"Formatted storyboard with {len(formatted['scenes'])} scenes")
        return formatted

    async def export_pdf(self, storyboard_data: Dict[str, Any], output_path: str) -> str:
        """Export storyboard as PDF document."""
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Add title page
            pdf.add_page()
            pdf.set_font("Arial", "B", 24)
            pdf.cell(0, 20, storyboard_data["title"], ln=True, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Generated on: {storyboard_data['timestamp']}", ln=True, align="C")
            
            # Add scenes
            for scene in storyboard_data["scenes"]:
                pdf.add_page()
                
                # Scene header
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, f"Scene {scene['scene_id']}: {scene['scene_heading']}", ln=True)
                
                # Image
                if scene.get("image_path"):
                    try:
                        pdf.image(scene["image_path"], x=10, y=pdf.get_y()+5, w=190)
                    except Exception as e:
                        logger.error(f"Error adding image to PDF: {str(e)}")
                
                # Scene details
                pdf.set_y(pdf.get_y() + 140)  # Move below image
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 5, f"Description: {scene['description']}")
                pdf.multi_cell(0, 5, f"Technical Notes: {scene.get('technical_params', {})}")
                
                # Annotations
                if scene.get("annotations"):
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 10, "Annotations:", ln=True)
                    pdf.set_font("Arial", "", 10)
                    for annotation in scene["annotations"]:
                        pdf.multi_cell(0, 5, f"- {annotation['text']}")
            
            # Save PDF
            pdf.output(output_path)
            logger.info(f"Exported storyboard PDF to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting PDF: {str(e)}")
            raise

    async def export_slideshow(self, storyboard_data: Dict[str, Any], output_dir: str) -> str:
        """Export storyboard as HTML slideshow."""
        try:
            # Create slideshow directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate HTML content
            html_content = []
            html_content.append("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Storyboard Slideshow</title>
                <style>
                    .slide { display: none; padding: 20px; }
                    .slide.active { display: block; }
                    .navigation { text-align: center; padding: 10px; }
                    .scene-image { max-width: 100%; height: auto; }
                    .annotations { margin-top: 10px; }
                </style>
                <script>
                    let currentSlide = 0;
                    function showSlide(n) {
                        const slides = document.getElementsByClassName('slide');
                        currentSlide = (n + slides.length) % slides.length;
                        for (let i = 0; i < slides.length; i++) {
                            slides[i].classList.remove('active');
                        }
                        slides[currentSlide].classList.add('active');
                    }
                </script>
            </head>
            <body>
            """)
            
            # Add slides
            for scene in storyboard_data["scenes"]:
                html_content.append(f"""
                <div class="slide">
                    <h2>Scene {scene['scene_id']}: {scene['scene_heading']}</h2>
                    <img src="{scene['web_path']}" class="scene-image" alt="Scene {scene['scene_id']}">
                    <div class="scene-details">
                        <p><strong>Description:</strong> {scene['description']}</p>
                        <p><strong>Technical Notes:</strong> {scene.get('technical_params', {})}</p>
                    </div>
                    <div class="annotations">
                        <h3>Annotations:</h3>
                        <ul>
                """)
                
                for annotation in scene.get("annotations", []):
                    html_content.append(f"<li>{annotation['text']}</li>")
                
                html_content.append("""
                        </ul>
                    </div>
                </div>
                """)
            
            # Add navigation
            html_content.append("""
                <div class="navigation">
                    <button onclick="showSlide(currentSlide - 1)">Previous</button>
                    <button onclick="showSlide(currentSlide + 1)">Next</button>
                </div>
                <script>showSlide(0);</script>
            </body>
            </html>
            """)
            
            # Save HTML file
            output_path = os.path.join(output_dir, "slideshow.html")
            with open(output_path, "w") as f:
                f.write("\n".join(html_content))
            
            logger.info(f"Exported storyboard slideshow to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting slideshow: {str(e)}")
            raise

    async def add_annotation(self, storyboard_data: Dict[str, Any], scene_id: str, annotation: str) -> Dict[str, Any]:
        """Add an annotation to a specific scene."""
        try:
            for scene in storyboard_data["scenes"]:
                if scene["scene_id"] == scene_id:
                    if "annotations" not in scene:
                        scene["annotations"] = []
                    
                    annotation_entry = {
                        "id": len(scene["annotations"]) + 1,
                        "text": annotation,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    scene["annotations"].append(annotation_entry)
                    logger.info(f"Added annotation to scene {scene_id}")
                    return storyboard_data
            
            logger.warning(f"Scene {scene_id} not found")
            return storyboard_data
            
        except Exception as e:
            logger.error(f"Error adding annotation: {str(e)}")
            raise

    async def reorder_sequence(self, storyboard_data: Dict[str, Any], new_order: List[str]) -> Dict[str, Any]:
        """Reorder the sequence of scenes in the storyboard."""
        try:
            # Validate all scene IDs exist
            current_scenes = {scene["scene_id"] for scene in storyboard_data["scenes"]}
            if not all(scene_id in current_scenes for scene_id in new_order):
                raise ValueError("Invalid scene IDs in new order")
            
            # Create new scene list in specified order
            new_scenes = []
            for scene_id in new_order:
                scene = next(s for s in storyboard_data["scenes"] if s["scene_id"] == scene_id)
                scene["sequence_number"] = len(new_scenes) + 1
                new_scenes.append(scene)
            
            storyboard_data["scenes"] = new_scenes
            storyboard_data["sequence_order"] = new_order
            
            logger.info("Updated storyboard sequence order")
            return storyboard_data
            
        except Exception as e:
            logger.error(f"Error reordering sequence: {str(e)}")
            raise 