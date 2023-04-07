#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Xiaobo Yang
@Contact : hal_42@zju.edu.cn
@Time    : 2023/3/5 14:14
@File    : voc_auger.py
@Software: PyCharm
@Desc    : 
"""
from typing import Any, Callable

from math import ceil

from PIL import Image
import numpy as np
from addict import Dict

from torchvision.transforms import ToTensor, Normalize, ToPILImage

from alchemy_cat.acplot import BGR2RGB
from alchemy_cat.alg import size2HW
from alchemy_cat.py_tools import PackCompose, Compose
from alchemy_cat.data import Dataset
import alchemy_cat.data.plugins.augers as au
from alchemy_cat.contrib.voc import lb2cls_lb

kPILMode = Image.BICUBIC  # 适配CLIP。

__all__ = ['VOC2Auger']


class VOC2Auger(Dataset):

    def __init__(self, dataset: Dataset,
                 is_color_jitter: bool=True,
                 scale_crop_method: Any=None,
                 is_rand_mirror: bool=True,
                 mean: tuple[float, float, float]=(0.48145466, 0.4578275, 0.40821073),
                 std: tuple[float, float, float]=(0.26862954, 0.26130258, 0.27577711),
                 lb_scale_factor: float | None=None, ol_cls_lb: bool=True):
        self.dataset = dataset

        self.is_color_jitter = is_color_jitter
        self.scale_crop_method = scale_crop_method
        self.is_rand_mirror = is_rand_mirror
        self.mean = mean
        self.std = std
        self.lb_scale_factor = lb_scale_factor
        self.ol_cls_lb = ol_cls_lb

        self.rand_color_jitter = au.RandColorJitter()  # VOC参数。

        self.scale_crop: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]
        match scale_crop_method:
            case {'method': 'rand_range',
                  'low_size': low_size, 'high_size': high_size, 'short_thresh': short_thresh,
                  'crop_size': crop_size}:
                assert short_thresh >= crop_size
                self.scale_crop = PackCompose([
                    au.RandRangeScale(low_size, high_size, short_thresh, align_corner=False, PIL_mode=kPILMode),
                    au.RandCrop(crop_size)  # if crop_size is not None else au.pack_identical  # 可以不做crop。
                ])
            case {'method': 'no_scale'} | None:
                self.scale_crop = au.pack_identical
            case (int() | (int(), int())) as size:
                h, w = size2HW(size)
                self.scale_crop = lambda img, lb: au.scale_img_label((h, w), img, lb,
                                                                     align_corner=False, PIL_mode=kPILMode)
            case {'method': 'rand_resize_crop', }:
                # TODO 让该模式支持img-label对的增强。
                # 好处：1）面积比例较高时，基本能不丢物体。2）能控制ratio范围。劣势：scale、ratio变化范围有限。
                pass
            case {'method': 'scale_align', 'aligner': aligner, 'scale_factors': scale_factors}:  # BS=1下可用。
                # 好处：1）尺寸变化范围任意大，2）不丢失物体；劣势：无法保证ratio不变。
                self.scale_crop = au.MultiScale(scale_factors, aligner, align_corner=False, PIL_mode=kPILMode)
            case {'method': 'scale_long_pad', 'aligner': aligner, 'scale_factors': scale_factors}:  # BS=1下可用。
                # 好处：1）尺寸变化范围任意大，2）不丢失物体，3）不改变ratio；劣势：需要pad。
                pass
            case {'method': 'fix_short', 'crop_size': crop_size}:
                self.scale_crop = PackCompose([
                    lambda img, lb: au.scale_img_label(crop_size / min(*img.shape[:2]),
                                                       img, lb,
                                                       align_corner=False, PIL_mode=kPILMode),
                    au.RandCrop(crop_size)
                ])
            case _:
                raise ValueError(f"不支持的{scale_crop_method=}。")

        self.rand_mirror = au.RandMirror()

        self.to_tensor = ToTensor()
        self.normalize = Normalize(mean, std)

    # @classmethod
    # def train(cls, dataset: Dataset,
    #           scale_crop_method: Any=None,
    #           mean: tuple[int, int, int]=(0.48145466, 0.4578275, 0.40821073),
    #           std: tuple[int, int, int]=(0.26862954, 0.26130258, 0.27577711),
    #           lb_scale_factor: float | None=None):
    #     return cls(dataset=dataset,
    #                is_rand_mirror=True, is_color_jitter=True,
    #                scale_crop_method=scale_crop_method,
    #                mean=mean, std=std,
    #                lb_scale_factor=lb_scale_factor)

    @property
    def inv2PIL(self) -> Compose:
        mean, std = self.mean, self.std
        return Compose([
            Normalize(
                mean=[-mean[0] / std[0], -mean[1] / std[1], -mean[2] / std[2]],
                std=[1 / std[0], 1 / std[1], 1 / std[2]]
            ),
            ToPILImage('RGB')
        ])

    @classmethod
    def test(cls, dataset: Dataset,
             mean: tuple[int, int, int]=(0.48145466, 0.4578275, 0.40821073),
             std: tuple[int, int, int]=(0.26862954, 0.26130258, 0.27577711),
             ):
        return cls(dataset=dataset,
                   is_rand_mirror=False, is_color_jitter=False,
                   scale_crop_method=None,
                   mean=mean, std=std,
                   lb_scale_factor=None, ol_cls_lb=False)

    def get_item(self, index) -> Dict:
        inp = self.dataset[index]
        img_id, img, lb, cls_lb = inp.img_id, inp.img, inp.lb, inp.cls_lb

        out = Dict()

        # * 色彩抖动。
        if self.is_color_jitter:
            img = self.rand_color_jitter(img)
        # * 缩放。
        img, lb = self.scale_crop(img, lb)
        # * 随机镜像。
        if self.is_rand_mirror:
            img, lb = self.rand_mirror(img, lb)
        # * 获取下采样后lb。
        if self.lb_scale_factor is not None:
            # 训练时，缩放裁剪后，图片尺寸是16k或16k+1，缩放后应当为k和k+1，ceil满足要求。
            scaled_lb = au.PIL2arr(au.arr2PIL(lb).resize((ceil(lb.shape[1] / self.lb_scale_factor),
                                                          ceil(lb.shape[0] / self.lb_scale_factor)),
                                                         resample=Image.NEAREST))
            out.scaled_lb = scaled_lb.astype(np.long)
        # * 获取增强后标签中类别。
        if self.ol_cls_lb:
            out.ol_cls_lb = lb2cls_lb(lb).astype(np.long)  # TODO 令该函数所有数据集通用。

        # * 测试增强。
        img = self.to_tensor(BGR2RGB(img).copy())
        img = self.normalize(img)

        # * 返回结果。
        out.img_id, out.img, out.lb, out.cls_lb = img_id, img, lb.astype(np.long), cls_lb.astype(np.long)
        return out

    def __len__(self):
        return len(self.dataset)
