import os
from typing import List
import cv2
import numpy as np

from .text_mask_utils import complete_mask_fill, complete_mask
from ..utils import TextBlock, Quadrilateral
from ..utils.bubble import is_ignore

async def dispatch(text_regions: List[TextBlock], raw_image: np.ndarray, raw_mask: np.ndarray, method: str = 'fit_text', verbose: bool = False, ignore_bubble: int = 0) -> np.ndarray:
    img_resized = cv2.resize(raw_image, (raw_image.shape[1] // 2, raw_image.shape[0] // 2), interpolation = cv2.INTER_LINEAR)
    mask_resized = cv2.resize(raw_mask, (raw_image.shape[1] // 2, raw_image.shape[0] // 2), interpolation = cv2.INTER_LINEAR)

    mask_resized[mask_resized > 0] = 255
    bboxes_resized = []
    for region in text_regions:
        for l in region.lines:
            a = Quadrilateral(l, '', 0)
            bboxes_resized.append((a.aabb.x // 2, a.aabb.y // 2, a.aabb.w // 2, a.aabb.h // 2))

    final_mask = complete_mask(img_resized, mask_resized, bboxes_resized) if method == 'fit_text' else complete_mask_fill(bboxes_resized)
    if final_mask is None:
        final_mask = np.zeros((raw_image.shape[0], raw_image.shape[1]), dtype = np.uint8)
    else:
        final_mask = cv2.resize(final_mask, (raw_image.shape[1], raw_image.shape[0]), interpolation = cv2.INTER_LINEAR)
        final_mask[final_mask > 0] = 255

    # cv2.imwrite(f'result/{task_id}/mask.png', final_mask)
    # cv2.imwrite(f'result/{task_id}/mask_img.png', overlay_mask(img_resized_2, final_mask))

    if ignore_bubble < 1 or ignore_bubble > 50:
        return final_mask

    # bubble
    kernel_size = int(max(final_mask.shape) * 0.025)  # 选择一个合适的核大小
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    final_mask = cv2.dilate(final_mask, kernel, iterations=1)  # 根据需要调整迭代次数
    # border
    contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        temp_mask = np.zeros_like(final_mask)
        # rect min
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(temp_mask, (x, y), (x + w, y + h), 255, -1)
        # get textblock
        textblock=cv2.bitwise_and(raw_image, raw_image, mask=temp_mask)
        if is_ignore(textblock, ignore_bubble):
            cv2.drawContours(final_mask, [cnt], -1, 0, -1)

    return final_mask
