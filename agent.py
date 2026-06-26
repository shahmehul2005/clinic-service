import os
import json
import base64
import re
from typing import List, Dict
from datetime import datetime
import uuid
import time
import requests

from google import genai
from google.genai import types
from google.adk.agents import Agent
from dotenv import load_dotenv

# Load env variables (e.g. GEMINI_API_KEY)
load_dotenv()

# Initialize Google GenAI client
client = genai.Client()

def generate_craft_images(image_input: str) -> Dict[str, List[str]]:
    """
    Complete workflow for analyzing a traditional craft image and generating 4 modern interpretations.
    
    Args:
        image_input (str): Base64 encoded image data, URL, or local file path to an image of the craft.
        
    Returns:
        dict: Dictionary containing 4 generated image paths (2 traditional variations + 2 modern implementations)
    """
    try:
        # Prepare the input image as a Part
        image_part = None
        if image_input.startswith("data:image"):
            header_match = re.match(r"^data:image\/[a-zA-Z]+;base64,", image_input)
            if header_match:
                base64_data = image_input[header_match.end():]
            else:
                base64_data = image_input
            image_bytes = base64.b64decode(base64_data)
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        elif image_input.startswith("http://") or image_input.startswith("https://"):
            res = requests.get(image_input, timeout=15)
            if res.status_code == 200:
                image_part = types.Part.from_bytes(data=res.content, mime_type="image/jpeg")
        elif os.path.exists(image_input) and os.path.isfile(image_input):
            with open(image_input, "rb") as f:
                image_bytes = f.read()
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        
        # Fallback to try decoding directly as raw base64 if it has no header
        if not image_part:
            try:
                image_bytes = base64.b64decode(image_input)
                image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            except Exception:
                raise ValueError("image_input must be a base64 string, URL, or valid local file path")

        # Step 1: Analyze the input image
        image_prompt = """
        Analyze this craft image and extract the following visual elements in JSON format:
        - craft_name: Name/type of the craft
        - color_palette: List of 5-7 dominant colors with hex codes and descriptions
        - motifs: Recurring patterns, symbols, or motifs
        - techniques: Inferred techniques based on visual evidence
        - materials: Primary materials used
        - design_structure: Overall design and form
        - style: Artistic style description
        - cultural_context: Cultural or religious significance if any
        - location: Geographic or cultural origin if identifiable
        """
        
        image_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image_prompt, image_part]
        )
        image_analysis = image_response.text

        # Step 2: Research techniques and materials
        research_prompt = f"""
        Based on the following craft analysis, research the specific techniques and materials mentioned with focus on ARTISAN FEASIBILITY:
        
        Image Analysis: {image_analysis}
        
        Provide detailed information about:
        1. Each technique mentioned - how it's traditionally performed by artisans, tools required, step-by-step process, and skill level needed
        2. Each material mentioned - its properties, traditional preparation methods, availability to artisans, and why it's used
        3. Cultural significance of these techniques and materials
        4. Any regional variations in how these techniques are applied
        5. PRACTICAL CONSTRAINTS: What makes these techniques achievable by traditional artisans (time, skill, tools, materials)
        6. ARTISAN WORKFLOW: The complete process from material preparation to final product that an artisan would follow
        
        CRITICAL: Focus on techniques and materials that are accessible and feasible for traditional artisans to work with.
        Format your response as a detailed JSON object with sections for techniques, materials, and artisan_constraints.
        """
        
        research_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=research_prompt
        )
        technique_material_research = research_response.text
        
        # Step 3: Generate 2 traditional innovative ideas
        traditional_ideas_prompt = f"""
        As a creative director, suggest 2 traditional variations for this craft that maintain the EXACT SAME STYLE as the original.
        CRITICAL CONSTRAINTS: 
        1. You MUST preserve the traditional techniques and materials exactly as they are
        2. Each idea MUST be achievable by traditional artisans using the same techniques and materials
        3. MAINTAIN THE SAME STYLE: Keep the overall form, structure, and artistic style identical to the original
        4. ONLY VARY: Colors, color combinations, or minor design patterns within the same style framework
        5. If there are religious deities involved, keep them respectful and decent
        
        Image Analysis: {image_analysis}
        Technique and Material Research: {technique_material_research}
        
        Generate 2 traditional variations that maintain the original style:
        1. Traditional Variation 1: [Same style as original, different color palette - describe specific color changes]
        2. Traditional Variation 2: [Same style as original, different color scheme - describe specific color changes]
        
        Each variation should:
        - Maintain the EXACT same artistic style, form, and structure as the original
        - Only change colors, color combinations, or minor pattern variations
        - Use the exact same traditional techniques and materials
        - Be achievable by artisans with their existing skills and tools
        - Preserve the cultural authenticity and visual identity of the original craft
        """
        
        traditional_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=traditional_ideas_prompt
        )
        traditional_ideas = traditional_response.text
        
        # Step 4: Generate 2 modern implementation ideas
        modern_ideas_prompt = f"""
        As a creative director, suggest 2 modern implementations of this traditional craft, keep some part of design same just applications different.
        CRITICAL CONSTRAINTS:
        1. These MUST be achievable by traditional artisans using their existing techniques and materials
        2. Blend traditional techniques with contemporary applications while preserving the craft's essence
        3. Focus on modern contexts where artisans can apply their traditional skills
        4. Ensure each idea is within the practical capabilities of traditional artisans
        
        Image Analysis: {image_analysis}
        Technique and Material Research: {technique_material_research}
        Traditional Ideas: {traditional_ideas}
        
        Generate 2 distinct modern implementation concepts that artisans can actually create:
        1. Modern Implementation 1: [description of modern application using traditional artisan techniques/materials]
        2. Modern Implementation 2: [description of modern application using traditional artisan techniques/materials]
        
        Each concept should:
        - Show how traditional craft techniques can be applied in modern contexts
        - Be achievable by artisans using their traditional skills and materials
        - Maintain the cultural essence while appealing to contemporary markets
        - Require no additional training or tools beyond what artisans already possess
        """
        
        modern_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=modern_ideas_prompt
        )
        modern_ideas = modern_response.text
        
        # Step 5: Generate image prompts for all 4 concepts
        prompts_prompt = f"""
        Create 4 detailed prompts for image generation based on these concepts:
        
        Image Analysis: {image_analysis}
        Technique and Material Research: {technique_material_research}
        Traditional Ideas: {traditional_ideas}
        Modern Ideas: {modern_ideas}
        
        Generate 4 prompts in this exact format:
        TRADITIONAL_1: [detailed prompt for traditional variation 1 - SAME STYLE as original, different colors only]
        TRADITIONAL_2: [detailed prompt for traditional variation 2 - SAME STYLE as original, different colors only]
        MODERN_1: [detailed prompt for modern implementation 1]
        MODERN_2: [detailed prompt for modern implementation 2]
        
        For TRADITIONAL prompts, emphasize:
        - IDENTICAL STYLE: Same artistic style, form, structure, and composition as the original
        - ONLY COLOR VARIATIONS: Different color palette, color scheme, or color combinations
        - Same traditional techniques and materials
        - Same cultural context and design elements
        
        For MODERN prompts, emphasize:
        - Preservation of traditional techniques and materials
        - Focus on making canvas changes for example: if materials are fabrics then you can change the craft applications preserving the design to pillow covers, fashion design, cloth bags, etc.
        if materials are brass or other metals, use them in other house decors preserving the design of craft, just changing the applications.
        if paintings are thehandicrafts, suggest a mix of traditional and contemporary design for craft.
        - High quality: "photorealistic", "4k", "detailed", "professional photography"
        - PRACTICAL FEASIBILITY: Show items that artisans can realistically create with their skills
        """
        
        prompts_response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompts_prompt
        )
        all_prompts = prompts_response.text
        
        # Parse prompts
        prompt_lines = all_prompts.split('\n')
        prompts_dict = {}
        current_key = None
        current_prompt = []
        
        for line in prompt_lines:
            if line.startswith('TRADITIONAL_') or line.startswith('MODERN_'):
                if current_key:
                    prompts_dict[current_key] = ' '.join(current_prompt)
                current_key = line.split(':')[0].strip()
                current_prompt = [line.split(':', 1)[1].strip()] if ':' in line else []
            elif current_key and line.strip():
                current_prompt.append(line.strip())
        
        if current_key:
            prompts_dict[current_key] = ' '.join(current_prompt)
        
        # Function to generate image with fallback
        def generate_image_with_fallback(prompt, key, max_retries=2):
            models_to_try = [
                ("imagen-3.0-generate-002", 0)
            ]
            
            for model_name, retry_count in models_to_try:
                try:
                    print(f"Attempting to generate {key} with {model_name}")
                    imagen_response = client.models.generate_images(
                        model=model_name,
                        prompt=prompt,
                        config=types.GenerateImagesConfig(
                            number_of_images=1,
                            output_mime_type="image/png"
                        )
                    )
                    
                    # Get the image as bytes
                    image_bytes = imagen_response.generated_images[0].image.image_bytes
                    
                    # Encode directly to base64 Data URI (eliminating GCS dependencies)
                    encoded = base64.b64encode(image_bytes).decode('utf-8')
                    output_path = f"data:image/png;base64,{encoded}"
                    
                    print(f"Successfully generated {key} with {model_name}")
                    return output_path
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"Error generating {key} with {model_name}: {error_msg}")
                    
                    # Check if it's a rate limit error
                    if "quota" in error_msg.lower() or "limit" in error_msg.lower() or "rate" in error_msg.lower():
                        print(f"Rate limit detected with {model_name}, trying next model...")
                        continue
                    
                    # For other errors, wait and retry
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count  # Exponential backoff
                        print(f"Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"All retries exhausted for {model_name}")
                        continue
            
            # If all models fail
            print(f"All image generation attempts failed for {key}")
            return None
        
        # Generate images
        generated_images = {}
        for key, prompt in prompts_dict.items():
            try:
                output_path = generate_image_with_fallback(prompt, key)
                generated_images[key] = output_path
            except Exception as e:
                print(f"Unexpected error generating image for {key}: {str(e)}")
                generated_images[key] = None
        
        return {
            "status": "success",
            "storage_mode": "local_base64",
            "image_analysis": image_analysis,
            "technique_material_research": technique_material_research,
            "traditional_ideas": traditional_ideas,
            "modern_ideas": modern_ideas,
            "generated_images": generated_images,
            "traditional_images": [generated_images.get("TRADITIONAL_1"), generated_images.get("TRADITIONAL_2")],
            "modern_images": [generated_images.get("MODERN_1"), generated_images.get("MODERN_2")]
        }
        
    except Exception as e:
        return {"status": "error", "error_message": f"Process failed: {str(e)}"}

# Create the agent optimized for standard Google AI Studio Gemini API
root_agent = Agent(
    name="muse_agent",
    model="gemini-2.0-flash",  # Using standard Gemini 2.0 Flash
    description="An AI agent that analyzes traditional craft images and generates 4 artisan-feasible interpretations (2 traditional + 2 modern) for Kalpana AI project, ensuring all ideas can be made by traditional artisans using their existing techniques and materials.",
    instruction="""
    You are a specialized craft analysis and generation agent for Kalpana AI.
    When provided with a craft image, analyze it and generate 4 images:
    - 2 traditional variations that maintain the EXACT SAME STYLE as the original, only changing colors or design patterns
    - 2 modern implementations blending traditional craft with contemporary applications
    
    CRITICAL FOCUS: All generated ideas MUST be achievable by traditional artisans using their existing techniques and materials. The traditional variations must preserve the original style while only varying colors or minor patterns. The agent ensures that every concept can be practically made by artisans without requiring additional training, tools, or materials beyond what they already possess.
    
    The function takes one parameter: image_input (base64 encoded image, URL, or local file path).
    Returns a structured response with 4 generated image paths and analysis data.
    """,
    tools=[generate_craft_images]
)