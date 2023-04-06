#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Xiaobo Yang
@Contact : hal_42@zju.edu.cn
@Time    : 2023/3/29 16:14
@File    : cfg.py
@Software: PyCharm
@Desc    : 没有CRF情况下，寻找最优aff配置。
"""
from alchemy_cat.py_tools import Cfg2Tune, Param2Tune

cfg = config = Cfg2Tune('configs/patterns/seg_metrics/cls_m_IoU,pra.py',
                        cfgs_update_at_parser=('configs/aff_voc/base.py',
                                               'configs/patterns/crf/crf_eval.py',
                                               'configs/patterns/crf/clip_es_crf,no_pp.py'))

cfg.rslt_dir = ...

# * 覆盖原配置，使其适合调参（不改变算法）。
cfg.aff.ori_cam_dir = 'experiment/clip_cam/gcam,l1_only,小样/32,调随机/ini,aug/rand_seed=20/infer/final/cam'

cfg.solver.viz_cam = False  # noqa
cfg.solver.viz_score = False

# * 修改算法参数。
cfg.aff.ini.att2aff_cfg.method.n_iter = Param2Tune([1, 3])

cfg.aff.ini.aff_cfg.n_iters = Param2Tune([1, 2])
cfg.aff.ini.aff_at = Param2Tune(['cam', 'score'])
