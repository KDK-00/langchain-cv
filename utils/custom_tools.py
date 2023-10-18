import sys
sys.path.append('Grounded-Segment-Anything')
sys.path.append('Grounded-Segment-Anything/EfficientSAM')

import os
import shutil
import streamlit as st
from pydantic import BaseModel, Field
from typing import Optional, Type, List
import numpy as np
import torch
from PIL import Image
import supervision as sv
from langchain.tools import BaseTool

from utils.inference import (
    # grounded_sam,
    instruct_pix2pix,
    sam,
    sd_inpaint,
    lama_cleaner,
    wurstchen,
    male_anime_generator,
    female_anime_generator
)
from utils.util import dilate_mask


def sam_inpaint(image, prompt, coordinates):
    image, mask = sam(image, coordinates)
    image = Image.fromarray(image)
    mask = Image.fromarray(mask)
    
    inpainted_image = sd_inpaint(image, mask, prompt)
    return inpainted_image

def image_transform(pil_image, prompt):
    if st.session_state["coord"] == False:  # 마스크가 없다면 이미지 전체 변환(pix2pix)
        transform_pillow = instruct_pix2pix(pil_image, prompt)[0]
    else: # 마스크가 있다면 특정 영역 inpaint
        mask = Image.fromarray(st.session_state["mask"])
        transform_pillow = sd_inpaint(pil_image, mask, prompt)
            
    
    return transform_pillow

def object_erase(image, mask, device):
    transform_pillow = lama_cleaner(image, mask, device)
    return transform_pillow


# class ZeroShotObjectDetectoonCheckInput(BaseModel):
#     """input_path check that is the input for zero-shot object detector."""
#     img_path: str = Field(..., description="image path for model input image")
#     class_list: List[str] = Field(..., description="List of situation the prompt is trying to find in image")

class ImageTransformCheckInput(BaseModel):
    prompt: str = Field(..., description="prompt for transform the image")


class ImageGenerationCheckInput(BaseModel):
    prompt: str = Field(..., description="prompt for generating image")
    num_images: int = Field(..., description="number of images to generate")

class MaleAnimeGenertorCheckInput(BaseModel):
    prompt: str = Field(..., description="prompt for generating image")
    num_images: int = Field(..., description="number of images to generate")
    
    
# class ZeroShotObjectDetectoonTool(BaseTool):  # TODO: 분류하고 detection 구분
#     name = "grounded_sam"             
#     description = "Please use this tool when you want to locate or determine the presence of a specific object."
#     return_direct=True
    
#     def _run(self, img_path: str, class_list: List[str]):
#         annotated_image = grounded_sam(img_path, class_list)
#         annotated_pillow = Image.fromarray(annotated_image)
#         st.session_state["ai_history"].append(annotated_pillow)
        
#         torch.cuda.empty_cache()
#         return annotated_pillow
    
#     def _arun(self, query: str):
#         raise NotImplementedError("This tool does not support async")

#     args_schema: Optional[Type[BaseModel]] = ZeroShotObjectDetectoonCheckInput


class ImageTransformTool(BaseTool):
    name = "image_transform"
    description = """
    Please use this tool when you want to change the image style or replace, add specific objects with something else.
    """
    return_direct=True
    
    def _run(self, prompt: str):
        pil_image = st.session_state["inference_image"][st.session_state["image_state"]]
        transform_pillow = image_transform(pil_image, prompt)
        return transform_pillow
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

    args_schema: Optional[Type[BaseModel]] = ImageTransformCheckInput


class ObjectEraseTool(BaseTool):  
    name = "object_erase"
    description = """
    Please use this tool when you want to clean, erase or delete certain objects from an image.
    """
    return_direct=True
    
    def _run(self, args=None):
        pil_image = st.session_state["inference_image"][st.session_state["image_state"]]
        np_image = np.array(pil_image)
        try:
            mask = st.session_state["mask"]
        except:
            st.exception(RuntimeError('There is no mask. Please masking the object in the drawing tool.'))
            return False

        if st.session_state["freedraw"] == False:
            mask = dilate_mask(mask, kernel_size=5, iterations=6)  # Extend masking to surrounding pixels of the object
            
        transform_pillow = object_erase(np_image, mask, "cuda")
        return transform_pillow
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")
    
    
class ImageGenerationTool(BaseTool):  
    name = "wurstchen"
    description = """
    Please use this tool when you want to generate images.
    """
    
    def _run(self, prompt: str, num_images: int, device: str = "cuda"):
        
        images = wurstchen(prompt, num_images, device) 
        
        for idx, image in enumerate(images):
            image.save(f"./frontend/public/images/{idx}.png")
        
        
        torch.cuda.empty_cache()
        return "complete!"
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

    args_schema: Optional[Type[BaseModel]] = ImageGenerationCheckInput


class MaleAnimeGenertorTool(BaseTool):  
    name = "male_anime_generator"
    description = """
    Please use this tool when you want to generate male,man,guy anime images.
    """
    return_direct=True
    
    def _run(self, prompt: str, num_images: int):
        shutil.rmtree("./frontend/public/images")
        os.makedirs("./frontend/public/images", exist_ok=True)
        images = male_anime_generator(prompt, num_images, device="cuda", use_controlnet=st.session_state["use_controlnet"]) 
        
        for idx, image in enumerate(images):
            image.save(f"./frontend/public/images/{idx}.png")
        
        torch.cuda.empty_cache()
        return "complete!"
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

    args_schema: Optional[Type[BaseModel]] = MaleAnimeGenertorCheckInput
    

class FemaleAnimeGenertorTool(BaseTool):  
    name = "female_anime_generator"
    description = """
    Please use this tool when you want to generate female,girl,woman anime images.
    """
    return_direct=True
    
    def _run(self, prompt: str, num_images: int):
        shutil.rmtree("./frontend/public/images")
        os.makedirs("./frontend/public/images", exist_ok=True)
        images = female_anime_generator(prompt, num_images, device="cuda", use_controlnet=st.session_state["use_controlnet"]) 
        
        for idx, image in enumerate(images):
            image.save(f"./frontend/public/images/{idx}.png")
        
        torch.cuda.empty_cache()
        return "complete!"
    
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

    args_schema: Optional[Type[BaseModel]] = MaleAnimeGenertorCheckInput
    