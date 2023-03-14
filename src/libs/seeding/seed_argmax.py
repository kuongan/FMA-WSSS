#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Xiaobo Yang
@Contact : hal_42@zju.edu.cn
@Time    : 2023/3/13 16:37
@File    : seed_thresh.py
@Software: PyCharm
@Desc    : 
"""
import numpy as np

from utils.norm import min_max_norm


def seed_argmax(cam: np.ndarray, fg_cls: np.ndarray, bg_method: dict) -> np.ndarray:
    cls_lb = np.pad(fg_cls + 1, (1, 0), mode='constant', constant_values=0)

    score = np.maximum(cam, 0)
    score = min_max_norm(score, dim=(1, 2))

    match bg_method:
        case {'method': 'thresh', 'thresh': thresh}:
            bg_score = np.full_like(score[0], thresh)[None, ...]
        case {'method': 'pow', 'pow': p}:
            bg_score = np.power(1 - np.max(score, axis=0, keepdims=True), p)
        case _:
            raise ValueError(f'Unknown bg_method: {bg_method}')

    score = np.concatenate((bg_score, score), axis=0)

    seed = np.argmax(score, axis=0)
    seed = cls_lb[seed].astype(np.uint8)

    return seed
