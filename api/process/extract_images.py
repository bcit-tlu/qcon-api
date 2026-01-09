import re
import time
from ..models import Image

def extract_images(questionlibrary):
    start_time = time.time()
    try:
        x = re.findall(r"\<img\s+.*?\>", questionlibrary.pandoc_output)
        if len(x) == 0:
            return 0
        
        # Step 1: Create all Image objects in bulk with image data already set
        # This reduces from 3 saves per image to 1 bulk operation
        image_objects = [
            Image(question_library=questionlibrary, image=image)
            for image in x
        ]
        # Bulk create all images at once
        created_images = Image.objects.bulk_create(image_objects)
        
        # Step 2: Build replacement map in memory
        # Map original image HTML to placeholder (handle duplicates by using first occurrence)
        # Note: If same image appears multiple times, we create multiple Image objects
        # but replace each occurrence with its corresponding placeholder in order
        replacement_pairs = []
        for image_obj in created_images:
            # Use exact string replacement instead of regex for better performance on large strings
            placeholder = "<<<<" + str(image_obj.id) + ">>>>"
            replacement_pairs.append((image_obj.image, placeholder))
        
        # Step 3: Apply all replacements in memory, then save once
        # Use string.replace() instead of regex for much faster performance on large base64 strings
        updated_output = questionlibrary.pandoc_output
        for original_image, placeholder in replacement_pairs:
            # Replace only the first occurrence to match each image with its placeholder
            updated_output = updated_output.replace(original_image, placeholder, 1)
        
        # Save the updated pandoc_output only once
        questionlibrary.pandoc_output = updated_output
        questionlibrary.save(update_fields=['pandoc_output'])
        
        total_time = time.time() - start_time
        print(f"[extract_images] Processed {len(created_images)} images in {total_time:.3f}s")
        
        return len(created_images)
    except Exception as e:
        raise ImageExtractError(e)
class ImageExtractError(Exception):
    def __init__(self, reason, message=""):
        self.reason = reason
        self.message = message

    def __str__(self):
        return f'{self.message} -> {self.reason}'
